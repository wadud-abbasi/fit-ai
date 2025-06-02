#!/usr/bin/env python
import os
import json
import logging
import openai
import time
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class ConversationAnalyzer:
    """
    Analyzes FIT kit reminder conversations to extract relevant data
    
    Uses OpenAI's GPT-4o to analyze conversations and extract structured data
    about the FIT kit status, patient information updates, and follow-up needs.
    """
    
    def __init__(self, api_key=None):
        """
        Initialize the conversation analyzer
        
        Args:
            api_key: OpenAI API key (optional, falls back to environment)
        """
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        openai.api_key = self.api_key
    
    def generate_conversation_summary(self, conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Generate a structured summary of the FIT kit conversation
        
        Args:
            conversation_history: List of messages in the conversation
            
        Returns:
            Dictionary with extracted information
        """
        # Prepare the prompt for GPT
        system_prompt = """
        You are a healthcare data analyst specialized in extracting information from patient conversations about FIT kits 
        (Fecal Immunochemical Tests) for colorectal cancer screening. 
        
        Analyze the conversation between a healthcare assistant and a patient, and extract the following information:
        
        1. kit_completed (boolean): Whether the patient has completed the FIT kit
        2. needs_new_kit (boolean): Whether the patient needs a new kit sent to them
        3. address_confirmed (boolean): Whether the patient confirmed their mailing address is correct
        4. callback_scheduled (boolean): Whether a callback was scheduled
        5. callback_datetime (string in ISO format, or null): When the callback is scheduled, if applicable
        6. address (string or null): Updated address if the patient provided one
        7. language (string or null): Patient's preferred language if mentioned
        8. comments (string): A brief summary of the key points of the conversation
        9. patient_reached (boolean): Always true for completed conversations
        
        Format the response as a JSON object with exactly these fields.
        Use null for unknown values, true/false for booleans.
        """
        
        # Prepare conversation text for analysis
        conversation_text = ""
        for message in conversation_history:
            if message["role"] != "system":  # Skip system prompts
                conversation_text += f"{message['role'].upper()}: {message['content']}\n\n"
        
        # Create messages for GPT
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Please analyze this conversation about a FIT kit reminder:\n\n{conversation_text}"}
        ]
        
        # Call GPT-4o
        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            # Parse the JSON response
            summary_text = response.choices[0].message.content
            summary = json.loads(summary_text)
            
            # Log the summary
            logger.info(f"Generated conversation summary: {summary}")
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating conversation summary: {str(e)}")
            # Return default empty summary
            return {
                "kit_completed": None,
                "needs_new_kit": None,
                "address_confirmed": None,
                "callback_scheduled": None,
                "callback_datetime": None,
                "address": None,
                "language": None,
                "comments": f"Error analyzing conversation: {str(e)}",
                "patient_reached": True
            }
    
    def extract_kit_status(self, summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract FIT kit status fields from conversation summary
        
        Args:
            summary: Conversation summary
            
        Returns:
            Dictionary with FIT kit status fields
        """
        # Extract relevant fields for public database
        kit_status = {}
        
        for field in ['kit_completed', 'needs_new_kit', 'address_confirmed', 
                     'callback_scheduled', 'callback_datetime', 'patient_reached']:
            if field in summary and summary[field] is not None:
                kit_status[field] = summary[field]
        
        # Add comments as a list item
        if 'comments' in summary and summary['comments']:
            kit_status['comments'] = summary['comments']
        
        return kit_status
    
    def extract_patient_updates(self, summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract patient PHI updates from conversation summary
        
        Args:
            summary: Conversation summary
            
        Returns:
            Dictionary with patient PHI fields to update
        """
        # Extract relevant fields for private database
        patient_updates = {}
        
        # Address updates
        if 'address' in summary and summary['address']:
            patient_updates['address'] = summary['address']
        
        # Language preference
        if 'language' in summary and summary['language']:
            patient_updates['language'] = summary['language']
        
        return patient_updates


# Singleton instance for use throughout the application
def get_conversation_analyzer():
    """Get conversation analyzer singleton"""
    if not hasattr(get_conversation_analyzer, 'instance'):
        get_conversation_analyzer.instance = ConversationAnalyzer()
    return get_conversation_analyzer.instance
