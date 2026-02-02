"""Pytest configuration and fixtures"""
import os
import pytest
import tempfile
import shutil
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock

# Import the main app
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

try:
    from routes import app
    from runner import FinancialAgentRunner
except ImportError:
    # Fallback for when imports fail during testing
    app = None
    FinancialAgentRunner = None


@pytest.fixture
def client():
    """FastAPI test client"""
    if app is None:
        pytest.skip("Cannot import routes app")
    return TestClient(app)


# Async client removed since we're using TestClient for all tests


@pytest.fixture
def temp_uploads_dir():
    """Temporary directory for file uploads during testing"""
    temp_dir = tempfile.mkdtemp()
    original_uploads = "uploads"
    
    # Create test uploads directory
    test_uploads = os.path.join(temp_dir, "uploads")
    os.makedirs(test_uploads, exist_ok=True)
    
    yield test_uploads
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_agent_runner():
    """Mock financial agent runner"""
    if FinancialAgentRunner is None:
        # Create a basic mock when we can't import the real class
        runner = Mock()
    else:
        runner = Mock(spec=FinancialAgentRunner)
    
    # Mock methods
    runner.get_or_create_session = AsyncMock(return_value="test-session-123")
    runner.get_conversation_history = Mock(return_value=[
        {
            "user_message": "Test message",
            "agent_response": "Test response",
            "timestamp": "2025-01-01T00:00:00Z"
        }
    ])
    runner.get_sessions_for_user = Mock(return_value=[
        {
            "id": "session-1",
            "user_id": "test_user",
            "title": "Test Session 1",
            "created_at": "2025-01-01T00:00:00Z",
            "last_activity": "2025-01-01T01:00:00Z",
            "message_count": 5,
            "state": {},
            "is_shared": False
        }
    ])
    runner.create_session = Mock(return_value={
        "id": "new-session-123",
        "user_id": "test_user",
        "title": "New Chat",
        "created_at": "2025-01-01T00:00:00Z",
        "last_activity": "2025-01-01T00:00:00Z",
        "message_count": 0,
        "state": {},
        "is_shared": False
    })
    runner.delete_session = Mock(return_value=True)
    runner.update_session_title = Mock(return_value=True)
    
    return runner


@pytest.fixture
def sample_session():
    """Sample session data"""
    return {
        "id": "test-session-123",
        "user_id": "test_user",
        "title": "Test Session",
        "created_at": "2025-01-01T00:00:00Z",
        "last_activity": "2025-01-01T01:00:00Z",
        "message_count": 3,
        "state": {"key": "value"},
        "is_shared": False
    }


@pytest.fixture
def sample_message():
    """Sample message data"""
    return {
        "content": "What is the revenue for Q4?",
        "message_type": "user",
        "session_id": "test-session-123",
        "user_id": "test_user"
    }


@pytest.fixture
def sample_file(temp_uploads_dir):
    """Sample file for upload testing"""
    file_path = os.path.join(temp_uploads_dir, "test_file.csv")
    content = "Name,Age,Salary\nJohn,30,50000\nJane,25,45000"
    
    with open(file_path, "w") as f:
        f.write(content)
    
    return {
        "path": file_path,
        "filename": "test_file.csv",
        "content": content,
        "size": len(content.encode())
    }


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch, temp_uploads_dir):
    """Setup test environment"""
    # Set test environment variables
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    
    # Store original os.path.join to avoid recursion
    original_join = os.path.join
    
    def mock_join(*args):
        if len(args) > 0 and args[0] == "uploads":
            return original_join(temp_uploads_dir, *args[1:])
        return original_join(*args)
    
    # Mock uploads directory
    monkeypatch.setattr("routes.os.path.join", mock_join)


@pytest.fixture
def mock_streaming_response():
    """Mock streaming response for chat"""
    async def mock_stream():
        # Simulate streaming chunks
        chunks = [
            {"type": "thinking", "data": "Analyzing your request...", "agent": "finance_master_agent"},
            {"type": "agent_switch", "data": "Switching to revenue agent", "agent": "revenue_agent"},
            {"type": "content", "data": "The revenue for Q4 was $1.2M"},
            {"type": "complete", "data": "msg-123", "hasDownloadData": False}
        ]
        
        for chunk in chunks:
            yield f"data: {chunk}\n\n"
    
    return mock_stream


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()