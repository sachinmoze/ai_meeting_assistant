"""
Settings dialog for the AI Meeting Assistant.
Allows configuration of audio devices, AI models, and application settings.
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Optional

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, 
    QComboBox, QPushButton, QGridLayout, QLineEdit, QCheckBox,
    QGroupBox, QFormLayout, QSpinBox, QDoubleSpinBox, QFileDialog,
    QMessageBox, QDialogButtonBox, QSlider, QWidget
)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QFont

from utils.logger import get_logger
from utils.config import config_manager
from audio.audio_capture import AudioCapture

logger = get_logger("settings")


class SettingsDialog(QDialog):
    """Settings dialog for the application."""
    
    def __init__(self):
        """Initialize the settings dialog."""
        super().__init__()
        
        # Load audio devices
        self.audio_capture = AudioCapture()
        self.audio_devices = self.audio_capture.list_devices()
        
        # Set up the UI
        self.init_ui()
        
        # Load current settings
        self.load_settings()
    
    def init_ui(self):
        """Initialize the user interface."""
        # Set window properties
        self.setWindowTitle("Settings")
        self.setMinimumWidth(600)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Tab widget
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)
        
        # Create tabs
        general_tab = self.create_general_tab()
        audio_tab = self.create_audio_tab()
        ai_tab = self.create_ai_tab()
        storage_tab = self.create_storage_tab()
        
        # Add tabs
        tab_widget.addTab(general_tab, "General")
        tab_widget.addTab(audio_tab, "Audio")
        tab_widget.addTab(ai_tab, "AI Models")
        tab_widget.addTab(storage_tab, "Storage")
        
        # Button box
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.save_settings)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)
    
    def create_general_tab(self):
        """Create the general settings tab.
        
        Returns:
            Widget containing general settings.
        """
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Application settings group
        app_group = QGroupBox("Application Settings")
        app_layout = QFormLayout(app_group)
        
        # Language
        self.language_combo = QComboBox()
        self.language_combo.addItem("English", "en")
        self.language_combo.addItem("Spanish", "es")
        self.language_combo.addItem("French", "fr")
        self.language_combo.addItem("German", "de")
        self.language_combo.addItem("Chinese", "zh")
        self.language_combo.addItem("Japanese", "ja")
        app_layout.addRow("Language:", self.language_combo)
        
        # Theme
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("System", "system")
        self.theme_combo.addItem("Light", "light")
        self.theme_combo.addItem("Dark", "dark")
        app_layout.addRow("Theme:", self.theme_combo)
        
        # Font size
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 16)
        app_layout.addRow("Font Size:", self.font_size_spin)
        
        # Debug mode
        self.debug_mode_check = QCheckBox("Enable verbose logging for troubleshooting")
        app_layout.addRow("Debug Mode:", self.debug_mode_check)
        
        layout.addWidget(app_group)
        
        # UI settings group
        ui_group = QGroupBox("UI Settings")
        ui_layout = QFormLayout(ui_group)
        
        # Show caption overlay
        self.caption_overlay_check = QCheckBox("Show live captions as overlay during meetings")
        ui_layout.addRow("Caption Overlay:", self.caption_overlay_check)
        
        # Overlay opacity
        self.overlay_opacity_slider = QSlider(Qt.Horizontal)
        self.overlay_opacity_slider.setRange(1, 10)
        self.overlay_opacity_slider.setTickPosition(QSlider.TicksBelow)
        self.overlay_opacity_slider.setTickInterval(1)
        ui_layout.addRow("Overlay Opacity:", self.overlay_opacity_slider)
        
        # Overlay position
        self.overlay_position_combo = QComboBox()
        self.overlay_position_combo.addItem("Bottom", "bottom")
        self.overlay_position_combo.addItem("Top", "top")
        ui_layout.addRow("Overlay Position:", self.overlay_position_combo)
        
        layout.addWidget(ui_group)
        
        # Add stretch to push groups to the top
        layout.addStretch()
        
        return tab
    
    def create_audio_tab(self):
        """Create the audio settings tab.
        
        Returns:
            Widget containing audio settings.
        """
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Audio device settings group
        device_group = QGroupBox("Audio Device Settings")
        device_layout = QFormLayout(device_group)
        
        # Audio device
        self.audio_device_combo = QComboBox()
        
        # Add available devices
        self.audio_device_combo.addItem("System Default", None)
        for device_id, device_name in self.audio_devices:
            self.audio_device_combo.addItem(device_name, device_id)
        
        device_layout.addRow("Audio Device:", self.audio_device_combo)
        layout.addWidget(device_group)
        
        # Audio processing settings group
        processing_group = QGroupBox("Audio Processing Settings")
        processing_layout = QFormLayout(processing_group)
        
        # Sample rate
        self.sample_rate_combo = QComboBox()
        self.sample_rate_combo.addItem("16000 Hz (Whisper Default)", 16000)
        self.sample_rate_combo.addItem("44100 Hz (CD Quality)", 44100)
        self.sample_rate_combo.addItem("48000 Hz (DVD Quality)", 48000)
        processing_layout.addRow("Sample Rate:", self.sample_rate_combo)
        
        # Channels
        self.channels_combo = QComboBox()
        self.channels_combo.addItem("Mono (1 channel)", 1)
        self.channels_combo.addItem("Stereo (2 channels)", 2)
        processing_layout.addRow("Channels:", self.channels_combo)
        
        # Chunk size
        self.chunk_size_combo = QComboBox()
        self.chunk_size_combo.addItem("1024 (Low Latency)", 1024)
        self.chunk_size_combo.addItem("2048", 2048)
        self.chunk_size_combo.addItem("4096 (Default)", 4096)
        self.chunk_size_combo.addItem("8192 (Better Quality)", 8192)
        processing_layout.addRow("Chunk Size:", self.chunk_size_combo)
        
        layout.addWidget(processing_group)
        
        # Add stretch to push groups to the top
        layout.addStretch()
        
        return tab
    
    def create_ai_tab(self):
        """Create the AI models settings tab.
        
        Returns:
            Widget containing AI model settings.
        """
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # API settings group
        api_group = QGroupBox("API Settings")
        api_layout = QFormLayout(api_group)
        
        # OpenAI API key
        self.openai_api_key_edit = QLineEdit()
        self.openai_api_key_edit.setEchoMode(QLineEdit.Password)
        api_layout.addRow("OpenAI API Key:", self.openai_api_key_edit)
        
        layout.addWidget(api_group)
        
        # Whisper settings group
        whisper_group = QGroupBox("Transcription Settings")
        whisper_layout = QFormLayout(whisper_group)
        
        # Use local Whisper model
        self.use_local_whisper_check = QCheckBox("Use local model (offline, no API costs)")
        whisper_layout.addRow("Local Whisper:", self.use_local_whisper_check)
        
        # Local Whisper model size
        self.local_whisper_model_combo = QComboBox()
        self.local_whisper_model_combo.addItem("Tiny (fastest, least accurate)", "tiny")
        self.local_whisper_model_combo.addItem("Base (fast, good accuracy)", "base")
        self.local_whisper_model_combo.addItem("Small (balanced)", "small")
        self.local_whisper_model_combo.addItem("Medium (accurate, slower)", "medium")
        self.local_whisper_model_combo.addItem("Large (most accurate, slowest)", "large")
        whisper_layout.addRow("Local Model Size:", self.local_whisper_model_combo)
        
        # Check if faster-whisper is available
        try:
            import faster_whisper
            local_whisper_available = True
        except (ImportError, OSError):
            local_whisper_available = False
        
        # Add warning message if needed
        if not local_whisper_available:
            whisper_warning = QLabel("⚠️ faster-whisper package is not properly installed. Local model will not be available.")
            whisper_warning.setStyleSheet("color: red;")
            whisper_layout.addRow("", whisper_warning)
            self.use_local_whisper_check.setEnabled(False)
            self.local_whisper_model_combo.setEnabled(False)
        else:
            # Connect checkbox to enable/disable model size
            self.use_local_whisper_check.stateChanged.connect(
                lambda state: self.local_whisper_model_combo.setEnabled(state == Qt.Checked)
            )
        
        layout.addWidget(whisper_group)
        
        # GPT settings group
        gpt_group = QGroupBox("Summarization Settings")
        gpt_layout = QFormLayout(gpt_group)
        
        # GPT model
        self.gpt_model_combo = QComboBox()
        self.gpt_model_combo.addItem("GPT-4-turbo (best quality)", "gpt-4-turbo")
        self.gpt_model_combo.addItem("GPT-4 (high quality)", "gpt-4")
        self.gpt_model_combo.addItem("GPT-3.5-turbo (faster, lower cost)", "gpt-3.5-turbo")
        gpt_layout.addRow("GPT Model:", self.gpt_model_combo)
        
        layout.addWidget(gpt_group)
        
        # Add stretch to push groups to the top
        layout.addStretch()
        
        return tab
    
    def create_storage_tab(self):
        """Create the storage settings tab.
        
        Returns:
            Widget containing storage settings.
        """
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Database settings group
        db_group = QGroupBox("Database Settings")
        db_layout = QFormLayout(db_group)
        
        # Database path
        self.db_path_edit = QLineEdit()
        self.db_path_edit.setReadOnly(True)
        
        db_path_layout = QHBoxLayout()
        db_path_layout.addWidget(self.db_path_edit)
        
        browse_db_button = QPushButton("Browse")
        browse_db_button.clicked.connect(self.browse_db_path)
        db_path_layout.addWidget(browse_db_button)
        
        db_layout.addRow("Database Path:", db_path_layout)
        
        layout.addWidget(db_group)
        
        # Export settings group
        export_group = QGroupBox("Export Settings")
        export_layout = QFormLayout(export_group)
        
        # Export directory
        self.export_dir_edit = QLineEdit()
        self.export_dir_edit.setReadOnly(True)
        
        export_dir_layout = QHBoxLayout()
        export_dir_layout.addWidget(self.export_dir_edit)
        
        browse_export_button = QPushButton("Browse")
        browse_export_button.clicked.connect(self.browse_export_dir)
        export_dir_layout.addWidget(browse_export_button)
        
        export_layout.addRow("Export Directory:", export_dir_layout)
        
        # Auto export
        self.auto_export_check = QCheckBox("Automatically export meetings after processing")
        export_layout.addRow("Auto Export:", self.auto_export_check)
        
        # Export format
        self.export_format_combo = QComboBox()
        self.export_format_combo.addItem("Markdown (.md)", "markdown")
        self.export_format_combo.addItem("PDF (.pdf)", "pdf")
        self.export_format_combo.addItem("Word (.docx)", "word")
        export_layout.addRow("Default Format:", self.export_format_combo)
        
        layout.addWidget(export_group)
        
        # Add stretch to push groups to the top
        layout.addStretch()
        
        return tab
    
    def browse_db_path(self):
        """Browse for database path."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Select Database Path", 
            self.db_path_edit.text(), 
            "SQLite Database (*.db)"
        )
        
        if file_path:
            self.db_path_edit.setText(file_path)
    
    def browse_export_dir(self):
        """Browse for export directory."""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Export Directory", 
            self.export_dir_edit.text()
        )
        
        if dir_path:
            self.export_dir_edit.setText(dir_path)
    
    def load_settings(self):
        """Load current settings into the UI."""
        try:
            # Get current config
            config = config_manager.config
            
            # General settings
            self.language_combo.setCurrentIndex(
                self.language_combo.findData(config.language)
            )
            
            self.theme_combo.setCurrentIndex(
                self.theme_combo.findData(config.ui.theme)
            )
            
            self.font_size_spin.setValue(config.ui.font_size)
            self.debug_mode_check.setChecked(config.debug_mode)
            self.caption_overlay_check.setChecked(config.ui.show_caption_overlay)
            self.overlay_opacity_slider.setValue(int(config.ui.overlay_opacity * 10))
            
            self.overlay_position_combo.setCurrentIndex(
                self.overlay_position_combo.findData(config.ui.overlay_position)
            )
            
            # Audio settings
            device_index = config.audio.device_index
            device_index_pos = self.audio_device_combo.findData(device_index)
            if device_index_pos >= 0:
                self.audio_device_combo.setCurrentIndex(device_index_pos)
            
            sample_rate_pos = self.sample_rate_combo.findData(config.audio.sample_rate)
            if sample_rate_pos >= 0:
                self.sample_rate_combo.setCurrentIndex(sample_rate_pos)
            
            channels_pos = self.channels_combo.findData(config.audio.channels)
            if channels_pos >= 0:
                self.channels_combo.setCurrentIndex(channels_pos)
            
            chunk_size_pos = self.chunk_size_combo.findData(config.audio.chunk_size)
            if chunk_size_pos >= 0:
                self.chunk_size_combo.setCurrentIndex(chunk_size_pos)
            
            # AI settings
            self.openai_api_key_edit.setText(config.ai.openai_api_key or "")
            self.use_local_whisper_check.setChecked(config.ai.use_local_whisper)
            
            local_model_pos = self.local_whisper_model_combo.findData(config.ai.local_whisper_model)
            if local_model_pos >= 0:
                self.local_whisper_model_combo.setCurrentIndex(local_model_pos)
            
            # Check if faster-whisper is available before enabling the checkbox
            try:
                import faster_whisper
                self.local_whisper_model_combo.setEnabled(config.ai.use_local_whisper)
            except (ImportError, OSError):
                # Don't enable the checkbox if faster-whisper is not available
                self.use_local_whisper_check.setEnabled(False)
                self.local_whisper_model_combo.setEnabled(False)
            
            gpt_model_pos = self.gpt_model_combo.findData(config.ai.summary_model)
            if gpt_model_pos >= 0:
                self.gpt_model_combo.setCurrentIndex(gpt_model_pos)
            
            # Storage settings
            self.db_path_edit.setText(config.storage.database_path)
            self.export_dir_edit.setText(config.storage.export_directory)
            self.auto_export_check.setChecked(config.storage.auto_export)
            
            export_format_pos = self.export_format_combo.findData(config.storage.export_format)
            if export_format_pos >= 0:
                self.export_format_combo.setCurrentIndex(export_format_pos)
            
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            QMessageBox.warning(
                self, "Settings Error", f"Error loading settings: {str(e)}"
            )
    
    def save_settings(self):
        """Save settings and close the dialog."""
        try:
            # Prepare new configuration
            new_config = {
                "language": self.language_combo.currentData(),
                "debug_mode": self.debug_mode_check.isChecked(),
                "ui": {
                    "theme": self.theme_combo.currentData(),
                    "font_size": self.font_size_spin.value(),
                    "show_caption_overlay": self.caption_overlay_check.isChecked(),
                    "overlay_opacity": self.overlay_opacity_slider.value() / 10.0,
                    "overlay_position": self.overlay_position_combo.currentData()
                },
                "audio": {
                    "device_index": self.audio_device_combo.currentData(),
                    "sample_rate": self.sample_rate_combo.currentData(),
                    "channels": self.channels_combo.currentData(),
                    "chunk_size": self.chunk_size_combo.currentData()
                },
                "ai": {
                    "openai_api_key": self.openai_api_key_edit.text().strip(),
                    "use_local_whisper": self.use_local_whisper_check.isChecked(),
                    "local_whisper_model": self.local_whisper_model_combo.currentData(),
                    "summary_model": self.gpt_model_combo.currentData()
                },
                "storage": {
                    "database_path": self.db_path_edit.text(),
                    "export_directory": self.export_dir_edit.text(),
                    "auto_export": self.auto_export_check.isChecked(),
                    "export_format": self.export_format_combo.currentData()
                }
            }
            
            # Update configuration
            config_manager.update_config(new_config)
            
            # Notify user
            QMessageBox.information(
                self, "Settings Saved", 
                "Settings have been saved successfully. Some changes may require restarting the application."
            )
            
            # Close dialog
            self.accept()
            
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            QMessageBox.warning(
                self, "Settings Error", f"Error saving settings: {str(e)}"
            )