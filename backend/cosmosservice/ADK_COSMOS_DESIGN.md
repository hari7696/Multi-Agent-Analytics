# ADK Cosmos DB Integration Design Document

## Overview
This document outlines the design and implementation strategy for integrating Google ADK (Agent Development Kit) with Azure Cosmos DB for persistent session and event storage.

## Current State Analysis

### ADK InMemorySessionService
- Currently using `InMemorySessionService()` in `agents/agent_runner.py` (line 8)
- Sessions and events are stored in memory only
- Data is lost when application restarts
- No scalability across multiple instances

### Migration Goal
Replace `InMemorySessionService` with `CosmosSessionService` that:
- Persists sessions and events to Azure Cosmos DB
- Maintains full ADK compatibility
- Supports state management and event history
- Enables scalability and data persistence

## ADK Data Structure Analysis

### Session Object Structure
```
google.adk.sessions.session.Session
├── id: str (UUID)                    # "087f8e38-b93d-45f0-a1e9-6904a8230a28"
├── app_name: str                     # "Social Media post generator"
├── user_id: str                      # "Hari"
├── state: dict                       # {"dark_joke": "text", "random_num": "146"}
├── events: List[Event]               # Array of Event objects
└── last_update_time: float           # Unix timestamp (1757296962.409481)
```

### Event Object Structure
```
google.adk.events.event.Event
├── id: str (UUID)                    # "f6e0e0f5-70ed-4afc-a9b4-e567b218d0c4"
├── author: str                       # "user", "postAgent", "funny_sub_agent"
├── timestamp: float                  # Unix timestamp (1757296961.374948)
├── partial: bool|None                # Can be None, False, True
├── content: google.genai.types.Content
│   ├── role: str                     # "user" or "model"
│   └── parts: List[google.genai.types.Part]
│       ├── text: str (optional)      # "Hi How is your day going?"
│       ├── function_call: FunctionCall (optional)
│       │   ├── id: str               # "call_gJQRYWNb9CUTDA07lVXS3Ifc"
│       │   ├── name: str             # "update_num_tool"
│       │   └── args: dict            # {"num": "146"}
│       └── function_response: FunctionResponse (optional)
│           ├── id: str               # "call_gJQRYWNb9CUTDA07lVXS3Ifc"
│           ├── name: str             # "update_num_tool"
│           └── response: dict        # {"result": None}
└── actions: google.adk.events.event_actions.EventActions
    ├── state_delta: dict             # {"random_num": "146", "dark_joke": "text"}
    └── transfer_to_agent: str (optional) # "funny_sub_agent"
```

### Key Observations from Runtime Analysis
1. **Timestamps**: ADK uses Unix timestamps as floats, not ISO strings
2. **State Management**: Simple dictionary with key-value pairs
3. **Function Calls**: Complex nested structures with id, name, args
4. **Function Responses**: Match function calls by id, contain response data
5. **State Updates**: Happen via `actions.state_delta` in events
6. **Event Flow**: User message → Agent function calls → Function responses → Agent response

## Cosmos DB Schema Design

### Database Structure
```
CosmosDB Database: [COSMOSDB_DATABASE]
├── Sessions Container (partition key: user_id)
│   └── One document per session
├── Events Container (partition key: session_id)  
│   └── One document per event (immutable)
└── Users Container (partition key: user_id) [future use]
```

### Container Operations Pattern
- **Sessions Container**: CREATE once, UPDATE state when needed, SOFT DELETE
- **Events Container**: CREATE only (no updates, no deletes) - append-only pattern

### State Storage Strategy
**Current state is stored in Sessions collection for performance and simplicity:**
- ✅ Fast access to current state via `session.state`
- ✅ ADK compatibility (Session object expects state to be available)
- ✅ Simple implementation (no need to replay events for state)
- ⚠️ Sessions collection will be updated when state changes (acceptable trade-off)

