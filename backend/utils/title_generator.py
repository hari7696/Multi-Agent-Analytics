#!/usr/bin/env python3
"""
Azure OpenAI Chat Title Generator
Simple and effective title generation using Azure OpenAI for financial chat sessions
"""

import os
import threading
from datetime import datetime
from typing import Optional
import litellm
from config import logger, api_base, api_key, api_version


class ChatTitleGenerator:
    """Generate intelligent chat titles using Azure OpenAI"""
    
    def __init__(self):
        """Initialize the Azure OpenAI client"""
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize LiteLLM client using config.py settings"""
        try:
            # Use the same configuration as the main system
            if not api_base or not api_key:
                logger.warning("Azure OpenAI credentials not found in config, falling back to rule-based generation")
                return
            
            # LiteLLM is already configured in config.py, so we can use it directly
            self.client = True  # Flag to indicate LiteLLM is available
            logger.info("LiteLLM client initialized for title generation using config.py settings")
            
        except Exception as e:
            logger.warning(f"Failed to initialize LiteLLM client: {e}")
            self.client = None
    
    def generate_title(self, user_message: str, chat_history: Optional[list] = None) -> str:
        """
        Generate a concise title for a chat session based on the user query.
        
        Args:
            user_message: The user's message that triggered title generation
            chat_history: Previous messages in the session (optional)
            
        Returns:
            str: A short title for the chat session
        """
        if not user_message or not user_message.strip():
            return "New Chat"
        
        # Try LiteLLM first
        if self.client:
            try:
                return self._generate_with_litellm(user_message, chat_history)
            except Exception as e:
                logger.warning(f"LiteLLM title generation failed: {e}, falling back to rule-based")
        
        # Fallback to rule-based generation
        return self._generate_fallback_title(user_message)
    
    def _generate_with_litellm(self, user_message: str, chat_history: Optional[list] = None) -> str:
        """Generate title using LiteLLM with Azure OpenAI"""
        # Prepare context
        history_context = ""
        if chat_history and len(chat_history) > 0:
            recent_messages = chat_history[-3:]  # Last 3 messages for context
            history_context = f"\nRecent conversation:\n{chr(10).join(recent_messages)}"
        
        prompt = f"""Generate a concise, descriptive title (maximum 5 words) for this financial chat session.

Current user message: {user_message.strip()}{history_context}

Rules:
- Maximum 5 words
- Focus on the main topic or request
- Use business/financial terminology when relevant
- Be specific and actionable
- No quotes or special characters

Examples:
- "Revenue Analysis Q1 2024"
- "Outstanding Invoice Report"
- "Contract Performance Review"
- "Budget Forecast Planning"

Title:"""

        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that creates concise, professional titles for business conversations. Always respond with just the title, no additional text."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ]
            
            response = litellm.completion(
                model="azure/gpt-4.1",  # Using the same model as config.py
                messages=messages,
                max_tokens=20,
                temperature=0.3,
                top_p=0.9
            )
            
            title = response.choices[0].message.content.strip()
            
            # Clean up the response
            title = title.replace('"', '').replace("'", '').strip()
            
            # Ensure it's not too long (max 5 words or 50 characters)
            words = title.split()
            if len(words) > 5:
                title = ' '.join(words[:5])
            
            # Hard character limit
            if len(title) > 25:
                title = title[:22] + '...'
            
            logger.debug(f"Generated title with LiteLLM: {title}")
            return title if title else self._generate_fallback_title(user_message)
            
        except Exception as e:
            logger.error(f"LiteLLM API call failed: {e}")
            raise
    
    def _generate_fallback_title(self, user_message: str) -> str:
        """Simple rule-based fallback title generation"""
        try:
            # Clean the message
            words = user_message.strip().split()
            
            # Remove common filler words
            filler_words = {'can', 'you', 'please', 'help', 'me', 'show', 'tell', 'i', 'want', 'to', 'need', 'would', 'like'}
            meaningful_words = [word for word in words if word.lower() not in filler_words]
            
            # If we have meaningful words, use them
            if meaningful_words:
                title = ' '.join(meaningful_words[:4])  # Max 4 words
            else:
                title = ' '.join(words[:4])  # Max 4 words from original
            
            # Capitalize first letter
            if title:
                title = title[0].upper() + title[1:] if len(title) > 1 else title.upper()
            
            # Hard character limit
            if len(title) > 25:
                title = title[:22] + '...'
            
            return title if title else "New Chat"
            
        except Exception as e:
            logger.error(f"Fallback title generation failed: {e}")
            return f"Chat {datetime.now().strftime('%m/%d')}"
    
    def generate_title_async(self, user_message: str, session_id: str, user_id: str, 
                           chat_history: Optional[list] = None, 
                           update_callback: Optional[callable] = None):
        """
        Generate title asynchronously in a background thread
        
        Args:
            user_message: The user's message
            session_id: Session ID to update
            user_id: User ID
            chat_history: Previous messages (optional)
            update_callback: Callback function to update the session title
        """
        def title_generation_task():
            try:
                title = self.generate_title(user_message, chat_history)

                if len(title) > 25:
                    title = title[:22] + '...'
                
                if update_callback and title and title != "New Chat":
                    update_callback(session_id, user_id, title)
                    logger.info(f"Updated session {session_id} title: {title}")
                    
            except Exception as e:
                logger.error(f"Async title generation failed for session {session_id}: {e}")
        
        # Start background thread
        thread = threading.Thread(target=title_generation_task, daemon=True)
        thread.start()


# Global instance
_title_generator = None

def get_title_generator() -> ChatTitleGenerator:
    """Get or create the global title generator instance"""
    global _title_generator
    if _title_generator is None:
        _title_generator = ChatTitleGenerator()
    return _title_generator

def generate_chat_title(user_message: str, chat_history: Optional[list] = None) -> str:
    """Convenience function to generate a chat title"""
    generator = get_title_generator()
    return generator.generate_title(user_message, chat_history)