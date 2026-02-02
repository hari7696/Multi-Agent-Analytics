from config import logger
from difflib import get_close_matches, SequenceMatcher
from google.adk.tools.tool_context import ToolContext
from typing import Dict, Optional
from datetime import datetime, timedelta
import pandas as pd

# Entity verification cache
_entity_cache: Dict[str, Dict] = {}
_cache_expiry: Dict[str, datetime] = {}

# Cache duration: 2 minutes (shorter than data cache)
ENTITY_CACHE_DURATION = 120

def _get_cache_key(entity_name: str, entity_value: str) -> str:
    """Generate cache key for entity verification"""
    return f"{entity_name.lower()}:{str(entity_value).lower()}"

def _is_entity_cache_valid(cache_key: str) -> bool:
    """Check if entity cache entry is still valid"""
    if cache_key not in _cache_expiry:
        return False
    return datetime.now() < _cache_expiry[cache_key]

def _cache_entity_result(cache_key: str, result: dict) -> None:
    """Cache entity verification result"""
    _entity_cache[cache_key] = result
    _cache_expiry[cache_key] = datetime.now() + timedelta(seconds=ENTITY_CACHE_DURATION)

def _store_verified_entity(tool_context: ToolContext, entity_name: str, entity_value: str) -> None:
    """Store verified entity in business context for conversation continuity"""
    try:
        business_context = tool_context.state.get("business_context", {})
        
        # Store based on entity type
        entity_name_lower = entity_name.lower()
        entity_value_str = str(entity_value)
        
        # Customer Name
        if "customer" in entity_name_lower and "name" in entity_name_lower:
            if entity_value_str not in business_context.get("customer_names", []):
                business_context.setdefault("customer_names", []).append(entity_value_str)
                logger.info("[ENTITY_VERIFIER] Stored customer name: %s", entity_value_str)
        
        # Salesperson Name
        elif "salesperson" in entity_name_lower and "name" in entity_name_lower:
            if entity_value_str not in business_context.get("salesperson_names", []):
                business_context.setdefault("salesperson_names", []).append(entity_value_str)
                logger.info("[ENTITY_VERIFIER] Stored salesperson name: %s", entity_value_str)
        
        # Territory Name
        elif "territory" in entity_name_lower and "name" in entity_name_lower:
            if entity_value_str not in business_context.get("territory_names", []):
                business_context.setdefault("territory_names", []).append(entity_value_str)
                logger.info("[ENTITY_VERIFIER] Stored territory name: %s", entity_value_str)
        
        # Product Name
        elif "product" in entity_name_lower and "name" in entity_name_lower:
            if entity_value_str not in business_context.get("product_names", []):
                business_context.setdefault("product_names", []).append(entity_value_str)
                logger.info("[ENTITY_VERIFIER] Stored product name: %s", entity_value_str)
        
        # Product Category
        elif "category" in entity_name_lower or "subcategory" in entity_name_lower:
            if entity_value_str not in business_context.get("product_categories", []):
                business_context.setdefault("product_categories", []).append(entity_value_str)
                logger.info("[ENTITY_VERIFIER] Stored product category: %s", entity_value_str)
        
        # Vendor Name
        elif "vendor" in entity_name_lower and "name" in entity_name_lower:
            if entity_value_str not in business_context.get("vendor_names", []):
                business_context.setdefault("vendor_names", []).append(entity_value_str)
                logger.info("[ENTITY_VERIFIER] Stored vendor name: %s", entity_value_str)
        
        # Department Name
        elif "department" in entity_name_lower and "name" in entity_name_lower:
            if entity_value_str not in business_context.get("department_names", []):
                business_context.setdefault("department_names", []).append(entity_value_str)
                logger.info("[ENTITY_VERIFIER] Stored department name: %s", entity_value_str)
        
        # Store all verified entities for reference
        entity_record = {"name": entity_name, "value": entity_value_str}
        if entity_record not in business_context.get("verified_entities", []):
            business_context.setdefault("verified_entities", []).append(entity_record)
        
        tool_context.state["business_context"] = business_context
        
    except Exception as e:
        logger.warning(f"[ENTITY_VERIFIER] Failed to store entity in business context: {e}")

def _calculate_similarity_scores(entity_value_str: str, lowercase_values: list) -> list:
    """Calculate similarity scores for all values"""
    scores = []
    for val in lowercase_values:
        similarity = SequenceMatcher(None, entity_value_str, val).ratio()
        scores.append((val, similarity))
    return sorted(scores, key=lambda x: x[1], reverse=True)

