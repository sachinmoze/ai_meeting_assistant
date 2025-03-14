from PyQt5.QtChart import (
    QChart, QChartView, QBarSet, QBarSeries, QLineSeries,
    QPieSeries, QBarCategoryAxis, QValueAxis, QDateTimeAxis,
    QPieSlice
)

from utils.logger import get_logger
from storage.database import Database
from PyQt5.QtWidgets import QFrame, QSizePolicy, QVBoxLayout, QLabel, QHBoxLayout, QGroupBox, QFormLayout, QDateEdit, QPushButton, QGridLayout, QTabWidget, QWidget, QTableWidget, QTableWidgetItem, QHeaderView
from PyQt5.QtCore import Qt, QDate
from datetime import datetime, timedelta
from collections import Counter
from PyQt5.QtGui import QFont, QPainter, QColor

logger = get_logger("dashboard")


class StatCard(QFrame):
    """Card widget for displaying a key statistic."""
    
    def __init__(self, title: str, value: str, subtitle: str = ""):
        """Initialize the stat card.
        
        Args:
            title: Card title.
            value: Main statistic value.
            subtitle: Optional subtitle or description.
        """
        super().__init__()
        self.setFrameShape(QFrame.StyledPanel)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(120)
        
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 10))
        layout.addWidget(title_label)
        
        # Value
        value_label = QLabel(value)
        value_label.setFont(QFont("Arial", 24, QFont.Bold))
        value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(value_label)
        
        # Subtitle
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setFont(QFont("Arial", 9))
            subtitle_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(subtitle_label)


