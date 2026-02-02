"""
Entity Cache Manager for Adventure Works
Caches distinct entity values from SQLite for fast verification
"""

import logging
from typing import Dict, Set, Optional
from datetime import datetime, timedelta

logger = logging.getLogger("fin_agent")

# Global cache storage
_entity_cache: Dict[str, Set[str]] = {}
_cache_loaded_at: Optional[datetime] = None
CACHE_EXPIRY_HOURS = 24  # Refresh cache after 24 hours


def load_entity_cache(force_reload: bool = False) -> Dict[str, Set[str]]:
    """
    Load distinct entities from SQLite into memory cache
    
    Args:
        force_reload: Force reload even if cache is valid
        
    Returns:
        Dict[str, Set[str]]: Entity cache dictionary
    """
    global _entity_cache, _cache_loaded_at
    
    # Check if cache is still valid
    if not force_reload and _cache_loaded_at:
        age = datetime.now() - _cache_loaded_at
        if age < timedelta(hours=CACHE_EXPIRY_HOURS):
            logger.debug(f"[ENTITY_CACHE] Using cached entities (age: {age})")
            return _entity_cache
    
    logger.info("[ENTITY_CACHE] Loading entities from database...")
    
    # Import here to avoid circular dependency
    from data_stage.db_connection import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Define entity queries - map entity_type to SQL query
    entity_queries = {
        # Sales entities
        'customer_name': """
            SELECT DISTINCT customer_name 
            FROM vw_customers_master 
            WHERE customer_name IS NOT NULL
        """,
        'salesperson_name': """
            SELECT DISTINCT salesperson_name 
            FROM vw_salesperson_master 
            WHERE salesperson_name IS NOT NULL
        """,
        'territory_name': """
            SELECT DISTINCT territory_name 
            FROM vw_sales_territory_master 
            WHERE territory_name IS NOT NULL
        """,
        
        # Production entities
        'product_name': """
            SELECT DISTINCT product_name 
            FROM vw_products_master 
            WHERE product_name IS NOT NULL
        """,
        'product_category': """
            SELECT DISTINCT product_category 
            FROM vw_products_master 
            WHERE product_category IS NOT NULL
        """,
        'product_subcategory': """
            SELECT DISTINCT product_subcategory 
            FROM vw_products_master 
            WHERE product_subcategory IS NOT NULL
        """,
        'model_name': """
            SELECT DISTINCT model_name 
            FROM vw_products_master 
            WHERE model_name IS NOT NULL
        """,
        'location_name': """
            SELECT DISTINCT location_name 
            FROM vw_inventory_current 
            WHERE location_name IS NOT NULL
        """,
        
        # Purchasing entities
        'vendor_name': """
            SELECT DISTINCT vendor_name 
            FROM vw_vendors_master 
            WHERE vendor_name IS NOT NULL
        """,
        
        # HR entities  
        'employee_name': """
            SELECT DISTINCT employee_name 
            FROM vw_employees_master 
            WHERE employee_name IS NOT NULL
        """,
        'department_name': """
            SELECT DISTINCT department_name 
            FROM vw_departments_master 
            WHERE department_name IS NOT NULL
        """,
        'shift_name': """
            SELECT DISTINCT shift_name 
            FROM vw_employee_dept_history 
            WHERE shift_name IS NOT NULL
        """,
    }
    
    _entity_cache.clear()
    
    for entity_type, query in entity_queries.items():
        try:
            cursor.execute(query)
            values = set(row[0] for row in cursor.fetchall() if row[0])
            _entity_cache[entity_type] = values
            logger.debug(f"[ENTITY_CACHE] Loaded {len(values)} values for {entity_type}")
        except Exception as e:
            logger.warning(f"[ENTITY_CACHE] Failed to load {entity_type}: {e}")
            _entity_cache[entity_type] = set()
    
    _cache_loaded_at = datetime.now()
    
    total_entities = sum(len(values) for values in _entity_cache.values())
    logger.info(f"[ENTITY_CACHE] Loaded {total_entities} total entities across {len(_entity_cache)} types")
    
    return _entity_cache


