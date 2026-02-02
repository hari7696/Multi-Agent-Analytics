"""
ADK Cosmos DB Serialization Reference
=====================================

This file contains the reference implementations for serialization/deserialization
functions based on runtime analysis of ADK data structures.

DO NOT EXECUTE - This is a reference template for implementation.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import time
import uuid

# ============================================================================
# EVENT SERIALIZATION (ADK → Cosmos DB)
# ============================================================================

def serialize_adk_event(event) -> Dict[str, Any]:
    """
    Convert ADK Event object to Cosmos DB document format
    
    Input: google.adk.events.event.Event object
    Output: Dict ready for Cosmos DB storage
    """
    
    # Basic event fields - always present
    event_doc = {
        "id": str(event.id),
        "event_id": str(event.id),
        "timestamp": float(event.timestamp),  # Keep as Unix timestamp number
        "author": str(event.author),
        "partial": event.partial,  # Can be None, True, False - preserve as-is
        "document_type": "adk_event"
    }
    
    # Serialize content if present
    if hasattr(event, 'content') and event.content:
        content_data = {
            "role": str(event.content.role),  # "user" or "model"
            "parts": []
        }
        
        # Process each part in content.parts
        for part in event.content.parts:
            part_data = {}
            
            # Handle text content
            if hasattr(part, 'text') and part.text:
                part_data["text"] = str(part.text)
            
            # Handle function_call
            if hasattr(part, 'function_call') and part.function_call:
                part_data["function_call"] = {
                    "id": str(part.function_call.id),
                    "name": str(part.function_call.name),
                    "args": dict(part.function_call.args)  # Convert to plain dict
                }
            
            # Handle function_response
            if hasattr(part, 'function_response') and part.function_response:
                part_data["function_response"] = {
                    "id": str(part.function_response.id),
                    "name": str(part.function_response.name),
                    "response": dict(part.function_response.response)  # Convert to plain dict
                }
            
            # Only add non-empty parts
            if part_data:
                content_data["parts"].append(part_data)
        
        event_doc["content"] = content_data
    
    # Serialize actions if present
    if hasattr(event, 'actions') and event.actions:
        actions_data = {}
        
        # Handle state_delta - this is how state gets updated
        if hasattr(event.actions, 'state_delta') and event.actions.state_delta:
            actions_data["state_delta"] = dict(event.actions.state_delta)
        
        # Handle transfer_to_agent
        if hasattr(event.actions, 'transfer_to_agent') and event.actions.transfer_to_agent:
            actions_data["transfer_to_agent"] = str(event.actions.transfer_to_agent)
        
        # Only add actions if there's content
        if actions_data:
            event_doc["actions"] = actions_data
    
    return event_doc


# ============================================================================
# EVENT DESERIALIZATION (Cosmos DB → ADK)
# ============================================================================

def deserialize_cosmos_event(cosmos_doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert Cosmos DB document to ADK Event dict format
    
    Input: Cosmos DB document dict
    Output: Dict that matches ADK Event model structure
    
    Note: ADK creates Event objects from dicts, so we return a properly structured dict
    """
    
    # Basic event structure
    event_dict = {
        "id": str(cosmos_doc.get("event_id", cosmos_doc.get("id", str(uuid.uuid4())))),
        "author": str(cosmos_doc.get("author", "unknown")),
        "timestamp": float(cosmos_doc.get("timestamp", time.time())),
        "partial": cosmos_doc.get("partial"),  # Preserve None/bool as-is
    }
    
    # Reconstruct content if present
    if cosmos_doc.get("content"):
        content_data = cosmos_doc["content"]
        parts = []
        
        for part_data in content_data.get("parts", []):
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
                    "args": fc["args"]
                }
            
            # Reconstruct function_response
            if "function_response" in part_data:
                fr = part_data["function_response"]
                part_dict["function_response"] = {
                    "id": fr["id"],
                    "name": fr["name"],
                    "response": fr["response"]
                }
            
            parts.append(part_dict)
        
        event_dict["content"] = {
            "role": content_data.get("role", "unknown"),
            "parts": parts
        }
    
    # Reconstruct actions if present
    if cosmos_doc.get("actions"):
        actions_data = cosmos_doc["actions"]
        event_dict["actions"] = {}
        
        if "state_delta" in actions_data:
            event_dict["actions"]["state_delta"] = actions_data["state_delta"]
        
        if "transfer_to_agent" in actions_data:
            event_dict["actions"]["transfer_to_agent"] = actions_data["transfer_to_agent"]
    
    return event_dict


