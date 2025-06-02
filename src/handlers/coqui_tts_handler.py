"""
Coqui TTS Handler for Text-to-Speech
"""
import os
import io
import base64
import time
import tempfile
import threading
from pathlib import Path
import torch
import numpy as np
from TTS.api import TTS
from ..utils.audit_logger import AuditLogger

class CoquiTTSHandler:
    """
    Handles text-to-speech conversion using Coqui TTS
    """
    
    def __init__(self):
        """Initialize Coqui TTS handler with voice model"""
        self.logger = AuditLogger()
        self.tts = None
        self.model_name = "tts_models/en/vctk/vits"  # Good quality multilingual model
        self.speaker = "p270"  # Default speaker voice (professional female voice)
        self.sample_rate = 22050  # Default for most Coqui models
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.is_initialized = False
        self.initialization_thread = None
        
        # Start initialization in a separate thread to avoid blocking
        self._initialize_async()
        
    def _initialize_async(self):
        """Initialize TTS model in a separate thread"""
        self.initialization_thread = threading.Thread(target=self._initialize_model)
        self.initialization_thread.daemon = True
        self.initialization_thread.start()
        
    def _initialize_model(self):
        """Load the TTS model"""
        try:
            self.logger.log_event("Loading Coqui TTS model...", "system")
            self.tts = TTS(model_name=self.model_name, progress_bar=False).to(self.device)
            self.is_initialized = True
            self.logger.log_event(f"Coqui TTS model loaded successfully on {self.device}", "system")
        except Exception as e:
            self.logger.log_event(f"Error loading Coqui TTS model: {str(e)}", "error")
            
    def wait_for_initialization(self, timeout=60):
        """
        Wait for model initialization to complete
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            bool: True if initialization completed, False if timed out
        """
        if self.is_initialized:
            return True
            
        start_time = time.time()
        while not self.is_initialized and (time.time() - start_time) < timeout:
            time.sleep(0.5)
            
        return self.is_initialized
        
    def set_voice(self, speaker="p270"):
        """
        Set the TTS voice/speaker
        
        Args:
            speaker: Speaker ID for VCTK model
        """
        self.speaker = speaker
        
    def text_to_speech(self, text, output_format="base64"):
        """
        Convert text to speech using Coqui TTS
        
        Args:
            text: Text to convert to speech
            output_format: Output format, "base64" or "wav_file"
            
        Returns:
            str or bytes: Base64-encoded audio or path to WAV file
        """
        if not self.wait_for_initialization():
            self.logger.log_event("TTS model initialization timed out", "error")
            return None
            
        if not text or not text.strip():
            return None
            
        try:
            # Generate speech with the selected voice
            wav = self.tts.tts(
                text=text.strip(),
                speaker=self.speaker,
                language="en"
            )
            
            if output_format == "base64":
                # Convert numpy array to WAV bytes
                byte_io = io.BytesIO()
                
                import wave
                import struct
                
                # Normalize and convert to int16
                wav_norm = (wav * 32767).astype(np.int16)
                
                with wave.open(byte_io, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)  # 2 bytes for int16
                    wf.setframerate(self.sample_rate)
                    wf.writeframes(wav_norm.tobytes())
                
                # Get bytes and encode as base64
                audio_bytes = byte_io.getvalue()
                base64_audio = base64.b64encode(audio_bytes).decode('utf-8')
                return base64_audio
                
            elif output_format == "wav_file":
                # Save to temporary file
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                    tmp_path = tmp_file.name
                
                # Save audio to file
                wav_norm = (wav * 32767).astype(np.int16)
                
                import wave
                with wave.open(tmp_path, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)  # 2 bytes for int16
                    wf.setframerate(self.sample_rate)
                    wf.writeframes(wav_norm.tobytes())
                
                return tmp_path
                
        except Exception as e:
            self.logger.log_event(f"Error generating speech: {str(e)}", "error")
            return None
            
    def list_available_speakers(self):
        """
        List all available speakers for the loaded model
        
        Returns:
            list: List of available speaker IDs
        """
        if not self.wait_for_initialization():
            return []
            
        try:
            speakers = self.tts.speakers
            return speakers if speakers else []
        except Exception as e:
            self.logger.log_event(f"Error listing speakers: {str(e)}", "error")
            return []
