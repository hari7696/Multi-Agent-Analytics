from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid
import json

from runner import FinancialAgentRunner
from google.genai import types
from config import logger
from utils.title_generator import get_title_generator

router = APIRouter()
runner = FinancialAgentRunner("WebFinancialAgent")

class ChatMessage(BaseModel):
    content: str
    message_type: str = "user"
    session_id: Optional[str] = None
    user_id: str = "web_user"
    files: Optional[List[str]] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    execution_time: float
    timestamp: str

class Message(BaseModel):
    id: str
    session_id: str
    user_id: str
    message_type: str
    content: str
    timestamp: str
    files: Optional[List[dict]] = None  # Changed from List[str] to List[dict] to support file metadata
    processing_steps: Optional[List[dict]] = None
    execution_time: Optional[float] = None

@router.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    try:
        start_time = datetime.now()
        
        response_text = ""
        
        final_session_id = message.session_id or await runner.get_or_create_session(message.user_id)
        
        history = runner.get_conversation_history(message.user_id, final_session_id, limit=10)
        
        conversation_messages = []
        
        for turn in history:
            if turn.get('user_message') and turn.get('user_message').strip():
                conversation_messages.append(types.Content(
                    role="user",
                    parts=[types.Part(text=turn['user_message'])]
                ))
            if turn.get('agent_response') and turn.get('agent_response').strip():
                conversation_messages.append(types.Content(
                    role="model",
                    parts=[types.Part(text=turn['agent_response'])]
                ))
        
        session = await runner.session_service.get_session(app_name="WebFinancialAgent", user_id=message.user_id, session_id=final_session_id)
        if session:
            updated_state = session.state.copy()
            updated_state["conversation_history"] = [
                {
                    "role": "user" if turn.get('user_message') else "assistant",
                    "content": turn.get('user_message') or turn.get('agent_response', ''),
                    "timestamp": turn.get('timestamp')
                }
                for turn in history
                if turn.get('user_message') or turn.get('agent_response')
            ]
            
            # Set user_id and session_id for tools
            updated_state["user_id"] = message.user_id
            updated_state["session_id"] = final_session_id
            logger.info(f"[CHAT] Setting session state - user_id: {message.user_id}, session_id: {final_session_id}")
            
            runner.session_service.update_session_state(
                "WebFinancialAgent", message.user_id, final_session_id, updated_state
            )

        current_message = types.Content(
            role="user", 
            parts=[types.Part(text=message.content)]
        )

        async for event in runner.runner.run_async(
            user_id=message.user_id,
            session_id=final_session_id,
            new_message=current_message
        ):
            if event.author != 'user':
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            response_text += part.text
                
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"Chat endpoint completed for session {final_session_id}")
        
        return ChatResponse(
            response=response_text or "I apologize, but I didn't generate a response. Please try again.",
            session_id=final_session_id,
            execution_time=execution_time,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error processing chat message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/users/{user_id}/sessions/{session_id}/messages/stream")
async def create_session_message_stream(user_id: str, session_id: str, message: ChatMessage):
    async def generate_stream():
        try:
            logger.debug(f"Starting streaming message request: user_id={user_id}, session_id={session_id}")
            start_time = datetime.now()
            
            yield f"data: {json.dumps({'type': 'thinking', 'data': 'Analyzing...', 'step': 'initialization', 'timestamp': datetime.now().isoformat()})}\n\n"
            
            history = runner.get_conversation_history(user_id, session_id, limit=10)
            
            conversation_messages = []
            
            for turn in history:
                if turn.get('user_message') and turn.get('user_message').strip():
                    conversation_messages.append(types.Content(
                        role="user",
                        parts=[types.Part(text=turn['user_message'])]
                    ))
                if turn.get('agent_response') and turn.get('agent_response').strip():
                    conversation_messages.append(types.Content(
                        role="model",
                        parts=[types.Part(text=turn['agent_response'])]
                    ))
            
            
            # Generate turn_id/message_id for this conversation turn
            turn_id = str(uuid.uuid4())
            
            # Generate title for first message (async in background - runs in parallel with response)
            try:
                session_data = runner.session_service.cosmos_client.get_session(session_id, user_id)
                current_title = session_data.get('title', 'New Chat') if session_data else 'New Chat'
                
                # If title is still "New Chat", this is the first message - generate a proper title
                if current_title == 'New Chat':
                    logger.info(f"First message detected! Starting title generation in background for session {session_id}")
                    title_generator = get_title_generator()
                    
                    def update_session_title(sess_id: str, usr_id: str, title: str):
                        """Callback to update session title"""
                        try:
                            logger.info(f"Title generation complete - updating session {sess_id} with title: '{title}'")
                            result = runner.session_service.cosmos_client.update_session(sess_id, usr_id, {
                                "title": title,
                                "updated_at": datetime.now().isoformat()
                            })
                            if result:
                                logger.info(f"✓ Session {sess_id} title successfully updated to: '{title}'")
                            else:
                                logger.warning(f"✗ Session {sess_id} title update returned empty result")
                        except Exception as e:
                            logger.error(f"✗ Failed to update session title for {sess_id}: {e}")
                    
                    # Start async title generation (runs in background while agent processes)
                    title_generator.generate_title_async(
                        user_message=message.content,
                        session_id=session_id,
                        user_id=user_id,
                        chat_history=None,
                        update_callback=update_session_title
                    )
                    logger.info(f"Title generation started in background for: '{message.content[:100]}...'")
                else:
                    logger.debug(f"Skipping title generation (title already set): current_title='{current_title}'")
            except Exception as title_error:
                logger.error(f"Error starting title generation: {title_error}", exc_info=True)
            
            session = await runner.session_service.get_session(app_name="WebFinancialAgent", user_id=user_id, session_id=session_id)
            if session:
                updated_state = session.state.copy()
                conversation_history = [
                    {
                        "role": "user" if turn.get('user_message') else "assistant",
                        "content": turn.get('user_message') or turn.get('agent_response', ''),
                        "timestamp": turn.get('timestamp')
                    }
                    for turn in history
                    if turn.get('user_message') or turn.get('agent_response')
                ]
                
                if len(conversation_history) > 10:
                    conversation_history = conversation_history[-10:]
                updated_state["conversation_history"] = conversation_history
                
                # Pass session_id, message_id, and user_id to tools through state
                updated_state["session_id"] = session_id
                updated_state["message_id"] = turn_id
                updated_state["turn_id"] = turn_id
                updated_state["user_id"] = user_id
                
                # Initialize essential agent variables if not present (cleaned up from previous turn)
                # These are used in agent prompts and as output_key - must be present for agents to work
                updated_state.setdefault("tech_impl_instructions", "tech_impl_instructions")
                updated_state.setdefault("validation_feedback", "validation_feedback")
                updated_state.setdefault("plotly_requirements", "plotly_requirements")
                updated_state.setdefault("plotly_feedback", "plotly_feedback")
                
                runner.session_service.update_session_state(
                    "WebFinancialAgent", user_id, session_id, updated_state
                )
            
            current_message = types.Content(
                role="user", 
                parts=[types.Part(text=message.content)]
            )
            
            response_text = ""
            current_agent = "finance_master_agent"
            step_counter = 0
            
            async for event in runner.runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=current_message
            ):
                step_counter += 1
                event_timestamp = datetime.now().isoformat()
                if event.author and event.author != 'user' and event.author != current_agent:
                    current_agent = event.author
                
                if event.author != 'user':
                    agent_display_names = {
                        'finance_master_agent': 'Master Agent',
                        'Invoice_agent': 'Invoice Agent',
                        'Contracts_Agent': 'Contracts Agent', 
                        'revenue_analysis_agent': 'Revenue Agent'
                    }
                    
                    agent_display = agent_display_names.get(current_agent, current_agent)
                    
                    if hasattr(event, 'content') and event.content:
                        if hasattr(event.content, 'parts'):
                            for part_idx, part in enumerate(event.content.parts):
                                
                                if hasattr(part, 'function_call') and part.function_call:
                                    tool_name = part.function_call.name if hasattr(part.function_call, 'name') else 'unknown_tool'
                                    
                                    if tool_name == 'transfer_to_agent':
                                        if hasattr(part.function_call, 'args') and 'agent_name' in part.function_call.args:
                                            target_agent = part.function_call.args['agent_name']
                                            target_display = agent_display_names.get(target_agent, target_agent)
                                            transfer_message = f"{agent_display}: Transferring to {target_display}"
                                            yield f"data: {json.dumps({'type': 'agent_switch', 'data': transfer_message, 'from_agent': current_agent, 'to_agent': target_agent, 'step': f'transfer_{step_counter}', 'timestamp': event_timestamp})}\n\n"
                                        else:
                                            transfer_message = f"{agent_display}: Transferring to specialist"
                                            yield f"data: {json.dumps({'type': 'agent_switch', 'data': transfer_message, 'step': f'transfer_{step_counter}', 'timestamp': event_timestamp})}\n\n"
                                    else:
                                        tool_descriptions = {
                                            'verify_entity_in_dataframe': f'{agent_display}: Verifying customer/manager names',
                                            'tech_implementation_coordinator': f'{agent_display}: Running data analysis',
                                            'check_contract_status': f'{agent_display}: Checking contract status',
                                            'shared_plotly_coordinator_tool': f'{agent_display}: Creating visualization'
                                        }
                                        tool_message = tool_descriptions.get(tool_name, f'{agent_display}: Calling {tool_name.replace("_", " ").title()}')
                                        yield f"data: {json.dumps({'type': 'tool_call', 'data': tool_message, 'tool': tool_name, 'step': f'tool_call_{step_counter}', 'agent': current_agent, 'timestamp': event_timestamp})}\n\n"
                                
                                elif hasattr(part, 'function_response') and part.function_response:
                                    tool_name = getattr(part.function_response, 'name', 'unknown_tool')
                                    response_message = f"{agent_display}: {tool_name.replace('_', ' ').title()} completed"
                                    yield f"data: {json.dumps({'type': 'tool_response', 'data': response_message, 'tool': tool_name, 'step': f'tool_response_{step_counter}', 'agent': current_agent, 'timestamp': event_timestamp})}\n\n"
                                
                                elif hasattr(part, 'text') and part.text:
                                    if event.is_final_response():
                                        chunk_text = part.text
                                        response_text += chunk_text
                                        
                                        # Clean the streamed text to remove blob URL references
                                        import re
                                        cleaned_chunk = chunk_text
                                        # Remove markdown links with blob URLs
                                        cleaned_chunk = re.sub(r'\[([^\]]+)\]\(https://[^\)]*blob\.core\.windows\.net[^\)]*\)', r'', cleaned_chunk)
                                        # Remove standalone blob URLs
                                        cleaned_chunk = re.sub(r'https://[^\s]*blob\.core\.windows\.net[^\s]*', '', cleaned_chunk)
                                        # Remove "View the detailed chart here:" patterns
                                        cleaned_chunk = re.sub(r'View the detailed chart here:\s*', '', cleaned_chunk, flags=re.IGNORECASE)
                                        cleaned_chunk = re.sub(r'View.*chart.*here:\s*', '', cleaned_chunk, flags=re.IGNORECASE)
                                        
                                        yield f"data: {json.dumps({'type': 'content', 'data': cleaned_chunk, 'agent': current_agent, 'timestamp': event_timestamp})}\n\n"
                                    else:
                                        clean_text = part.text.strip()
                                        if clean_text and len(clean_text) > 5:
                                            thinking_message = f"{agent_display}: {clean_text}"
                                            yield f"data: {json.dumps({'type': 'thinking', 'data': thinking_message, 'step': f'thinking_{step_counter}', 'agent': current_agent, 'timestamp': event_timestamp})}\n\n"
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            try:
                # Get file URLs from session state if they were generated during tool execution
                session = await runner.session_service.get_session(app_name="WebFinancialAgent", user_id=user_id, session_id=session_id)
                
                # Retrieve turn-specific URLs
                csv_file_url = session.state.get(f"csv_file_url_{turn_id}") if session else None
                csv_file_metadata = session.state.get(f"csv_file_metadata_{turn_id}") if session else None
                visualization_url = session.state.get(f"visualization_url_{turn_id}") if session else None
                visualization_metadata_stored = session.state.get("visualization_metadata") if session else None
                
                # ========================================
                # STREAM VISUALIZATION FIRST (before cleanup removes plotly_json)
                # ========================================
                if session:
                    plotly_json = session.state.get("plotly_json")
                    plotly_metadata = session.state.get("visualization_metadata", {})
                    plotly_fresh = session.state.get("plotly_fresh", False)
                    
                    if plotly_json and plotly_fresh:
                        # Include visualization_url in the plotly event so frontend can store it immediately
                        plotly_data = {
                            'type': 'plotly_visualization', 
                            'plotly_json': plotly_json,
                            'metadata': plotly_metadata,
                            'title': plotly_metadata.get('title', 'Financial Visualization'),
                            'insights': response_text,
                            'visualization_url': visualization_url,  # Use variable captured earlier
                            'timestamp': datetime.now().isoformat()
                        }
                        yield f"data: {json.dumps(plotly_data)}\n\n"
                        logger.info(f"✅ Sent Plotly visualization data from {current_agent} for session {session_id} (URL: {visualization_url is not None})")
                
                # ========================================
                # FINAL CLEANUP: Remove large data from session state before saving to Cosmos DB
                # ========================================
                if session:
                    large_fields_to_remove = [
                        "plotly_json", "plotly_dict", "plotly_feedback", "plotly_requirements",
                        "tech_impl_instructions", "validation_feedback", "visualization_metadata",
                        "plotly_fresh", "analysis_result_full"
                    ]
                    for field in large_fields_to_remove:
                        session.state.pop(field, None)
                    
                    # Remove turn-specific file URLs after they've been saved to turn data
                    # This prevents state bloat from accumulating URLs for every message
                    session.state.pop(f"csv_file_url_{turn_id}", None)
                    session.state.pop(f"csv_file_metadata_{turn_id}", None)
                    session.state.pop(f"visualization_url_{turn_id}", None)
                    
                    # Remove any analysis_result_full_ prefixed keys
                    keys_to_remove = [key for key in session.state.keys() if key.startswith("analysis_result_full_")]
                    for key in keys_to_remove:
                        session.state.pop(key, None)
                    
                    # Update session with cleaned state
                    runner.session_service.update_session_state(
                        "WebFinancialAgent", user_id, session_id, session.state
                    )
                    logger.info("Cleaned up large fields from session state before saving to Cosmos DB")
                
                # Clean up agent response: Remove any blob storage URL references
                # The visualization will be shown via PlotlyVisualization component
                cleaned_response_text = response_text
                if visualization_url:
                    import re
                    # Remove markdown links containing blob URLs: [text](url)
                    cleaned_response_text = re.sub(r'\[([^\]]+)\]\(https://[^\)]*blob\.core\.windows\.net[^\)]*\)', r'', cleaned_response_text)
                    # Remove standalone blob URLs
                    cleaned_response_text = re.sub(r'https://[^\s]*blob\.core\.windows\.net[^\s]*', '', cleaned_response_text)
                    # Remove "View the detailed chart here:" text patterns
                    cleaned_response_text = re.sub(r'View the detailed chart here:\s*', '', cleaned_response_text, flags=re.IGNORECASE)
                    cleaned_response_text = re.sub(r'View.*chart.*here:\s*', '', cleaned_response_text, flags=re.IGNORECASE)
                    # Clean up extra whitespace
                    cleaned_response_text = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_response_text)
                    cleaned_response_text = cleaned_response_text.strip()
                
                # Prepare lightweight turn data for conversation container
                # ONLY include small, essential data (NEVER plotly_json, plotly_dict, plotly_feedback, etc.)
                turn_data = {
                    "turn_id": turn_id,
                    "user_message": message.content,
                    "agent_response": cleaned_response_text,
                    "agent_used": current_agent or "finance_master_agent",
                    "timestamp": start_time.isoformat(),
                    "csv_file_url": csv_file_url,
                    # Only store essential CSV metadata, not columns or full data
                    "csv_file_metadata": {
                        "filename": csv_file_metadata.get("filename"),
                        "format": csv_file_metadata.get("format"),
                        "record_count": csv_file_metadata.get("record_count"),
                        "file_size_bytes": csv_file_metadata.get("file_size_bytes")
                    } if csv_file_metadata and isinstance(csv_file_metadata, dict) else None,
                    "visualization_url": visualization_url,
                    # Only store lightweight visualization metadata, not full plotly data
                    "visualization_metadata": {
                        "chart_type": visualization_metadata_stored.get("chart_type"),
                        "data_points": visualization_metadata_stored.get("data_points"),
                        "has_title": visualization_metadata_stored.get("has_title"),
                        "traces_count": visualization_metadata_stored.get("traces_count")
                    } if visualization_metadata_stored else None
                }
                
                # Explicitly verify NO large data leaked into turn_data
                for key in ["plotly_json", "plotly_dict", "plotly_feedback", "plotly_requirements", 
                           "tech_impl_instructions", "validation_feedback", "analysis_result_full"]:
                    if key in turn_data:
                        logger.warning(f"Removing large field '{key}' from turn_data before saving to conversation")
                        turn_data.pop(key)
                
                runner.session_service.save_conversation_turn(session_id, turn_data, execution_time)
                logger.info(f"Conversation turn saved for session {session_id} with turn_id {turn_id} (CSV: {bool(csv_file_url)}, Viz: {bool(visualization_url)})")
            except Exception as save_error:
                logger.error(f"Failed to save conversation turn for session {session_id}: {save_error}")
            
            # Check for fallback analysis data (for agents that didn't use blob storage)
            try:
                session = await runner.session_service.get_session(app_name="WebFinancialAgent", user_id=user_id, session_id=session_id)
                if session:
                    if current_agent in ['Invoice_agent', 'revenue_analysis_agent', 'Contracts_Agent']:
                        if session.state.get("analysis_result_full"):
                            logger.info(f"Download data available for {current_agent}")
                        else:
                            logger.warning(f"No download data found for {current_agent}")
            except Exception as plotly_error:
                logger.error(f"Error checking for Plotly data: {plotly_error}")
            
            # Use the CSV and visualization URLs we already captured earlier (lines 312-314)
            # Don't reset or re-fetch - the turn-specific keys are already deleted by cleanup
            message_id = str(uuid.uuid4())
            has_download_data = bool(csv_file_url)
            
            if csv_file_url:
                logger.info(f"Completion signal: CSV file available in blob storage: {csv_file_url}")
                
            completion_data = {
                'type': 'complete', 
                'data': message_id, 
                'hasDownloadData': has_download_data,
                'csv_file_url': csv_file_url,
                # Don't send visualization_url in completion - chart is already displayed inline via plotly_json
                'timestamp': datetime.now().isoformat()
            }
            yield f"data: {json.dumps(completion_data)}\n\n"
            
        except Exception as e:
            logger.error(f"Error in streaming message: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type"
        }
    )

