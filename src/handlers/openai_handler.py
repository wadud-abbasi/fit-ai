import os
import logging
import json
import openai
import asyncio
import time
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class OpenAIHandler:
    """
    Handles OpenAI GPT-4o for conversation and TTS for speech generation
    """
    
    def __init__(self, api_key: str, fallback_model: str = "gpt-3.5-turbo"):
        """
        Initialize the OpenAI handler
        
        Args:
            api_key: OpenAI API key
            fallback_model: Model to use if GPT-4o is unavailable
        """
        self.api_key = api_key
        openai.api_key = api_key
        self.primary_model = "gpt-4o"
        self.fallback_model = fallback_model
        self.tts_model = "tts-1"
        self.tts_voice = "nova"  # Options: alloy, echo, fable, onyx, nova, shimmer
        
    async def generate_response(self, 
                         messages: List[Dict[str, str]], 
                         max_tokens: int = 150, 
                         temperature: float = 0.7) -> Optional[str]:
        """
        Generate a conversational response using GPT-4o
        
        Args:
            messages: List of message objects with role and content
            max_tokens: Maximum tokens to generate
            temperature: Randomness of the response (0-1)
            
        Returns:
            Generated response text or None if failed
        """
        try:
            response = await openai.chat.completions.create(
                model=self.primary_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=False
            )
            
            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content.strip()
            return None
            
        except Exception as e:
            logger.error(f"Error generating GPT response: {str(e)}")
            
            # Try with fallback model
            try:
                logger.info(f"Attempting with fallback model {self.fallback_model}")
                response = await openai.chat.completions.create(
                    model=self.fallback_model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=False
                )
                
                if response.choices and len(response.choices) > 0:
                    return response.choices[0].message.content.strip()
                return None
                
            except Exception as fallback_error:
                logger.error(f"Error with fallback model: {str(fallback_error)}")
                return None
    
    async def generate_speech(self, text: str) -> Optional[bytes]:
        """
        Generate speech audio from text using OpenAI TTS API
        
        Args:
            text: Text to convert to speech
            
        Returns:
            Audio data as bytes or None if failed
        """
        if not text:
            logger.warning("Empty text provided for speech generation")
            return None
        
        try:
            response = await openai.audio.speech.create(
                model=self.tts_model,
                voice=self.tts_voice,
                input=text
            )
            
            # Get the audio data
            audio_data = response.content
            
            return audio_data
            
        except Exception as e:
            logger.error(f"Error generating speech: {str(e)}")
            return None
    
    async def process_conversation(self, 
                            session_data: Dict[str, Any],
                            user_input: str) -> Dict[str, Any]:
        """
        Process a complete conversation turn - generate response and speech
        
        Args:
            session_data: Dictionary with call session information including conversation history
            user_input: Latest user input to respond to
            
        Returns:
            Dict with response text, audio data, and updated session
        """
        result = {
            "success": False,
            "response_text": None,
            "audio_data": None,
            "session_data": session_data
        }
        
        # Add user input to conversation history
        if "conversation_history" not in session_data:
            session_data["conversation_history"] = []
            
            # Add system prompt if not present
            if not any(msg.get("role") == "system" for msg in session_data["conversation_history"]):
                reminder_type = session_data.get("reminder_type", "general")
                
                if reminder_type == "medication":
                    system_prompt = """You are a friendly healthcare assistant calling to remind a patient about their medication. 
                    Be conversational, empathetic, and brief. If they've taken their medication, acknowledge and thank them. 
                    If not, gently remind them of its importance. Answer basic questions, but defer medical questions to their doctor. 
                    Wrap up the call politely once you've confirmed whether they've taken their medication."""
                elif reminder_type == "fit_kit":
                    system_prompt = """You are a friendly healthcare assistant calling to remind a patient about completing their FIT kit 
                    (Fecal Immunochemical Test) for colorectal cancer screening. Be conversational, empathetic, and brief. 
                    If they've completed and returned the kit, acknowledge and thank them. If not, explain its importance and offer to 
                    answer questions about the process. Wrap up the call politely once you've confirmed whether they've completed the kit."""
                else:
                    system_prompt = """You are a friendly healthcare assistant making a follow-up call. 
                    Be conversational, empathetic, and brief. Answer basic questions, but defer medical questions to their doctor."""
                    
                session_data["conversation_history"].append({"role": "system", "content": system_prompt})
        
        # Add user message
        session_data["conversation_history"].append({"role": "user", "content": user_input})
        
        # Generate response
        start_time = time.time()
        response_text = await self.generate_response(session_data["conversation_history"])
        logger.info(f"Response generation took {time.time() - start_time:.2f} seconds")
        
        if not response_text:
            logger.error("Failed to generate response")
            return result
        
        # Add assistant response to history
        session_data["conversation_history"].append({"role": "assistant", "content": response_text})
        
        # Generate speech
        start_time = time.time()
        audio_data = await self.generate_speech(response_text)
        logger.info(f"Speech generation took {time.time() - start_time:.2f} seconds")
        
        if not audio_data:
            logger.error("Failed to generate speech")
            return result
        
        # Update result
        result["success"] = True
        result["response_text"] = response_text
        result["audio_data"] = audio_data
        result["session_data"] = session_data
        
        return result


