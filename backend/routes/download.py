from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, JSONResponse
from datetime import datetime
import pandas as pd
import httpx
import csv
import io

from runner import FinancialAgentRunner
from config import logger


router = APIRouter()
runner = FinancialAgentRunner("WebFinancialAgent")


@router.get("/users/{user_id}/sessions/{session_id}/download-data")
async def download_session_data(
    user_id: str, 
    session_id: str
):
    """
    Download session analysis data as CSV
    """
    try:
        
        session = await runner.session_service.get_session(app_name="WebFinancialAgent", user_id=user_id, session_id=session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        full_data = []
        data_source = "no_data"
        
        # Try to get data from analysis_result_full
        raw_data = session.state.get("analysis_result_full", {})
        data_source = "analysis_result_full"
        
        if isinstance(raw_data, dict) and "data" in raw_data:
            full_data = raw_data["data"]
            data_metadata = {
                "row_count": raw_data.get("row_count", len(full_data)),
                "columns": raw_data.get("columns", []),
                "generated_at": raw_data.get("generated_at"),
                "agent": raw_data.get("agent"),
                "truncated": raw_data.get("truncated", False)
            }
            logger.info(f"Using new format data with metadata: {data_metadata}")
        elif isinstance(raw_data, list):
            full_data = raw_data
            logger.info("Using legacy format data")
        else:
            full_data = []
            
        # Fallback: try to find agent-specific data
        if not full_data or len(full_data) == 0:
            for key in session.state.keys():
                if key.startswith("analysis_result_full_") and session.state.get(key):
                    agent_data = session.state.get(key, {})
                    if isinstance(agent_data, dict) and "data" in agent_data:
                        full_data = agent_data["data"]
                    else:
                        full_data = agent_data
                    data_source = key
                    logger.info(f"Found agent-specific data in {key}")
                    break
        
        logger.info(f"Using {data_source} data")
        logger.info(f"Retrieved data from {data_source}, type: {type(full_data)}")
        logger.info(f"Data length: {len(full_data) if isinstance(full_data, list) else 'N/A'}")
        
        if isinstance(full_data, list) and len(full_data) > 0:
            logger.info(f"First element type: {type(full_data[0])}")
            logger.info(f"First element sample: {str(full_data[0])[:200]}...")
        elif isinstance(full_data, str):
            logger.info(f"Got string data instead of records: {full_data[:200]}...")
            raise HTTPException(status_code=404, detail="No CSV data available - only text summary found")
        
        # Check if we have data
        if not full_data:
            # Fetch session title once for error message
            cosmos_session = runner.session_service.cosmos_client.get_session(session_id, user_id)
            session_title = cosmos_session.get('title', 'Unknown') if cosmos_session else 'Unknown'
            logger.error(f"No analysis data found for session {session_id} (title: {session_title})")
            
            available_keys = list(session.state.keys()) if session.state else []
            logger.error(f"Available session state keys: {available_keys}")
            
            raise HTTPException(
                status_code=404, 
                detail=f"No analysis data found for session '{session_title}'. Please run an analysis first."
            )
        
        # Get session title for filename
        cosmos_session = runner.session_service.cosmos_client.get_session(session_id, user_id)
        session_title = cosmos_session.get('title', 'Financial_Analysis') if cosmos_session else 'Financial_Analysis'
        
        # Create safe filename
        clean_title = "".join(c for c in session_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        clean_title = clean_title.replace(' ', '_') or 'Financial_Analysis'
        
        date_str = datetime.now().strftime("%Y%m%d_%H%M")
        
        # Convert to DataFrame and CSV
        df = pd.DataFrame(full_data)
        
        logger.info(f"Generating CSV download for session {session_id}: {len(df)} records, {len(df.columns)} columns")
        
        csv_content = df.to_csv(index=False)
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={clean_title}_{date_str}.csv"}
        )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading data for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/visualization-json")
async def get_visualization_json(url: str):
    """
    Proxy endpoint to fetch plotly JSON from blob storage
    This avoids CORS issues by proxying through our backend
    """
    try:
        logger.info(f"Fetching visualization JSON from: {url[:100]}...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            # Return the JSON content
            plotly_json = response.text
            logger.info(f"Successfully fetched visualization JSON ({len(plotly_json)} bytes)")
            
            return Response(
                content=plotly_json,
                media_type="application/json",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET",
                    "Access-Control-Allow-Headers": "*"
                }
            )
            
    except httpx.HTTPError as e:
        logger.error(f"Error fetching visualization from blob storage: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to fetch visualization: {str(e)}")
    except Exception as e:
        logger.error(f"Error in visualization proxy: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/csv-data")
async def get_csv_data(url: str):
    """
    Proxy endpoint to fetch CSV data from blob storage
    This avoids CORS issues by proxying through our backend
    Returns parsed JSON array for frontend table display
    """
    try:
        logger.info(f"Fetching CSV data from: {url[:100]}...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            # Get CSV content
            csv_content = response.text
            logger.info(f"Successfully fetched CSV data ({len(csv_content)} bytes)")
            
            # Parse CSV to JSON array
            reader = csv.DictReader(io.StringIO(csv_content))
            data = list(reader)
            
            logger.info(f"Parsed CSV into {len(data)} rows")
            
            return JSONResponse(
                content={"data": data, "record_count": len(data)},
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET",
                    "Access-Control-Allow-Headers": "*"
                }
            )
            
    except httpx.HTTPError as e:
        logger.error(f"Error fetching CSV from blob storage: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to fetch CSV: {str(e)}")
    except Exception as e:
        logger.error(f"Error in CSV proxy: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
