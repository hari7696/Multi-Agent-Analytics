"""
Cosmos DB Session Service for ADK
=================================

This package provides a complete Cosmos DB-based implementation of ADK's BaseSessionService
for persistent session and event storage.

Key Components:
- CosmosDBClient: Direct Cosmos DB operations
- CosmosSessionService: ADK BaseSessionService implementation
- Data Converters: Serialization/deserialization functions

Usage:
    from cosmosservice import cosmos_session_service
    
    # Replace InMemorySessionService with:
    session_service = cosmos_session_service

Features:
- Full ADK BaseSessionService compatibility
- Persistent session and event storage
- State management with Cosmos DB persistence
- Event history reconstruction
- Performance optimized queries
- Comprehensive error handling and logging

Architecture:
- Sessions Collection: Partition by user_id, stores session metadata and current state
- Events Collection: Partition by session_id, append-only event storage
- State Management: Current state in Sessions, history via Events state_delta
"""

from .cosmos_client import CosmosDBClient, cosmos_client
from .cosmos_session_service import CosmosSessionService, cosmos_session_service
from .data_converters import (
    serialize_adk_event,
    deserialize_cosmos_event,
    serialize_session_for_cosmos,
    deserialize_session_from_cosmos,
    validate_json_serializable
)

# Version information
__version__ = "1.0.0"
__author__ = "ADK Cosmos DB Integration Team"

# Main exports - ready-to-use instances
__all__ = [
    # Ready-to-use instances
    "cosmos_session_service",  # Main export - drop-in replacement for InMemorySessionService
    "cosmos_client",
    
    # Classes for advanced usage
    "CosmosSessionService",
    "CosmosDBClient",
    
    # Utility functions
    "serialize_adk_event",
    "deserialize_cosmos_event", 
    "serialize_session_for_cosmos",
    "deserialize_session_from_cosmos",
    "validate_json_serializable",
    
    # Package metadata
    "__version__"
]

# Package-level configuration
def test_connection() -> bool:
    """
    Test Cosmos DB connection for the entire package.
    
    Returns:
        True if connection is successful, False otherwise
    """
    return cosmos_client.test_connection()

def get_package_info() -> dict:
    """
    Get package information and status.
    
    Returns:
        Dictionary with package information
    """
    return {
        "name": "cosmosservice",
        "version": __version__,
        "author": __author__,
        "cosmos_connection": test_connection(),
        "components": {
            "cosmos_client": "CosmosDBClient for direct database operations",
            "cosmos_session_service": "ADK BaseSessionService implementation", 
            "data_converters": "Serialization/deserialization functions"
        },
        "usage": "from cosmosservice import cosmos_session_service"
    }

# Initialize logging
import logging
logger = logging.getLogger(__name__)
logger.info(f"CosmosService package v{__version__} initialized")

# Validate package initialization
try:
    # Test that all components can be imported
    assert cosmos_client is not None, "cosmos_client not initialized"
    assert cosmos_session_service is not None, "cosmos_session_service not initialized"
    logger.info("CosmosService package validation successful")
except Exception as e:
    logger.error(f"CosmosService package validation failed: {e}")
    raise
