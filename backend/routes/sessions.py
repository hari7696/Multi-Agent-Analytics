from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid

from runner import FinancialAgentRunner

router = APIRouter()
runner = FinancialAgentRunner("WebFinancialAgent")

class CreateSessionRequest(BaseModel):
    initial_state: Optional[dict] = None
    title: str = "New Chat"

class Session(BaseModel):
    id: str
    user_id: str
    title: str
    created_at: str
    last_activity: str
    message_count: int = 0
    is_shared: bool = False
    state: Optional[dict] = {}

@router.post("/users/{user_id}/sessions", response_model=Session)
async def create_user_session(user_id: str, request: CreateSessionRequest):
    try:
        session_id = await runner.create_new_session(user_id, request.initial_state)
        
        now = datetime.now().isoformat()
        
        title = request.title if request.title and request.title.strip() else "New Chat"
        
        # Always set the title in the session document
        runner.session_service.cosmos_client.update_session(session_id, user_id, {
            "title": title,
            "conversation_count": 0,
            "updated_at": datetime.now().isoformat()
        })
        
        session = Session(
            id=session_id,
            user_id=user_id,
            title=title,
            created_at=now,
            last_activity=now,
            message_count=0,
            is_shared=False,
            state=request.initial_state or {}
        )
        
        return session
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.options("/users/{user_id}/sessions")
async def options_user_sessions(user_id: str):
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        }
    )

@router.get("/users/{user_id}/sessions", response_model=List[Session])
async def get_user_sessions(user_id: str, limit: int = 20, offset: int = 0):
    try:
        sessions_data = runner.get_user_sessions(user_id, limit, offset)
        
        sessions = []
        for session_data in sessions_data:
            session = Session(
                id=session_data.get('session_id', session_data.get('id', str(uuid.uuid4()))),
                user_id=user_id,
                title=session_data.get('title', 'Chat Session'),
                created_at=session_data.get('created_at', datetime.now().isoformat()),
                last_activity=session_data.get('updated_at', session_data.get('last_activity', datetime.now().isoformat())),
                message_count=session_data.get('conversation_count', session_data.get('message_count', 0)),
                is_shared=session_data.get('is_shared', False),
                state=session_data.get('state', {})
            )
            sessions.append(session)
        
        return sessions
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.options("/users/{user_id}/sessions/{session_id}")
async def options_user_session(user_id: str, session_id: str):
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, DELETE, PUT, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        }
    )

@router.get("/users/{user_id}/sessions/{session_id}", response_model=Session)
async def get_user_session(user_id: str, session_id: str):
    try:
        # Use cosmos_client directly to get the raw session document
        session_data = runner.session_service.cosmos_client.get_session(session_id, user_id)
        
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = Session(
            id=session_data.get('session_id', session_data.get('id', session_id)),
            user_id=user_id,
            title=session_data.get('title', 'New Chat'),
            created_at=session_data.get('created_at', datetime.now().isoformat()),
            last_activity=session_data.get('updated_at', session_data.get('last_activity', datetime.now().isoformat())),
            message_count=session_data.get('conversation_count', session_data.get('message_count', 0)),
            is_shared=session_data.get('is_shared', False),
            state=session_data.get('state', {})
        )
        
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/users/{user_id}/sessions/{session_id}")
async def delete_user_session(user_id: str, session_id: str):
    try:
        success = await runner.close_session(user_id, session_id)
        
        if success:
            return {"message": "Session deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Session not found or could not be deleted")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/users/{user_id}/sessions/{session_id}/title")
async def update_session_title(user_id: str, session_id: str, title_update: dict):
    try:
        new_title = title_update.get("title", "").strip()
        if not new_title:
            raise HTTPException(status_code=400, detail="Title cannot be empty")
        
        if len(new_title) > 100:
            raise HTTPException(status_code=400, detail="Title too long (max 100 characters)")
        
        runner.session_service.cosmos_client.update_session(session_id, user_id, {
            "title": new_title,
            "updated_at": datetime.now().isoformat()
        })
        
        return {"message": "Title updated successfully", "title": new_title}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/users/{user_id}/sessions/{session_id}/share")
async def update_session_sharing(user_id: str, session_id: str, share_update: dict):
    try:
        is_shared = share_update.get("is_shared")
        if is_shared is None:
            raise HTTPException(status_code=400, detail="is_shared field is required")
        
        if not isinstance(is_shared, bool):
            raise HTTPException(status_code=400, detail="is_shared must be a boolean")
        
        # Update the session sharing status
        runner.session_service.cosmos_client.update_session(session_id, user_id, {
            "is_shared": is_shared,
            "updated_at": datetime.now().isoformat()
        })
        
        action = "enabled" if is_shared else "disabled"
        return {"message": f"Session sharing {action} successfully", "is_shared": is_shared}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.options("/users/{user_id}/sessions/{session_id}/share")
async def options_session_sharing(user_id: str, session_id: str):
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "PUT, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        }
    )

@router.options("/users/{user_id}/sessions/{session_id}")
async def options_user_session(user_id: str, session_id: str):
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        }
    )

@router.get("/sessions/{user_id}")
async def get_sessions(user_id: str):
    try:
        sessions = runner.get_user_sessions(user_id)
        return {"sessions": sessions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/my-sessions", response_model=List[Session])
async def get_my_sessions(user_id: str = "web_user", limit: int = 20, offset: int = 0):
    """
    Get user's sessions
    """
    try:
        sessions_data = runner.get_user_sessions(user_id, limit, offset)
        
        sessions = []
        for session_data in sessions_data:
            session = Session(
                id=session_data.get('session_id', session_data.get('id', str(uuid.uuid4()))),
                user_id=user_id,
                title=session_data.get('title', 'Chat Session'),
                created_at=session_data.get('created_at', datetime.now().isoformat()),
                last_activity=session_data.get('updated_at', session_data.get('last_activity', datetime.now().isoformat())),
                message_count=session_data.get('conversation_count', session_data.get('message_count', 0)),
                is_shared=session_data.get('is_shared', False),
                state=session_data.get('state', {})
            )
            sessions.append(session)
        
        return sessions
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/debug/user-info")
async def debug_user_info():
    """
    Debug endpoint
    """
    return {
        "message": "Debug endpoint",
        "note": "No authentication configured"
    }

@router.get("/history/{session_id}")
async def get_history(session_id: str, user_id: str = "web_user"):
    try:
        history = runner.get_conversation_history(user_id, session_id)
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/share/{session_id}")
async def get_shared_session(session_id: str):
    try:
        # Get session from database  
        session_data = runner.session_service.cosmos_client.get_session_by_id(session_id)
        
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Check if session is shared
        if not session_data.get("is_shared", False):
            raise HTTPException(status_code=403, detail="Session is not shared")
        
        # Get conversation history
        user_id = session_data.get("user_id", "web_user")
        history = runner.get_conversation_history(user_id, session_id)
        
        return {
            "session": {
                "id": session_data.get("session_id", session_id),
                "title": session_data.get("title", "Shared Chat"),
                "created_at": session_data.get("created_at"),
                "is_shared": True
            },
            "history": history
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))