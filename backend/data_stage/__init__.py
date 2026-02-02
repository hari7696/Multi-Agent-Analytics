"""
Adventure Works OLTP - Data Stage Initialization
Initializes database connection and entity cache on import
"""
import logging
from .db_connection import get_connection, query_to_dataframe

logger = logging.getLogger("fin_agent")

def initialize():
    """Initialize database and caches"""
    try:
        # Test database connection
        conn = get_connection()
        if conn:
            conn.execute("SELECT 1")
            logger.info("[DATA_STAGE] Database connection verified")
        
        # Load entity cache
        from tools.entity_cache import load_entity_cache
        load_entity_cache()
        logger.info("[DATA_STAGE] Entity cache loaded")
        
    except Exception as e:
        logger.error(f"[DATA_STAGE] Failed to initialize: {e}")

# Initialize on import
initialize()

__all__ = ['get_connection', 'query_to_dataframe']
