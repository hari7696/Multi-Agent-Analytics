"""
Cosmos DB Session Service for ADK
=================================

This module implements the CosmosSessionService class that extends BaseSessionService
to provide persistent session and event storage using Azure Cosmos DB.

Key Features:
- Full ADK BaseSessionService compatibility
- Persistent session and event storage
- State management with Cosmos DB persistence
- Event history reconstruction
- Performance optimized queries

Implementation Strategy:
- Sessions stored in Sessions collection (partition by user_id)
- Events stored in Events collection (partition by session_id, append-only)
- State stored in Sessions collection for fast access
- All 6 BaseSessionService methods implemented
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import uuid
import time
import asyncio

# ADK imports
from google.adk.sessions import BaseSessionService, Session
from google.adk.sessions.base_session_service import GetSessionConfig, ListSessionsResponse
from google.adk.events.event import Event

# Local imports
from .cosmos_client import cosmos_client
from .data_converters import (
    serialize_adk_event, deserialize_cosmos_event,
    serialize_session_for_cosmos, deserialize_session_from_cosmos
)
from config import logger


class CosmosSessionService(BaseSessionService):
    """
    ADK-compliant session service using Azure Cosmos DB for persistence.
    
    Implements all 6 BaseSessionService methods:
    - 4 Abstract methods: create_session, get_session, list_sessions, delete_session
    - 2 Inherited methods: append_event, __update_session_state (overridden for persistence)
    
    Design Principles:
    - Sessions collection: CREATE once, UPDATE state when needed, SOFT DELETE
    - Events collection: CREATE only (append-only, immutable)
    - State management: Current state in Sessions, history in Events via state_delta
    """
    
    def __init__(self):
        """Initialize Cosmos DB session service."""
        self.cosmos_client = cosmos_client
        logger.info("CosmosSessionService initialized with Cosmos DB persistence")
    
    # ========================================================================
    # ABSTRACT METHODS (Required Implementation)
    # ========================================================================
    
    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        state: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Session:
        """
        Create a new session with optional initial state.
        
        Args:
            app_name: Name of the application
            user_id: User identifier
            state: Initial session state dictionary
            session_id: Optional session ID (generated if not provided)
            
        Returns:
            Created Session object
        """
        try:
            # Generate session ID if not provided
            if not session_id:
                session_id = str(uuid.uuid4())
            
            # Prepare metadata for Cosmos DB
            metadata = {
                "app_name": app_name,
                "initial_state": state or {},
                "created_by": "cosmos_session_service",
                "version": "1.0"
            }
            
            # Create session in Cosmos DB
            cosmos_session = self.cosmos_client.create_session(
                session_id=session_id,
                user_id=user_id,
                metadata=metadata
            )
            
            # Create ADK Session object
            session = Session(
                id=session_id,
                app_name=app_name,
                user_id=user_id,
                state=state or {},
                events=[],  # No events initially
                last_update_time=datetime.now(timezone.utc).timestamp()
            )
            
            logger.info(f"Created session {session_id} for user {user_id} in app {app_name}")
            return session
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise
    
    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: Optional[GetSessionConfig] = None,
    ) -> Optional[Session]:
        """
        Get session by ID with full event history loaded.
        
        Args:
            app_name: Name of the application
            user_id: User identifier
            session_id: Session identifier
            config: Optional configuration for event loading
            
        Returns:
            Session object with events loaded, or None if not found
        """
        try:
            # Get session document from Cosmos DB
            cosmos_session = self.cosmos_client.get_session(session_id, user_id)
            if not cosmos_session:
                logger.debug(f"Session {session_id} not found for user {user_id}")
                return None
            
            # Determine event loading parameters
            event_limit = 50  # Default limit
            after_timestamp = None
            
            if config:
                if config.num_recent_events:
                    event_limit = config.num_recent_events
                if config.after_timestamp:
                    after_timestamp = config.after_timestamp
            
            # Load events from Cosmos DB
            cosmos_events = self.cosmos_client.get_session_events(session_id, limit=event_limit)
            
            # Filter events by timestamp if specified
            if after_timestamp:
                cosmos_events = [
                    event for event in cosmos_events 
                    if event.get("timestamp", 0) > after_timestamp
                ]
            
            # Convert Cosmos events to ADK Events
            adk_events = []
            for cosmos_event in cosmos_events:
                try:
                    event_dict = deserialize_cosmos_event(cosmos_event)
                    adk_event = Event(**event_dict)
                    adk_events.append(adk_event)
                except Exception as e:
                    logger.error(f"Failed to deserialize event: {e}")
                    continue
            
            # Create ADK Session with loaded events
            session_dict = deserialize_session_from_cosmos(cosmos_session, adk_events)
            session = Session(**session_dict)
            
            logger.debug(f"Loaded session {session_id} with {len(adk_events)} events")
            return session
            
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None
    
    async def list_sessions(
        self, *, app_name: str, user_id: str
    ) -> ListSessionsResponse:
        """
        List all sessions for a user in the specified app.
        
        Args:
            app_name: Name of the application
            user_id: User identifier
            
        Returns:
            ListSessionsResponse with session metadata (no events loaded)
        """
        try:
            # Get sessions from Cosmos DB
            cosmos_sessions = self.cosmos_client.list_user_sessions(user_id, limit=50)
            
            # Filter by app_name and convert to ADK Sessions
            sessions = []
            for cosmos_session in cosmos_sessions:
                # Check if session belongs to the specified app
                if cosmos_session.get("app_name") == app_name:
                    try:
                        # Create Session object without events (metadata only)
                        session_dict = deserialize_session_from_cosmos(cosmos_session, [])
                        session = Session(**session_dict)
                        sessions.append(session)
                    except Exception as e:
                        logger.error(f"Failed to create session from metadata: {e}")
                        continue
            
            logger.debug(f"Listed {len(sessions)} sessions for user {user_id} in app {app_name}")
            return ListSessionsResponse(sessions=sessions)
            
        except Exception as e:
            logger.error(f"Failed to list sessions for user {user_id}: {e}")
            return ListSessionsResponse(sessions=[])
    
    async def delete_session(
        self, *, app_name: str, user_id: str, session_id: str
    ) -> None:
        """
        Delete a session (soft delete - mark as deleted).
        
        Args:
            app_name: Name of the application
            user_id: User identifier
            session_id: Session identifier
        """
        try:
            # Soft delete in Cosmos DB
            self.cosmos_client.delete_session(session_id, user_id)
            logger.info(f"Deleted session {session_id} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            raise
    
    # ========================================================================
    # INHERITED METHODS (Override for Persistence)
    # ========================================================================
    
    async def append_event(self, session: Session, event: Event) -> Event:
        """
        Append event to session and persist to Cosmos DB.
        
        This method overrides the base implementation to add Cosmos DB persistence.
        
        Args:
            session: Session object to append event to
            event: Event object to append
            
        Returns:
            The appended event
        """
        try:
            # Skip partial events (as per base implementation)
            if event.partial:
                return event
            
            # Update session state based on event (calls __update_session_state)
            self.__update_session_state(session, event)
            
            # Add event to session's events list (in-memory)
            session.events.append(event)
            
            # Update session timestamp
            session.last_update_time = datetime.now(timezone.utc).timestamp()
            
            # Serialize and store event in Cosmos DB
            event_data = serialize_adk_event(event)
            event_data["user_id"] = session.user_id  # Add denormalization
            
            success = self.cosmos_client.store_event(session.id, event_data)
            if not success:
                logger.error(f"Failed to store event {event.id} in Cosmos DB")
            
            logger.debug(f"Appended and persisted event {event.id} to session {session.id}")
            return event
            
        except Exception as e:
            logger.error(f"Failed to append event to session {session.id}: {e}")
            return event
    
    def __update_session_state(self, session: Session, event: Event) -> None:
        """
        Update session state based on event and persist to Cosmos DB.
        
        This method overrides the base implementation to add Cosmos DB persistence.
        
        Args:
            session: Session object to update
            event: Event containing potential state changes
        """
        try:
            # Update in-memory session state with state_delta from event
            if event.actions and event.actions.state_delta:
                # Apply state delta to session state
                for key, value in event.actions.state_delta.items():
                    session.state[key] = value
                
            
            # Check if state was actually updated
            if event.actions and event.actions.state_delta:
                # Persist updated state to Cosmos DB
                updates = {
                    "state": session.state,
                    "last_update_time": datetime.now(timezone.utc).timestamp()
                }
                
                result = self.cosmos_client.update_session(
                    session.id, session.user_id, updates
                )
                
                if result:
                    logger.debug(f"Updated session state in Cosmos DB for session {session.id}")
                else:
                    logger.error(f"Failed to update session state in Cosmos DB for session {session.id}")
            
        except Exception as e:
            logger.error(f"Failed to update session state for session {session.id}: {e}")
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def update_session_state(self, app_name: str, user_id: str, session_id: str, state: Dict[str, Any]) -> bool:
        """
        Update session state in Cosmos DB.
        
        Args:
            app_name: Name of the application
            user_id: User identifier
            session_id: Session identifier
            state: New state dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            updates = {
                "state": state,
                "last_update_time": datetime.now(timezone.utc).timestamp()
            }
            
            result = self.cosmos_client.update_session(session_id, user_id, updates)
            if result:
                logger.debug(f"Updated session state for session {session_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to update session state for session {session_id}: {e}")
            return False
    
    def save_conversation_turn(self, session_id: str, turn_data: Dict[str, Any], execution_time: float) -> bool:
        """
        Save a conversation turn.
        
        Args:
            session_id: Session identifier
            turn_data: Conversation turn data
            execution_time: Execution time in seconds
            
        Returns:
            True if successful, False otherwise
        """
        return self.cosmos_client.save_conversation_turn(session_id, turn_data, execution_time)
    
    def get_session_sync(self, app_name: str, user_id: str, session_id: str) -> Optional[Session]:
        """
        Synchronous version of get_session for testing purposes.
        
        Args:
            app_name: Name of the application
            user_id: User identifier
            session_id: Session identifier
            
        Returns:
            Session object or None if not found
        """
        try:
            # Run async method in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    self.get_session(
                        app_name=app_name,
                        user_id=user_id,
                        session_id=session_id
                    )
                )
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"Failed to get session synchronously: {e}")
            return None
    
    def test_cosmos_connection(self) -> bool:
        """
        Test Cosmos DB connection.
        
        Returns:
            True if connection is successful, False otherwise
        """
        return self.cosmos_client.test_connection()


# Global instance for easy import
cosmos_session_service = CosmosSessionService()
