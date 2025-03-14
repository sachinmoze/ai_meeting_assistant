"""
Logging configuration for the AI Meeting Assistant.
Sets up a logger that writes to both console and file.
"""

import sys
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime

from .config import config_manager

# Create logs directory
CONFIG_DIR = Path.home() / ".ai_meeting_assistant"
LOGS_DIR = CONFIG_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Get current date for log filename
current_date = datetime.now().strftime("%Y-%m-%d")
LOG_FILE = LOGS_DIR / f"app_{current_date}.log"

# Configure logger
logger = logging.getLogger("ai_meeting_assistant")
logger.setLevel(logging.DEBUG if config_manager.config.debug_mode else logging.INFO)

# Console handler with color formatting
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG if config_manager.config.debug_mode else logging.INFO)

# File handler with rotation (max 5MB, keep 5 backup files)
file_handler = RotatingFileHandler(
    LOG_FILE, maxBytes=5*1024*1024, backupCount=5, encoding="utf-8"
)
file_handler.setLevel(logging.DEBUG)

# Create formatter
class ColoredFormatter(logging.Formatter):
    """Custom formatter with color support for console output."""
    
    COLORS = {
        'DEBUG': '\033[94m',  # Blue
        'INFO': '\033[92m',   # Green
        'WARNING': '\033[93m', # Yellow
        'ERROR': '\033[91m',  # Red
        'CRITICAL': '\033[91m\033[1m',  # Bold Red
        'RESET': '\033[0m'    # Reset
    }
    
    def format(self, record):
        # Save original format
        orig_fmt = self._style._fmt
        
        # Add color based on log level
        if hasattr(record, 'levelname') and record.levelname in self.COLORS:
            color = self.COLORS[record.levelname]
            reset = self.COLORS['RESET']
            self._style._fmt = f"{color}%(levelname)s{reset} - %(message)s"
        
        # Call the original formatter
        result = super().format(record)
        
        # Restore original format
        self._style._fmt = orig_fmt
        
        return result

# Set formatters
console_formatter = ColoredFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

console_handler.setFormatter(console_formatter)
file_handler.setFormatter(file_formatter)

# Add handlers to logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)


def get_logger(module_name: str) -> logging.Logger:
    """Get a logger for a specific module.
    
    Args:
        module_name: The name of the module.
        
    Returns:
        A configured logger instance.
    """
    return logging.getLogger(f"ai_meeting_assistant.{module_name}")