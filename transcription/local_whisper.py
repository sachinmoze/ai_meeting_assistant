"""
Local Whisper model integration for offline speech-to-text transcription.
Uses faster-whisper, an optimized implementation of OpenAI's Whisper model.
"""

import time
import os
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Union
from pathlib import Path

from utils.logger import get_logger
from utils.config import config_manager

logger = get_logger("local_whisper")

# Flag to track whether faster-whisper is available
FASTER_WHISPER_AVAILABLE = False

# Try to import faster-whisper, but don't crash if it's not available
try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except (ImportError, OSError) as e:
    logger.warning(f"Could not import faster-whisper: {e}")
    logger.warning("Local Whisper model will not be available. Using OpenAI API only.")
    WhisperModel = None


class LocalWhisperTranscriber:
    """Transcribe audio using a local Whisper model."""
    
    def __init__(self):
        """Initialize the local Whisper transcriber."""
        self.config = config_manager.config.ai
        self.model_size = self.config.local_whisper_model
        self.model = None
        self.sample_rate = 16000  # Whisper expects 16kHz audio
        self.available = FASTER_WHISPER_AVAILABLE
        
    def _load_model(self):
        """Load the Whisper model if not already loaded."""
        if not self.available:
            raise RuntimeError("faster-whisper is not available. Cannot load local model.")
            
        if self.model is None:
            try:
                logger.info(f"Loading local Whisper model: {self.model_size}")
                start_time = time.time()
                
                # Check if CUDA is available and use it if possible
                compute_type = "float16"  # Default for better performance on GPU
                device = "cuda"
                
                try:
                    # Try to load on GPU first
                    self.model = WhisperModel(self.model_size, device=device, compute_type=compute_type)
                    logger.info("Model loaded on GPU")
                except Exception as e:
                    # Fall back to CPU if GPU loading fails
                    logger.warning(f"Failed to load model on GPU: {e}")
                    logger.info("Loading model on CPU")
                    self.model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
                
                elapsed = time.time() - start_time
                logger.info(f"Model loaded in {elapsed:.2f} seconds")
                
            except Exception as e:
                logger.error(f"Error loading Whisper model: {e}")
                raise RuntimeError(f"Failed to load Whisper model: {e}")
    
    def transcribe_file(self, audio_file: Union[str, Path]) -> Dict[str, Any]:
        """Transcribe an audio file using local Whisper model.
        
        Args:
            audio_file: Path to the audio file to transcribe.
            
        Returns:
            Dictionary containing transcription and metadata.
        """
        if not self.available:
            return {
                "text": "Local Whisper model is not available. Please use the OpenAI API instead.",
                "segments": [],
                "language": "en",
                "duration": 0,
                "processing_time": 0,
                "error": "Local model not available"
            }
            
        try:
            self._load_model()
            
            logger.info(f"Transcribing file: {audio_file}")
            start_time = time.time()
            
            # Run inference
            segments, info = self.model.transcribe(
                str(audio_file),
                language="en",  # Can be set to None for auto-detection
                vad_filter=True,  # Voice activity detection to filter out non-speech
                word_timestamps=True  # Get timestamps for individual words
            )
            
            # Convert segments to list and extract text
            segment_list = []
            full_text = ""
            
            for segment in segments:
                segment_dict = {
                    "id": len(segment_list),
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text,
                    "words": [{"word": word.word, "start": word.start, "end": word.end} 
                             for word in segment.words]
                }
                segment_list.append(segment_dict)
                full_text += segment.text + " "
            
            elapsed = time.time() - start_time
            logger.info(f"Transcription completed in {elapsed:.2f} seconds")
            
            return {
                "text": full_text.strip(),
                "segments": segment_list,
                "language": info.language,
                "duration": info.duration,
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
    
    def transcribe_chunk(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """Transcribe an audio chunk using local Whisper model.
        
        Args:
            audio_data: Audio data as numpy array.
            
        Returns:
            Dictionary containing transcription and metadata.
        """
        if not self.available:
            return {
                "text": "",
                "segments": [],
                "language": "en",
                "duration": 0,
                "processing_time": 0,
                "error": "Local model not available"
            }
            
        try:
            self._load_model()
            
            start_time = time.time()
            
            # Run inference directly on the numpy array
            segments, info = self.model.transcribe(
                audio_data,
                language="en",
                vad_filter=True,
                word_timestamps=True
            )
            
            # Convert segments to list and extract text
            segment_list = []
            full_text = ""
            
            for segment in segments:
                segment_dict = {
                    "id": len(segment_list),
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text,
                    "words": [{"word": word.word, "start": word.start, "end": word.end} 
                             for word in segment.words]
                }
                segment_list.append(segment_dict)
                full_text += segment.text + " "
            
            elapsed = time.time() - start_time
            logger.debug(f"Chunk transcription completed in {elapsed:.2f} seconds")
            
            return {
                "text": full_text.strip(),
                "segments": segment_list,
                "language": info.language,
                "duration": info.duration if hasattr(info, 'duration') else 0,
                "processing_time": elapsed
            }
            
        except Exception as e:
            logger.error(f"Error transcribing audio chunk: {e}")
            return {
                "text": "",
                "segments": [],
                "language": "en",
                "duration": 0,
                "processing_time": 0
            }
    
    def unload_model(self):
        """Unload the model to free up memory."""
        if self.model is not None:
            logger.info("Unloading Whisper model")
            self.model = None