**Alternative approaches considered:**
- Store only state deltas in events, reconstruct current state by replaying
- Pros: Truly immutable sessions, complete state history
- Cons: Slower state access, more complex implementation, potential consistency issues

### Sessions Collection Schema
```json
{
  "id": "session_uuid",
  "session_id": "session_uuid",           // Unique identifier
  "user_id": "user_id",                   // Partition key
  "app_name": "Social Media post generator",
  "state": {                              // Direct dict storage - no serialization needed
    "dark_joke": "My day's going great—unlike the American healthcare system!",
    "random_num": "146"
  },
  "created_at": "2025-01-27T10:30:00Z",   // ISO timestamp
  "updated_at": "2025-01-27T10:35:00Z",   // ISO timestamp  
  "last_update_time": 1757296962.409481,  // Unix timestamp (matches ADK)
  "status": "active"                       // "active" | "closed"
}
```

### Events Collection Schema
```json
{
  "id": "event_uuid",
  "event_id": "event_uuid",               // Unique identifier
  "session_id": "session_uuid",           // Partition key
  "user_id": "user_id",                   // Denormalization for queries
  "timestamp": 1757296962.409481,         // Unix timestamp as number
  "author": "postAgent",                  // "user" | agent_name
  "partial": false,                       // boolean or null
  "document_type": "adk_event",           // Document type identifier
  "content": {
    "role": "model",                      // "user" | "model"
    "parts": [
      {
        "text": "response text",            // Optional text content
        "function_call": {                 // Optional function call
          "id": "call_gJQRYWNb9CUTDA07lVXS3Ifc",
          "name": "update_num_tool",
          "args": {"num": "146"}
        },
        "function_response": {             // Optional function response
          "id": "call_gJQRYWNb9CUTDA07lVXS3Ifc", 
          "name": "update_num_tool",
          "response": {"result": null}
        }
      }
    ]
  },
  "actions": {
    "state_delta": {"random_num": "146"}, // State updates
    "transfer_to_agent": "funny_sub_agent" // Agent transfers
  }
}
```

## BaseSessionService Interface Requirements

### Required Abstract Methods (MUST Override)
```python
async def create_session(*, app_name: str, user_id: str, 
                        state: Optional[dict] = None, 
                        session_id: Optional[str] = None) -> Session

async def get_session(*, app_name: str, user_id: str, session_id: str,
                     config: Optional[GetSessionConfig] = None) -> Optional[Session]

async def list_sessions(*, app_name: str, user_id: str) -> ListSessionsResponse

async def delete_session(*, app_name: str, user_id: str, session_id: str) -> None
```

### Inherited Methods (SHOULD Override for Cosmos DB)
```python
async def append_event(session: Session, event: Event) -> Event
def __update_session_state(session: Session, event: Event) -> None
```

### Complete Method Implementation Strategy
**ALL methods in BaseSessionService must be implemented** to ensure full Cosmos DB integration:
- **4 Abstract methods**: Must be implemented (create, get, list, delete)
- **2 Inherited methods**: Should be overridden for persistence (append_event, __update_session_state)

## Implementation Strategy

### Complete Method Implementation (ALL 6 Methods)
1. **`create_session`**: Create new session document in Cosmos DB
2. **`get_session`**: Load session + events from Cosmos DB → ADK format  
3. **`list_sessions`**: Query sessions by user_id from Cosmos DB
4. **`delete_session`**: Mark session as deleted in Cosmos DB
5. **`append_event`**: Store individual event as new Cosmos DB document + update session
6. **`__update_session_state`**: Update session state in Cosmos DB (called by append_event)

### Data Flow - Event Storage Strategy
**Key Principle: Each event is stored as a separate Cosmos DB document (no frequent updates)**

