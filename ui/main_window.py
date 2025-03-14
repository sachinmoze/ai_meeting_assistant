"""
Main application window for the AI Meeting Assistant.
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import json
import threading
import time
from typing import Dict, List, Optional, Any, Tuple

from PyQt5.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QListWidget, QListWidgetItem,
    QTabWidget, QSplitter, QFileDialog, QMessageBox, QComboBox,
    QLineEdit, QGroupBox, QFormLayout, QCheckBox, QProgressBar,
    QAction, QMenu, QStatusBar, QSystemTrayIcon, QStyle, QToolBar
)
from PyQt5.QtCore import Qt, QSize, QTimer, pyqtSignal, pyqtSlot, QThread
from PyQt5.QtGui import QIcon, QFont, QColor, QPalette

from utils.logger import get_logger
from utils.config import config_manager
from audio.audio_capture import AudioCapture
from audio.audio_processing import AudioProcessor
from transcription.whisper_api import WhisperTranscriber
from transcription.local_whisper import LocalWhisperTranscriber
from ai.summarization import MeetingSummarizer
from ai.action_items import ActionItemExtractor
from storage.database import Database
from storage.export import MeetingExporter
from ui.dashboard import DashboardWidget
from ui.settings import SettingsDialog

logger = get_logger("main_window")


class TranscriptionWorker(QThread):
    """Worker thread for real-time transcription."""
    
    transcription_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, audio_data, use_local_model):
        """Initialize the transcription worker.
        
        Args:
            audio_data: Audio data to transcribe.
            use_local_model: Whether to use the local Whisper model.
        """
        super().__init__()
        self.audio_data = audio_data
        self.use_local_model = use_local_model
        
        # Initialize transcribers
        if self.use_local_model:
            self.transcriber = LocalWhisperTranscriber()
            # Check if local model is available
            if not self.transcriber.available:
                logger.warning("Local Whisper model not available for worker. Falling back to OpenAI API.")
                self.use_local_model = False
                self.transcriber = WhisperTranscriber()
        else:
            self.transcriber = WhisperTranscriber()
    
    def run(self):
        """Run the transcription task."""
        try:
            # Process the audio chunk
            if self.use_local_model:
                result = self.transcriber.transcribe_chunk(self.audio_data)
            else:
                # Use a thread-safe approach for async functions
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    self.transcriber.transcribe_chunk(self.audio_data)
                )
                loop.close()
            
            # Get the transcribed text
            transcribed_text = result.get("text", "")
            
            # Emit the signal with the transcribed text
            if transcribed_text:
                self.transcription_ready.emit(transcribed_text)
            
        except Exception as e:
            logger.error(f"Error in transcription worker: {e}")
            self.error_occurred.emit(str(e))


class AudioRecordingThread(QThread):
    """Thread for continuous audio recording and processing."""
    
    audio_chunk_ready = pyqtSignal(object)  # Signal to emit audio chunks
    error_occurred = pyqtSignal(str)
    
    def __init__(self, chunk_duration_ms=5000):
        """Initialize the audio recording thread.
        
        Args:
            chunk_duration_ms: Duration of each audio chunk in milliseconds.
        """
        super().__init__()
        self.chunk_duration_ms = chunk_duration_ms
        self.running = False
        self.audio_capture = AudioCapture()
        self.audio_processor = AudioProcessor()
        self.chunks = []
    
    def run(self):
        """Run the audio recording thread."""
        try:
            self.running = True
            
            # Get the sample rate and calculate chunk size
            sample_rate = self.audio_capture.config.sample_rate
            channels = self.audio_capture.config.channels
            chunk_size = int(sample_rate * self.chunk_duration_ms / 1000)
            
            # Start audio capture
            def audio_callback(audio_data):
                # Process the audio data
                processed_data = self.audio_processor.preprocess(audio_data)
                
                # Store the chunk
                self.chunks.append(processed_data)
                
                # Emit the signal with the processed audio data
                self.audio_chunk_ready.emit(processed_data)
            
            # Start recording with the callback
            success = self.audio_capture.start_recording(callback=audio_callback)
            
            if not success:
                self.error_occurred.emit("Failed to start audio recording")
                return
            
            # Keep the thread running while recording
            while self.running:
                time.sleep(0.1)
            
            # Stop recording
            self.audio_capture.stop_recording()
            
        except Exception as e:
            logger.error(f"Error in audio recording thread: {e}")
            self.error_occurred.emit(str(e))
    
    def stop(self):
        """Stop the audio recording thread."""
        self.running = False
        self.wait()
    
    def get_all_audio(self):
        """Get all recorded audio chunks combined.
        
        Returns:
            Combined audio data.
        """
        import numpy as np
        if not self.chunks:
            return None
        
        return np.concatenate(self.chunks)


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        
        # Initialize components
        self.audio_capture = AudioCapture()
        self.db = Database()
        self.meeting_exporter = MeetingExporter()
        self.summarizer = MeetingSummarizer()
        self.action_item_extractor = ActionItemExtractor()
        
        # State variables
        self.recording = False
        self.current_meeting_id = None
        self.audio_thread = None
        self.transcription_workers = []
        self.full_transcript = ""
        self.meeting_title = "New Meeting"
        self.meeting_start_time = None
        self.processing_summary = False
        
        # Set up the UI
        self.init_ui()
        
        # Load saved meetings
        self.load_meetings()
    
    def init_ui(self):
        """Initialize the user interface."""
        # Set window properties
        self.setWindowTitle("AI Meeting Assistant")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Create toolbar
        self.create_toolbar()
        
        # Create splitter for main content
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel (meeting list)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Meeting list
        meetings_label = QLabel("Recent Meetings")
        meetings_label.setFont(QFont("Arial", 12, QFont.Bold))
        left_layout.addWidget(meetings_label)
        
        self.meeting_list = QListWidget()
        self.meeting_list.itemClicked.connect(self.load_meeting)
        left_layout.addWidget(self.meeting_list)
        
        # Search box
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search meetings...")
        self.search_box.textChanged.connect(self.search_meetings)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_box)
        left_layout.addLayout(search_layout)
        
        # Add dashboard button
        dashboard_button = QPushButton("Open Dashboard")
        dashboard_button.clicked.connect(self.open_dashboard)
        left_layout.addWidget(dashboard_button)
        
        # Right panel (tabs)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        right_layout.addWidget(self.tab_widget)
        
        # Recording tab
        recording_tab = QWidget()
        recording_layout = QVBoxLayout(recording_tab)
        
        # Meeting title
        title_layout = QHBoxLayout()
        title_label = QLabel("Meeting Title:")
        self.title_edit = QLineEdit("New Meeting")
        title_layout.addWidget(title_label)
        title_layout.addWidget(self.title_edit)
        recording_layout.addLayout(title_layout)
        
        # Recording controls
        # Recording controls
        controls_layout = QHBoxLayout()
        self.record_button = QPushButton("Start Recording")
        self.record_button.clicked.connect(self.toggle_recording)
        self.record_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))  # Changed here too
        
        self.pause_button = QPushButton("Pause")
        self.pause_button.setEnabled(False)
        self.pause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))  # This might need changing too
        
        self.stop_button = QPushButton("Stop & Process")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_recording)
        self.stop_button.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        
        controls_layout.addWidget(self.record_button)
        controls_layout.addWidget(self.pause_button)
        controls_layout.addWidget(self.stop_button)
        recording_layout.addLayout(controls_layout)
        
        # Status and progress
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Ready to record")
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.progress_bar)
        recording_layout.addLayout(status_layout)
        
        # Live transcription
        transcript_group = QGroupBox("Live Transcription")
        transcript_layout = QVBoxLayout(transcript_group)
        self.transcript_display = QTextEdit()
        self.transcript_display.setReadOnly(True)
        transcript_layout.addWidget(self.transcript_display)
        recording_layout.addWidget(transcript_group)
        
        # Summary tab
        summary_tab = QWidget()
        summary_layout = QVBoxLayout(summary_tab)
        
        # Meeting info section
        info_group = QGroupBox("Meeting Information")
        info_layout = QFormLayout(info_group)
        self.info_title = QLabel("-")
        self.info_date = QLabel("-")
        self.info_duration = QLabel("-")
        info_layout.addRow("Title:", self.info_title)
        info_layout.addRow("Date:", self.info_date)
        info_layout.addRow("Duration:", self.info_duration)
        summary_layout.addWidget(info_group)
        
        # Summary section
        summary_group = QGroupBox("Summary")
        summary_layout_inner = QVBoxLayout(summary_group)
        self.summary_display = QTextEdit()
        self.summary_display.setReadOnly(True)
        summary_layout_inner.addWidget(self.summary_display)
        summary_layout.addWidget(summary_group)
        
        # Key points section
        key_points_group = QGroupBox("Key Points")
        key_points_layout = QVBoxLayout(key_points_group)
        self.key_points_display = QListWidget()
        key_points_layout.addWidget(self.key_points_display)
        summary_layout.addWidget(key_points_group)
        
        # Action items section
        action_items_group = QGroupBox("Action Items")
        action_items_layout = QVBoxLayout(action_items_group)
        self.action_items_display = QListWidget()
        action_items_layout.addWidget(self.action_items_display)
        summary_layout.addWidget(action_items_group)
        
        # Transcript tab
        transcript_tab = QWidget()
        transcript_tab_layout = QVBoxLayout(transcript_tab)
        self.full_transcript_display = QTextEdit()
        self.full_transcript_display.setReadOnly(True)
        transcript_tab_layout.addWidget(self.full_transcript_display)
        
        # Export buttons
        export_layout = QHBoxLayout()
        self.export_markdown_button = QPushButton("Export to Markdown")
        self.export_markdown_button.clicked.connect(self.export_to_markdown)
        self.export_pdf_button = QPushButton("Export to PDF")
        self.export_pdf_button.clicked.connect(self.export_to_pdf)
        self.export_word_button = QPushButton("Export to Word")
        self.export_word_button.clicked.connect(self.export_to_word)
        
        export_layout.addWidget(self.export_markdown_button)
        export_layout.addWidget(self.export_pdf_button)
        export_layout.addWidget(self.export_word_button)
        transcript_tab_layout.addLayout(export_layout)
        
        # Add tabs
        self.tab_widget.addTab(recording_tab, "Recording")
        self.tab_widget.addTab(summary_tab, "Summary")
        self.tab_widget.addTab(transcript_tab, "Full Transcript")
        
        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        
        # Set splitter sizes (30% left, 70% right)
        splitter.setSizes([300, 700])
        
        # Status bar
        self.statusBar().showMessage("Ready")
        
        # Enable export buttons only when meeting is loaded
        self.enable_export_buttons(False)
    
    def create_toolbar(self):
        """Create the application toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(32, 32))
        self.addToolBar(toolbar)

        # New meeting action
        new_meeting_action = QAction(
            self.style().standardIcon(QStyle.SP_FileIcon),
            "New Meeting", self
        )
        new_meeting_action.triggered.connect(self.new_meeting)
        toolbar.addAction(new_meeting_action)

        # Start recording action - Use a different icon
        self.record_action = QAction(
            self.style().standardIcon(QStyle.SP_MediaPlay),  # Changed to SP_MediaPlay
            "Start Recording", self
        )
        self.record_action.triggered.connect(self.toggle_recording)
        toolbar.addAction(self.record_action)

        # Stop recording action
        self.stop_action = QAction(
            self.style().standardIcon(QStyle.SP_MediaStop),
            "Stop Recording", self
        )
        self.stop_action.triggered.connect(self.stop_recording)
        self.stop_action.setEnabled(False)
        toolbar.addAction(self.stop_action)
    
    # Rest of the method stays the same...
        
        toolbar.addSeparator()
        
        # Export actions
        export_menu = QMenu("Export", self)
        
        export_markdown_action = QAction("Export to Markdown", self)
        export_markdown_action.triggered.connect(self.export_to_markdown)
        export_menu.addAction(export_markdown_action)
        
        export_pdf_action = QAction("Export to PDF", self)
        export_pdf_action.triggered.connect(self.export_to_pdf)
        export_menu.addAction(export_pdf_action)
        
        export_word_action = QAction("Export to Word", self)
        export_word_action.triggered.connect(self.export_to_word)
        export_menu.addAction(export_word_action)
        
        export_action = QAction(
            self.style().standardIcon(QStyle.SP_DialogSaveButton),
            "Export", self
        )
        export_action.setMenu(export_menu)
        toolbar.addAction(export_action)
        
        toolbar.addSeparator()
        
        # Settings action
        settings_action = QAction(
            self.style().standardIcon(QStyle.SP_FileDialogDetailedView),
            "Settings", self
        )
        settings_action.triggered.connect(self.open_settings)
        toolbar.addAction(settings_action)
        
        # Help action
        help_action = QAction(
            self.style().standardIcon(QStyle.SP_MessageBoxQuestion),
            "Help", self
        )
        help_action.triggered.connect(self.show_help)
        toolbar.addAction(help_action)
    
    def load_meetings(self):
        """Load meetings from the database."""
        try:
            # Clear the list
            self.meeting_list.clear()
            
            # Get recent meetings
            meetings = self.db.get_meetings(limit=50)
            
            # Add meetings to the list
            for meeting in meetings:
                item = QListWidgetItem(meeting.title)
                item.setData(Qt.UserRole, meeting.id)
                
                # Format date for display
                date_str = meeting.date.strftime("%Y-%m-%d %H:%M")
                item.setToolTip(f"{meeting.title}\n{date_str}")
                
                self.meeting_list.addItem(item)
                
        except Exception as e:
            logger.error(f"Error loading meetings: {e}")
            QMessageBox.warning(
                self, "Load Error", f"Could not load meetings: {str(e)}"
            )
    
    def load_meeting(self, item):
        """Load a meeting when selected from the list.
        
        Args:
            item: Selected QListWidgetItem.
        """
        try:
            # Get meeting ID
            meeting_id = item.data(Qt.UserRole)
            if not meeting_id:
                return
            
            self.current_meeting_id = meeting_id
            
            # Get meeting from database
            meeting = self.db.get_meeting(meeting_id)
            if not meeting:
                QMessageBox.warning(
                    self, "Load Error", f"Could not find meeting with ID: {meeting_id}"
                )
                return
            
            # Update meeting info
            self.meeting_title = meeting.title
            self.info_title.setText(meeting.title)
            self.info_date.setText(meeting.date.strftime("%Y-%m-%d %H:%M"))
            
            # Format duration
            if meeting.duration:
                hours, remainder = divmod(int(meeting.duration), 3600)
                minutes, seconds = divmod(remainder, 60)
                duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                self.info_duration.setText(duration_str)
            else:
                self.info_duration.setText("Unknown")
            
            # Get transcript
            transcript = self.db.get_transcript(meeting_id)
            if transcript:
                self.full_transcript = transcript.full_text
                self.full_transcript_display.setText(transcript.full_text)
            else:
                self.full_transcript = ""
                self.full_transcript_display.setText("No transcript available.")
            
            # Get summary
            summary = self.db.get_summary(meeting_id)
            if summary:
                self.summary_display.setText(summary.summary_text)
                
                # Load key points
                self.key_points_display.clear()
                if summary.key_points:
                    key_points = json.loads(summary.key_points)
                    for point in key_points:
                        self.key_points_display.addItem(point)
            else:
                self.summary_display.setText("No summary available.")
                self.key_points_display.clear()
            
            # Get action items
            self.action_items_display.clear()
            action_items = self.db.get_action_items(meeting_id=meeting_id)
            for item in action_items:
                # Format due date
                if item.due_date:
                    due_date_str = item.due_date.strftime("%Y-%m-%d")
                else:
                    due_date_str = "Not specified"
                
                # Create list item
                status_icon = "✅" if item.status == "completed" else "⏳" if item.status == "pending" else "❌"
                list_item = QListWidgetItem(
                    f"{status_icon} {item.task} (Assigned to: {item.assignee}, Due: {due_date_str})"
                )
                list_item.setData(Qt.UserRole, item.id)
                self.action_items_display.addItem(list_item)
            
            # Switch to summary tab
            self.tab_widget.setCurrentIndex(1)
            
            # Enable export buttons
            self.enable_export_buttons(True)
            
            # Update status
            self.statusBar().showMessage(f"Loaded meeting: {meeting.title}")
            
        except Exception as e:
            logger.error(f"Error loading meeting: {e}")
            QMessageBox.warning(
                self, "Load Error", f"Could not load meeting: {str(e)}"
            )
    
    def new_meeting(self):
        """Create a new meeting."""
        # Reset UI for new meeting
        self.current_meeting_id = None
        self.meeting_title = "New Meeting"
        self.title_edit.setText(self.meeting_title)
        self.transcript_display.clear()
        self.full_transcript_display.clear()
        self.summary_display.clear()
        self.key_points_display.clear()
        self.action_items_display.clear()
        self.full_transcript = ""
        
        # Switch to recording tab
        self.tab_widget.setCurrentIndex(0)
        
        # Disable export buttons
        self.enable_export_buttons(False)
        
        # Update status
        self.statusBar().showMessage("New meeting ready to record")
    
    def toggle_recording(self):
        """Start or stop recording."""
        if not self.recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        """Start recording the meeting."""
        if self.recording:
            return
        
        try:
            # Get meeting title
            self.meeting_title = self.title_edit.text() or "New Meeting"
            
            # Record start time
            self.meeting_start_time = datetime.now()
            
            # Update UI
            self.record_button.setText("Recording...")
            self.record_button.setEnabled(False)
            self.pause_button.setEnabled(True)
            self.stop_button.setEnabled(True)
            self.record_action.setEnabled(False)
            self.stop_action.setEnabled(True)
            self.status_label.setText("Recording in progress...")
            
            # Clear transcript display
            self.transcript_display.clear()
            self.full_transcript = ""
            
            # Update state
            self.recording = True
            
            # Start audio recording thread
            self.audio_thread = AudioRecordingThread()
            self.audio_thread.audio_chunk_ready.connect(self.process_audio_chunk)
            self.audio_thread.error_occurred.connect(self.handle_audio_error)
            self.audio_thread.start()
            
            # Update status
            self.statusBar().showMessage(f"Recording started: {self.meeting_title}")
            
        except Exception as e:
            logger.error(f"Error starting recording: {e}")
            QMessageBox.warning(
                self, "Recording Error", f"Could not start recording: {str(e)}"
            )
            self.recording = False
            self.record_button.setText("Start Recording")
            self.record_button.setEnabled(True)
            self.pause_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.record_action.setEnabled(True)
            self.stop_action.setEnabled(False)
    
    def stop_recording(self):
        """Stop recording and process the meeting."""
        if not self.recording:
            return
        
        try:
            # Update UI
            self.status_label.setText("Processing recording...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(10)
            
            # Stop audio thread
            if self.audio_thread:
                self.audio_thread.stop()
                
                # Get all recorded audio
                all_audio = self.audio_thread.get_all_audio()
                
                # Process the complete recording
                if all_audio is not None:
                    # Save the recording to a temporary file for full processing
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                        temp_path = temp_file.name
                    
                    # Save audio to file
                    import wave
                    import numpy as np
                    with wave.open(temp_path, 'wb') as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)  # 16-bit
                        wf.setframerate(16000)  # Whisper expects 16kHz
                        wf.writeframes((all_audio * 32767).astype(np.int16).tobytes())
                    
                    self.progress_bar.setValue(30)
                    
                    # Transcribe the full audio file
                    self.status_label.setText("Transcribing audio...")
                    
                    # Choose transcriber based on config
                    use_local = config_manager.config.ai.use_local_whisper
                    if use_local:
                        transcriber = LocalWhisperTranscriber()
                        # Check if local model is available
                        if not transcriber.available:
                            logger.warning("Local Whisper model not available. Falling back to OpenAI API.")
                            use_local = False
                            transcriber = WhisperTranscriber()
                            result = transcriber.transcribe_file(temp_path)
                        else:
                            result = transcriber.transcribe_file(temp_path)
                    else:
                        transcriber = WhisperTranscriber()
                        result = transcriber.transcribe_file(temp_path)
                    
                    self.progress_bar.setValue(60)
                    
                    # Get transcript
                    self.full_transcript = result.get("text", "")
                    
                    # Calculate duration
                    end_time = datetime.now()
                    duration = (end_time - self.meeting_start_time).total_seconds()
                    
                    # Create meeting in database
                    meeting = self.db.create_meeting(
                        title=self.meeting_title,
                        date=self.meeting_start_time,
                        duration=duration,
                        audio_path=temp_path
                    )
                    
                    # Save transcript
                    transcript = self.db.create_transcript(
                        meeting_id=meeting.id,
                        full_text=self.full_transcript,
                        segments=result.get("segments", []),
                        language=result.get("language", "en")
                    )
                    
                    self.progress_bar.setValue(70)
                    
                    # Process summary and action items
                    self.current_meeting_id = meeting.id
                    self.process_summary()
                    
                    # Update full transcript display
                    self.full_transcript_display.setText(self.full_transcript)
                    
                    # Enable export buttons
                    self.enable_export_buttons(True)
                    
                    # Update meeting list
                    self.load_meetings()
            
            # Update UI
            self.recording = False
            self.record_button.setText("Start Recording")
            self.record_button.setEnabled(True)
            self.pause_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.record_action.setEnabled(True)
            self.stop_action.setEnabled(False)
            self.status_label.setText("Recording processed")
            self.progress_bar.setValue(100)
            
            # Hide progress bar after a delay
            QTimer.singleShot(3000, lambda: self.progress_bar.setVisible(False))
            
            # Update status
            self.statusBar().showMessage(f"Recording completed: {self.meeting_title}")
            
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            QMessageBox.warning(
                self, "Processing Error", f"Error processing recording: {str(e)}"
            )
            self.recording = False
            self.record_button.setText("Start Recording")
            self.record_button.setEnabled(True)
            self.pause_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.record_action.setEnabled(True)
            self.stop_action.setEnabled(False)
            self.progress_bar.setVisible(False)
    
    def process_audio_chunk(self, audio_data):
        """Process an audio chunk for real-time transcription.
        
        Args:
            audio_data: Audio data to process.
        """
        if not self.recording:
            return
        
        # Create a transcription worker
        worker = TranscriptionWorker(
            audio_data, config_manager.config.ai.use_local_whisper
        )
        worker.transcription_ready.connect(self.update_transcription)
        worker.error_occurred.connect(self.handle_transcription_error)
        
        # Add to the list of workers and start
        self.transcription_workers.append(worker)
        worker.start()
    
    def update_transcription(self, text):
        """Update the transcription display with new text.
        
        Args:
            text: New transcribed text.
        """
        if text:
            # Append to the transcript display
            current_text = self.transcript_display.toPlainText()
            if current_text:
                current_text += " " + text
            else:
                current_text = text
            
            self.transcript_display.setText(current_text)
            
            # Scroll to the bottom
            cursor = self.transcript_display.textCursor()
            cursor.movePosition(cursor.End)
            self.transcript_display.setTextCursor(cursor)
    
    def handle_audio_error(self, error_msg):
        """Handle errors from the audio recording thread.
        
        Args:
            error_msg: Error message.
        """
        logger.error(f"Audio recording error: {error_msg}")
        QMessageBox.warning(
            self, "Recording Error", f"Audio recording error: {error_msg}"
        )
        self.stop_recording()
    
    def handle_transcription_error(self, error_msg):
        """Handle errors from the transcription worker.
        
        Args:
            error_msg: Error message.
        """
        logger.error(f"Transcription error: {error_msg}")
        # We don't show a message box for every transcription error
        # to avoid interrupting the recording
        self.statusBar().showMessage(f"Transcription error: {error_msg}", 5000)
    
    def process_summary(self):
        """Process the meeting summary and action items."""
        if not self.current_meeting_id or not self.full_transcript or self.processing_summary:
            return
        
        # Set processing flag
        self.processing_summary = True
        
        try:
            # Update status
            self.status_label.setText("Generating summary...")
            self.statusBar().showMessage("Generating meeting summary...")
            
            # Start a thread for summary processing
            summary_thread = SummaryProcessingThread(
                self.current_meeting_id, self.full_transcript, self.meeting_title, self.db,
                self.summarizer, self.action_item_extractor
            )
            summary_thread.summary_ready.connect(self.display_summary)
            summary_thread.error_occurred.connect(self.handle_summary_error)
            summary_thread.start()
            
        except Exception as e:
            logger.error(f"Error processing summary: {e}")
            self.processing_summary = False
            self.status_label.setText("Error generating summary")
            QMessageBox.warning(
                self, "Summary Error", f"Error generating summary: {str(e)}"
            )
    
    def display_summary(self, summary_data):
        """Display the meeting summary.
        
        Args:
            summary_data: Dictionary containing summary data.
        """
        # Reset processing flag
        self.processing_summary = False
        
        # Update UI
        self.summary_display.setText(summary_data.get("summary_text", ""))
        
        # Update key points
        self.key_points_display.clear()
        for point in summary_data.get("key_points", []):
            self.key_points_display.addItem(point)
        
        # Update action items
        self.action_items_display.clear()
        for item in summary_data.get("action_items", []):
            # Format due date
            due_date = item.get("due_date")
            if due_date:
                due_date_str = due_date.strftime("%Y-%m-%d") if isinstance(due_date, datetime) else str(due_date)
            else:
                due_date_str = "Not specified"
            
            # Create list item
            list_item = QListWidgetItem(
                f"⏳ {item.get('task')} (Assigned to: {item.get('assignee', 'Unassigned')}, Due: {due_date_str})"
            )
            list_item.setData(Qt.UserRole, item.get("id"))
            self.action_items_display.addItem(list_item)
        
        # Switch to summary tab
        self.tab_widget.setCurrentIndex(1)
        
        # Update status
        self.status_label.setText("Summary generated")
        self.statusBar().showMessage("Meeting summary generated successfully")
    
    def handle_summary_error(self, error_msg):
        """Handle errors from the summary processing thread.
        
        Args:
            error_msg: Error message.
        """
        # Reset processing flag
        self.processing_summary = False
        
        logger.error(f"Summary processing error: {error_msg}")
        self.status_label.setText("Error generating summary")
        QMessageBox.warning(
            self, "Summary Error", f"Error generating summary: {error_msg}"
        )
    
    def export_to_markdown(self):
        """Export the meeting to a Markdown file."""
        if not self.current_meeting_id:
            QMessageBox.warning(
                self, "Export Error", "No meeting is currently loaded"
            )
            return
        
        try:
            # Get meeting data
            meeting = self.db.get_meeting(self.current_meeting_id)
            if not meeting:
                QMessageBox.warning(
                    self, "Export Error", "Could not find the current meeting"
                )
                return
            
            # Get file path
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export to Markdown", 
                str(Path.home() / f"{self._slugify(meeting.title)}.md"),
                "Markdown Files (*.md)"
            )
            
            if not file_path:
                return
            
            # Get transcript
            transcript = self.db.get_transcript(self.current_meeting_id)
            
            # Get summary
            summary = self.db.get_summary(self.current_meeting_id)
            
            # Get action items
            action_items = self.db.get_action_items(meeting_id=self.current_meeting_id)
            
            # Parse participants and tags
            participants = json.loads(meeting.participants) if meeting.participants else []
            tags = json.loads(meeting.tags) if meeting.tags else []
            
            # Prepare data for export
            summary_data = {}
            if summary:
                summary_data = {
                    "summary_text": summary.summary_text,
                    "key_points": json.loads(summary.key_points) if summary.key_points else [],
                    "topics": json.loads(summary.topics) if summary.topics else [],
                    "decisions": json.loads(summary.decisions) if summary.decisions else [],
                    "questions": json.loads(summary.questions) if summary.questions else []
                }
            
            transcript_data = {}
            if transcript:
                transcript_data = {
                    "full_text": transcript.full_text,
                    "segments": json.loads(transcript.segments) if transcript.segments else []
                }
            
            action_item_data = []
            for item in action_items:
                action_item_data.append({
                    "id": item.id,
                    "task": item.task,
                    "assignee": item.assignee,
                    "due_date": item.due_date,
                    "status": item.status
                })
            
            # Prepare meeting data
            meeting_data = {
                "title": meeting.title,
                "date": meeting.date,
                "duration": meeting.duration,
                "participants": participants,
                "tags": tags,
                "summary": summary_data,
                "transcript": transcript_data,
                "action_items": action_item_data
            }
            
            # Export to Markdown
            output_path = self.meeting_exporter.export_to_markdown(meeting_data, Path(file_path))
            
            # Show success message
            QMessageBox.information(
                self, "Export Successful", f"Meeting exported to {output_path}"
            )
            
        except Exception as e:
            logger.error(f"Error exporting to Markdown: {e}")
            QMessageBox.warning(
                self, "Export Error", f"Could not export to Markdown: {str(e)}"
            )
    
    def export_to_pdf(self):
        """Export the meeting to a PDF file."""
        if not self.current_meeting_id:
            QMessageBox.warning(
                self, "Export Error", "No meeting is currently loaded"
            )
            return
        
        try:
            # Get meeting data
            meeting = self.db.get_meeting(self.current_meeting_id)
            if not meeting:
                QMessageBox.warning(
                    self, "Export Error", "Could not find the current meeting"
                )
                return
            
            # Get file path
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export to PDF", 
                str(Path.home() / f"{self._slugify(meeting.title)}.pdf"),
                "PDF Files (*.pdf)"
            )
            
            if not file_path:
                return
            
            # Get transcript, summary, and action items
            transcript = self.db.get_transcript(self.current_meeting_id)
            summary = self.db.get_summary(self.current_meeting_id)
            action_items = self.db.get_action_items(meeting_id=self.current_meeting_id)
            
            # Parse participants and tags
            participants = json.loads(meeting.participants) if meeting.participants else []
            tags = json.loads(meeting.tags) if meeting.tags else []
            
            # Prepare data for export (same as for Markdown)
            summary_data = {}
            if summary:
                summary_data = {
                    "summary_text": summary.summary_text,
                    "key_points": json.loads(summary.key_points) if summary.key_points else [],
                    "topics": json.loads(summary.topics) if summary.topics else [],
                    "decisions": json.loads(summary.decisions) if summary.decisions else [],
                    "questions": json.loads(summary.questions) if summary.questions else []
                }
            
            transcript_data = {}
            if transcript:
                transcript_data = {
                    "full_text": transcript.full_text,
                    "segments": json.loads(transcript.segments) if transcript.segments else []
                }
            
            action_item_data = []
            for item in action_items:
                action_item_data.append({
                    "id": item.id,
                    "task": item.task,
                    "assignee": item.assignee,
                    "due_date": item.due_date,
                    "status": item.status
                })
            
            # Prepare meeting data
            meeting_data = {
                "title": meeting.title,
                "date": meeting.date,
                "duration": meeting.duration,
                "participants": participants,
                "tags": tags,
                "summary": summary_data,
                "transcript": transcript_data,
                "action_items": action_item_data
            }
            
            # Export to PDF
            output_path = self.meeting_exporter.export_to_pdf(meeting_data, Path(file_path))
            
            # Show success message
            QMessageBox.information(
                self, "Export Successful", f"Meeting exported to {output_path}"
            )
            
        except Exception as e:
            logger.error(f"Error exporting to PDF: {e}")
            QMessageBox.warning(
                self, "Export Error", f"Could not export to PDF: {str(e)}"
            )
    
    def export_to_word(self):
        """Export the meeting to a Word document."""
        if not self.current_meeting_id:
            QMessageBox.warning(
                self, "Export Error", "No meeting is currently loaded"
            )
            return
        
        try:
            # Get meeting data
            meeting = self.db.get_meeting(self.current_meeting_id)
            if not meeting:
                QMessageBox.warning(
                    self, "Export Error", "Could not find the current meeting"
                )
                return
            
            # Get file path
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export to Word", 
                str(Path.home() / f"{self._slugify(meeting.title)}.docx"),
                "Word Documents (*.docx)"
            )
            
            if not file_path:
                return
            
            # Get transcript, summary, and action items
            transcript = self.db.get_transcript(self.current_meeting_id)
            summary = self.db.get_summary(self.current_meeting_id)
            action_items = self.db.get_action_items(meeting_id=self.current_meeting_id)
            
            # Parse participants and tags
            participants = json.loads(meeting.participants) if meeting.participants else []
            tags = json.loads(meeting.tags) if meeting.tags else []
            
            # Prepare data for export (same as for Markdown and PDF)
            summary_data = {}
            if summary:
                summary_data = {
                    "summary_text": summary.summary_text,
                    "key_points": json.loads(summary.key_points) if summary.key_points else [],
                    "topics": json.loads(summary.topics) if summary.topics else [],
                    "decisions": json.loads(summary.decisions) if summary.decisions else [],
                    "questions": json.loads(summary.questions) if summary.questions else []
                }
            
            transcript_data = {}
            if transcript:
                transcript_data = {
                    "full_text": transcript.full_text,
                    "segments": json.loads(transcript.segments) if transcript.segments else []
                }
            
            action_item_data = []
            for item in action_items:
                action_item_data.append({
                    "id": item.id,
                    "task": item.task,
                    "assignee": item.assignee,
                    "due_date": item.due_date,
                    "status": item.status
                })
            
            # Prepare meeting data
            meeting_data = {
                "title": meeting.title,
                "date": meeting.date,
                "duration": meeting.duration,
                "participants": participants,
                "tags": tags,
                "summary": summary_data,
                "transcript": transcript_data,
                "action_items": action_item_data
            }
            
            # Export to Word
            output_path = self.meeting_exporter.export_to_docx(meeting_data, Path(file_path))
            
            # Show success message
            QMessageBox.information(
                self, "Export Successful", f"Meeting exported to {output_path}"
            )
            
        except Exception as e:
            logger.error(f"Error exporting to Word: {e}")
            QMessageBox.warning(
                self, "Export Error", f"Could not export to Word: {str(e)}"
            )
    
    def search_meetings(self):
        """Search meetings based on the search box text."""
        search_text = self.search_box.text().lower()
        
        # If search box is empty, reload all meetings
        if not search_text:
            self.load_meetings()
            return
        
        try:
            # Get all meetings
            meetings = self.db.get_meetings(limit=500)
            
            # Clear the list
            self.meeting_list.clear()
            
            # Add matching meetings to the list
            for meeting in meetings:
                if search_text in meeting.title.lower():
                    item = QListWidgetItem(meeting.title)
                    item.setData(Qt.UserRole, meeting.id)
                    
                    # Format date for display
                    date_str = meeting.date.strftime("%Y-%m-%d %H:%M")
                    item.setToolTip(f"{meeting.title}\n{date_str}")
                    
                    self.meeting_list.addItem(item)
            
            # Update status
            count = self.meeting_list.count()
            self.statusBar().showMessage(f"Found {count} meetings matching '{search_text}'")
            
        except Exception as e:
            logger.error(f"Error searching meetings: {e}")
            QMessageBox.warning(
                self, "Search Error", f"Could not search meetings: {str(e)}"
            )
    
    def open_dashboard(self):
        """Open the dashboard window."""
        try:
            self.dashboard = DashboardWidget(self.db)
            self.dashboard.show()
        except Exception as e:
            logger.error(f"Error opening dashboard: {e}")
            QMessageBox.warning(
                self, "Dashboard Error", f"Could not open dashboard: {str(e)}"
            )
    
    def open_settings(self):
        """Open the settings dialog."""
        try:
            settings_dialog = SettingsDialog()
            if settings_dialog.exec_():
                # Reload audio devices if settings changed
                self.audio_capture = AudioCapture()
        except Exception as e:
            logger.error(f"Error opening settings: {e}")
            QMessageBox.warning(
                self, "Settings Error", f"Could not open settings: {str(e)}"
            )
    
    def show_help(self):
        """Show the help dialog."""
        help_text = """
<h2>AI Meeting Assistant Help</h2>

<h3>Recording a Meeting</h3>
<p>1. Click "Start Recording" to begin capturing audio.</p>
<p>2. The application will transcribe speech in real-time.</p>
<p>3. Click "Stop & Process" when the meeting is finished.</p>
<p>4. The app will generate a summary and extract action items.</p>

<h3>Managing Meetings</h3>
<p>- Previous meetings are shown in the left panel.</p>
<p>- Click on a meeting to view its summary and transcript.</p>
<p>- Use the search box to find specific meetings.</p>

<h3>Exporting</h3>
<p>You can export meetings to:</p>
<ul>
<li>Markdown (.md)</li>
<li>PDF (.pdf)</li>
<li>Word document (.docx)</li>
</ul>

<h3>Dashboard</h3>
<p>The dashboard provides analytics on your meetings and action items.</p>

<h3>Settings</h3>
<p>Configure audio devices, AI models, and other options in the Settings dialog.</p>
"""
        QMessageBox.information(self, "Help", help_text)
    
    def enable_export_buttons(self, enabled):
        """Enable or disable export buttons.
        
        Args:
            enabled: Whether to enable the buttons.
        """
        self.export_markdown_button.setEnabled(enabled)
        self.export_pdf_button.setEnabled(enabled)
        self.export_word_button.setEnabled(enabled)
    
    def _slugify(self, text):
        """Convert text to a URL-friendly slug.
        
        Args:
            text: Text to convert.
            
        Returns:
            Slugified text.
        """
        # Remove special characters
        slug = "".join(c if c.isalnum() or c in "-_" else "_" for c in text.lower())
        
        # Remove multiple consecutive underscores
        slug = "_".join(filter(None, slug.split("_")))
        
        return slug