@router.options("/users/{user_id}/sessions/{session_id}/messages")
async def options_session_messages(user_id: str, session_id: str):
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        }
    )

@router.get("/users/{user_id}/sessions/{session_id}/messages", response_model=List[Message])
async def get_session_messages(user_id: str, session_id: str, limit: int = 50, offset: int = 0):
    try:
        logger.info(f"Retrieving messages for session {session_id}, user {user_id}")
        
        history = runner.get_conversation_history(user_id, session_id, limit * 2)  # Get more to account for filtering
        logger.info(f"Retrieved {len(history)} conversation items for session {session_id}")
        
        messages = []
        for msg_data in history:
            try:
                # Only process conversation turns (skip ADK events)
                # Conversation turns have 'user_message' or 'agent_response' fields
                if not (msg_data.get('user_message') or msg_data.get('agent_response')):
                    # This is an ADK event, skip it
                    continue
                
                # This is a conversation turn
                turn_id = msg_data.get('turn_id', str(uuid.uuid4()))
                timestamp = msg_data.get('timestamp', datetime.now().isoformat())
                
                # Create user message if present
                if msg_data.get('user_message') and msg_data['user_message'].strip():
                    user_msg = Message(
                        id=f"{turn_id}_user",
                        session_id=session_id,
                        user_id=user_id,
                        message_type='user',
                        content=msg_data['user_message'],
                        timestamp=timestamp,
                        files=[],
                        processing_steps=[],
                        execution_time=None
                    )
                    messages.append(user_msg)
                
                # Create assistant message if present
                if msg_data.get('agent_response') and msg_data['agent_response'].strip():
                    # Build files array with download URLs
                    files = []
                    if msg_data.get('csv_file_url'):
                        files.append({
                            'url': msg_data['csv_file_url'],
                            'type': 'csv',
                            'metadata': msg_data.get('csv_file_metadata', {})
                        })
                    if msg_data.get('visualization_url'):
                        files.append({
                            'url': msg_data['visualization_url'],
                            'type': 'visualization',
                            'metadata': msg_data.get('visualization_metadata', {})
                        })
                    
                    assistant_msg = Message(
                        id=f"{turn_id}_assistant",
                        session_id=session_id,
                        user_id=user_id,
                        message_type='assistant',
                        content=msg_data['agent_response'],
                        timestamp=timestamp,
                        files=files,
                        processing_steps=[],
                        execution_time=msg_data.get('execution_time')
                    )
                    messages.append(assistant_msg)
                
            except Exception as parse_error:
                logger.warning(f"Failed to parse message data: {parse_error}")
                continue
        
        # Apply offset and limit after parsing
        messages = messages[offset:offset + limit]
        messages.sort(key=lambda x: x.timestamp)
        
        logger.info(f"Returning {len(messages)} messages for session {session_id}")
        return messages
        
    except Exception as e:
        logger.error(f"Error getting messages for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/users/{user_id}/sessions/{session_id}/messages", response_model=Message)
