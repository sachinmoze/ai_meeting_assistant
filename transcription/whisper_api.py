"""
OpenAI Whisper API integration for speech-to-text transcription.
Handles real-time and batch transcription of audio data.
"""

import os
import time
import asyncio
import tempfile
import wave
import io
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Union
from pathlib import Path
import openai
from PyQt5.QtWidgets import QMessageBox

from utils.logger import get_logger
from utils.config import config_manager

logger = get_logger("whisper_api")

class WhisperTranscriber:
    """Transcribe audio using OpenAI's Whisper API."""
    
    def __init__(self):
        """Initialize the Whisper transcriber."""
        self.config = config_manager.config.ai
        if not self.config.openai_api_key:
            logger.error("OpenAI API key is missing. Please set it in the settings.")
            QMessageBox.warning(
                None, 
                "API Key Missing", 
                "OpenAI API key is missing. Please go to Settings > AI Models to enter your API key."
            )
        self.client = openai.OpenAI(api_key=self.config.openai_api_key)
        self.sample_rate = 16000  # Whisper expects 16kHz audio
    
    def transcribe_file(self, audio_file: Union[str, Path]) -> Dict[str, Any]:
        """Transcribe an audio file using Whisper API.
        
        Args:
            audio_file: Path to the audio file to transcribe.
            
        Returns:
            Dictionary containing transcription and metadata.
        """
        try:
            logger.info(f"Transcribing file: {audio_file}")
            
            with open(audio_file, "rb") as file:
                start_time = time.time()
                
                # Call Whisper API
                transcription = self.client.audio.transcriptions.create(
                    file=file,
                    model="whisper-1",
                    response_format="verbose_json",
                    timestamp_granularities=["segment", "word"]
                )
                
                elapsed = time.time() - start_time
                logger.info(f"Transcription completed in {elapsed:.2f} seconds")
                
                return {
                    "text": transcription.text,
                    "segments": transcription.segments,
                    "language": transcription.language,
                    "duration": transcription.duration,
                    "processing_time": elapsed
                }
                
        except Exception as e:
            logger.error(f"Error transcribing audio file: {e}")
            return {
                "text": f"Error transcribing audio: {str(e)}",
                "segments": [],
                "language": "en",
                "duration": 0,
                "processing_time": 0
            }
    
    async def transcribe_chunk(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """Transcribe an audio chunk using Whisper API.
        
        Args:
            audio_data: Audio data as numpy array.
            
        Returns:
            Dictionary containing transcription and metadata.
        """
        try:
            # Convert numpy array to WAV file in memory
            with io.BytesIO() as wav_io:
                with wave.open(wav_io, 'wb') as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)  # 16-bit
                    wav_file.setframerate(self.sample_rate)
                    wav_file.writeframes(audio_data.tobytes())
                
                # Get the WAV data
                wav_io.seek(0)
                wav_data = wav_io.read()
            
            # Create a temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(wav_data)
                temp_path = temp_file.name
            
            try:
                # Call the API
                start_time = time.time()
                with open(temp_path, "rb") as file:
                    # Run the API call in an executor to avoid blocking
                    loop = asyncio.get_event_loop()
                    transcription = await loop.run_in_executor(
                        None,
                        lambda: self.client.audio.transcriptions.create(
                            file=file,
                            model="whisper-1",
                            response_format="verbose_json"
                        )
                    )
                
                elapsed = time.time() - start_time
                logger.debug(f"Chunk transcription completed in {elapsed:.2f} seconds")
                
                return {
                    "text": transcription.text,
                    "segments": transcription.segments,
                    "language": transcription.language,
                    "duration": transcription.duration,
                    "processing_time": elapsed
                }
                
            finally:
                # Remove temporary file
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
                
        except Exception as e:
            logger.error(f"Error transcribing audio chunk: {e}")
            return {
                "text": "",
                "segments": [],
                "language": "en",
                "duration": 0,
                "processing_time": 0
            }