class ConversationManager:
    """
    Manages conversations for multiple calls
    """
    
    def __init__(self, api_key: str):
        """
        Initialize the conversation manager
        
        Args:
            api_key: OpenAI API key
        """
        self.api_key = api_key
        self.openai_handler = OpenAIHandler(api_key)
        self.sessions = {}  # call_sid -> session data
        
    def create_session(self, call_sid: str, phone_number: str, reminder_type: str = "medication") -> bool:
        """
        Create a new conversation session
        
        Args:
            call_sid: Twilio call SID
            phone_number: Patient phone number
            reminder_type: Type of reminder ('medication' or 'fit_kit')
            
        Returns:
            True if session created successfully
        """
        if call_sid in self.sessions:
            logger.warning(f"Session already exists for call {call_sid}")
            return True
        
        # Create new session
        self.sessions[call_sid] = {
            "call_sid": call_sid,
            "phone_number": phone_number,
            "reminder_type": reminder_type,
            "conversation_history": [],
            "created_at": time.time()
        }
        
        # Add system prompt
        if reminder_type == "medication":
            system_prompt = """You are a friendly healthcare assistant calling to remind a patient about their medication. 
            Be conversational, empathetic, and brief. If they've taken their medication, acknowledge and thank them. 
            If not, gently remind them of its importance. Answer basic questions, but defer medical questions to their doctor. 
            Wrap up the call politely once you've confirmed whether they've taken their medication."""
        elif reminder_type == "fit_kit":
            system_prompt = """You are a friendly healthcare assistant calling to remind a patient about completing their FIT kit 
            (Fecal Immunochemical Test) for colorectal cancer screening. Be conversational, empathetic, and brief. 
            If they've completed and returned the kit, acknowledge and thank them. If not, explain its importance and offer to 
            answer questions about the process. Wrap up the call politely once you've confirmed whether they've completed the kit."""
        else:
            system_prompt = """You are a friendly healthcare assistant making a follow-up call. 
            Be conversational, empathetic, and brief. Answer basic questions, but defer medical questions to their doctor."""
            
        self.sessions[call_sid]["conversation_history"].append({"role": "system", "content": system_prompt})
        
        return True
    
    async def generate_initial_greeting(self, call_sid: str) -> Optional[Dict[str, Any]]:
        """
        Generate an initial greeting for a call
        
        Args:
            call_sid: Twilio call SID
            
        Returns:
            Dict with response text and audio data, or None if failed
        """
        if call_sid not in self.sessions:
            logger.warning(f"No session found for call {call_sid}")
            return None
        
        session = self.sessions[call_sid]
        reminder_type = session["reminder_type"]
        
        # Create prompt for initial greeting
        if reminder_type == "medication":
            prompt = "Generate a brief, friendly greeting for a medication reminder call. Introduce yourself as a healthcare assistant calling to check if they've taken their medication today."
        elif reminder_type == "fit_kit":
            prompt = "Generate a brief, friendly greeting for a call about a FIT kit (colorectal cancer screening). Introduce yourself as a healthcare assistant calling to check if they've completed and returned their kit."
        else:
            prompt = "Generate a brief, friendly greeting for a healthcare follow-up call. Introduce yourself as a healthcare assistant."
        
        # Add the prompt to the conversation history
        session["conversation_history"].append({"role": "user", "content": prompt})
        
        # Generate response and speech
        result = await self.openai_handler.process_conversation(session, prompt)
        
        if not result["success"]:
            # Use fallback greeting
            fallback_greeting = "Hello, this is your healthcare assistant calling with a reminder. How are you doing today?"
            session["conversation_history"].append({"role": "assistant", "content": fallback_greeting})
            
            # Try to generate speech for fallback greeting
            audio_data = await self.openai_handler.generate_speech(fallback_greeting)
            
            return {
                "text": fallback_greeting,
                "audio": audio_data,
                "success": audio_data is not None
            }
        
        return {
            "text": result["response_text"],
            "audio": result["audio_data"],
            "success": True
        }
    
    async def process_user_input(self, call_sid: str, user_input: str) -> Optional[Dict[str, Any]]:
        """
        Process user input and generate a response
        
        Args:
            call_sid: Twilio call SID
            user_input: User's speech transcription
            
        Returns:
            Dict with response text and audio data, or None if failed
        """
        if call_sid not in self.sessions:
            logger.warning(f"No session found for call {call_sid}")
            return None
        
        # Get session
        session = self.sessions[call_sid]
        
        # Process conversation
        result = await self.openai_handler.process_conversation(session, user_input)
        
        if not result["success"]:
            return None
        
        # Update session
        self.sessions[call_sid] = result["session_data"]
        
        return {
            "text": result["response_text"],
            "audio": result["audio_data"],
            "success": True
        }
    
    def end_session(self, call_sid: str) -> bool:
        """
        End a conversation session
        
        Args:
            call_sid: Twilio call SID
            
        Returns:
            True if session ended successfully
        """
        if call_sid not in self.sessions:
            logger.warning(f"No session found to end for call {call_sid}")
            return False
        
        # Get final conversation history for logging/storage
        final_conversation = self.sessions[call_sid]["conversation_history"]
        
        # Remove session
        del self.sessions[call_sid]
        
        return True