def verify_entity_in_dataframe(entity_name: str, entity_value: str, tool_context: ToolContext) -> dict:
    """
    Three-Phase Entity Verification:
    Phase 1: Exact Match (100%) - Return immediately
    Phase 2: High Confidence (60%+) - Auto-select the best match
    Phase 3: Medium Confidence (40-60%) - Return options for user choice
    """
    
    # Check cache first
    cache_key = _get_cache_key(entity_name, entity_value)
    if _is_entity_cache_valid(cache_key):
        logger.debug(f"[ENTITY_VERIFIER] Using cached result for {entity_name}:{entity_value}")
        return _entity_cache[cache_key].copy()
    
    logger.info(f"[ENTITY_VERIFIER] Starting 3-phase entity verification. Entity: {entity_name}, Value: {entity_value}")
    logger.info(f"[ENTITY_VERIFIER] Agent calling this tool: {tool_context.agent_name}")
    
    # Initialize business context storage in tool_context.state if not present
    if "business_context" not in tool_context.state:
        tool_context.state["business_context"] = {
            "customer_names": [],
            "salesperson_names": [],
            "territory_names": [],
            "product_names": [],
            "product_categories": [],
            "vendor_names": [],
            "department_names": [],
            "verified_entities": []
        }
        logger.debug("[ENTITY_VERIFIER] Initialized business_context in tool state")
    
    try:
        logger.debug("[ENTITY_VERIFIER] Using entity cache for verification")
        
        # Map entity name to cache type
        from tools.entity_cache import map_column_to_entity_type, get_entity_values
        
        entity_type = map_column_to_entity_type(entity_name)
        
        if not entity_type:
            logger.warning(f"[ENTITY_VERIFIER] No entity type mapping for '{entity_name}'")
            result = {"status": "not_found", "message": f"Entity '{entity_name}' not configured for verification"}
            _cache_entity_result(cache_key, result)
            return result
        
        # Get cached values
        cached_values = get_entity_values(entity_type)
        
        if not cached_values:
            logger.warning(f"[ENTITY_VERIFIER] No cached values for entity type '{entity_type}'")
            result = {"status": "not_found", "message": f"No values found for entity '{entity_name}'"}
            _cache_entity_result(cache_key, result)
            return result
        
        logger.info(f"[ENTITY_VERIFIER] Found {len(cached_values)} cached values for '{entity_type}'")
        
        # Convert entity_value to string and lowercase for case insensitive comparison
        try:
            float_val = float(entity_value)
            if float_val.is_integer():
                entity_value_str = str(int(float_val)).lower()
                logger.info(f"[ENTITY_VERIFIER] Converted float entity value {entity_value} to integer string: {entity_value_str}")
            else:
                entity_value_str = str(entity_value).lower()
                logger.info(f"[ENTITY_VERIFIER] Converted entity value {entity_value} to string: {entity_value_str}")
        except (ValueError, TypeError):
            entity_value_str = str(entity_value).lower()
            logger.info(f"[ENTITY_VERIFIER] Entity value {entity_value} is not numeric, converted to string: {entity_value_str}")
        
        # Prepare cached values for matching
        original_values = list(cached_values)
        lowercase_values = [val.lower() for val in original_values]
        
        logger.debug(f"[ENTITY_VERIFIER] Total unique values in cache: {len(original_values)}")
        
        # ============================================================
        # PHASE 1: EXACT MATCH (100% Confidence)
        # ============================================================
        if entity_value_str in lowercase_values:
            logger.info(f"[ENTITY_VERIFIER] ✅ PHASE 1 - EXACT MATCH (100%): Entity {entity_name} = '{entity_value}' found in database")
            
            # Find original case value
            for i, low_val in enumerate(lowercase_values):
                if low_val == entity_value_str:
                    original_match = original_values[i]
                    break
            else:
                original_match = entity_value
            
            # Store verified entity in business context for conversation continuity
            _store_verified_entity(tool_context, entity_name, original_match)
            
            result = {
                "status": "success",
                "phase": "exact_match",
                "confidence": 1.0,
                "matched_value": original_match,
                "message": f"Exact match found: {original_match}"
            }
            _cache_entity_result(cache_key, result)
            return result
        
        # ============================================================
        # PHASE 2 & 3: FUZZY MATCHING
        # ============================================================
        logger.info("[ENTITY_VERIFIER] No exact match found. Computing similarity scores for all values...")
        
        # Calculate similarity scores for all values
        similarity_scores = _calculate_similarity_scores(entity_value_str, lowercase_values)
        
        # Filter and categorize by confidence thresholds
        high_confidence_matches = []  # 60%+ similarity OR substring match
        medium_confidence_matches = []  # 40-60% similarity
        
        for val, score in similarity_scores:
            # Check if search term is a complete substring (e.g., "freeman" in "freeman corporation")
            is_substring_match = entity_value_str in val or val in entity_value_str
            
            # Boost confidence for substring matches
            if is_substring_match and score >= 0.50:
                # Substring match with decent similarity -> High confidence
                # Boost the score to reflect high confidence (minimum 0.85 for substring matches)
                boosted_score = max(score, 0.85)
                logger.debug(f"[ENTITY_VERIFIER] Substring match detected: '{entity_value_str}' in '{val}' (score: {score:.2f} -> {boosted_score:.2f})")
                high_confidence_matches.append((val, boosted_score))
            elif score >= 0.60:
                high_confidence_matches.append((val, score))
            elif score >= 0.40:
                medium_confidence_matches.append((val, score))
        
        logger.info(f"[ENTITY_VERIFIER] Found {len(high_confidence_matches)} high confidence matches (60%+ or substring match)")
        logger.info(f"[ENTITY_VERIFIER] Found {len(medium_confidence_matches)} medium confidence matches (40-60%)")
        
        # Re-sort high_confidence_matches by score (highest first) after boosting
        # This ensures substring matches with boosted scores are prioritized
        high_confidence_matches = sorted(high_confidence_matches, key=lambda x: x[1], reverse=True)
        
        # ============================================================
        # PHASE 2: HIGH CONFIDENCE MATCH (60%+ Similarity OR Substring Match)
        # Auto-select the BEST match only
        # ============================================================
        if high_confidence_matches:
            best_match_lower, best_score = high_confidence_matches[0]
            
            # Find original case value
            for i, low_val in enumerate(lowercase_values):
                if low_val == best_match_lower:
                    best_match_original = original_values[i]
                    break
            else:
                best_match_original = best_match_lower
            
            logger.info(f"[ENTITY_VERIFIER] ✅ PHASE 2 - HIGH CONFIDENCE ({best_score*100:.1f}%): Auto-selecting '{best_match_original}'")
            
            # Store verified entity in business context
            _store_verified_entity(tool_context, entity_name, best_match_original)
            
            result = {
                "status": "success",
                "phase": "high_confidence",
                "confidence": best_score,
                "matched_value": best_match_original,
                "message": f"High confidence match found: {best_match_original} (similarity: {best_score*100:.1f}%)"
            }
            _cache_entity_result(cache_key, result)
            return result
        
        # ============================================================
        # PHASE 3: MEDIUM CONFIDENCE MATCH (40-60% Similarity)
        # Return multiple options for user to choose
        # ============================================================
        if medium_confidence_matches:
            # Map back to original case values
            options = []
            for match_lower, score in medium_confidence_matches[:5]:  # Limit to top 5
                for i, low_val in enumerate(lowercase_values):
                    if low_val == match_lower:
                        options.append({
                            "value": original_values[i],
                            "similarity": score,
                            "similarity_percent": f"{score*100:.1f}%"
                        })
                        break
            
            logger.info(f"[ENTITY_VERIFIER] ⚠️ PHASE 3 - MEDIUM CONFIDENCE (40-60%): Returning {len(options)} options for user selection")
            for opt in options:
                logger.info(f"  - {opt['value']} ({opt['similarity_percent']})")
            
            result = {
                "status": "needs_clarification",
                "phase": "medium_confidence",
                "message": f"Multiple possible matches found for '{entity_value}'. Please select the correct one:",
                "options": options,
                "entity_name": entity_name,
                "original_query": entity_value
            }
            _cache_entity_result(cache_key, result)
            return result
        
        # ============================================================
        # NO MATCH: Below 40% similarity
        # ============================================================
        logger.warning(f"[ENTITY_VERIFIER] ❌ NO MATCH: No matches above 40% similarity for '{entity_value}' in {entity_name}")
        result = {
            "status": "not_found",
            "phase": "no_match",
            "message": f"No matches found for '{entity_value}' in {entity_name}. Please verify the value and try again."
        }
        _cache_entity_result(cache_key, result)
        return result
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[ENTITY_VERIFIER] ERROR during entity verification: {error_msg}")
        logger.error(f"[ENTITY_VERIFIER] Exception type: {type(e).__name__}")
        # Don't cache errors - they should be retried
        return {"status": "error", "message": f"Error verifying entity: {error_msg}"}

def clear_entity_cache():
    """Clear entity verification cache"""
    global _entity_cache, _cache_expiry
    _entity_cache.clear()
    _cache_expiry.clear()
    logger.info("[ENTITY_VERIFIER] Entity cache cleared")

def get_entity_cache_info():
    """Get entity cache statistics"""
    now = datetime.now()
    valid_entries = sum(1 for key in _cache_expiry if _cache_expiry[key] > now)
    return {
        "total_cached_entities": len(_entity_cache),
        "valid_entries": valid_entries,
        "expired_entries": len(_entity_cache) - valid_entries,
        "cache_duration_seconds": ENTITY_CACHE_DURATION
    }