```
1. create_session():
   Create new session document in Sessions collection
   
2. get_session():
   Load session document from Sessions collection
   Query all events from Events collection by session_id
   Reconstruct ADK Session with loaded events
   
3. list_sessions():
   Query Sessions collection by user_id
   Return session metadata (no events loaded)
   
4. delete_session():
   Update session document status to "deleted"
   
5. append_event():
   Create NEW event document in Events collection
   Add event to in-memory session.events list
   Call __update_session_state() to update session
   
6. __update_session_state():
   Extract event.actions.state_delta
   Update session.state dict in memory
   Update session document in Sessions collection with new state
   (Note: This causes Sessions collection to be updated - acceptable for performance)
```

### Event Storage Pattern
- **Each event = One Cosmos DB document** in Events collection
- **No event updates** - events are immutable once stored
- **Session state updates** - only Sessions collection documents get updated
- **Event history** - reconstructed by querying Events collection by session_id

## Serialization/Deserialization Strategy

### Event Serialization (ADK → Cosmos DB)
```python
def serialize_adk_event(event: Event) -> Dict[str, Any]:
    """Convert ADK Event to Cosmos DB document"""
    return {
        "id": str(event.id),
        "event_id": str(event.id),
        "timestamp": float(event.timestamp),      # Keep as number
        "author": str(event.author),
        "partial": event.partial,                 # None/bool as-is
        "document_type": "adk_event",
        "content": serialize_content(event.content),
        "actions": serialize_actions(event.actions)
    }
```

### Event Deserialization (Cosmos DB → ADK)
```python
def deserialize_cosmos_event(cosmos_doc: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Cosmos DB document to ADK Event dict format"""
    return {
        "id": str(cosmos_doc["event_id"]),
        "author": str(cosmos_doc["author"]),
        "timestamp": float(cosmos_doc["timestamp"]),
        "partial": cosmos_doc.get("partial"),
        "content": deserialize_content(cosmos_doc.get("content")),
        "actions": deserialize_actions(cosmos_doc.get("actions"))
    }
```

### Content Serialization Details
```python
# Function Call Serialization
"function_call": {
    "id": str(part.function_call.id),
    "name": str(part.function_call.name), 
    "args": dict(part.function_call.args)
}

# Function Response Serialization  
"function_response": {
    "id": str(part.function_response.id),
    "name": str(part.function_response.name),
    "response": dict(part.function_response.response)
}
```

### Session Serialization
```python
# Session → Cosmos DB
def serialize_session_for_cosmos(session: Session) -> Dict[str, Any]:
    return {
        "id": str(session.id),
        "session_id": str(session.id),
        "user_id": str(session.user_id),
        "app_name": str(session.app_name),
        "state": dict(session.state),           # Direct dict copy
        "last_update_time": float(session.last_update_time),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "status": "active"
    }

# Cosmos DB → Session
def deserialize_session_from_cosmos(cosmos_doc: Dict, events: List[Event]) -> Session:
    return Session(
        id=str(cosmos_doc["session_id"]),
        app_name=str(cosmos_doc["app_name"]),
        user_id=str(cosmos_doc["user_id"]),
        state=dict(cosmos_doc.get("state", {})), # Direct dict copy
        events=events,                           # Pre-loaded Event objects
        last_update_time=float(cosmos_doc.get("last_update_time", time.time()))
    )
```

## State Management Flow

### State Update Process
```python
# 1. Agent calls tool_context.state['key'] = value
# 2. This creates an event with state_delta:
event.actions.state_delta = {"key": "value"}

# 3. In __update_session_state():
if event.actions and event.actions.state_delta:
    for key, value in event.actions.state_delta.items():
        session.state[key] = value  # Update in-memory state

# 4. In append_event():
# - Call __update_session_state() to update session.state
# - Store event in Cosmos Events collection  
# - Update session document with new state dict
```

