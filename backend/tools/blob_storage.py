#!/usr/bin/env python3
"""
Azure Blob Storage Service for Financial Analysis Data
Handles upload, download, and URL generation for large datasets
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
import pandas as pd
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
import uuid
from azure.storage.blob import ContentSettings

logger = logging.getLogger(__name__)

class FinancialDataBlobStorage:
    """Production-grade blob storage for financial analysis datasets"""
    
    def __init__(self, connection_string: Optional[str] = None, container_name: Optional[str] = None):
        """
        Initialize blob storage client
        
        Args:
            connection_string: Azure storage connection string
                             If None, will try to get from KeyVault or environment variable
            container_name: Azure storage container name
                          If None, will try to get from KeyVault or environment variable
        """
        # Get from environment variables
        self.connection_string = connection_string or os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        if not self.connection_string:
            raise ValueError("Azure Storage connection string is required")
        
        # Get container name from environment or use default
        self.container_name = container_name or os.getenv('AZURE_CONTAINER_NAME') or "mtfinance-agent-container"
        
        self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
        self.account_name = self._extract_account_name()
        self.account_key = self._extract_account_key()
        
        logger.info(f"Blob storage initialized with container: {self.container_name}")
        
        # Ensure container exists
        self._ensure_container_exists()
    
    def _extract_account_name(self) -> str:
        """Extract storage account name from connection string"""
        try:
            for part in self.connection_string.split(';'):
                if part.startswith('AccountName='):
                    return part.split('=', 1)[1]
            raise ValueError("AccountName not found in connection string")
        except Exception as e:
            logger.error(f"Failed to extract account name: {e}")
            return "unknown"
    
    def _extract_account_key(self) -> str:
        """Extract storage account key from connection string"""
        try:
            for part in self.connection_string.split(';'):
                if part.startswith('AccountKey='):
                    return part.split('=', 1)[1]
            raise ValueError("AccountKey not found in connection string")
        except Exception as e:
            logger.error(f"Failed to extract account key: {e}")
            return ""
    
    def _ensure_container_exists(self):
        """Create container if it doesn't exist"""
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            container_client.create_container()
            logger.info(f"Created blob container: {self.container_name}")
        except ResourceExistsError:
            logger.debug(f"Container {self.container_name} already exists")
        except Exception as e:
            logger.error(f"Failed to ensure container exists: {e}")
    
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
        Upload dataset to blob storage and return download metadata
        
        Args:
            dataset: Pandas DataFrame to upload
            session_id: Session identifier for folder organization
            agent_name: Name of the agent that generated the data
            format: File format ('csv' or 'excel')
            user_id: User identifier for folder organization
            message_id: Message identifier for folder organization
        
        Returns:
            Tuple of (blob_url, metadata_dict)
        """
        try:
            # Generate unique filename
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            file_id = str(uuid.uuid4())[:8]
            
            if format.lower() == 'excel':
                filename = f"{timestamp}_{agent_name}_{file_id}.xlsx"
                content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            else:
                filename = f"{timestamp}_{agent_name}_{file_id}.csv"
                content_type = "text/csv"
            
            # Create blob path: user_id/session_id/message_id/filename
            if user_id and message_id:
                blob_path = f"{user_id}/{session_id}/{message_id}/{filename}"
            else:
                # Fallback to old structure for backward compatibility
                blob_path = f"{session_id}/{filename}"
            
            # Convert dataset to bytes
            if format.lower() == 'excel':
                import io
                buffer = io.BytesIO()
                dataset.to_excel(buffer, index=False, engine='openpyxl')
                file_content = buffer.getvalue()
            else:
                file_content = dataset.to_csv(index=False).encode('utf-8')
            
            # Upload to blob storage
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, 
                blob=blob_path
            )
            
            
            
            blob_client.upload_blob(
                file_content, 
                overwrite=True,
                content_settings=ContentSettings(
                    content_type=content_type,
                    content_disposition=f'attachment; filename="{filename}"'
                )
            )
            
            # Generate SAS URL for secure downloads (expires in 7 days)
            download_url = self.generate_download_url(blob_path, expires_hours=168, force_download=True)  # 7 days
            
            # Create minimal metadata (no columns array to reduce storage)
            metadata = {
                "blob_path": blob_path,
                "filename": filename,
                "format": format,
                "record_count": len(dataset),
                "file_size_bytes": len(file_content),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
            }
            
            logger.info(f"Uploaded dataset to blob: {blob_path} ({len(dataset)} records, {len(file_content)} bytes)")
            return download_url, metadata
            
        except Exception as e:
            logger.error(f"Failed to upload dataset to blob storage: {e}")
            raise
    
    def upload_visualization(
        self,
        plotly_json: str,
        session_id: str,
        agent_name: str,
        user_id: str = None,
        message_id: str = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Upload Plotly visualization as HTML to blob storage
        
        Args:
            plotly_json: Plotly figure JSON string
            session_id: Session identifier
            agent_name: Name of the agent that generated the visualization
            user_id: User identifier for folder organization
            message_id: Message identifier for folder organization
        
        Returns:
            Tuple of (blob_url, metadata_dict)
        """
        try:
            import json
            
            # Generate unique filename - store as JSON not HTML
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            file_id = str(uuid.uuid4())[:8]
            filename = f"{timestamp}_{agent_name}_viz_{file_id}.json"
            
            # Create blob path: user_id/session_id/message_id/filename
            if user_id and message_id:
                blob_path = f"{user_id}/{session_id}/{message_id}/{filename}"
            else:
                # Fallback to old structure for backward compatibility
                blob_path = f"{session_id}/{filename}"
            
            # Verify plotly_json is valid before storing
            try:
                plotly_dict_test = json.loads(plotly_json)
                logger.info(f"Storing plotly JSON to blob: {len(plotly_dict_test.get('data', []))} traces")
            except json.JSONDecodeError as e:
                logger.error(f"Invalid plotly JSON before storage: {e}")
                raise
            
            # Store raw Plotly JSON (not HTML) so frontend can render with PlotlyVisualization component
            # This ensures identical rendering between streaming and after page refresh
            file_content = plotly_json.encode('utf-8')
            
            # Upload to blob storage
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_path
            )
            
            from azure.storage.blob import ContentSettings
            
            blob_client.upload_blob(
                file_content,
                overwrite=True,
                content_settings=ContentSettings(
                    content_type='application/json',
                    content_disposition=f'inline; filename="{filename}"'
                )
            )
            
            # Generate SAS URL for secure downloads (expires in 7 days) 
            download_url = self.generate_download_url(blob_path, expires_hours=168, force_download=True)
            
            # Parse metadata from JSON
            plotly_dict = json.loads(plotly_json)
            
            # Create minimal metadata (no redundant session info)
            metadata = {
                "blob_path": blob_path,
                "filename": filename,
                "format": "html",
                "file_size_bytes": len(file_content),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                "chart_type": plotly_dict.get('data', [{}])[0].get('type', 'unknown') if plotly_dict.get('data') else 'unknown'
            }
            
            logger.info(f"Uploaded visualization to blob: {blob_path} ({len(file_content)} bytes)")
            return download_url, metadata
            
        except Exception as e:
            logger.error(f"Failed to upload visualization to blob storage: {e}")
            raise
    
    def generate_download_url(self, blob_path: str, expires_hours: int = 24, force_download: bool = True) -> str:
        """
        Generate a secure SAS URL for downloading the blob
        
        Args:
            blob_path: Path to blob in container
            expires_hours: Hours until URL expires
            force_download: If True, forces browser to download instead of displaying
        
        Returns:
            Secure download URL
        """
        try:
            # Extract filename from blob_path
            filename = blob_path.split('/')[-1]
            
            # Generate SAS token with content_disposition for forced download
            sas_token = generate_blob_sas(
                account_name=self.account_name,
                account_key=self.account_key,
                container_name=self.container_name,
                blob_name=blob_path,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.now(timezone.utc) + timedelta(hours=expires_hours),
                content_disposition=f'attachment; filename="{filename}"' if force_download else None
            )
            
            # Construct full URL
            blob_url = f"https://{self.account_name}.blob.core.windows.net/{self.container_name}/{blob_path}?{sas_token}"
            return blob_url
            
        except Exception as e:
            logger.error(f"Failed to generate download URL for {blob_path}: {e}")
            raise
    
    def delete_blob(self, blob_path: str) -> bool:
        """
        Delete a blob from storage
        
        Args:
            blob_path: Path to blob in container
        
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_path
            )
            blob_client.delete_blob()
            logger.info(f"Deleted blob: {blob_path}")
            return True
            
        except ResourceNotFoundError:
            logger.warning(f"Blob not found for deletion: {blob_path}")
            return True  # Already deleted
        except Exception as e:
            logger.error(f"Failed to delete blob {blob_path}: {e}")
            return False
    
    def cleanup_expired_files(self, session_id: Optional[str] = None) -> int:
        """
        Clean up expired files (older than 7 days)
        
        Args:
            session_id: If provided, only clean files for this session
        
        Returns:
            Number of files deleted
        """
        try:
            deleted_count = 0
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=7)
            
            # List blobs in container
            prefix = f"{session_id}/" if session_id else None
            blobs = self.blob_service_client.get_container_client(self.container_name).list_blobs(name_starts_with=prefix)
            
            for blob in blobs:
                if blob.last_modified < cutoff_time:
                    if self.delete_blob(blob.name):
                        deleted_count += 1
            
            logger.info(f"Cleanup completed: deleted {deleted_count} expired files")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired files: {e}")
            return 0
    
    def get_blob_info(self, blob_path: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a blob
        
        Args:
            blob_path: Path to blob in container
        
        Returns:
            Blob information dictionary or None if not found
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_path
            )
            
            properties = blob_client.get_blob_properties()
            return {
                "name": blob_path,
                "size": properties.size,
                "last_modified": properties.last_modified.isoformat(),
                "content_type": properties.content_settings.content_type,
                "exists": True
            }
            
        except ResourceNotFoundError:
            return None
        except Exception as e:
            logger.error(f"Failed to get blob info for {blob_path}: {e}")
            return None


# Global instance (initialized when connection string is available)
_blob_storage_instance = None

def get_blob_storage() -> Optional[FinancialDataBlobStorage]:
    """Get blob storage instance (singleton pattern)"""
    global _blob_storage_instance
    
    if _blob_storage_instance is None:
        try:
            # Get credentials from environment variables
            connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
            container_name = os.getenv('AZURE_CONTAINER_NAME')
            
            if connection_string:
                _blob_storage_instance = FinancialDataBlobStorage(connection_string, container_name)
                logger.info("Blob storage initialized successfully")
            else:
                logger.debug("Azure Storage connection string not found, blob storage disabled")
                return None
        except Exception as e:
            logger.warning(f"Blob storage initialization failed: {e}")
            return None
    
    return _blob_storage_instance

def is_blob_storage_available() -> bool:
    """Check if blob storage is available and configured"""
    return get_blob_storage() is not None