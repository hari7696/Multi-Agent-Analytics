"""
ADK Cosmos DB Data Converters
=============================

This module provides serialization and deserialization functions to convert between
ADK data structures and Cosmos DB document formats.

Key Principles:
- Maintain full fidelity between ADK objects and Cosmos DB documents
- Handle complex nested structures (function calls, responses, state deltas)
- Preserve timestamp precision (Unix floats)
- Ensure JSON serializability
- Handle None/null values correctly

Based on runtime analysis of ADK data structures from agent_runner.py execution.
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
import time
import uuid
import json
import logging

# Use the same logger as the main application
from config import logger


# ============================================================================
# EVENT SERIALIZATION (ADK → Cosmos DB)
# ============================================================================

def serialize_adk_event(event) -> Dict[str, Any]:
    """
    Convert ADK Event object to Cosmos DB document format.
    
    Args:
        event: google.adk.events.event.Event object
        
    Returns:
        Dict ready for Cosmos DB storage in Events collection
        
    Example ADK Event structure (from runtime analysis):
        Event {
            id: "f6e0e0f5-70ed-4afc-a9b4-e567b218d0c4",
            author: "postAgent",
            timestamp: 1757296961.374948,  # Unix float
            partial: False,
            content: {
                role: "model",
                parts: [
                    {text: "response"},
                    {function_call: {id, name, args}},
                    {function_response: {id, name, response}}
                ]
            },
            actions: {
                state_delta: {"random_num": "146"},
                transfer_to_agent: "funny_sub_agent"
            }
        }
    """
    try:
        # Basic event fields - always present
        event_doc = {
            "event_id": str(event.id),
            "author": str(event.author),
            "timestamp": float(event.timestamp),  # Keep as Unix timestamp number
            "partial": event.partial,  # Can be None, True, False - preserve as-is
            "user_id": None  # Will be set by caller for denormalization
        }
        
        # Serialize content if present
        if hasattr(event, 'content') and event.content:
            event_doc["content"] = serialize_content(event.content)
        
        # Serialize actions if present
        if hasattr(event, 'actions') and event.actions:
            event_doc["actions"] = serialize_actions(event.actions)
        
        logger.debug(f"Serialized ADK event: {event.id}")
        return event_doc
        
    except Exception as e:
        logger.error(f"Failed to serialize ADK event: {e}")
        # Return minimal fallback structure
        return {
            "event_id": str(getattr(event, 'id', uuid.uuid4())),
            "author": str(getattr(event, 'author', 'unknown')),
            "timestamp": float(getattr(event, 'timestamp', time.time())),
            "partial": getattr(event, 'partial', None),
            "serialization_error": str(e)
        }


def serialize_content(content) -> Dict[str, Any]:
    """
    Serialize ADK Content object to dictionary.
    
    Args:
        content: google.genai.types.Content object
        
    Returns:
        Serialized content dictionary
    """
    try:
        content_data = {
            "role": str(content.role),  # "user" or "model"
            "parts": []
        }
        
        # Process each part in content.parts
        if hasattr(content, 'parts') and content.parts:
            for part in content.parts:
                part_data = serialize_part(part)
                if part_data:  # Only add non-empty parts
                    content_data["parts"].append(part_data)
        
        return content_data
        
    except Exception as e:
        logger.error(f"Failed to serialize content: {e}")
        return {"role": "unknown", "parts": []}


def serialize_part(part) -> Dict[str, Any]:
    """
    Serialize ADK Part object to dictionary.
    
    Args:
        part: google.genai.types.Part object
        
    Returns:
        Serialized part dictionary
    """
    try:
        part_data = {}
        
        # Handle text content
        if hasattr(part, 'text') and part.text:
            part_data["text"] = str(part.text)
        
        # Handle function_call
        if hasattr(part, 'function_call') and part.function_call:
            fc = part.function_call
            part_data["function_call"] = {
                "id": str(fc.id),
                "name": str(fc.name),
                "args": dict(fc.args) if fc.args else {}
            }
        
        # Handle function_response
        if hasattr(part, 'function_response') and part.function_response:
            fr = part.function_response
            part_data["function_response"] = {
                "id": str(fr.id),
                "name": str(fr.name),
                "response": dict(fr.response) if fr.response else {}
            }
        
        return part_data
        
    except Exception as e:
        logger.error(f"Failed to serialize part: {e}")
        return {}


def serialize_actions(actions) -> Dict[str, Any]:
    """
    Serialize ADK EventActions object to dictionary.
    
    Args:
        actions: google.adk.events.event_actions.EventActions object
        
    Returns:
        Serialized actions dictionary
    """
    try:
        actions_data = {}
        
        # Handle state_delta - this is how state gets updated
        if hasattr(actions, 'state_delta') and actions.state_delta:
            actions_data["state_delta"] = dict(actions.state_delta)
        
        # Handle transfer_to_agent
        if hasattr(actions, 'transfer_to_agent') and actions.transfer_to_agent:
            actions_data["transfer_to_agent"] = str(actions.transfer_to_agent)
        
        return actions_data
        
    except Exception as e:
        logger.error(f"Failed to serialize actions: {e}")
        return {}


# ============================================================================
# EVENT DESERIALIZATION (Cosmos DB → ADK)
# ============================================================================

def deserialize_cosmos_event(cosmos_doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert Cosmos DB document to ADK Event dict format.
    
    Args:
        cosmos_doc: Cosmos DB event document
        
    Returns:
        Dict that matches ADK Event model structure for Event() constructor
        
    Note: ADK creates Event objects from dicts, so we return a properly structured dict
    """
    try:
        # Basic event structure
        event_dict = {
            "id": str(cosmos_doc.get("event_id", cosmos_doc.get("id", str(uuid.uuid4())))),
            "author": str(cosmos_doc.get("author", "unknown")),
            "timestamp": float(cosmos_doc.get("timestamp", time.time())),
            "partial": cosmos_doc.get("partial"),  # Preserve None/bool as-is
        }
        
        # Reconstruct content if present
        if cosmos_doc.get("content"):
            event_dict["content"] = deserialize_content(cosmos_doc["content"])
        
        # Reconstruct actions if present
        if cosmos_doc.get("actions"):
            event_dict["actions"] = deserialize_actions(cosmos_doc["actions"])
        
        logger.debug(f"Deserialized Cosmos event: {event_dict['id']}")
        return event_dict
        
    except Exception as e:
        logger.error(f"Failed to deserialize Cosmos event: {e}")
        # Return minimal valid event structure
        return {
            "id": str(uuid.uuid4()),
            "author": "unknown",
            "timestamp": time.time(),
            "partial": None,
            "content": None,
            "actions": {}
        }