### Example State Evolution
```python
# Initial state
session.state = {"dark_joke": "Joke isnt generated by sub agent yet", "random_num": 1000000000000}

# After update_num_tool(146)
event.actions.state_delta = {"random_num": "146"}
session.state = {"dark_joke": "Joke isnt generated by sub agent yet", "random_num": "146"}

# After funny_sub_agent generates joke
event.actions.state_delta = {"dark_joke": "My day's going great—unlike the American healthcare system!"}
session.state = {"dark_joke": "My day's going great—unlike the American healthcare system!", "random_num": "146"}
```

## Implementation Architecture

### Directory Structure
```
cosmosservice/
├── __init__.py
├── cosmos_client.py              # Cosmos DB operations
├── cosmos_session_service.py     # ADK BaseSessionService implementation
├── data_converters.py           # Serialization/deserialization functions
└── ADK_COSMOS_DESIGN.md         # This documentation
```

### Key Classes
```python
class CosmosDBClient:
    """Handles direct Cosmos DB operations"""
    # Session Operations (Sessions Collection)
    def create_session(session_id, user_id, metadata) -> Dict
    def get_session(session_id, user_id) -> Dict
    def update_session(session_id, user_id, updates) -> Dict  # State updates only
    def list_user_sessions(user_id, limit) -> List[Dict]
    def delete_session(session_id, user_id) -> Dict  # Soft delete
    
    # Event Operations (Events Collection - Append Only)
    def store_event(session_id, event_data) -> bool  # CREATE only
    def get_session_events(session_id, limit) -> List[Dict]  # QUERY only

class CosmosSessionService(BaseSessionService):
    """ADK-compliant session service using Cosmos DB - ALL 6 methods"""
    # Abstract Methods (Required)
    async def create_session(...) -> Session
    async def get_session(...) -> Optional[Session]
    async def list_sessions(...) -> ListSessionsResponse
    async def delete_session(...) -> None
    
    # Inherited Methods (Override for persistence)
    async def append_event(session, event) -> Event  
    def __update_session_state(session, event) -> None
```

## Environment Configuration

### Required Environment Variables
```bash
COSMOSDB_ENDPOINT=https://your-account.documents.azure.com:443/
COSMOSDB_KEY=your-primary-key
COSMOSDB_DATABASE=your-database-name
COSMOSDB_SESSION_CONTAINER=sessions
COSMOSDB_CONVERSATION_CONTAINER=events
```

## Migration Steps

### Phase 1: Implementation
1. Create cosmos_client.py with basic CRUD operations
2. Create data_converters.py with serialization functions
3. Create cosmos_session_service.py with 3 key methods
4. Add environment configuration

### Phase 2: Integration
1. Update agents/agent_runner.py import
2. Replace InMemorySessionService with CosmosSessionService
3. Test session creation and state management
4. Verify event persistence and retrieval

### Phase 3: Validation
1. Run existing agent workflow
2. Verify state updates persist correctly
3. Test session retrieval across restarts
4. Validate event history accuracy

## Key Implementation Considerations

### Data Fidelity
- Preserve exact ADK object structures
- Maintain timestamp precision (Unix floats)
- Handle None/null values correctly
- Preserve function call/response relationships

### Performance
- Limit event loading (e.g., last 50 events)
- Use partition keys efficiently
- Batch operations where possible
- Consider caching for frequent state updates

### Error Handling
- Graceful degradation for network issues
- Validation of serialized data
- Fallback mechanisms for corrupted data
- Proper logging for debugging

### Type Safety
- Always convert to expected types (str, float, dict)
- Handle missing fields with defaults
- Validate required fields before storage
- Ensure JSON serializability

## Testing Strategy

### Unit Tests
- Serialization/deserialization functions
- Individual Cosmos DB operations
- State update logic
- Error handling scenarios

### Integration Tests  
- Full agent workflow with Cosmos DB
- Session persistence across restarts
- Multi-event conversations
- State management accuracy

### Performance Tests
- Large session histories
- Concurrent session access
- Event storage throughput
- Query performance

---

*This document serves as the definitive guide for the ADK Cosmos DB integration implementation.*
