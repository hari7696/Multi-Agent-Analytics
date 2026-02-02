import sys
from io import StringIO
import pandas as pd
import numpy as np
from datetime import datetime
from google.adk.tools.tool_context import ToolContext
from tools.gaurdrails import validate_code
from tools.data_loader import load_data
from tools.storage_manager import upload_analysis_dataset, is_storage_available

import logging
import traceback


logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

def convert_to_json_serializable(obj):
    """Convert numpy types and other non-serializable types to JSON-compatible Python types"""
    if isinstance(obj, dict):
        return {key: convert_to_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_json_serializable(item) for item in obj]
    elif isinstance(obj, np.integer):  # Handles all numpy integer types (int8, int16, int32, int64)
        return int(obj)
    elif isinstance(obj, np.floating):  # Handles all numpy float types (float16, float32, float64)
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif pd.isna(obj):
        return None
    else:
        return obj

def execute_code(code: str, tool_context: ToolContext) -> dict:
    
    agent_name = getattr(tool_context, 'agent_name', 'unknown')
    
    # Read session_id, user_id, and message_id from session state or tool_context attributes
    # Priority: state > tool_context attributes > session object
    session_id = (
        tool_context.state.get('session_id') or 
        getattr(tool_context, 'session_id', None) or
        getattr(getattr(tool_context, 'session', None), 'id', None) or
        'default_session'
    )
    user_id = (
        tool_context.state.get('user_id') or 
        getattr(tool_context, 'user_id', None) or
        getattr(getattr(tool_context, 'session', None), 'user_id', None) or
        'default_user'
    )
    message_id = tool_context.state.get('message_id', None)
    turn_id = tool_context.state.get('turn_id', message_id)
    
    # Log warning if using defaults
    if session_id == 'default_session' or user_id == 'default_user':
        logger.warning(f"[CODE_EXECUTOR] Using default values - session_id: {session_id}, user_id: {user_id}")
        logger.warning(f"[CODE_EXECUTOR] tool_context.state keys: {list(tool_context.state.keys())}")
        logger.warning(f"[CODE_EXECUTOR] tool_context attributes: {[attr for attr in dir(tool_context) if not attr.startswith('_')]}")
    
    validation = validate_code(code)
    if not validation["valid"]:
        return {
            "status": "error",
            "message": "Code validation failed",
            "details": validation.get("issues", validation.get("error"))
        }
    from data_stage.db_connection import get_connection
    conn = get_connection()
    
    old_stdout = sys.stdout
    sys.stdout = output_capture = StringIO()
    # uncomment this to save the code to a file
    # with open('code.py', 'a') as f:
    #     f.write(code)
    #     f.write('\n\n\n')


    try:
        exec_globals = {
            'conn': conn,
            'pd': pd,
            'np': np,
            'datetime': datetime
        }
        
        exec(code, exec_globals)
        
        if 'result' not in exec_globals:
            return {
                "status": "error",
                "message": "Code did not produce 'result' variable"
            }
        
        result = exec_globals['result']
        data_summary = exec_globals['data_summary']
        
        # Convert numpy types to JSON-serializable Python types
        data_summary = convert_to_json_serializable(data_summary)
        
        # uncomment this to save the result and data summary to a files
        # with open('sampleoutput.txt', 'a') as f:
        #     result.to_csv(f, index=False)
        #     f.write(f"Data summary: {data_summary}\n")

        if hasattr(data_summary, 'data_summary'):
            return {
                "status": "error",
                "message": "Code did not produce 'data_summary' variable"
            }
        
        if hasattr(result, 'result'):
            return {
                "status": "error",
                "message": "Code did not produce 'result' variable"
            }
        
        if not isinstance(result, pd.DataFrame):
            result_type = type(result).__name__
            example_fix = ""
            if result_type == "dict":
                example_fix = "Return data frame instead of dictionary"
            elif result_type == "list":
                example_fix = "Return data frame instead of list"
            elif result_type in ["int", "float", "str"]:
                example_fix = "Return data frame instead of int, float, or string"
            return {
                "status": "error", 
                "message": f"Code generated {result_type} instead of DataFrame!",
                "details": f"The technical specialist must assign a pandas DataFrame to the 'result' variable. Current result is {result_type}. You must return the complete filtered dataset as a DataFrame, not a {result_type}"
            }

        data_summary_type = type(data_summary).__name__
        if not isinstance(data_summary, dict):
            example_fix = "Return dictionary instead of int, float, or string"
        elif data_summary_type == "list":
            example_fix = "Return dictionary instead of list"
        elif data_summary_type in ["int", "float", "str"]:
            example_fix = "Return dictionary instead of int, float, or string"
            return {
                "status": "error",
                "message": f"Code generated {data_summary_type} instead of dictionary!",
                "details": f"The technical specialist must assign a dictionary to the 'data_summary' variable. Current data_summary is {data_summary_type}. You must return the summary statistics as a dictionary, not a {data_summary_type}"
            }
        
        if isinstance(result, pd.DataFrame):
            for col in result.select_dtypes(include=['datetime64']).columns:
                result[col] = result[col].dt.strftime('%Y-%m-%d')
            
            for col in result.columns:
                if hasattr(result[col], 'dtype') and 'period' in str(result[col].dtype).lower():
                    result[col] = result[col].astype(str)
            
            for col in result.columns:
                if result[col].dtype == 'object':
                        result[col] = result[col].astype(str)
            
            if len(result) > 5:
                try:
                    # Don't store full data in state - it will be uploaded to blob storage
                    # Only store lightweight metadata after upload
                    
                    # Upload to blob storage with new structure
                    if is_storage_available() and message_id:
                        try:
                            from tools.storage_manager import get_storage_manager
                            storage = get_storage_manager()
                            
                            download_url, storage_metadata = storage.upload_dataset(
                                result, session_id, "", 'csv', 
                                user_id=user_id, message_id=message_id
                            )
                            # Store file URLs with turn_id to prevent overwriting across messages
                            tool_context.state[f"csv_file_url_{turn_id}"] = download_url
                            tool_context.state[f"csv_file_metadata_{turn_id}"] = storage_metadata
                            
                            # Remove analysis_result_full - no longer needed
                            if "analysis_result_full" in tool_context.state:
                                del tool_context.state["analysis_result_full"]
                            
                            logger.info(f"Stored CSV URL in session state for turn {turn_id} (minimal storage mode)")
                        except Exception as upload_error:
                            logger.warning(f"Failed to upload CSV to storage: {upload_error}")
                    
                except Exception:
                    try:
                        # Upload to blob storage with new structure
                        if is_storage_available() and message_id:
                            try:
                                from tools.storage_manager import get_storage_manager
                                storage = get_storage_manager()
                                
                                download_url, storage_metadata = storage.upload_dataset(
                                    result, session_id, agent_name, 'csv',
                                    user_id=user_id, message_id=message_id
                                )
                                
                                # Store file URLs with turn_id to prevent overwriting across messages
                                tool_context.state[f"csv_file_url_{turn_id}"] = download_url
                                tool_context.state[f"csv_file_metadata_{turn_id}"] = storage_metadata
                                
                                # Remove analysis_result_full - no longer needed
                                if "analysis_result_full" in tool_context.state:
                                    del tool_context.state["analysis_result_full"]
                                
                                logger.info(f"Stored CSV URL in session state for turn {turn_id} (minimal storage mode)")
                            except Exception as upload_error:
                                logger.warning(f"Failed to upload CSV to storage: {upload_error}")
                    except Exception:
                        # Fallback failed, continue without storage
                        logger.debug("Fallback storage attempt failed")
            else:
                if "analysis_result_full" in tool_context.state:
                    del tool_context.state["analysis_result_full"]
            
            summary_stats = {
                **data_summary,
                "agent": agent_name,
                "timestamp": datetime.now().isoformat()
            }
            
            # Convert again to ensure any additional numpy types are converted
            summary_stats = convert_to_json_serializable(summary_stats)
            
            # for col in result.columns:
            #     if col in ['customer_no', 'po_number']:
            #         continue
            #     if result[col].dtype in ['int64', 'float64', 'int32', 'float32'] and not result[col].isna().all():
            #         summary_stats[f"{col}_total"] = float(result[col].sum())
            #         summary_stats[f"{col}_average"] = float(result[col].mean())
            #         summary_stats[f"{col}_max"] = float(result[col].max())
            #         summary_stats[f"{col}_min"] = float(result[col].min())
            #     elif result[col].dtype == 'object':
            #         unique_counts = result[col].value_counts().head(5).to_dict()
            #         summary_stats[f"{col}_top_values"] = unique_counts
            #         summary_stats[f"{col}_unique_count"] = result[col].nunique()
            
            
            tool_context.state["analysis_summary"] = summary_stats
            
            return {
                "status": "success", 
                "summary_statistics": summary_stats,
                "full_data_available": True,
                "output": output_capture.getvalue()
            }
            
    except Exception as e:
        error_traceback = traceback.format_exc()
        with open('code.py', 'a') as f:
            f.write(f"Error: {str(e)}\n")
            f.write(f"Traceback: {error_traceback}\n")
        return {
            "status": "error",
            "message": str(e),
            "traceback": error_traceback,
            "output": output_capture.getvalue()
        }

    finally:
        sys.stdout = old_stdout

def signal_complete(completion_status: str, tool_context: ToolContext) -> dict:
    print(f"[Tool Call] signal_complete triggered by {tool_context.agent_name}")
    tool_context.actions.escalate = True
    
    return {
        "status": "loop_terminated", 
        "message": f"Code generation completed successfully with status: {completion_status}. Loop terminated.",
        "agent": tool_context.agent_name
    }