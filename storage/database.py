"""
Database operations for the AI Meeting Assistant.
Handles storage and retrieval of meeting data, transcripts, and summaries.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union

import sqlalchemy as sa
from sqlalchemy import (
    create_engine, Column, String, Text, DateTime, 
    Integer, Float, Boolean, ForeignKey, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session

from utils.logger import get_logger
from utils.config import config_manager

logger = get_logger("database")

# Create the declarative base
Base = declarative_base()


class Meeting(Base):
    """Meeting table model."""
    
    __tablename__ = "meetings"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    date = Column(DateTime, nullable=False, default=datetime.now)
    duration = Column(Float, nullable=True)  # Duration in seconds
    participants = Column(Text, nullable=True)  # JSON string of participants
    tags = Column(Text, nullable=True)  # JSON string of tags
    transcript_path = Column(String(255), nullable=True)  # Path to transcript file
    audio_path = Column(String(255), nullable=True)  # Path to audio file
    notes = Column(Text, nullable=True)  # Additional notes
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    transcript = relationship("Transcript", back_populates="meeting", uselist=False, cascade="all, delete-orphan")
    summary = relationship("Summary", back_populates="meeting", uselist=False, cascade="all, delete-orphan")
    action_items = relationship("ActionItem", back_populates="meeting", cascade="all, delete-orphan")


class Transcript(Base):
    """Transcript table model."""
    
    __tablename__ = "transcripts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=False)
    full_text = Column(Text, nullable=False)
    segments = Column(Text, nullable=True)  # JSON string of transcript segments
    language = Column(String(10), nullable=True)
    word_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    meeting = relationship("Meeting", back_populates="transcript")


class Summary(Base):
    """Summary table model."""
    
    __tablename__ = "summaries"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=False)
    summary_text = Column(Text, nullable=False)
    key_points = Column(Text, nullable=True)  # JSON string of key points
    topics = Column(Text, nullable=True)  # JSON string of topics
    decisions = Column(Text, nullable=True)  # JSON string of decisions
    questions = Column(Text, nullable=True)  # JSON string of questions and answers
    model_used = Column(String(50), nullable=True)  # Model used for summarization
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    meeting = relationship("Meeting", back_populates="summary")


class ActionItem(Base):
    """Action item table model."""
    
    __tablename__ = "action_items"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=False)
    task = Column(Text, nullable=False)
    assignee = Column(String(100), nullable=True)
    due_date = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="pending")  # pending, completed, or cancelled
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    meeting = relationship("Meeting", back_populates="action_items")


class Database:
    """Database manager for the AI Meeting Assistant."""
    
    def __init__(self):
        """Initialize the database connection."""
        self.config = config_manager.config.storage
        self.db_path = self.config.database_path
        self.engine = self._create_engine()
        self.Session = sessionmaker(bind=self.engine)
        
        # Create tables if they don't exist
        self._create_tables()
    
    def _create_engine(self):
        """Create SQLAlchemy engine.
        
        Returns:
            SQLAlchemy engine instance.
        """
        db_url = f"sqlite:///{self.db_path}"
        logger.info(f"Connecting to database at {self.db_path}")
        return create_engine(db_url)
    
    def _create_tables(self):
        """Create database tables if they don't exist."""
        try:
            logger.info("Creating database tables if they don't exist")
            Base.metadata.create_all(self.engine)
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise
    
    def get_session(self) -> Session:
        """Get a database session.
        
        Returns:
            SQLAlchemy session instance.
        """
        return self.Session()
    
    # Meeting operations
    
    def create_meeting(self, title: str, date: Optional[datetime] = None, 
                       duration: Optional[float] = None, participants: Optional[List[str]] = None,
                       tags: Optional[List[str]] = None, notes: Optional[str] = None,
                       transcript_path: Optional[str] = None, audio_path: Optional[str] = None) -> Meeting:
        """Create a new meeting record.
        
        Args:
            title: Meeting title.
            date: Meeting date and time.
            duration: Meeting duration in seconds.
            participants: List of participant names.
            tags: List of tags for the meeting.
            notes: Additional notes.
            transcript_path: Path to the transcript file.
            audio_path: Path to the audio file.
            
        Returns:
            Newly created Meeting object.
        """
        session = self.get_session()
        try:
            meeting = Meeting(
                title=title,
                date=date or datetime.now(),
                duration=duration,
                participants=json.dumps(participants) if participants else None,
                tags=json.dumps(tags) if tags else None,
                notes=notes,
                transcript_path=transcript_path,
                audio_path=audio_path
            )
            
            session.add(meeting)
            session.commit()
            logger.info(f"Created new meeting: {meeting.id} - {meeting.title}")
            return meeting
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating meeting: {e}")
            raise
        finally:
            session.close()
    
    def get_meeting(self, meeting_id: str) -> Optional[Meeting]:
        """Get a meeting by ID.
        
        Args:
            meeting_id: Meeting ID.
            
        Returns:
            Meeting object or None if not found.
        """
        session = self.get_session()
        try:
            meeting = session.query(Meeting).filter(Meeting.id == meeting_id).first()
            return meeting
        finally:
            session.close()
    
    def get_meetings(self, limit: int = 100, offset: int = 0, 
                    tags: Optional[List[str]] = None, 
                    start_date: Optional[datetime] = None,
                    end_date: Optional[datetime] = None) -> List[Meeting]:
        """Get a list of meetings with optional filtering.
        
        Args:
            limit: Maximum number of meetings to return.
            offset: Number of meetings to skip.
            tags: Filter by tags.
            start_date: Filter by start date.
            end_date: Filter by end date.
            
        Returns:
            List of Meeting objects.
        """
        session = self.get_session()
        try:
            query = session.query(Meeting)
            
            if tags:
                # Filter by any of the tags
                tag_filters = []
                for tag in tags:
                    tag_filters.append(Meeting.tags.like(f'%"{tag}"%'))
                query = query.filter(sa.or_(*tag_filters))
            
            if start_date:
                query = query.filter(Meeting.date >= start_date)
            
            if end_date:
                query = query.filter(Meeting.date <= end_date)
            
            # Order by date, most recent first
            query = query.order_by(Meeting.date.desc())
            
            # Apply limit and offset
            meetings = query.limit(limit).offset(offset).all()
            return meetings
        finally:
            session.close()
    
    def update_meeting(self, meeting_id: str, **kwargs) -> Optional[Meeting]:
        """Update a meeting.
        
        Args:
            meeting_id: Meeting ID.
            **kwargs: Fields to update.
            
        Returns:
            Updated Meeting object or None if not found.
        """
        session = self.get_session()
        try:
            meeting = session.query(Meeting).filter(Meeting.id == meeting_id).first()
            if not meeting:
                return None
            
            # Handle special fields
            if 'participants' in kwargs:
                kwargs['participants'] = json.dumps(kwargs['participants'])
            
            if 'tags' in kwargs:
                kwargs['tags'] = json.dumps(kwargs['tags'])
            
            # Update fields
            for key, value in kwargs.items():
                if hasattr(meeting, key):
                    setattr(meeting, key, value)
            
            session.commit()
            logger.info(f"Updated meeting: {meeting_id}")
            return meeting
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating meeting: {e}")
            raise
        finally:
            session.close()
    
    def delete_meeting(self, meeting_id: str) -> bool:
        """Delete a meeting.
        
        Args:
            meeting_id: Meeting ID.
            
        Returns:
            True if deleted, False if not found.
        """
        session = self.get_session()
        try:
            meeting = session.query(Meeting).filter(Meeting.id == meeting_id).first()
            if not meeting:
                return False
            
            session.delete(meeting)
            session.commit()
            logger.info(f"Deleted meeting: {meeting_id}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting meeting: {e}")
            raise
        finally:
            session.close()
    
    # Transcript operations
    
    def create_transcript(self, meeting_id: str, full_text: str, segments: Optional[List[Dict]] = None,
                         language: Optional[str] = None) -> Optional[Transcript]:
        """Create a transcript for a meeting.
        
        Args:
            meeting_id: Meeting ID.
            full_text: Full transcript text.
            segments: List of transcript segments.
            language: Transcript language.
            
        Returns:
            Newly created Transcript object or None if meeting not found.
        """
        session = self.get_session()
        try:
            # Check if meeting exists
            meeting = session.query(Meeting).filter(Meeting.id == meeting_id).first()
            if not meeting:
                logger.error(f"Meeting not found: {meeting_id}")
                return None
            
            # Check if transcript already exists
            existing = session.query(Transcript).filter(Transcript.meeting_id == meeting_id).first()
            if existing:
                logger.warning(f"Transcript already exists for meeting {meeting_id}, updating")
                existing.full_text = full_text
                existing.segments = json.dumps(segments) if segments else None
                existing.language = language
                existing.word_count = len(full_text.split()) if full_text else 0
                existing.updated_at = datetime.now()
                session.commit()
                return existing
            
            # Create new transcript
            transcript = Transcript(
                meeting_id=meeting_id,
                full_text=full_text,
                segments=json.dumps(segments) if segments else None,
                language=language,
                word_count=len(full_text.split()) if full_text else 0
            )
            
            session.add(transcript)
            session.commit()
            logger.info(f"Created transcript for meeting: {meeting_id}")
            return transcript
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating transcript: {e}")
            raise
        finally:
            session.close()
    
    def get_transcript(self, meeting_id: str) -> Optional[Transcript]:
        """Get a meeting transcript.
        
        Args:
            meeting_id: Meeting ID.
            
        Returns:
            Transcript object or None if not found.
        """
        session = self.get_session()
        try:
            transcript = session.query(Transcript).filter(Transcript.meeting_id == meeting_id).first()
            return transcript
        finally:
            session.close()
    
    # Summary operations
    
    def create_summary(self, meeting_id: str, summary_text: str, key_points: Optional[List[str]] = None,
                      topics: Optional[List[Dict]] = None, decisions: Optional[List[str]] = None,
                      questions: Optional[List[Dict]] = None, model_used: Optional[str] = None) -> Optional[Summary]:
        """Create a summary for a meeting.
        
        Args:
            meeting_id: Meeting ID.
            summary_text: Summary text.
            key_points: List of key points.
            topics: List of topics.
            decisions: List of decisions.
            questions: List of questions and answers.
            model_used: Model used for summarization.
            
        Returns:
            Newly created Summary object or None if meeting not found.
        """
        session = self.get_session()
        try:
            # Check if meeting exists
            meeting = session.query(Meeting).filter(Meeting.id == meeting_id).first()
            if not meeting:
                logger.error(f"Meeting not found: {meeting_id}")
                return None
            
            # Check if summary already exists
            existing = session.query(Summary).filter(Summary.meeting_id == meeting_id).first()
            if existing:
                logger.warning(f"Summary already exists for meeting {meeting_id}, updating")
                existing.summary_text = summary_text
                existing.key_points = json.dumps(key_points) if key_points else None
                existing.topics = json.dumps(topics) if topics else None
                existing.decisions = json.dumps(decisions) if decisions else None
                existing.questions = json.dumps(questions) if questions else None
                existing.model_used = model_used
                existing.updated_at = datetime.now()
                session.commit()
                return existing
            
            # Create new summary
            summary = Summary(
                meeting_id=meeting_id,
                summary_text=summary_text,
                key_points=json.dumps(key_points) if key_points else None,
                topics=json.dumps(topics) if topics else None,
                decisions=json.dumps(decisions) if decisions else None,
                questions=json.dumps(questions) if questions else None,
                model_used=model_used
            )
            
            session.add(summary)
            session.commit()
            logger.info(f"Created summary for meeting: {meeting_id}")
            return summary
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating summary: {e}")
            raise
        finally:
            session.close()
    
    def get_summary(self, meeting_id: str) -> Optional[Summary]:
        """Get a meeting summary.
        
        Args:
            meeting_id: Meeting ID.
            
        Returns:
            Summary object or None if not found.
        """
        session = self.get_session()
        try:
            summary = session.query(Summary).filter(Summary.meeting_id == meeting_id).first()
            return summary
        finally:
            session.close()
    
    # Action item operations
    
    def create_action_item(self, meeting_id: str, task: str, assignee: Optional[str] = None,
                         due_date: Optional[datetime] = None, status: str = "pending") -> Optional[ActionItem]:
        """Create an action item for a meeting.
        
        Args:
            meeting_id: Meeting ID.
            task: Action item task description.
            assignee: Person assigned to the task.
            due_date: Task due date.
            status: Task status.
            
        Returns:
            Newly created ActionItem object or None if meeting not found.
        """
        session = self.get_session()
        try:
            # Check if meeting exists
            meeting = session.query(Meeting).filter(Meeting.id == meeting_id).first()
            if not meeting:
                logger.error(f"Meeting not found: {meeting_id}")
                return None
            
            # Create new action item
            action_item = ActionItem(
                meeting_id=meeting_id,
                task=task,
                assignee=assignee,
                due_date=due_date,
                status=status
            )
            
            session.add(action_item)
            session.commit()
            logger.info(f"Created action item for meeting: {meeting_id}")
            return action_item
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating action item: {e}")
            raise
        finally:
            session.close()
    
    def get_action_items(self, meeting_id: Optional[str] = None, status: Optional[str] = None,
                        assignee: Optional[str] = None) -> List[ActionItem]:
        """Get action items with optional filtering.
        
        Args:
            meeting_id: Filter by meeting ID.
            status: Filter by status.
            assignee: Filter by assignee.
            
        Returns:
            List of ActionItem objects.
        """
        session = self.get_session()
        try:
            query = session.query(ActionItem)
            
            if meeting_id:
                query = query.filter(ActionItem.meeting_id == meeting_id)
            
            if status:
                query = query.filter(ActionItem.status == status)
            
            if assignee:
                query = query.filter(ActionItem.assignee == assignee)
            
            # Order by due date if available, otherwise by creation date
            query = query.order_by(
                sa.case(
                    (ActionItem.due_date.is_(None), 1),
                    else_=0
                ),
                ActionItem.due_date,
                ActionItem.created_at
            )
            
            items = query.all()
            return items
        finally:
            session.close()
    
    def update_action_item(self, item_id: str, **kwargs) -> Optional[ActionItem]:
        """Update an action item.
        
        Args:
            item_id: Action item ID.
            **kwargs: Fields to update.
            
        Returns:
            Updated ActionItem object or None if not found.
        """
        session = self.get_session()
        try:
            item = session.query(ActionItem).filter(ActionItem.id == item_id).first()
            if not item:
                return None
            
            # Update fields
            for key, value in kwargs.items():
                if hasattr(item, key):
                    setattr(item, key, value)
            
            session.commit()
            logger.info(f"Updated action item: {item_id}")
            return item
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating action item: {e}")
            raise
        finally:
            session.close()
    
    def delete_action_item(self, item_id: str) -> bool:
        """Delete an action item.
        
        Args:
            item_id: Action item ID.
            
        Returns:
            True if deleted, False if not found.
        """
        session = self.get_session()
        try:
            item = session.query(ActionItem).filter(ActionItem.id == item_id).first()
            if not item:
                return False
            
            session.delete(item)
            session.commit()
            logger.info(f"Deleted action item: {item_id}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting action item: {e}")
            raise
        finally:
            session.close()