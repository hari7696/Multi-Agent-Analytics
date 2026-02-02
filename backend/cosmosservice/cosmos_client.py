"""
Cosmos DB Client for ADK Session and Event Storage
=================================================

This module provides a CosmosDBClient class that handles all direct Cosmos DB operations
for storing and retrieving ADK sessions and events.

Key Design Principles:
- Sessions Collection: CREATE once, UPDATE state when needed, SOFT DELETE
- Events Collection: CREATE only (append-only, immutable)
- Partition Keys: Sessions by user_id, Events by session_id
"""

import os
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import json
import logging

from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosResourceExistsError, CosmosResourceNotFoundError

# Use the same logger as the main application
from config import logger


class CosmosDBClient:
    """
    Cosmos DB client for ADK session and event storage.
    
    Handles all direct database operations with proper error handling,
    validation, and performance optimization.
    """
    
    def __init__(self):
        """Initialize Cosmos DB client with environment configuration."""
        # Load configuration from environment
        self.endpoint = os.getenv("COSMOSDB_ENDPOINT")
        self.key = os.getenv("COSMOSDB_KEY")
        self.database_name = os.getenv("COSMOSDB_DATABASE")
        self.session_container_name = os.getenv("COSMOSDB_SESSION_CONTAINER", "sessions")
        self.event_container_name = os.getenv("COSMOSDB_CONVERSATION_CONTAINER", "events")
        
        # Validate required configuration
        if not all([self.endpoint, self.key, self.database_name]):
            raise ValueError(
                "Missing required Cosmos DB configuration. Please set: "
                "COSMOSDB_ENDPOINT, COSMOSDB_KEY, COSMOSDB_DATABASE"
            )
        
        # Initialize Cosmos client
        self.client = CosmosClient(self.endpoint, self.key)
        self.database = None
        self.session_container = None
        self.event_container = None
        
        # Initialize database and containers
        self._initialize_database()
        
        logger.info(f"CosmosDBClient initialized for database: {self.database_name}")
    
    def _initialize_database(self):
        """Initialize database and containers with proper partition keys."""
        try:
            # Create database if it doesn't exist
            self.database = self.client.create_database_if_not_exists(
                id=self.database_name
            )
            logger.info(f"Database '{self.database_name}' initialized")
            
            # Create sessions container (partition by user_id)
            self.session_container = self.database.create_container_if_not_exists(
                id=self.session_container_name,
                partition_key=PartitionKey(path="/user_id")
            )
            logger.info(f"Sessions container '{self.session_container_name}' initialized")
            
            # Create events container (partition by session_id)
            self.event_container = self.database.create_container_if_not_exists(
                id=self.event_container_name,
                partition_key=PartitionKey(path="/session_id")
            )
            logger.info(f"Events container '{self.event_container_name}' initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Cosmos DB: {e}")
            raise
    
    # ========================================================================
    # SESSION OPERATIONS (Sessions Collection)
    # ========================================================================
    
    def create_session(self, session_id: str, user_id: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a new session document in Sessions collection.
        
        Args:
            session_id: Unique session identifier
            user_id: User identifier (partition key)
            metadata: Additional session metadata (app_name, initial_state, etc.)
            
        Returns:
            Created session document
            
        Raises:
            CosmosResourceExistsError: If session already exists
        """
        # Extract initial state from metadata if provided
        initial_state = {}
        if metadata and 'initial_state' in metadata:
            initial_state = metadata.pop('initial_state')
        
        # Create session document
        session_doc = {
            "id": session_id,
            "session_id": session_id,
            "user_id": user_id,  # Partition key
            "app_name": metadata.get('app_name', 'unknown') if metadata else 'unknown',
            "state": initial_state,  # Current session state
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "last_update_time": datetime.now(timezone.utc).timestamp(),  # Unix timestamp for ADK
            "status": "active",
            "metadata": metadata or {}
        }
        
        try:
            response = self.session_container.create_item(body=session_doc)
            logger.debug(f"Session created: {session_id} for user: {user_id}")
            return response
            
        except CosmosResourceExistsError:
            logger.warning(f"Session {session_id} already exists for user {user_id}")
            # Return existing session instead of failing
            return self.get_session(session_id, user_id)
            
        except Exception as e:
            logger.error(f"Failed to create session {session_id}: {e}")
            raise
    
    def get_session(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session document by ID and user_id.
        
        Args:
            session_id: Session identifier
            user_id: User identifier (partition key)
            
        Returns:
            Session document or None if not found
        """
        try:
            # Direct read using partition key for optimal performance
            response = self.session_container.read_item(
                item=session_id,
                partition_key=user_id
            )
            logger.debug(f"Session retrieved: {session_id}")
            return response
            
        except CosmosResourceNotFoundError:
            logger.debug(f"Session {session_id} not found for user {user_id}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None
    
    def update_session(self, session_id: str, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update session document (primarily for state changes).
        
        Args:
            session_id: Session identifier
            user_id: User identifier (partition key)
            updates: Fields to update (typically state and last_update_time)
            
        Returns:
            Updated session document
        """
        try:
            # Get current session
            session = self.get_session(session_id, user_id)
            if not session:
                logger.warning(f"Cannot update non-existent session: {session_id}")
                return {}
            
            # Apply updates
            session.update(updates)
            session["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            # Validate JSON serializability before saving
            try:
                json.dumps(session)
            except (TypeError, ValueError) as json_error:
                logger.error(f"Session update is not JSON serializable: {json_error}")
                # Create minimal fallback
                session = {
                    "id": session_id,
                    "session_id": session_id,
                    "user_id": user_id,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "serialization_error": str(json_error)
                }
            
            # Replace the document
            response = self.session_container.replace_item(
                item=session_id,
                body=session
            )
            logger.debug(f"Session updated: {session_id}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to update session {session_id}: {e}")
            return {}
    
    def list_user_sessions(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        List sessions for a user (excluding deleted sessions).
        
        Args:
            user_id: User identifier (partition key)
            limit: Maximum number of sessions to return
            
        Returns:
            List of session documents (metadata only, no events)
        """
        try:
            # Query sessions by user_id, excluding deleted ones
            query = """
            SELECT * FROM c 
            WHERE c.user_id = @user_id 
            AND (c.status != 'deleted' OR IS_NULL(c.status) OR NOT IS_DEFINED(c.status))
            ORDER BY c.updated_at DESC
            """
            
            items = list(self.session_container.query_items(
                query=query,
                parameters=[{"name": "@user_id", "value": user_id}],
                max_item_count=limit,
                enable_cross_partition_query=False  # Same partition
            ))
            
            logger.debug(f"Retrieved {len(items)} sessions for user: {user_id}")
            return items
            
        except Exception as e:
            logger.error(f"Failed to list sessions for user {user_id}: {e}")
            return []
    
    def delete_session(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """
        Soft delete a session (mark as deleted, don't actually remove).
        
        Args:
            session_id: Session identifier
            user_id: User identifier (partition key)
            
        Returns:
            Updated session document
        """
        try:
            updates = {
                "status": "deleted",
                "deleted_at": datetime.now(timezone.utc).isoformat()
            }
            
            result = self.update_session(session_id, user_id, updates)
            logger.info(f"Session soft deleted: {session_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return {}
    
    # ========================================================================
    # EVENT OPERATIONS (Events Collection - Append Only)
    # ========================================================================
    
    def store_event(self, session_id: str, event_data: Dict[str, Any]) -> bool:
        """
        Store an ADK event as a new document in Events collection.
        
        This is an append-only operation - events are never updated once stored.
        
        Args:
            session_id: Session identifier (partition key)
            event_data: Serialized event data from serialize_adk_event()
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate required fields
            if not session_id:
                logger.error("store_event: session_id is required")
                return False
                
            if not event_data or not isinstance(event_data, dict):
                logger.error("store_event: event_data must be a non-empty dictionary")
                return False
            
            # Ensure required fields with defaults
            event_id = event_data.get("event_id", str(uuid.uuid4()))
            timestamp = event_data.get("timestamp", datetime.now(timezone.utc).timestamp())
            
            # Create event document for Cosmos DB
            event_document = {
                "id": str(event_id),
                "event_id": str(event_id),
                "session_id": str(session_id),  # Partition key
                "timestamp": float(timestamp),  # Keep as number for sorting
                "document_type": "adk_event",
                **event_data  # Include all serialized event data
            }
            
            # Validate JSON serializability
            try:
                json.dumps(event_document)
            except (TypeError, ValueError) as json_error:
                logger.error(f"Event document is not JSON serializable: {json_error}")
                return False
            
            # Store in Events collection
            self.event_container.create_item(body=event_document)
            logger.debug(f"Event stored: {event_id} for session: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store event for session {session_id}: {e}")
            return False
    
    def get_session_events(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get all events for a session, ordered by timestamp.
        
        Args:
            session_id: Session identifier (partition key)
            limit: Maximum number of events to return
            
        Returns:
            List of event documents, ordered chronologically
        """
        try:
            if not session_id:
                logger.warning("get_session_events: session_id is required")
                return []
            
            # Query events by session_id, ordered by timestamp
            query = """
            SELECT * FROM c 
            WHERE c.session_id = @session_id 
            AND c.document_type = 'adk_event'
            ORDER BY c.timestamp ASC
            """
            
            items = list(self.event_container.query_items(
                query=query,
                parameters=[{"name": "@session_id", "value": session_id}],
                max_item_count=limit,
                enable_cross_partition_query=False  # Same partition
            ))
            
            logger.debug(f"Retrieved {len(items)} events for session: {session_id}")
            return items
            
        except Exception as e:
            logger.error(f"Failed to get events for session {session_id}: {e}")
            return []
    
    # ========================================================================
    # CONVERSATION MANAGEMENT
    # ========================================================================
    
    def get_conversation_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get conversation history for a session.
        
        Args:
            session_id: Session identifier (partition key)
            limit: Maximum number of conversation turns to return
            
        Returns:
            List of conversation turn documents
        """
        try:
            query = """
            SELECT * FROM c 
            WHERE c.session_id = @session_id 
            AND c.document_type = 'conversation_turn'
            ORDER BY c.timestamp DESC
            """
            
            items = list(self.event_container.query_items(
                query=query,
                parameters=[{"name": "@session_id", "value": session_id}],
                max_item_count=limit,
                enable_cross_partition_query=False
            ))
            
            return list(reversed(items))
            
        except Exception as e:
            logger.error(f"Failed to get conversation history for session {session_id}: {e}")
            return []
    
    def get_user_sessions(self, user_id: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get sessions for a user with pagination.
        
        Args:
            user_id: User identifier
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip
            
        Returns:
            List of session documents
        """
        try:
            sessions = self.list_user_sessions(user_id, limit + offset)
            return sessions[offset:offset + limit]
            
        except Exception as e:
            logger.error(f"Failed to get user sessions for {user_id}: {e}")
            return []
    
    def save_conversation_turn(self, session_id: str, turn_data: Dict[str, Any], execution_time: float) -> bool:
        """
        Save a conversation turn to the events collection.
        
        Args:
            session_id: Session identifier (partition key)
            turn_data: Conversation turn data
            execution_time: Execution time in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            turn_id = turn_data.get('turn_id', str(uuid.uuid4()))
            timestamp = turn_data.get('timestamp', datetime.now(timezone.utc).isoformat())
            
            document = {
                "id": str(turn_id),
                "turn_id": str(turn_id),
                "session_id": session_id,
                "document_type": "conversation_turn",
                "timestamp": timestamp,
                "execution_time": execution_time,
                **turn_data
            }
            
            self.event_container.create_item(body=document)
            logger.debug(f"Conversation turn saved: {turn_id} for session: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save conversation turn for session {session_id}: {e}")
            return False
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def test_connection(self) -> bool:
        """
        Test Cosmos DB connection and container access.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Test database access
            db_properties = self.database.read()
            logger.info(f"Database connection successful: {db_properties['id']}")
            
            # Test container access
            session_props = self.session_container.read()
            event_props = self.event_container.read()
            
            logger.info(f"Container access successful: {session_props['id']}, {event_props['id']}")
            return True
            
        except Exception as e:
            logger.error(f"Cosmos DB connection test failed: {e}")
            return False


# Global instance for easy import
cosmos_client = CosmosDBClient()
