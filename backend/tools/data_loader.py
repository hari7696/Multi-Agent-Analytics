import pandas as pd
from config import logger
import os
from datetime import datetime
from typing import Optional

_unified_data_cache: Optional[pd.DataFrame] = None
_unified_data_cache_time: Optional[datetime] = None
_contract_data_cache: Optional[tuple] = None
_contract_data_cache_time: Optional[datetime] = None

CACHE_DURATION = 300

def _is_cache_valid(cache_time: Optional[datetime]) -> bool:
    """Check if cache is still valid"""
    if cache_time is None:
        return False
    return (datetime.now() - cache_time).total_seconds() < CACHE_DURATION

def load_data() -> pd.DataFrame:
    """Load the unified financial dataset with caching"""
    global _unified_data_cache, _unified_data_cache_time
    
    if _is_cache_valid(_unified_data_cache_time) and _unified_data_cache is not None:
        logger.debug("[DATA_LOADER] Using cached unified dataset")
        return _unified_data_cache.copy()
    
    logger.info("[DATA_LOADER] Loading unified financial dataset from disk")
    
    try:
        file_path = "data/unified_data.pkl"
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Data file not found: {file_path}")
            
        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        
        if (_unified_data_cache_time is not None and 
            file_mtime > _unified_data_cache_time):
            logger.info("[DATA_LOADER] Data file updated, invalidating cache")
            _unified_data_cache = None
            _unified_data_cache_time = None
        
        logger.info(f"[DATA_LOADER] Loading data from: {file_path}")
        
        unified_data = pd.read_pickle(file_path)
        
        _unified_data_cache = unified_data
        _unified_data_cache_time = datetime.now()
        
        logger.info(f"[DATA_LOADER] Successfully loaded and cached unified dataset. Shape: {unified_data.shape}")
        logger.debug(f"[DATA_LOADER] Dataset columns: {list(unified_data.columns)}")
        logger.debug(f"[DATA_LOADER] Dataset memory usage: {unified_data.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")
        
        if len(unified_data) > 0:
            logger.debug(f"[DATA_LOADER] Data types: {unified_data.dtypes.to_dict()}")
            logger.debug(f"[DATA_LOADER] Missing values per column: {unified_data.isnull().sum().to_dict()}")
        
        return unified_data.copy()
        
    except FileNotFoundError:
        logger.error(f"[DATA_LOADER] File not found: {file_path}")
        raise
    except Exception as e:
        logger.error(f"[DATA_LOADER] Error loading unified dataset: {str(e)}")
        logger.error(f"[DATA_LOADER] Exception type: {type(e).__name__}")
        raise

def load_contract_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load contract-related datasets with caching"""
    global _contract_data_cache, _contract_data_cache_time
    
    if _is_cache_valid(_contract_data_cache_time) and _contract_data_cache is not None:
        logger.debug("[DATA_LOADER] Using cached contract datasets")
        tcv_line, sales_register = _contract_data_cache
        return (tcv_line.copy(), sales_register.copy())
    
    logger.info("[DATA_LOADER] Loading contract datasets from disk")
    
    try:
        tcv_file_path = "data/tcv_line_selected.pkl"
        sales_file_path = "data/sales_register_selected.pkl"
        
        logger.info(f"[DATA_LOADER] Loading TCV line data from: {tcv_file_path}")
        tcv_line = pd.read_pickle(tcv_file_path)
        logger.info(f"[DATA_LOADER] Successfully loaded TCV line data. Shape: {tcv_line.shape}")
        
        logger.info(f"[DATA_LOADER] Loading sales register data from: {sales_file_path}")
        sales_register = pd.read_pickle(sales_file_path)
        logger.info(f"[DATA_LOADER] Successfully loaded sales register data. Shape: {sales_register.shape}")
        
        _contract_data_cache = (tcv_line, sales_register)
        _contract_data_cache_time = datetime.now()
        
        logger.info(f"[DATA_LOADER] Contract datasets loaded and cached successfully")
        logger.info(f"[DATA_LOADER] TCV line columns: {list(tcv_line.columns)}")
        logger.info(f"[DATA_LOADER] Sales register columns: {list(sales_register.columns)}")
        
        return (tcv_line.copy(), sales_register.copy())
        
    except FileNotFoundError as e:
        logger.error(f"[DATA_LOADER] File not found during contract data loading: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"[DATA_LOADER] Error loading contract datasets: {str(e)}")
        logger.error(f"[DATA_LOADER] Exception type: {type(e).__name__}")
        raise

def clear_cache():
    """Clear all cached data (useful for testing or memory management)"""
    global _unified_data_cache, _unified_data_cache_time, _contract_data_cache, _contract_data_cache_time
    _unified_data_cache = None
    _unified_data_cache_time = None
    _contract_data_cache = None
    _contract_data_cache_time = None
    logger.info("[DATA_LOADER] All caches cleared")

def get_cache_info():
    """Get information about current cache status"""
    unified_cached = _unified_data_cache is not None and _is_cache_valid(_unified_data_cache_time)
    contract_cached = _contract_data_cache is not None and _is_cache_valid(_contract_data_cache_time)
    
    return {
        "unified_data_cached": unified_cached,
        "contract_data_cached": contract_cached,
        "unified_cache_time": _unified_data_cache_time,
        "contract_cache_time": _contract_data_cache_time,
        "cache_duration_seconds": CACHE_DURATION
    }

