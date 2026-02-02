"""
Database Connection Manager for Adventure Works SQLite
Provides connection pooling and query utilities
"""

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
import pandas as pd
import logging

logger = logging.getLogger("fin_agent")

_connection = None


def get_connection() -> sqlite3.Connection:
    """
    Get or create SQLite connection (singleton pattern)
    
    Returns:
        sqlite3.Connection: Database connection
    """
    global _connection
    if _connection is None:
        db_path = Path(__file__).parent / "data" / "adventureworks.db"
        if not db_path.exists():
            raise FileNotFoundError(f"Database not found at {db_path}")
        
        _connection = sqlite3.connect(db_path, check_same_thread=False)
        _connection.row_factory = sqlite3.Row  # Enable column access by name
        logger.info(f"[DB_CONNECTION] Connected to database: {db_path}")
    
    return _connection


def query_to_dataframe(query: str, params: Optional[tuple] = None) -> pd.DataFrame:
    """
    Execute SQL query and return DataFrame
    
    Args:
        query: SQL query string
        params: Optional query parameters
        
    Returns:
        pd.DataFrame: Query results as DataFrame
    """
    conn = get_connection()
    try:
        df = pd.read_sql(query, conn, params=params)
        logger.debug(f"[DB_CONNECTION] Query returned {len(df)} rows")
        return df
    except Exception as e:
        logger.error(f"[DB_CONNECTION] Query failed: {e}")
        logger.error(f"[DB_CONNECTION] Query: {query[:200]}...")
        raise


def execute_query(query: str, params: Optional[tuple] = None) -> int:
    """
    Execute a non-SELECT query (INSERT, UPDATE, DELETE)
    
    Args:
        query: SQL query string
        params: Optional query parameters
        
    Returns:
        int: Number of rows affected
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        conn.commit()
        rows_affected = cursor.rowcount
        logger.debug(f"[DB_CONNECTION] Query affected {rows_affected} rows")
        return rows_affected
    except Exception as e:
        logger.error(f"[DB_CONNECTION] Execute query failed: {e}")
        conn.rollback()
        raise


def get_table_list() -> List[str]:
    """
    Get list of all tables in the database
    
    Returns:
        List[str]: List of table names
    """
    query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    df = query_to_dataframe(query)
    return df['name'].tolist()


def get_view_list() -> List[str]:
    """
    Get list of all views in the database
    
    Returns:
        List[str]: List of view names
    """
    query = "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name"
    df = query_to_dataframe(query)
    return df['name'].tolist()


def get_table_info(table_name: str) -> Dict[str, Any]:
    """
    Get information about a specific table or view
    
    Args:
        table_name: Name of the table or view
        
    Returns:
        Dict with keys: columns, row_count, sample_data
    """
    conn = get_connection()
    
    # Get column info
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [{'name': row[1], 'type': row[2]} for row in cursor.fetchall()]
    
    # Get row count
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    row_count = cursor.fetchone()[0]
    
    # Get sample data (first 5 rows)
    sample_df = query_to_dataframe(f"SELECT * FROM {table_name} LIMIT 5")
    
    return {
        'columns': columns,
        'row_count': row_count,
        'sample_data': sample_df.to_dict('records')
    }


def test_connection() -> bool:
    """
    Test database connection
    
    Returns:
        bool: True if connection successful
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        if result[0] == 1:
            logger.info("[DB_CONNECTION] Database connection test successful")
            return True
        return False
    except Exception as e:
        logger.error(f"[DB_CONNECTION] Connection test failed: {e}")
        return False


def close_connection():
    """Close the database connection"""
    global _connection
    if _connection:
        _connection.close()
        _connection = None
        logger.info("[DB_CONNECTION] Connection closed")


if __name__ == "__main__":
    # Test the connection and display database info
    logging.basicConfig(level=logging.INFO)
    
    print("=== Adventure Works Database Connection Test ===\n")
    
    # Test connection
    if test_connection():
        print("✓ Database connection successful\n")
        
        # List tables
        tables = get_table_list()
        print(f"Tables: {len(tables)}")
        print(f"  Sample: {', '.join(tables[:5])}...\n")
        
        # List views
        views = get_view_list()
        print(f"Views: {len(views)}")
        for view in views:
            print(f"  - {view}")
        
        # Test a sample query
        print("\n=== Sample Query Test ===")
        query = "SELECT * FROM vw_sales_order_header LIMIT 3"
        df = query_to_dataframe(query)
        print(f"Query returned {len(df)} rows, {len(df.columns)} columns")
        print(f"Columns: {list(df.columns)[:5]}...")
        
        close_connection()
    else:
        print("✗ Database connection failed")