def get_entity_values(entity_type: str) -> Set[str]:
    """
    Get cached entity values for a specific type
    
    Args:
        entity_type: Type of entity (e.g., 'customer_name', 'product_name')
        
    Returns:
        Set[str]: Set of distinct entity values
    """
    if not _entity_cache:
        load_entity_cache()
    
    return _entity_cache.get(entity_type, set())


def map_column_to_entity_type(column_name: str) -> str | None:
    """
    Map a column name to its entity cache type
    
    Args:
        column_name: Column name from query
        
    Returns:
        str | None: Entity type or None if not mapped
    """
    column_lower = column_name.lower()
    
    # Map common column names to entity types
    mapping = {
        'customer_name': 'customer_name',
        'customer_full_name': 'customer_name',
        'salesperson_name': 'salesperson_name',
        'salesperson_full_name': 'salesperson_name',
        'territory_name': 'territory_name',
        'sales_territory_name': 'territory_name',
        'product_name': 'product_name',
        'product_category': 'product_category',
        'product_subcategory': 'product_subcategory',
        'vendor_name': 'vendor_name',
        'employee_name': 'employee_name',
        'employee_full_name': 'employee_name',
        'department_name': 'department_name',
        'location_name': 'location_name',
        'model_name': 'model_name',
        'shift_name': 'shift_name',
    }
    
    return mapping.get(column_lower, None)


def get_all_entity_types() -> list:
    """
    Get list of all available entity types
    
    Returns:
        list: List of entity type names
    """
    if not _entity_cache:
        load_entity_cache()
    
    return list(_entity_cache.keys())


def get_cache_stats() -> Dict:
    """
    Get statistics about the entity cache
    
    Returns:
        Dict: Cache statistics
    """
    if not _entity_cache:
        return {'loaded': False}
    
    stats = {
        'loaded': True,
        'loaded_at': _cache_loaded_at.isoformat() if _cache_loaded_at else None,
        'entity_types': len(_entity_cache),
        'total_entities': sum(len(values) for values in _entity_cache.values()),
        'by_type': {
            entity_type: len(values) 
            for entity_type, values in _entity_cache.items()
        }
    }
    
    return stats


def clear_cache():
    """Clear the entity cache (force reload on next access)"""
    global _entity_cache, _cache_loaded_at
    _entity_cache.clear()
    _cache_loaded_at = None
    logger.info("[ENTITY_CACHE] Cache cleared")


def map_column_to_entity_type(column_name: str) -> Optional[str]:
    """
    Map a column name to an entity type
    
    Args:
        column_name: Column name from schema
        
    Returns:
        Optional[str]: Entity type or None if no mapping
    """
    # Normalize column name
    col_lower = column_name.lower()
    
    # Direct mappings
    mappings = {
        'customer_name': 'customer_name',
        'salesperson_name': 'salesperson_name',
        'territory_name': 'territory_name',
        'product_name': 'product_name',
        'product_category': 'product_category',
        'product_subcategory': 'product_subcategory',
        'model_name': 'model_name',
        'location_name': 'location_name',
        'vendor_name': 'vendor_name',
        'department_name': 'department_name',
        'shift_name': 'shift_name',
    }
    
    return mappings.get(col_lower)


if __name__ == "__main__":
    # Test the entity cache
    logging.basicConfig(level=logging.INFO)
    
    print("=== Entity Cache Test ===\n")
    
    # Load cache
    cache = load_entity_cache()
    
    # Display stats
    stats = get_cache_stats()
    print(f"Cache loaded: {stats['loaded']}")
    print(f"Entity types: {stats['entity_types']}")
    print(f"Total entities: {stats['total_entities']}\n")
    
    print("Entities by type:")
    for entity_type, count in sorted(stats['by_type'].items()):
        print(f"  {entity_type}: {count}")
    
    # Show sample values
    print("\nSample values:")
    for entity_type in ['customer_name', 'product_name', 'territory_name']:
        values = get_entity_values(entity_type)
        if values:
            sample = list(values)[:3]
            print(f"  {entity_type}: {sample}")