async def create_session_message(user_id: str, session_id: str, message: ChatMessage):
    try:
        logger.info(f"Received message request: user_id={user_id}, session_id={session_id}, message={message.content}")
        start_time = datetime.now()
        
        response_text = ""
        
        logger.info(f"Starting financial agent processing for session {session_id}")
        
        history = runner.get_conversation_history(user_id, session_id, limit=10)
        
        conversation_messages = []
        
        for turn in history:
            if turn.get('user_message') and turn.get('user_message').strip():
                conversation_messages.append(types.Content(
                    role="user",
                    parts=[types.Part(text=turn['user_message'])]
                ))
            if turn.get('agent_response') and turn.get('agent_response').strip():
                conversation_messages.append(types.Content(
                    role="model",
                    parts=[types.Part(text=turn['agent_response'])]
                ))
        
        session = await runner.session_service.get_session(app_name="WebFinancialAgent", user_id=user_id, session_id=session_id)
        if session:
            updated_state = session.state.copy()
            updated_state["conversation_history"] = [
                {
                    "role": "user" if turn.get('user_message') else "assistant",
                    "content": turn.get('user_message') or turn.get('agent_response', ''),
                    "timestamp": turn.get('timestamp')
                }
                for turn in history
                if turn.get('user_message') or turn.get('agent_response')
            ]
            
            runner.session_service.update_session_state(
                "WebFinancialAgent", user_id, session_id, updated_state
            )

        current_message = types.Content(
            role="user", 
            parts=[types.Part(text=message.content)]
        )
        
        async for event in runner.runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=current_message
        ):
            logger.debug(f"Received event: author={event.author}, content={event.content}")
            if event.author != 'user':
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            response_text += part.text
        
        logger.info(f"Financial agent processing completed. Response: {response_text[:100]}...")
        execution_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"Non-streaming message endpoint completed for session {session_id}")
        
        now = datetime.now().isoformat()
        
        new_message = Message(
            id=str(uuid.uuid4()),
            session_id=session_id,
            user_id=user_id,
            content=response_text or "I apologize, but I didn't generate a response. Please try again.",
            message_type='assistant',
            timestamp=now,
            files=[],
            processing_steps=[],
            execution_time=execution_time
        )
        
        logger.info(f"Returning message response: {new_message.id}")
        return new_message
        
    except Exception as e:
        logger.error(f"Error creating message in session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))