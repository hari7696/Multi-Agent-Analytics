"""Test utilities and helpers"""
import json
import tempfile
import os
from typing import Dict, Any, List
from datetime import datetime, timedelta
import uuid


class TestDataFactory:
    """Factory for creating test data"""
    
    @staticmethod
    def create_session(
        session_id: str = None,
        user_id: str = "test_user",
        title: str = "Test Session",
        message_count: int = 0,
        is_shared: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Create test session data"""
        base_time = datetime.now().isoformat()
        
        return {
            "id": session_id or str(uuid.uuid4()),
            "user_id": user_id,
            "title": title,
            "created_at": base_time,
            "last_activity": base_time,
            "message_count": message_count,
            "state": {},
            "is_shared": is_shared,
            **kwargs
        }
    
    @staticmethod
    def create_message(
        message_id: str = None,
        session_id: str = "test-session",
        user_id: str = "test_user",
        message_type: str = "user",
        content: str = "Test message",
        files: List[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create test message data"""
        return {
            "id": message_id or str(uuid.uuid4()),
            "session_id": session_id,
            "user_id": user_id,
            "message_type": message_type,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "files": files,
            "execution_time": None,
            **kwargs
        }
    
    @staticmethod
    def create_conversation_history(num_turns: int = 2) -> List[Dict[str, Any]]:
        """Create test conversation history"""
        history = []
        base_time = datetime.now()
        
        for i in range(num_turns):
            turn_time = (base_time + timedelta(minutes=i*5)).isoformat()
            history.append({
                "user_message": f"User question {i+1}",
                "agent_response": f"Agent response {i+1}",
                "timestamp": turn_time
            })
        
        return history
    
    @staticmethod
    def create_file_data(
        filename: str = "test.csv",
        content: bytes = b"col1,col2\n1,2\n3,4",
        session_id: str = "test-session"
    ) -> Dict[str, Any]:
        """Create test file upload data"""
        return {
            "filename": filename,
            "size": len(content),
            "path": f"{session_id}/{uuid.uuid4().hex}_{filename}",
            "upload_time": datetime.now().isoformat(),
            "content": content
        }


class MockRunner:
    """Mock financial agent runner for testing"""
    
    def __init__(self):
        self.sessions = {}
        self.messages = {}
        self.conversation_history = {}
    
    def create_session(self, user_id: str, title: str = "New Chat", **kwargs):
        """Mock create session"""
        session = TestDataFactory.create_session(
            user_id=user_id,
            title=title,
            **kwargs
        )
        self.sessions[session["id"]] = session
        return session
    
    def get_sessions_for_user(self, user_id: str, limit: int = 20, offset: int = 0):
        """Mock get sessions for user"""
        user_sessions = [s for s in self.sessions.values() if s["user_id"] == user_id]
        return user_sessions[offset:offset + limit]
    
    def delete_session(self, user_id: str, session_id: str):
        """Mock delete session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        raise Exception("Session not found")
    
    def update_session_title(self, user_id: str, session_id: str, new_title: str):
        """Mock update session title"""
        if session_id in self.sessions:
            self.sessions[session_id]["title"] = new_title
            return True
        raise Exception("Session not found")
    
    def send_message(self, user_id: str, session_id: str, content: str, files: List[str] = None):
        """Mock send message"""
        message = TestDataFactory.create_message(
            session_id=session_id,
            user_id=user_id,
            content=content,
            files=files
        )
        
        if session_id not in self.messages:
            self.messages[session_id] = []
        self.messages[session_id].append(message)
        
        return message
    
    def get_messages_for_session(self, user_id: str, session_id: str, limit: int = 50, offset: int = 0):
        """Mock get messages for session"""
        session_messages = self.messages.get(session_id, [])
        return session_messages[offset:offset + limit]
    
    def get_conversation_history(self, user_id: str, session_id: str, limit: int = 10):
        """Mock get conversation history"""
        return self.conversation_history.get(session_id, [])


class APITestClient:
    """Enhanced test client with helper methods"""
    
    def __init__(self, client):
        self.client = client
        self.base_url = "http://testserver"
    
    def create_session(self, user_id: str = "test_user", title: str = "Test Session"):
        """Helper to create a session"""
        return self.client.post(f"/api/users/{user_id}/sessions", json={
            "title": title
        })
    
    def send_message(self, user_id: str, session_id: str, content: str, files: List[str] = None):
        """Helper to send a message"""
        payload = {
            "content": content,
            "message_type": "user"
        }
        if files:
            payload["files"] = files
            
        return self.client.post(f"/api/users/{user_id}/sessions/{session_id}/messages", json=payload)
    
    def upload_file(self, user_id: str, session_id: str, filename: str, content: bytes):
        """Helper to upload a file"""
        from io import BytesIO
        files = {"file": (filename, BytesIO(content), "application/octet-stream")}
        return self.client.post(f"/api/users/{user_id}/sessions/{session_id}/files", files=files)
    
    def get_sessions(self, user_id: str, limit: int = 20, offset: int = 0):
        """Helper to get sessions"""
        return self.client.get(f"/api/users/{user_id}/sessions?limit={limit}&offset={offset}")
    
    def share_session(self, user_id: str, session_id: str, is_shared: bool = True):
        """Helper to toggle session sharing"""
        return self.client.put(f"/api/users/{user_id}/sessions/{session_id}/share", json={
            "is_shared": is_shared
        })


def assert_valid_timestamp(timestamp_str: str):
    """Assert that a string is a valid ISO timestamp"""
    try:
        datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    except ValueError:
        raise AssertionError(f"Invalid timestamp format: {timestamp_str}")


def assert_valid_uuid(uuid_str: str):
    """Assert that a string is a valid UUID"""
    try:
        uuid.UUID(uuid_str)
    except ValueError:
        raise AssertionError(f"Invalid UUID format: {uuid_str}")


def create_temp_file(content: str, suffix: str = ".txt") -> str:
    """Create a temporary file and return its path"""
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(content)
    except:
        os.close(fd)
        raise
    return path


def compare_dicts_ignore_keys(dict1: dict, dict2: dict, ignore_keys: set = None) -> bool:
    """Compare dictionaries while ignoring specified keys"""
    ignore_keys = ignore_keys or set()
    
    filtered_dict1 = {k: v for k, v in dict1.items() if k not in ignore_keys}
    filtered_dict2 = {k: v for k, v in dict2.items() if k not in ignore_keys}
    
    return filtered_dict1 == filtered_dict2


def load_test_data(filename: str) -> Any:
    """Load test data from JSON file"""
    test_data_dir = os.path.join(os.path.dirname(__file__), "fixtures")
    file_path = os.path.join(test_data_dir, filename)
    
    with open(file_path, 'r') as f:
        return json.load(f)