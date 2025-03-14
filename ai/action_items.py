"""
Action item extraction and tracking.
Extracts action items from meeting transcripts and tracks their completion status.
"""

import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import re
import openai

from utils.logger import get_logger
from utils.config import config_manager

logger = get_logger("action_items")

class ActionItem:
    """Represents an action item from a meeting."""
    
    def __init__(
        self,
        task: str,
        assignee: Optional[str] = None,
        due_date: Optional[datetime] = None,
        meeting_id: Optional[str] = None,
        status: str = "pending",
        created_at: Optional[datetime] = None,
        item_id: Optional[str] = None
    ):
        """Initialize an action item.
        
        Args:
            task: Description of the task.
            assignee: Person responsible for the task.
            due_date: When the task is due.
            meeting_id: ID of the meeting where this action item was created.
            status: Current status of the action item.
            created_at: When the action item was created.
            item_id: Unique identifier for the action item.
        """
        self.task = task
        self.assignee = assignee or "Unassigned"
        self.due_date = due_date
        self.meeting_id = meeting_id
        self.status = status  # pending, completed, or cancelled
        self.created_at = created_at or datetime.now()
        self.item_id = item_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the action item to a dictionary.
        
        Returns:
            Dictionary representation of the action item.
        """
        return {
            "task": self.task,
            "assignee": self.assignee,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "meeting_id": self.meeting_id,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "item_id": self.item_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ActionItem':
        """Create an action item from a dictionary.
        
        Args:
            data: Dictionary representation of an action item.
            
        Returns:
            An ActionItem instance.
        """
        return cls(
            task=data["task"],
            assignee=data.get("assignee"),
            due_date=datetime.fromisoformat(data["due_date"]) if data.get("due_date") else None,
            meeting_id=data.get("meeting_id"),
            status=data.get("status", "pending"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            item_id=data.get("item_id")
        )


class ActionItemExtractor:
    """Extract action items from meeting transcripts."""
    
    def __init__(self):
        """Initialize the action item extractor."""
        self.config = config_manager.config.ai
        self.client = openai.OpenAI(api_key=self.config.openai_api_key)
        self.model = self.config.summary_model
    
    async def extract_action_items(self, transcript: str, meeting_id: Optional[str] = None) -> List[ActionItem]:
        """Extract action items from a meeting transcript.
        
        Args:
            transcript: The meeting transcript.
            meeting_id: Optional ID of the meeting.
            
        Returns:
            List of extracted ActionItem objects.
        """
        try:
            logger.info("Extracting action items from transcript")
            start_time = time.time()
            
            # Run the API call in an executor to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self._create_system_prompt()},
                        {"role": "user", "content": transcript}
                    ],
                    temperature=0.1,
                    response_format={"type": "json_object"}
                )
            )
            
            # Extract and parse the response
            response_text = response.choices[0].message.content
            
            # Parse the JSON response
            import json
            try:
                action_items_data = json.loads(response_text)
                raw_items = action_items_data.get("action_items", [])
            except json.JSONDecodeError:
                logger.error("Failed to parse action items JSON")
                raw_items = []
            
            # Convert to ActionItem objects
            action_items = []
            for item in raw_items:
                due_date = self._parse_due_date(item.get("due_date", "Not specified"))
                
                action_item = ActionItem(
                    task=item.get("task", ""),
                    assignee=item.get("assignee", "Unassigned"),
                    due_date=due_date,
                    meeting_id=meeting_id,
                    status="pending"
                )
                action_items.append(action_item)
            
            elapsed = time.time() - start_time
            logger.info(f"Extracted {len(action_items)} action items in {elapsed:.2f} seconds")
            
            return action_items
            
        except Exception as e:
            logger.error(f"Error extracting action items: {e}")
            return []
    
    def _create_system_prompt(self) -> str:
        """Create a system prompt for action item extraction.
        
        Returns:
            System prompt string.
        """
        return """You are an AI assistant specializing in extracting action items from meeting transcripts.

Review the meeting transcript carefully and extract all action items, tasks, or commitments that people agreed to do.

For each action item, identify:
1. The task description
2. Who is assigned to do it
3. Any mentioned due date or deadline

Return your response as a JSON object with the following structure:
{
    "action_items": [
        {
            "task": "Description of the task",
            "assignee": "Person name or 'Unassigned'",
            "due_date": "Due date if mentioned or 'Not specified'"
        }
    ]
}

Be specific about what needs to be done and who needs to do it.
If no assignee is mentioned, use "Unassigned".
If no due date is mentioned, use "Not specified".
Only include clear commitments or tasks, not general discussions or ideas.
"""
    
    def _parse_due_date(self, date_string: str) -> Optional[datetime]:
        """Parse a due date string into a datetime object.
        
        Args:
            date_string: String representation of a due date.
            
        Returns:
            Datetime object or None if parsing fails.
        """
        if date_string in ["Not specified", "None", "Unspecified", ""]:
            return None
        
        try:
            # Try direct datetime parsing
            return datetime.fromisoformat(date_string)
        except (ValueError, TypeError):
            pass
        
        # Check for relative dates
        today = datetime.now()
        
        # Handle "today", "tomorrow"
        if re.search(r'\btoday\b', date_string, re.IGNORECASE):
            return today.replace(hour=23, minute=59, second=59)
        
        if re.search(r'\btomorrow\b', date_string, re.IGNORECASE):
            return (today + timedelta(days=1)).replace(hour=23, minute=59, second=59)
        
        # Handle "next week", "next month"
        if re.search(r'\bnext week\b', date_string, re.IGNORECASE):
            return today + timedelta(days=7)
        
        if re.search(r'\bnext month\b', date_string, re.IGNORECASE):
            # Simple approximation
            return today + timedelta(days=30)
        
        # Handle day names
        day_mapping = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 
            'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6
        }
        
        for day, day_num in day_mapping.items():
            if re.search(fr'\b{day}\b', date_string, re.IGNORECASE):
                current_day = today.weekday()
                days_ahead = (day_num - current_day) % 7
                if days_ahead == 0:  # Same day, so likely next week
                    days_ahead = 7
                return (today + timedelta(days=days_ahead)).replace(hour=23, minute=59, second=59)
        
        # Try various date formats
        date_formats = [
            "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", 
            "%B %d, %Y", "%d %B %Y", "%b %d, %Y", 
            "%d %b %Y"
        ]
        
        for fmt in date_formats:
            try:
                # Extract a date-like pattern and try to parse it
                pattern = r'\d{1,4}[-/]\d{1,2}[-/]\d{1,4}|\d{1,2} [A-Za-z]{3,9} \d{2,4}|[A-Za-z]{3,9} \d{1,2},? \d{2,4}'
                match = re.search(pattern, date_string)
                if match:
                    return datetime.strptime(match.group(), fmt)
            except ValueError:
                continue
        
        # If all else fails, return None
        return None