def deserialize_content(content_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deserialize content dictionary to ADK Content format.
    
    Args:
        content_data: Serialized content dictionary
        
    Returns:
        Dict for ADK Content constructor
    """
    try:
        parts = []
        
        for part_data in content_data.get("parts", []):
            part_dict = deserialize_part(part_data)
            if part_dict:
                parts.append(part_dict)
        
        return {
            "role": content_data.get("role", "unknown"),
            "parts": parts
        }
        
    except Exception as e:
        logger.error(f"Failed to deserialize content: {e}")
        return {"role": "unknown", "parts": []}


def deserialize_part(part_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deserialize part dictionary to ADK Part format.
    
    Args:
        part_data: Serialized part dictionary
        
    Returns:
        Dict for ADK Part constructor
    """
    try:
        part_dict = {}
        
        # Reconstruct text
        if "text" in part_data:
            part_dict["text"] = part_data["text"]
        
        # Reconstruct function_call
        if "function_call" in part_data:
            fc = part_data["function_call"]
            part_dict["function_call"] = {
                "id": fc["id"],
                "name": fc["name"],
                "args": fc.get("args", {})
            }
        
        # Reconstruct function_response
        if "function_response" in part_data:
            fr = part_data["function_response"]
            part_dict["function_response"] = {
                "id": fr["id"],
                "name": fr["name"],
                "response": fr.get("response", {})
            }
        
        return part_dict
        
    except Exception as e:
        logger.error(f"Failed to deserialize part: {e}")
        return {}


def deserialize_actions(actions_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deserialize actions dictionary to ADK EventActions format.
    
    Args:
        actions_data: Serialized actions dictionary
        
    Returns:
        Dict for ADK EventActions constructor
    """
    try:
        actions_dict = {}
        
        if "state_delta" in actions_data:
            actions_dict["state_delta"] = actions_data["state_delta"]
        
        if "transfer_to_agent" in actions_data:
            actions_dict["transfer_to_agent"] = actions_data["transfer_to_agent"]
        
        return actions_dict
        
    except Exception as e:
        logger.error(f"Failed to deserialize actions: {e}")
        return {}


# ============================================================================
# SESSION SERIALIZATION
# ============================================================================

def serialize_session_for_cosmos(session) -> Dict[str, Any]:
    """
    Convert ADK Session to Cosmos DB session document.
    
    Args:
        session: google.adk.sessions.session.Session object
        
    Returns:
        Dict ready for Cosmos DB Sessions collection
        
    Example ADK Session structure (from runtime analysis):
        Session {
            id: "087f8e38-b93d-45f0-a1e9-6904a8230a28",
            app_name: "Social Media post generator",
            user_id: "Hari",
            state: {"dark_joke": "text", "random_num": "146"},
            events: [Event, Event, ...],
            last_update_time: 1757296962.409481
        }
    """
    try:
        return {
            "session_id": str(session.id),
            "user_id": str(session.user_id),
            "app_name": str(session.app_name),
            "state": dict(session.state) if session.state else {},  # Direct dict copy
            "last_update_time": float(session.last_update_time),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "status": "active"
        }
        
    except Exception as e:
        logger.error(f"Failed to serialize session for Cosmos: {e}")
        return {
            "session_id": str(getattr(session, 'id', uuid.uuid4())),
            "user_id": str(getattr(session, 'user_id', 'unknown')),
            "app_name": str(getattr(session, 'app_name', 'unknown')),
            "state": {},
            "last_update_time": time.time(),
            "status": "active",
            "serialization_error": str(e)
        }


def deserialize_session_from_cosmos(cosmos_doc: Dict[str, Any], events: List) -> Dict[str, Any]:
    """
    Convert Cosmos DB document + events to ADK Session constructor args.
    
    Args:
        cosmos_doc: Cosmos DB session document
        events: List of ADK Event objects (pre-loaded and deserialized)
        
    Returns:
        Dict for ADK Session() constructor
    """
    try:
        return {
            "id": str(cosmos_doc.get("session_id", cosmos_doc.get("id"))),
            "app_name": str(cosmos_doc.get("app_name", "unknown")),
            "user_id": str(cosmos_doc.get("user_id", "unknown")),
            "state": dict(cosmos_doc.get("state", {})),  # Direct dict copy
            "events": events,  # Pre-loaded Event objects
            "last_update_time": float(cosmos_doc.get("last_update_time", time.time()))
        }
        
    except Exception as e:
        logger.error(f"Failed to deserialize session from Cosmos: {e}")
        return {
            "id": str(uuid.uuid4()),
            "app_name": "unknown",
            "user_id": "unknown",
            "state": {},
            "events": [],
            "last_update_time": time.time()
        }


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def validate_json_serializable(data: Any) -> bool:
    """
    Validate that data is JSON serializable.
    
    Args:
        data: Data to validate
        
    Returns:
        True if serializable, False otherwise
    """
    try:
        json.dumps(data)
        return True
    except (TypeError, ValueError):
        return False


def safe_str(obj: Any) -> str:
    """
    Safely convert any object to string.
    
    Args:
        obj: Object to convert
        
    Returns:
        String representation
    """
    try:
        if obj is None:
            return ""
        return str(obj)
    except Exception:
        return "conversion_error"


def safe_dict(obj: Any) -> Dict[str, Any]:
    """
    Safely convert object to dictionary.
    
    Args:
        obj: Object to convert
        
    Returns:
        Dictionary representation
    """
    try:
        if isinstance(obj, dict):
            return obj
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return {"value": safe_str(obj)}
    except Exception:
        return {"conversion_error": "failed_to_convert_to_dict"}


# ============================================================================
# EXAMPLE USAGE PATTERNS (for reference)
# ============================================================================

"""
Example Usage:

# Storing an event
event_doc = serialize_adk_event(adk_event)
event_doc["user_id"] = session.user_id  # Add denormalization
cosmos_client.store_event(session_id, event_doc)

# Loading events
cosmos_docs = cosmos_client.get_session_events(session_id)
adk_events = []
for doc in cosmos_docs:
    event_dict = deserialize_cosmos_event(doc)
    adk_event = Event(**event_dict)  # ADK creates Event from dict
    adk_events.append(adk_event)

# Storing session
session_doc = serialize_session_for_cosmos(adk_session)
cosmos_client.create_session(session_id, user_id, session_doc)

# Loading session
session_doc = cosmos_client.get_session(session_id, user_id)
events = load_session_events(session_id)  # Load and deserialize events
session_dict = deserialize_session_from_cosmos(session_doc, events)
adk_session = Session(**session_dict)  # ADK creates Session from dict

# State management flow
if event.actions and event.actions.state_delta:
    for key, value in event.actions.state_delta.items():
        session.state[key] = value
    # Persist updated state to Cosmos DB
    updates = {"state": session.state, "last_update_time": time.time()}
    cosmos_client.update_session(session_id, user_id, updates)
"""
