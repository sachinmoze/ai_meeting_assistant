"""
AI Meeting Assistant - Main entry point.
Captures system audio, transcribes speech in real-time, and summarizes meetings.
"""

import sys
import os
from pathlib import Path
import logging
from datetime import datetime
import traceback

from PyQt5.QtWidgets import QApplication, QStyleFactory, QMessageBox
from PyQt5.QtCore import Qt, QSettings

from utils.logger import get_logger
from utils.config import config_manager
from ui.main_window import MainWindow

logger = get_logger("main")


def configure_application():
    """Configure the application settings."""
    # Create application directories if they don't exist
    config_dir = Path.home() / ".ai_meeting_assistant"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    (config_dir / "logs").mkdir(parents=True, exist_ok=True)
    
    # Set application metadata
    QApplication.setApplicationName("AI Meeting Assistant")
    QApplication.setApplicationVersion("1.0.0")
    QApplication.setOrganizationName("CloudTribe AI Labs")
    QApplication.setOrganizationDomain("cloudtribe.ai")
    
    # Configure styles based on user preferences
    theme = config_manager.config.ui.theme
    if theme == "dark":
        # Set up dark theme
        from PyQt5.QtGui import QPalette, QColor
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)
        QApplication.setPalette(dark_palette)
    elif theme == "light":
        # Reset to default light theme
        QApplication.setPalette(QApplication.style().standardPalette())


def handle_exception(exc_type, exc_value, exc_traceback):
    """Global exception handler to log unhandled exceptions."""
    if issubclass(exc_type, KeyboardInterrupt):
        # Standard system exit, no need to log
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    # Log the exception
    logger.critical("Unhandled exception:", exc_info=(exc_type, exc_value, exc_traceback))
    
    # Format traceback
    error_details = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    
    # Show error dialog if running in GUI mode
    if QApplication.instance():
        QMessageBox.critical(
            None, 
            "Critical Error",
            f"An unexpected error occurred:\n\n{str(exc_value)}\n\nDetails have been logged."
        )


def main():
    """Main application entry point."""
    # Set up global exception handler
    sys.excepthook = handle_exception
    
    # Create and configure the Qt application
    app = QApplication(sys.argv)
    
    # Configure application settings
    configure_application()
    
    # Set application style
    app.setStyle("Fusion")
    
    # Create and show the main window
    window = MainWindow()
    window.show()
    
    # Start the application event loop
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()