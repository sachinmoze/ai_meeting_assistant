"""
System audio capture functionality.
Captures audio from the system's output or microphone.
"""

import time
import threading
import numpy as np
import pyaudio
import wave
from typing import Optional, Callable, Dict, List, Tuple
from pathlib import Path

from utils.logger import get_logger
from utils.config import config_manager

logger = get_logger("audio_capture")

class AudioCapture:
    """Captures audio from the system output or microphone."""
    
    def __init__(self):
        """Initialize the audio capture system."""
        self.config = config_manager.config.audio
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.is_recording = False
        self._recording_thread = None
        self._callback = None
        self._temp_file = None
        self._frames = []
        self._wav_file = None
        
        # Get available devices for selection
        self.available_devices = self._get_available_devices()
    
    def _get_available_devices(self) -> Dict[int, str]:
        """Get a dictionary of available audio devices.
        
        Returns:
            Dict mapping device indices to their names.
        """
        devices = {}
        
        for i in range(self.audio.get_device_count()):
            try:
                device_info = self.audio.get_device_info_by_index(i)
                if device_info['maxInputChannels'] > 0:
                    name = device_info['name']
                    devices[i] = f"{name} (Input)"
                if device_info['maxOutputChannels'] > 0:
                    name = device_info['name']
                    devices[i] = f"{name} (Output)"
            except Exception as e:
                logger.error(f"Error getting device info for index {i}: {e}")
        
        return devices

    def list_devices(self) -> List[Tuple[int, str]]:
        """List all available audio input and output devices.
        
        Returns:
            List of tuples (device_index, device_name)
        """
        return list(self.available_devices.items())
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Callback function for audio stream.
        
        Args:
            in_data: Input audio data.
            frame_count: Number of frames.
            time_info: Time information.
            status: Status flag.
            
        Returns:
            Tuple of (input_data, pyaudio.paContinue)
        """
        if self.is_recording:
            self._frames.append(in_data)
            
            # If a callback function is registered, call it with the audio data
            if self._callback:
                try:
                    # Convert bytes to numpy array for processing
                    audio_data = np.frombuffer(in_data, dtype=np.int16)
                    self._callback(audio_data)
                except Exception as e:
                    logger.error(f"Error in audio callback: {e}")
            
            # Write to temporary WAV file if open
            if self._wav_file:
                self._wav_file.writeframes(in_data)
                
        return (in_data, pyaudio.paContinue)
    
    def start_recording(self, device_index: Optional[int] = None, callback: Optional[Callable] = None, 
                        save_path: Optional[Path] = None) -> bool:
        """Start recording audio.
        
        Args:
            device_index: Index of the audio device to use. If None, uses the configured default.
            callback: Optional callback function to receive audio data.
            save_path: Optional path to save the recorded audio.
            
        Returns:
            True if recording started successfully, False otherwise.
        """
        if self.is_recording:
            logger.warning("Recording is already in progress")
            return False
        
        try:
            # Use device index from parameters, config, or default to system default
            device_idx = device_index if device_index is not None else self.config.device_index
            
            logger.info(f"Starting audio recording from device index: {device_idx}")
            
            # Create a stream for audio capture
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=self.config.channels,
                rate=self.config.sample_rate,
                input=True,
                input_device_index=device_idx,
                frames_per_buffer=self.config.chunk_size,
                stream_callback=self._audio_callback
            )
            
            # Start the stream
            self.stream.start_stream()
            self.is_recording = True
            self._callback = callback
            self._frames = []
            
            # If save path provided, open a WAV file for writing
            if save_path:
                self._temp_file = save_path
                self._wav_file = wave.open(str(save_path), 'wb')
                self._wav_file.setnchannels(self.config.channels)
                self._wav_file.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
                self._wav_file.setframerate(self.config.sample_rate)
            
            logger.info("Audio recording started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start audio recording: {e}")
            return False
    
    def stop_recording(self) -> Optional[Path]:
        """Stop recording audio.
        
        Returns:
            Path to the recorded audio file if available, None otherwise.
        """
        if not self.is_recording:
            logger.warning("No recording in progress")
            return None
        
        logger.info("Stopping audio recording")
        
        self.is_recording = False
        
        # Stop and close the stream
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        
        # Close the WAV file if open
        if self._wav_file:
            self._wav_file.close()
            self._wav_file = None
            logger.info(f"Audio saved to {self._temp_file}")
            return self._temp_file
        
        return None
    
    def save_recording(self, file_path: Path) -> bool:
        """Save the current recording to a file.
        
        Args:
            file_path: Path to save the audio file.
            
        Returns:
            True if saved successfully, False otherwise.
        """
        if not self._frames:
            logger.warning("No audio data to save")
            return False
        
        try:
            logger.info(f"Saving audio to {file_path}")
            
            with wave.open(str(file_path), 'wb') as wf:
                wf.setnchannels(self.config.channels)
                wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
                wf.setframerate(self.config.sample_rate)
                wf.writeframes(b''.join(self._frames))
            
            logger.info(f"Audio saved successfully to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save audio: {e}")
            return False
    
    def __del__(self):
        """Clean up resources."""
        if self.stream:
            self.stream.close()
        
        if self.audio:
            self.audio.terminate()
        
        if self._wav_file:
            self._wav_file.close()