# ============================================================================
# SESSION SERIALIZATION
# ============================================================================

def serialize_session_for_cosmos(session) -> Dict[str, Any]:
    """
    Convert ADK Session to Cosmos DB session document
    
    Input: google.adk.sessions.session.Session object
    Output: Dict ready for Cosmos DB sessions collection
    """
    return {
        "id": str(session.id),
        "session_id": str(session.id),
        "user_id": str(session.user_id),
        "app_name": str(session.app_name),
        "state": dict(session.state),  # Direct dict copy - no complex serialization needed
        "last_update_time": float(session.last_update_time),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "status": "active"
    }


def deserialize_session_from_cosmos(cosmos_doc: Dict[str, Any], events: List) -> Dict[str, Any]:
    """
    Convert Cosmos DB document + events to ADK Session constructor args
    
    Input: Cosmos DB session document + loaded Event objects
    Output: Dict for Session() constructor
    """
    return {
        "id": str(cosmos_doc["session_id"]),
        "app_name": str(cosmos_doc["app_name"]),
        "user_id": str(cosmos_doc["user_id"]),
        "state": dict(cosmos_doc.get("state", {})),  # Direct dict copy
        "events": events,  # Pre-loaded Event objects
        "last_update_time": float(cosmos_doc.get("last_update_time", time.time()))
    }


# ============================================================================
# EXAMPLE USAGE PATTERNS
# ============================================================================

"""
# Storing an event
event_doc = serialize_adk_event(adk_event)
cosmos_client.store_event(session_id, event_doc)

# Loading events
cosmos_docs = cosmos_client.get_session_events(session_id)
adk_events = [Event(**deserialize_cosmos_event(doc)) for doc in cosmos_docs]

# Storing session
session_doc = serialize_session_for_cosmos(adk_session)
cosmos_client.create_session(session_id, user_id, session_doc)

# Loading session
session_doc = cosmos_client.get_session(session_id, user_id)
events = load_session_events(session_id)
adk_session = Session(**deserialize_session_from_cosmos(session_doc, events))

# State management flow
if event.actions and event.actions.state_delta:
    for key, value in event.actions.state_delta.items():
        session.state[key] = value
    # Persist updated state to Cosmos DB
    cosmos_client.update_session(session_id, user_id, {"state": session.state})
"""


# ============================================================================
# RUNTIME ANALYSIS RESULTS (for reference)
# ============================================================================

"""
ADK Data Structures Observed:

Session:
- Type: <class 'google.adk.sessions.session.Session'>
- id: "087f8e38-b93d-45f0-a1e9-6904a8230a28"
- app_name: "Social Media post generator"
- user_id: "Hari"
- state: {'dark_joke': 'My day's going great—unlike the American healthcare system!', 'random_num': '146'}
- events: List of Event objects
- last_update_time: 1757296962.409481 (Unix timestamp float)

Event:
- Type: <class 'google.adk.events.event.Event'>
- id: "f6e0e0f5-70ed-4afc-a9b4-e567b218d0c4"
- author: "postAgent" | "user" | "funny_sub_agent"
- timestamp: 1757296961.374948 (Unix timestamp float)
- partial: False | None | True
- content.role: "model" | "user"
- content.parts: List of Part objects

Part Types Observed:
1. Text parts: part.text = "response text"
2. Function call parts: part.function_call = {id, name, args}
3. Function response parts: part.function_response = {id, name, response}

Actions Observed:
- actions.state_delta: {'random_num': '146'} | {'dark_joke': 'joke text'}
- actions.transfer_to_agent: 'funny_sub_agent'

State Evolution Example:
Initial: {"dark_joke": "Joke isnt generated by sub agent yet", "random_num": 1000000000000}
After tool: {"dark_joke": "Joke isnt generated by sub agent yet", "random_num": "146"}
After agent: {"dark_joke": "My day's going great—unlike the American healthcare system!", "random_num": "146"}
"""