class SummaryProcessingThread(QThread):
    """Thread for processing meeting summary and action items."""
    
    summary_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, meeting_id, transcript, meeting_title, db, summarizer, action_item_extractor):
        """Initialize the summary processing thread.
        
        Args:
            meeting_id: Meeting ID.
            transcript: Meeting transcript.
            meeting_title: Meeting title.
            db: Database instance.
            summarizer: MeetingSummarizer instance.
            action_item_extractor: ActionItemExtractor instance.
        """
        super().__init__()
        self.meeting_id = meeting_id
        self.transcript = transcript
        self.meeting_title = meeting_title
        self.db = db
        self.summarizer = summarizer
        self.action_item_extractor = action_item_extractor
    
    def run(self):
        """Run the summary processing task."""
        try:
            # Process summary
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Generate summary
            summary_data = loop.run_until_complete(
                self.summarizer.summarize(self.transcript, self.meeting_title)
            )
            
            # Extract action items
            action_items = loop.run_until_complete(
                self.action_item_extractor.extract_action_items(self.transcript, self.meeting_id)
            )
            
            loop.close()
            
            # Save summary to database
            self.db.create_summary(
                meeting_id=self.meeting_id,
                summary_text=summary_data.get("summary", ""),
                key_points=summary_data.get("key_points", []),
                topics=summary_data.get("topics", []),
                decisions=summary_data.get("decisions", []),
                questions=summary_data.get("questions", []),
                model_used=summary_data.get("model_used", "")
            )
            
            # Save action items to database
            for item in action_items:
                self.db.create_action_item(
                    meeting_id=self.meeting_id,
                    task=item.task,
                    assignee=item.assignee,
                    due_date=item.due_date,
                    status=item.status
                )
            
            # Prepare data for the UI
            result = {
                "summary_text": summary_data.get("summary", ""),
                "key_points": summary_data.get("key_points", []),
                "topics": summary_data.get("topics", []),
                "decisions": summary_data.get("decisions", []),
                "action_items": [item.to_dict() for item in action_items]
            }
            
            # Emit signal with the result
            self.summary_ready.emit(result)
            
        except Exception as e:
            logger.error(f"Error in summary processing thread: {e}")
            self.error_occurred.emit(str(e))


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    # Create and show the main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())