"""
OpenAI Whisper v3 Handler for Speech-to-Text
"""
import os
import time
import io
import base64
import threading
from queue import Queue
import openai
import numpy as np
import librosa
from ..utils.audit_logger import AuditLogger

class WhisperHandler:
    """
    Handles real-time speech transcription using OpenAI Whisper v3
    """
    
    def __init__(self):
        """Initialize the WhisperHandler with OpenAI API key"""
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        openai.api_key = self.api_key
        self.logger = AuditLogger()
        
        # Audio processing parameters
        self.sample_rate = 16000  # Whisper expects 16kHz audio
        self.queue = Queue()
        self.audio_buffer = []
        self.is_processing = False
        self.processing_thread = None
        self.last_transcript = ""
        self.full_transcript = ""
        self.transcript_callback = None
        
        # Interim transcription parameters
        self.buffer_duration_sec = 3.0  # Process chunks every 3 seconds
        self.buffer_size = int(self.sample_rate * self.buffer_duration_sec)
        self.min_audio_length = self.sample_rate // 2  # At least 0.5 seconds to process
        
    def start_transcription(self, transcript_callback=None):
        """Start the transcription process with optional callback"""
        self.transcript_callback = transcript_callback
        self.is_processing = True
        self.audio_buffer = []
        self.last_transcript = ""
        self.full_transcript = ""
        
        # Start processing thread
        self.processing_thread = threading.Thread(target=self._process_audio_queue)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        self.logger.log_event("Whisper transcription started", "system")
        return True
        
    def stop_transcription(self):
        """Stop the transcription process"""
        if self.is_processing:
            self.is_processing = False
            
            # Process any remaining audio
            if len(self.audio_buffer) >= self.min_audio_length:
                self._transcribe_buffer()
                
            if self.processing_thread:
                self.processing_thread.join(timeout=5.0)
                
            self.logger.log_event("Whisper transcription stopped", "system")
            
        return {"transcript": self.full_transcript}
        
    def add_audio_data(self, audio_data):
        """
        Add audio data to the buffer for transcription
        
        Args:
            audio_data: Base64-encoded audio data from Twilio
        """
        if not self.is_processing:
            return
            
        try:
            # Decode base64 audio
            raw_audio = base64.b64decode(audio_data)
            
            # Convert to numpy array - Twilio sends 8kHz mulaw, need to convert
            audio_array = np.frombuffer(raw_audio, dtype=np.int16)
            
            # Resample to 16kHz if needed - simplified for this example
            # In a real implementation, use librosa.resample properly
            audio_resampled = librosa.resample(
                audio_array.astype(np.float32) / 32768.0,  # Normalize to [-1, 1]
                orig_sr=8000,  # Twilio's mulaw format is 8kHz
                target_sr=self.sample_rate
            )
            
            # Add to buffer
            self.audio_buffer.extend(audio_resampled)
            
            # Process if buffer is long enough
            if len(self.audio_buffer) >= self.buffer_size:
                self.queue.put(self.audio_buffer[:self.buffer_size])
                self.audio_buffer = self.audio_buffer[self.buffer_size:]
                
        except Exception as e:
            self.logger.log_event(f"Error processing audio data: {str(e)}", "error")
            
    def _process_audio_queue(self):
        """Process audio queue in a separate thread"""
        while self.is_processing:
            try:
                if not self.queue.empty():
                    audio_data = self.queue.get()
                    self._transcribe_buffer(audio_data)
                    self.queue.task_done()
                else:
                    time.sleep(0.1)  # Sleep briefly to prevent CPU spinning
            except Exception as e:
                self.logger.log_event(f"Error in audio processing thread: {str(e)}", "error")
                
    def _transcribe_buffer(self, audio_data=None):
        """
        Transcribe the current audio buffer using Whisper API
        
        Args:
            audio_data: Optional audio data to transcribe, uses self.audio_buffer if None
        """
        buffer_to_process = audio_data if audio_data is not None else self.audio_buffer
        
        if len(buffer_to_process) < self.min_audio_length:
            return
            
        try:
            # Convert float array to int16 for saving
            int16_data = np.array(buffer_to_process * 32768, dtype=np.int16)
            
            # Create an in-memory file-like object
            byte_io = io.BytesIO()
            import wave
            
            # Save as WAV
            with wave.open(byte_io, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 2 bytes for int16
                wf.setframerate(self.sample_rate)
                wf.writeframes(int16_data.tobytes())
                
            # Reset the file pointer to the beginning
            byte_io.seek(0)
            
            # Call OpenAI Whisper API
            response = openai.audio.transcriptions.create(
                model="whisper-1",  # Will use the latest version available
                file=byte_io,
                response_format="text",
                language="en"
            )
            
            # Get transcript
            transcript = response if isinstance(response, str) else response.text
            
            # Update transcripts
            if transcript and transcript.strip():
                self.last_transcript = transcript.strip()
                self.full_transcript += " " + self.last_transcript
                self.full_transcript = self.full_transcript.strip()
                
                # Call the callback if provided
                if self.transcript_callback:
                    self.transcript_callback(self.last_transcript, is_final=True)
                    
            # Clear buffer if this was processing the instance buffer
            if audio_data is None:
                self.audio_buffer = []
                
        except Exception as e:
            self.logger.log_event(f"Error transcribing audio: {str(e)}", "error")
            
    def get_transcription(self):
        """Get the current complete transcription"""
        return self.full_transcript
