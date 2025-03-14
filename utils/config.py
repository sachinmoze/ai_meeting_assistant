"""
Configuration management for the AI Meeting Assistant.
Handles loading settings from environment variables and a configuration file.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Define the default configuration directory
CONFIG_DIR = Path.home() / ".ai_meeting_assistant"
CONFIG_FILE = CONFIG_DIR / "config.json"


class AIConfig(BaseModel):
    """AI configuration settings."""
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    summary_model: str = Field("gpt-4-turbo", description="Model used for meeting summarization")
    local_whisper_model: str = Field("base", description="Whisper model size for local transcription")
    use_local_whisper: bool = Field(False, description="Whether to use local Whisper model")


class AudioConfig(BaseModel):
    """Audio configuration settings."""
    sample_rate: int = Field(16000, description="Audio sample rate")
    channels: int = Field(1, description="Number of audio channels")
    chunk_size: int = Field(4096, description="Audio chunk size")
    device_index: Optional[int] = Field(None, description="Audio device index")


class StorageConfig(BaseModel):
    """Storage configuration settings."""
    database_path: str = Field(str(CONFIG_DIR / "meetings.db"), description="Path to SQLite database")
    export_directory: str = Field(str(Path.home() / "Documents" / "AI Meeting Assistant"), 
                                description="Default directory for exported files")
    auto_export: bool = Field(False, description="Whether to automatically export meetings")
    export_format: str = Field("markdown", description="Default export format")


class UIConfig(BaseModel):
    """UI configuration settings."""
    theme: str = Field("system", description="UI theme (light, dark, system)")
    font_size: int = Field(10, description="UI font size")
    show_caption_overlay: bool = Field(True, description="Whether to show caption overlay")
    overlay_opacity: float = Field(0.8, description="Caption overlay opacity")
    overlay_position: str = Field("bottom", description="Caption overlay position")


class AppConfig(BaseModel):
    """Main application configuration."""
    ai: AIConfig = Field(default_factory=AIConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    language: str = Field("en", description="Application language")
    debug_mode: bool = Field(False, description="Whether debug mode is enabled")


class ConfigManager:
    """Manages the application configuration."""
    
    def __init__(self):
        self._config = self._load_config()
    
    def _load_config(self) -> AppConfig:
        """Load configuration from file and environment variables."""
        # Create config directory if it doesn't exist
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        
        # Initialize with default values
        config = AppConfig()
        
        # Try to load from config file
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    file_config = json.load(f)
                    config = AppConfig.parse_obj(file_config)
            except (json.JSONDecodeError, Exception) as e:
                print(f"Error loading config file: {e}")
        
        # Override with environment variables
        if os.getenv("OPENAI_API_KEY"):
            config.ai.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        return config
    
    def save_config(self):
        """Save the current configuration to file."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        
        with open(CONFIG_FILE, "w") as f:
            json.dump(self._config.dict(), f, indent=2)
    
    @property
    def config(self) -> AppConfig:
        """Get the current configuration."""
        return self._config
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update the configuration with new values."""
        # Update the config with the new values
        for section, values in new_config.items():
            if hasattr(self._config, section):
                section_obj = getattr(self._config, section)
                for key, value in values.items():
                    if hasattr(section_obj, key):
                        setattr(section_obj, key, value)
        
        # Save the updated config
        self.save_config()


# Create a singleton instance
config_manager = ConfigManager()