class DashboardWidget(QWidget):
    """Dashboard widget for displaying meeting analytics."""
    
    def __init__(self, db: Database):
        """Initialize the dashboard.
        
        Args:
            db: Database instance.
        """
        super().__init__()
        self.db = db
        
        # Date filters
        self.start_date = datetime.now() - timedelta(days=30)
        self.end_date = datetime.now()
        
        # Set up the UI
        self.init_ui()
        
        # Load data
        self.load_data()
    
    def init_ui(self):
        """Initialize the user interface."""
        # Set window properties
        self.setWindowTitle("Meeting Analytics Dashboard")
        self.setGeometry(100, 100, 1000, 800)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Header with title and filters
        header_layout = QHBoxLayout()
        
        # Title
        title_label = QLabel("Meeting Analytics Dashboard")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        header_layout.addWidget(title_label)
        
        # Add spacer
        header_layout.addStretch()
        
        # Date filters
        date_filter_group = QGroupBox("Date Range")
        date_filter_layout = QHBoxLayout(date_filter_group)
        
        # Start date
        start_date_layout = QFormLayout()
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setDate(QDate(self.start_date.year, self.start_date.month, self.start_date.day))
        self.start_date_edit.setCalendarPopup(True)
        start_date_layout.addRow("From:", self.start_date_edit)
        date_filter_layout.addLayout(start_date_layout)
        
        # End date
        end_date_layout = QFormLayout()
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setDate(QDate(self.end_date.year, self.end_date.month, self.end_date.day))
        self.end_date_edit.setCalendarPopup(True)
        end_date_layout.addRow("To:", self.end_date_edit)
        date_filter_layout.addLayout(end_date_layout)
        
        # Apply button
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self.apply_filters)
        date_filter_layout.addWidget(apply_button)
        
        header_layout.addWidget(date_filter_group)
        main_layout.addLayout(header_layout)
        
        # Stat cards
        stats_layout = QGridLayout()
        
        self.total_meetings_card = StatCard("Total Meetings", "-")
        stats_layout.addWidget(self.total_meetings_card, 0, 0)
        
        self.total_duration_card = StatCard("Total Duration", "-")
        stats_layout.addWidget(self.total_duration_card, 0, 1)
        
        self.avg_duration_card = StatCard("Avg. Duration", "-")
        stats_layout.addWidget(self.avg_duration_card, 0, 2)
        
        self.total_action_items_card = StatCard("Action Items", "-")
        stats_layout.addWidget(self.total_action_items_card, 0, 3)
        
        self.completion_rate_card = StatCard("Completion Rate", "-")
        stats_layout.addWidget(self.completion_rate_card, 1, 0)
        
        self.avg_items_card = StatCard("Avg. Action Items", "-")
        stats_layout.addWidget(self.avg_items_card, 1, 1)
        
        self.avg_transcript_card = StatCard("Avg. Transcript Length", "-")
        stats_layout.addWidget(self.avg_transcript_card, 1, 2)
        
        self.longest_meeting_card = StatCard("Longest Meeting", "-")
        stats_layout.addWidget(self.longest_meeting_card, 1, 3)
        
        main_layout.addLayout(stats_layout)
        
        # Tab widget for charts
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Meetings tab
        meetings_tab = QWidget()
        meetings_layout = QVBoxLayout(meetings_tab)
        
        # Meetings over time chart
        meetings_over_time_label = QLabel("Meetings Over Time")
        meetings_over_time_label.setFont(QFont("Arial", 12, QFont.Bold))
        meetings_layout.addWidget(meetings_over_time_label)
        
        self.meetings_chart_view = QChartView()
        self.meetings_chart_view.setMinimumHeight(250)
        meetings_layout.addWidget(self.meetings_chart_view)
        
        # Meeting duration chart
        meeting_duration_label = QLabel("Meeting Duration Distribution")
        meeting_duration_label.setFont(QFont("Arial", 12, QFont.Bold))
        meetings_layout.addWidget(meeting_duration_label)
        
        self.duration_chart_view = QChartView()
        self.duration_chart_view.setMinimumHeight(250)
        meetings_layout.addWidget(self.duration_chart_view)
        
        # Action items tab
        action_items_tab = QWidget()
        action_items_layout = QVBoxLayout(action_items_tab)
        
        # Action items status chart
        action_items_status_label = QLabel("Action Item Status")
        action_items_status_label.setFont(QFont("Arial", 12, QFont.Bold))
        action_items_layout.addWidget(action_items_status_label)
        
        self.action_items_status_chart_view = QChartView()
        self.action_items_status_chart_view.setMinimumHeight(250)
        action_items_layout.addWidget(self.action_items_status_chart_view)
        
        # Assignee chart
        assignee_label = QLabel("Action Items by Assignee")
        assignee_label.setFont(QFont("Arial", 12, QFont.Bold))
        action_items_layout.addWidget(assignee_label)
        
        self.assignee_chart_view = QChartView()
        self.assignee_chart_view.setMinimumHeight(250)
        action_items_layout.addWidget(self.assignee_chart_view)
        
        # Recent meetings tab
        recent_tab = QWidget()
        recent_layout = QVBoxLayout(recent_tab)
        
        # Recent meetings table
        recent_meetings_label = QLabel("Recent Meetings")
        recent_meetings_label.setFont(QFont("Arial", 12, QFont.Bold))
        recent_layout.addWidget(recent_meetings_label)
        
        self.meetings_table = QTableWidget()
        self.meetings_table.setColumnCount(5)
        self.meetings_table.setHorizontalHeaderLabels(["Title", "Date", "Duration", "Action Items", "Status"])
        self.meetings_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.meetings_table.setMinimumHeight(400)
        recent_layout.addWidget(self.meetings_table)
        
        # Add tabs
        self.tab_widget.addTab(meetings_tab, "Meetings")
        self.tab_widget.addTab(action_items_tab, "Action Items")
        self.tab_widget.addTab(recent_tab, "Recent Meetings")
    
    def load_data(self):
        """Load and display data."""
        try:
            # Convert QDate to datetime
            start_date = datetime(
                self.start_date_edit.date().year(),
                self.start_date_edit.date().month(),
                self.start_date_edit.date().day()
            )
            end_date = datetime(
                self.end_date_edit.date().year(),
                self.end_date_edit.date().month(),
                self.end_date_edit.date().day(),
                23, 59, 59  # End of the day
            )
            
            # Get meetings in the date range
            meetings = self.db.get_meetings(
                start_date=start_date,
                end_date=end_date,
                limit=1000
            )
            
            # Update stat cards
            self.update_stat_cards(meetings)
            
            # Update charts
            self.update_meetings_chart(meetings)
            self.update_duration_chart(meetings)
            self.update_action_items_charts(meetings)
            
            # Update recent meetings table
            self.update_meetings_table(meetings[:20])  # Show only most recent 20
            
        except Exception as e:
            logger.error(f"Error loading dashboard data: {e}")
    
    def update_stat_cards(self, meetings):
        """Update the statistics cards.
        
        Args:
            meetings: List of Meeting objects.
        """
        try:
            # Total meetings
            total_meetings = len(meetings)
            self.total_meetings_card.findChild(QLabel, "", Qt.FindDirectChildrenOnly).setText(str(total_meetings))
            
            # Total duration
            total_duration = sum(m.duration or 0 for m in meetings)
            hours, remainder = divmod(int(total_duration), 3600)
            minutes, _ = divmod(remainder, 60)
            total_duration_str = f"{hours:02d}h {minutes:02d}m"
            self.total_duration_card.findChild(QLabel, "", Qt.FindDirectChildrenOnly).setText(total_duration_str)
            
            # Average duration
            avg_duration = total_duration / total_meetings if total_meetings > 0 else 0
            avg_hours, avg_remainder = divmod(int(avg_duration), 3600)
            avg_minutes, _ = divmod(avg_remainder, 60)
            avg_duration_str = f"{avg_hours:02d}h {avg_minutes:02d}m"
            self.avg_duration_card.findChild(QLabel, "", Qt.FindDirectChildrenOnly).setText(avg_duration_str)
            
            # Total action items
            session = self.db.get_session()
            try:
                all_action_items = []
                for meeting in meetings:
                    items = self.db.get_action_items(meeting_id=meeting.id)
                    all_action_items.extend(items)
                
                total_action_items = len(all_action_items)
                self.total_action_items_card.findChild(QLabel, "", Qt.FindDirectChildrenOnly).setText(str(total_action_items))
                
                # Completion rate
                completed_items = sum(1 for item in all_action_items if item.status == "completed")
                completion_rate = (completed_items / total_action_items * 100) if total_action_items > 0 else 0
                self.completion_rate_card.findChild(QLabel, "", Qt.FindDirectChildrenOnly).setText(f"{completion_rate:.1f}%")
                
                # Average items per meeting
                avg_items = total_action_items / total_meetings if total_meetings > 0 else 0
                self.avg_items_card.findChild(QLabel, "", Qt.FindDirectChildrenOnly).setText(f"{avg_items:.1f}")
            finally:
                session.close()
            
            # Average transcript length
            total_words = 0
            transcripted_meetings = 0
            
            session = self.db.get_session()
            try:
                for meeting in meetings:
                    transcript = self.db.get_transcript(meeting.id)
                    if transcript and transcript.word_count:
                        total_words += transcript.word_count
                        transcripted_meetings += 1
                
                avg_words = total_words / transcripted_meetings if transcripted_meetings > 0 else 0
                self.avg_transcript_card.findChild(QLabel, "", Qt.FindDirectChildrenOnly).setText(f"{avg_words:.0f} words")
            finally:
                session.close()
            
            # Longest meeting
            if meetings:
                longest_meeting = max(meetings, key=lambda m: m.duration or 0)
                longest_hours, longest_remainder = divmod(int(longest_meeting.duration or 0), 3600)
                longest_minutes, _ = divmod(longest_remainder, 60)
                longest_duration_str = f"{longest_hours:02d}h {longest_minutes:02d}m"
                self.longest_meeting_card.findChild(QLabel, "", Qt.FindDirectChildrenOnly).setText(longest_duration_str)
                subtitle = longest_meeting.title[:20] + "..." if len(longest_meeting.title) > 20 else longest_meeting.title
                self.longest_meeting_card.findChild(QLabel, "", Qt.FindChildrenRecursively).setText(subtitle)
            
        except Exception as e:
            logger.error(f"Error updating stat cards: {e}")
    
    def update_meetings_chart(self, meetings):
        """Update the meetings over time chart.
        
        Args:
            meetings: List of Meeting objects.
        """
        try:
            # Group meetings by date
            meetings_by_date = {}
            
            for meeting in meetings:
                date_str = meeting.date.strftime("%Y-%m-%d")
                if date_str in meetings_by_date:
                    meetings_by_date[date_str] += 1
                else:
                    meetings_by_date[date_str] = 1
            
            # Sort dates
            sorted_dates = sorted(meetings_by_date.keys())
            
            # Create chart
            chart = QChart()
            chart.setTitle("Meetings Per Day")
            
            # Create line series
            series = QLineSeries()
            series.setName("Number of Meetings")
            
            # Add points
            for i, date_str in enumerate(sorted_dates):
                date = QDate.fromString(date_str, "yyyy-MM-dd")
                value = meetings_by_date[date_str]
                series.append(i, value)
            
            chart.addSeries(series)
            
            # Set axes
            axis_x = QBarCategoryAxis()
            axis_x.append(sorted_dates)
            chart.addAxis(axis_x, Qt.AlignBottom)
            series.attachAxis(axis_x)
            
            axis_y = QValueAxis()
            max_value = max(meetings_by_date.values()) if meetings_by_date else 5
            axis_y.setRange(0, max_value + 1)
            axis_y.setTickCount(max_value + 2)
            axis_y.setLabelFormat("%d")
            chart.addAxis(axis_y, Qt.AlignLeft)
            series.attachAxis(axis_y)
            
            # Set chart to view
            self.meetings_chart_view.setChart(chart)
            self.meetings_chart_view.setRenderHint(QPainter.Antialiasing)
            
        except Exception as e:
            logger.error(f"Error updating meetings chart: {e}")
    
    def update_duration_chart(self, meetings):
        """Update the meeting duration chart.
        
        Args:
            meetings: List of Meeting objects.
        """
        try:
            # Group meetings by duration
            duration_ranges = {
                "0-15m": 0,
                "15-30m": 0,
                "30-60m": 0,
                "1-2h": 0,
                "2h+": 0
            }
            
            for meeting in meetings:
                duration_minutes = (meeting.duration or 0) / 60
                
                if duration_minutes <= 15:
                    duration_ranges["0-15m"] += 1
                elif duration_minutes <= 30:
                    duration_ranges["15-30m"] += 1
                elif duration_minutes <= 60:
                    duration_ranges["30-60m"] += 1
                elif duration_minutes <= 120:
                    duration_ranges["1-2h"] += 1
                else:
                    duration_ranges["2h+"] += 1
            
            # Create chart
            chart = QChart()
            chart.setTitle("Meeting Duration Distribution")
            
            # Create bar set
            bar_set = QBarSet("Number of Meetings")
            
            # Add values
            for value in duration_ranges.values():
                bar_set.append(value)
            
            # Create bar series
            series = QBarSeries()
            series.append(bar_set)
            chart.addSeries(series)
            
            # Set axes
            axis_x = QBarCategoryAxis()
            axis_x.append(list(duration_ranges.keys()))
            chart.addAxis(axis_x, Qt.AlignBottom)
            series.attachAxis(axis_x)
            
            axis_y = QValueAxis()
            max_value = max(duration_ranges.values()) if duration_ranges else 5
            axis_y.setRange(0, max_value + 1)
            axis_y.setTickCount(max_value + 2)
            axis_y.setLabelFormat("%d")
            chart.addAxis(axis_y, Qt.AlignLeft)
            series.attachAxis(axis_y)
            
            # Set chart to view
            self.duration_chart_view.setChart(chart)
            self.duration_chart_view.setRenderHint(QPainter.Antialiasing)
            
        except Exception as e:
            logger.error(f"Error updating duration chart: {e}")
    
    def update_action_items_charts(self, meetings):
        """Update action items charts.
        
        Args:
            meetings: List of Meeting objects.
        """
        try:
            # Get all action items for meetings
            all_action_items = []
            for meeting in meetings:
                items = self.db.get_action_items(meeting_id=meeting.id)
                all_action_items.extend(items)
            
            # Status chart (pie chart)
            status_counts = Counter()
            for item in all_action_items:
                status_counts[item.status] += 1
            
            # Create pie series
            status_series = QPieSeries()
            
            # Add slices
            for status, count in status_counts.items():
                slice = status_series.append(status.capitalize(), count)
                
                # Set colors
                if status == "completed":
                    slice.setBrush(QColor("#4CAF50"))  # Green
                elif status == "pending":
                    slice.setBrush(QColor("#FFC107"))  # Yellow
                else:
                    slice.setBrush(QColor("#F44336"))  # Red
                
                # Explode the slices
                slice.setExploded(True)
                slice.setLabelVisible(True)
                slice.setLabelPosition(QPieSlice.LabelOutside)
                slice.setLabel(f"{status.capitalize()}: {count} ({count/sum(status_counts.values())*100:.1f}%)")
            
            # Create chart
            status_chart = QChart()
            status_chart.setTitle("Action Item Status")
            status_chart.addSeries(status_series)
            status_chart.legend().setVisible(False)
            
            # Set chart to view
            self.action_items_status_chart_view.setChart(status_chart)
            self.action_items_status_chart_view.setRenderHint(QPainter.Antialiasing)
            
            # Assignee chart
            assignee_counts = Counter()
            for item in all_action_items:
                assignee = item.assignee if item.assignee and item.assignee != "Unassigned" else "Unassigned"
                assignee_counts[assignee] += 1
            
            # Get top 10 assignees
            top_assignees = assignee_counts.most_common(10)
            
            # Create bar set
            assignee_set = QBarSet("Number of Action Items")
            
            # Add values
            for _, count in top_assignees:
                assignee_set.append(count)
            
            # Create bar series
            assignee_series = QBarSeries()
            assignee_series.append(assignee_set)
            
            # Create chart
            assignee_chart = QChart()
            assignee_chart.setTitle("Action Items by Assignee (Top 10)")
            assignee_chart.addSeries(assignee_series)
            
            # Set axes
            axis_x = QBarCategoryAxis()
            axis_x.append([name for name, _ in top_assignees])
            assignee_chart.addAxis(axis_x, Qt.AlignBottom)
            assignee_series.attachAxis(axis_x)
            
            axis_y = QValueAxis()
            max_value = max([count for _, count in top_assignees]) if top_assignees else 5
            axis_y.setRange(0, max_value + 1)
            axis_y.setTickCount(max_value + 2)
            axis_y.setLabelFormat("%d")
            assignee_chart.addAxis(axis_y, Qt.AlignLeft)
            assignee_series.attachAxis(axis_y)
            
            # Set chart to view
            self.assignee_chart_view.setChart(assignee_chart)
            self.assignee_chart_view.setRenderHint(QPainter.Antialiasing)
            
        except Exception as e:
            logger.error(f"Error updating action items charts: {e}")
    
    def update_meetings_table(self, meetings):
        """Update the recent meetings table.
        
        Args:
            meetings: List of Meeting objects to display.
        """
        try:
            # Clear table
            self.meetings_table.setRowCount(0)
            
            # Add meetings
            for i, meeting in enumerate(meetings):
                self.meetings_table.insertRow(i)
                
                # Title
                title_item = QTableWidgetItem(meeting.title)
                self.meetings_table.setItem(i, 0, title_item)
                
                # Date
                date_str = meeting.date.strftime("%Y-%m-%d %H:%M")
                date_item = QTableWidgetItem(date_str)
                self.meetings_table.setItem(i, 1, date_item)
                
                # Duration
                hours, remainder = divmod(int(meeting.duration or 0), 3600)
                minutes, _ = divmod(remainder, 60)
                duration_str = f"{hours:02d}:{minutes:02d}"
                duration_item = QTableWidgetItem(duration_str)
                self.meetings_table.setItem(i, 2, duration_item)
                
                # Action items
                action_items = self.db.get_action_items(meeting_id=meeting.id)
                action_items_item = QTableWidgetItem(str(len(action_items)))
                self.meetings_table.setItem(i, 3, action_items_item)
                
                # Status
                completed = sum(1 for item in action_items if item.status == "completed")
                total = len(action_items)
                status_str = f"{completed}/{total} completed"
                status_item = QTableWidgetItem(status_str)
                self.meetings_table.setItem(i, 4, status_item)
            
            # Resize columns to fit content
            self.meetings_table.resizeColumnsToContents()
            
        except Exception as e:
            logger.error(f"Error updating meetings table: {e}")
    
    def apply_filters(self):
        """Apply date filters and refresh data."""
        # Reload data with new filters
        self.load_data()