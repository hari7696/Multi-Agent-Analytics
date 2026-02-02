#!/usr/bin/env python3
"""
Storage Manager - Azure Blob Storage Only
Manages file uploads to Azure Blob Storage
"""

import os
import logging
from typing import Optional, Dict, Any, Tuple
import pandas as pd

logger = logging.getLogger(__name__)

class StorageManager:
    """Storage manager for Azure Blob Storage"""
    
    def __init__(self):
        """Initialize storage manager with Azure Blob Storage"""
        self.storage_backend = None
        self.backend_type = None
        self._initialize_backend()
    
    def _initialize_backend(self):
        """Initialize Azure Blob Storage backend"""
        # Check if Azure Blob Storage is available
        azure_connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        
        if not azure_connection_string:
            logger.error("AZURE_STORAGE_CONNECTION_STRING environment variable is required")
            raise RuntimeError("Azure Storage connection string not configured")
        
        try:
            from tools.blob_storage import FinancialDataBlobStorage
            self.storage_backend = FinancialDataBlobStorage(azure_connection_string)
            self.backend_type = "azure_blob"
            logger.info("✅ Azure Blob Storage initialized successfully")
        except Exception as e:
            logger.error(f"Azure Blob Storage initialization failed: {e}")
            raise RuntimeError(f"Failed to initialize Azure Blob Storage: {e}")
    
    def upload_dataset(
        self, 
        dataset: pd.DataFrame, 
        session_id: str, 
        agent_name: str,
        format: str = 'csv',
        user_id: str = None,
        message_id: str = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Upload dataset using the configured storage backend
        
        Args:
            dataset: Pandas DataFrame to upload
            session_id: Session identifier for folder organization
            agent_name: Name of the agent that generated the data
            format: File format ('csv' or 'excel')
            user_id: User identifier for folder organization
            message_id: Message identifier for folder organization
        
        Returns:
            Tuple of (download_url, metadata_dict)
        """
        if not self.storage_backend:
            raise RuntimeError("No storage backend initialized")
        
        download_url, metadata = self.storage_backend.upload_dataset(
            dataset, session_id, agent_name, format,
            user_id=user_id, message_id=message_id
        )
        
        # Add backend type to metadata
        metadata["backend_type"] = self.backend_type
        
        return download_url, metadata
    
    def upload_visualization(
        self,
        plotly_json: str,
        session_id: str,
        agent_name: str,
        user_id: str = None,
        message_id: str = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Upload Plotly visualization JSON using the configured storage backend
        
        Args:
            plotly_json: Plotly figure as JSON string
            session_id: Session identifier for folder organization
            agent_name: Name of the agent that generated the visualization
            user_id: User identifier for folder organization
            message_id: Message identifier for folder organization
        
        Returns:
            Tuple of (download_url, metadata_dict)
        """
        if not self.storage_backend:
            raise RuntimeError("No storage backend initialized")
        
        download_url, metadata = self.storage_backend.upload_visualization(
            plotly_json, session_id, agent_name, user_id, message_id
        )
        
        # Add backend type to metadata
        metadata["backend_type"] = self.backend_type
        
        return download_url, metadata
    
    def generate_download_url(self, blob_path: str, expires_hours: int = 24) -> str:
        """Generate download URL"""
        if not self.storage_backend:
            raise RuntimeError("No storage backend initialized")
        
        return self.storage_backend.generate_download_url(blob_path, expires_hours)
    
    def delete_blob(self, blob_path: str) -> bool:
        """Delete file/blob"""
        if not self.storage_backend:
            raise RuntimeError("No storage backend initialized")
        
        return self.storage_backend.delete_blob(blob_path)
    
    def cleanup_expired_files(self, session_id: Optional[str] = None) -> int:
        """Clean up expired files"""
        if not self.storage_backend:
            raise RuntimeError("No storage backend initialized")
        
        return self.storage_backend.cleanup_expired_files(session_id)
    
    def get_blob_info(self, blob_path: str) -> Optional[Dict[str, Any]]:
        """Get file/blob information"""
        if not self.storage_backend:
            raise RuntimeError("No storage backend initialized")
        
        return self.storage_backend.get_blob_info(blob_path)
    
    def get_backend_info(self) -> Dict[str, Any]:
        """Get information about the current backend"""
        return {
            "backend_type": self.backend_type,
            "backend_class": self.storage_backend.__class__.__name__,
            "azure_configured": bool(os.getenv('AZURE_STORAGE_CONNECTION_STRING'))
        }


# Global storage manager instance
_storage_manager_instance = None

def get_storage_manager() -> StorageManager:
    """Get storage manager instance (singleton pattern)"""
    global _storage_manager_instance
    
    if _storage_manager_instance is None:
        _storage_manager_instance = StorageManager()
    
    return _storage_manager_instance

def upload_analysis_dataset(
    dataset: pd.DataFrame, 
    session_id: str, 
    agent_name: str,
    format: str = 'csv'
) -> Tuple[str, Dict[str, Any]]:
    """
    Convenience function to upload analysis dataset
    
    Args:
        dataset: Pandas DataFrame to upload
        session_id: Session identifier
        agent_name: Agent that generated the data
        format: File format ('csv' or 'excel')
    
    Returns:
        Tuple of (download_url, metadata)
    """
    storage = get_storage_manager()
    return storage.upload_dataset(dataset, session_id, agent_name, format)

def is_storage_available() -> bool:
    """Check if storage is available and working"""
    try:
        storage = get_storage_manager()
        return storage.storage_backend is not None
    except Exception:
        return False