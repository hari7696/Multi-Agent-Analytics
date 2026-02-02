import sys
from io import StringIO
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from google.adk.tools.tool_context import ToolContext
from tools.gaurdrails import validate_code
import json
import logging

logger = logging.getLogger(__name__)



def execute_plotly_code(code: str, tool_context: ToolContext) -> dict:
    """Execute Plotly Python code safely with the unified dataset."""
    
    agent_name = getattr(tool_context, 'agent_name', 'plotly_specialist')
    
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
        logger.warning(f"[PLOTLY_EXECUTOR] Using default values - session_id: {session_id}, user_id: {user_id}")
        logger.warning(f"[PLOTLY_EXECUTOR] tool_context.state keys: {list(tool_context.state.keys())}")
        logger.warning(f"[PLOTLY_EXECUTOR] tool_context attributes: {[attr for attr in dir(tool_context) if not attr.startswith('_')]}")
    
    # Validate code first
    validation = validate_code(code)
    if not validation["valid"]:
        return {
            "status": "error",
            "message": "Code validation failed",
            "details": validation.get("issues", validation.get("error"))
        }
    
    # Get SQLite connection
    from data_stage.db_connection import get_connection
    conn = get_connection()
    
    # Capture output
    old_stdout = sys.stdout
    sys.stdout = output_capture = StringIO()
    
    try:
        # Create safe execution environment with Plotly
        exec_globals = {
            'conn': conn,
            'pd': pd,
            'np': np,
            'datetime': datetime,
            'go': go,
            'px': px
        }
        
        # Execute code
        exec(code, exec_globals)
        
        # Check for result
        if 'result' not in exec_globals:
            return {
                "status": "error",
                "message": "Code did not produce 'result' variable with Plotly figure"
            }
        
        result = exec_globals['result']
        
        # Verify result is a Plotly figure
        if not hasattr(result, 'to_json'):
            return {
                "status": "error",
                "message": "Result is not a valid Plotly figure object"
            }
        
        # Convert Plotly figure to JSON
        try:
            plotly_json = result.to_json()
            plotly_dict = json.loads(plotly_json)
            
            # Store ONLY plotly_json temporarily for streaming (NOT plotly_dict - too large)
            # This will be cleaned up after streaming and NOT saved to Cosmos DB
            tool_context.state["plotly_json"] = plotly_json
            tool_context.state["plotly_fresh"] = True  # Flag to indicate this was just generated
            
            # Generate visualization metadata for insights
            viz_metadata = {
                "chart_type": _detect_chart_type(plotly_dict),
                "data_points": _count_data_points(plotly_dict),
                "has_title": bool(plotly_dict.get('layout', {}).get('title')),
                "x_axis": plotly_dict.get('layout', {}).get('xaxis', {}).get('title', {}).get('text', 'Unknown'),
                "y_axis": plotly_dict.get('layout', {}).get('yaxis', {}).get('title', {}).get('text', 'Unknown'),
                "traces_count": len(plotly_dict.get('data', []))
            }
            
            
            tool_context.state["visualization_metadata"] = viz_metadata
            
            # Upload visualization to blob storage and save URL to Cosmos DB
            if message_id:
                try:
                    from tools.storage_manager import get_storage_manager
                    storage = get_storage_manager()
                    
                    # Log chart details before upload for debugging
                    chart_info = {
                        "chart_type": _detect_chart_type(plotly_dict),
                        "data_traces": len(plotly_dict.get('data', [])),
                        "has_layout": bool(plotly_dict.get('layout')),
                        "title": plotly_dict.get('layout', {}).get('title', {}).get('text', 'No title')
                    }
                    logger.info(f"Uploading visualization for turn {turn_id}: {chart_info}")
                    
                    # Use StorageManager wrapper (not storage_backend directly)
                    visualization_url, storage_metadata = storage.upload_visualization(
                        plotly_json=plotly_json,
                        session_id=session_id,
                        agent_name=agent_name,
                        user_id=user_id,
                        message_id=message_id
                    )
                    
                    viz_metadata["visualization_url"] = visualization_url
                    viz_metadata["storage_metadata"] = storage_metadata
                    
                    # Store visualization URL with turn_id to prevent overwriting across messages
                    tool_context.state[f"visualization_url_{turn_id}"] = visualization_url
                    logger.info(f"✅ Stored visualization URL in session state for turn {turn_id}: {visualization_url[:100]}...")
                        
                except Exception as upload_error:
                    logger.warning(f"Failed to upload visualization to storage: {upload_error}")
                    import traceback
                    logger.warning(f"Upload error traceback: {traceback.format_exc()}")
            
            return {
                "status": "success", 
                "plotly_json": plotly_json,
                "visualization_metadata": viz_metadata,
                "output": output_capture.getvalue()
            }
            
        except Exception as json_error:
            return {
                "status": "error",
                "message": f"Failed to serialize Plotly figure to JSON: {str(json_error)}",
                "output": output_capture.getvalue()
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "output": output_capture.getvalue()
        }
    finally:
        sys.stdout = old_stdout

def _detect_chart_type(plotly_dict: dict) -> str:
    """Detect the primary chart type from Plotly JSON."""
    try:
        data = plotly_dict.get('data', [])
        if not data:
            return "unknown"
        
        trace_types = [trace.get('type', 'scatter') for trace in data]
        
        # Determine primary chart type
        if 'bar' in trace_types:
            return "bar_chart"
        elif 'pie' in trace_types:
            return "pie_chart"
        elif 'scatter' in trace_types:
            modes = [trace.get('mode', '') for trace in data if trace.get('type') == 'scatter']
            if any('lines' in mode for mode in modes):
                return "line_chart"
            else:
                return "scatter_plot"
        elif 'histogram' in trace_types:
            return "histogram"
        elif 'box' in trace_types:
            return "box_plot"
        else:
            return trace_types[0] if trace_types else "unknown"
    except:
        return "unknown"

def _count_data_points(plotly_dict: dict) -> int:
    """Count total data points across all traces."""
    try:
        total_points = 0
        data = plotly_dict.get('data', [])
        for trace in data:
            if 'x' in trace and isinstance(trace['x'], list):
                total_points += len(trace['x'])
            elif 'y' in trace and isinstance(trace['y'], list):
                total_points += len(trace['y'])
        return total_points
    except:
        return 0

def signal_plotly_complete(completion_status: str, tool_context: ToolContext) -> dict:
    """
    Signal that Plotly visualization generation is complete and successful. 
    This tool MUST be called to terminate the Plotly loop.
    
    CRITICAL: This function must be called by the agent to exit the loop.
    """
    print(f"[Tool Call] signal_plotly_complete triggered by {tool_context.agent_name}")
    tool_context.actions.escalate = True
    
    return {
        "status": "plotly_loop_terminated",
        "message": f"Plotly visualization generation completed successfully with status: {completion_status}. Loop terminated.",
        "agent": tool_context.agent_name
    }
