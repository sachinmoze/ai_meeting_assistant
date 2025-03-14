"""
Meeting summarization using GPT-4.
Generates concise summaries, action items, and key points from meeting transcripts.
"""

import time
import asyncio
from typing import Dict, List, Optional, Any
import openai

from utils.logger import get_logger
from utils.config import config_manager

logger = get_logger("summarization")

class MeetingSummarizer:
    """Summarize meeting transcripts using GPT-4."""
    
    def __init__(self):
        """Initialize the meeting summarizer."""
        self.config = config_manager.config.ai
        self.client = openai.OpenAI(api_key=self.config.openai_api_key)
        self.model = self.config.summary_model
    
    async def summarize(self, transcript: str, meeting_title: Optional[str] = None, 
                        meeting_context: Optional[str] = None) -> Dict[str, Any]:
        """Summarize a meeting transcript.
        
        Args:
            transcript: The full meeting transcript.
            meeting_title: Optional title of the meeting.
            meeting_context: Optional context about the meeting.
            
        Returns:
            Dictionary containing summary, action items, and key points.
        """
        try:
            logger.info(f"Generating summary for transcript of length {len(transcript)}")
            start_time = time.time()
            
            system_prompt = self._create_system_prompt(meeting_title, meeting_context)
            
            # Run the API call in an executor to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": transcript}
                    ],
                    temperature=0.2,
                    response_format={"type": "json_object"}
                )
            )
            
            # Extract and parse the response
            summary_text = response.choices[0].message.content
            
            # Parse the JSON response
            import json
            try:
                summary_data = json.loads(summary_text)
            except json.JSONDecodeError:
                logger.error("Failed to parse summary JSON, returning raw text")
                summary_data = {
                    "summary": summary_text,
                    "action_items": [],
                    "key_points": []
                }
            
            elapsed = time.time() - start_time
            logger.info(f"Summary generated in {elapsed:.2f} seconds")
            
            # Add processing metadata
            summary_data["processing_time"] = elapsed
            summary_data["model_used"] = self.model
            
            return summary_data
            
        except Exception as e:
            logger.error(f"Error generating meeting summary: {e}")
            return {
                "summary": f"Error generating summary: {str(e)}",
                "action_items": [],
                "key_points": [],
                "topics": [],
                "processing_time": 0,
                "model_used": self.model
            }
    
    def _create_system_prompt(self, meeting_title: Optional[str], 
                             meeting_context: Optional[str]) -> str:
        """Create a system prompt for the GPT model.
        
        Args:
            meeting_title: Optional title of the meeting.
            meeting_context: Optional context about the meeting.
            
        Returns:
            System prompt string.
        """
        title_info = f"Title: {meeting_title}\n" if meeting_title else ""
        context_info = f"Context: {meeting_context}\n" if meeting_context else ""
        
        return f"""You are an AI meeting assistant that creates clear, concise summaries of meeting transcripts.

{title_info}{context_info}

Analyze the meeting transcript and produce a JSON response with the following structure:
{{
    "summary": "A concise 3-5 paragraph summary of the meeting highlighting the main topics and decisions",
    "action_items": [
        {{
            "assignee": "Person name or 'Unassigned'",
            "task": "Description of the action item",
            "due_date": "Due date if mentioned or 'Not specified'"
        }}
    ],
    "key_points": [
        "Key point 1",
        "Key point 2"
    ],
    "topics": [
        {{
            "name": "Topic name",
            "discussion": "Brief summary of the discussion about this topic"
        }}
    ],
    "decisions": [
        "Decision 1",
        "Decision 2"
    ],
    "questions": [
        {{
            "question": "Question raised in the meeting",
            "answer": "Answer provided if any, or 'Unanswered'"
        }}
    ]
}}

Focus on extracting concrete information, decisions, and next steps. Be precise and factual.
Identify distinct topics discussed, even if they weren't explicitly labeled as topics.
Group related points under the same topic.
For action items, try to identify who is responsible and any mentioned deadlines.
"""
    
    async def generate_meeting_title(self, transcript: str) -> str:
        """Generate a title for a meeting based on its transcript.
        
        Args:
            transcript: The meeting transcript.
            
        Returns:
            A generated meeting title.
        """
        try:
            # Use a shorter portion of the transcript
            truncated = transcript[:5000] if len(transcript) > 5000 else transcript
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "Generate a brief, specific title for this meeting transcript. The title should capture the main purpose or focus of the meeting in 10 words or less."},
                        {"role": "user", "content": truncated}
                    ],
                    temperature=0.3,
                    max_tokens=50
                )
            )
            
            title = response.choices[0].message.content.strip()
            # Remove quotes if they're present
            title = title.strip('"\'')
            
            return title
            
        except Exception as e:
            logger.error(f"Error generating meeting title: {e}")
            return "Meeting Transcript"