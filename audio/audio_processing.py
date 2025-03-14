"""
Audio preprocessing functionality.
Processes audio data to improve transcription quality.
"""

import numpy as np
from typing import Optional, Tuple

from utils.logger import get_logger

logger = get_logger("audio_processing")

class AudioProcessor:
    """Process audio data to improve transcription quality."""
    
    def __init__(self, sample_rate: int = 16000):
        """Initialize the audio processor.
        
        Args:
            sample_rate: The sample rate of the audio data.
        """
        self.sample_rate = sample_rate
    
    def preprocess(self, audio_data: np.ndarray) -> np.ndarray:
        """Preprocess audio data for better transcription results.
        
        This method applies several audio processing techniques to improve
        speech recognition quality:
        1. Normalization
        2. Noise reduction
        3. Silence trimming
        
        Args:
            audio_data: Raw audio data as numpy array.
            
        Returns:
            Processed audio data.
        """
        try:
            # Ensure the audio data is in the right format
            audio_data = audio_data.astype(np.float32)
            
            # Normalize audio (scale to range -1 to 1)
            audio_data = self._normalize(audio_data)
            
            # Reduce background noise
            audio_data = self._reduce_noise(audio_data)
            
            # Trim silence from the beginning and end
            audio_data, _ = self._trim_silence(audio_data)
            
            return audio_data
            
        except Exception as e:
            logger.error(f"Error preprocessing audio: {e}")
            # Return original data if processing fails
            return audio_data
    
    def _normalize(self, audio_data: np.ndarray) -> np.ndarray:
        """Normalize audio to the range [-1, 1].
        
        Args:
            audio_data: Audio data as numpy array.
            
        Returns:
            Normalized audio data.
        """
        # Avoid division by zero
        if np.max(np.abs(audio_data)) > 0:
            return audio_data / np.max(np.abs(audio_data))
        return audio_data
    
    def _reduce_noise(self, audio_data: np.ndarray) -> np.ndarray:
        """Apply simple noise reduction.
        
        Uses a basic noise gate to reduce background noise.
        
        Args:
            audio_data: Audio data as numpy array.
            
        Returns:
            Noise-reduced audio data.
        """
        # Calculate noise threshold (simple approach)
        noise_threshold = np.mean(np.abs(audio_data)) * 0.1
        
        # Apply noise gate
        audio_data = np.where(
            np.abs(audio_data) < noise_threshold,
            np.zeros_like(audio_data),
            audio_data
        )
        
        return audio_data
    
    def _trim_silence(self, audio_data: np.ndarray, 
                     threshold: float = 0.02, 
                     frame_length: int = 2048) -> Tuple[np.ndarray, Tuple[int, int]]:
        """Trim silence from the beginning and end of the audio.
        
        Args:
            audio_data: Audio data as numpy array.
            threshold: Energy threshold for silence detection.
            frame_length: Length of each frame for energy calculation.
            
        Returns:
            Tuple of (trimmed_audio, (start_index, end_index))
        """
        # Calculate energy in frames
        if len(audio_data) <= frame_length:
            return audio_data, (0, len(audio_data))
        
        hop_length = frame_length // 4
        energy = []
        
        for i in range(0, len(audio_data) - frame_length, hop_length):
            frame = audio_data[i:i+frame_length]
            energy.append(np.mean(frame**2))
        
        energy = np.array(energy)
        
        # Find where energy is above threshold
        non_silent = np.where(energy > threshold)[0]
        
        if len(non_silent) == 0:
            # All silence
            return np.zeros(0, dtype=audio_data.dtype), (0, 0)
        
        # Convert frame indices to sample indices
        start_idx = max(0, non_silent[0] * hop_length)
        end_idx = min(len(audio_data), (non_silent[-1] + 1) * hop_length + frame_length)
        
        return audio_data[start_idx:end_idx], (start_idx, end_idx)
    
    def adjust_volume(self, audio_data: np.ndarray, gain_db: float) -> np.ndarray:
        """Adjust the volume of the audio data.
        
        Args:
            audio_data: Audio data as numpy array.
            gain_db: Gain in decibels to apply.
            
        Returns:
            Volume-adjusted audio data.
        """
        # Convert dB to linear gain
        gain_linear = 10 ** (gain_db / 20.0)
        
        # Apply gain
        return audio_data * gain_linear