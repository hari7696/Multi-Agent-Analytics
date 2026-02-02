"""
Event Processing Utilities for Financial Agent System
Handles ADK event processing with enhanced formatting and logging
"""

from typing import List, Any, Optional
from datetime import datetime
from config import logger
from google.genai import types


# ANSI color codes for terminal output
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Background colors
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"


async def display_session_state(session_service, app_name: str, user_id: str, 
                         session_id: str, label: str = "Current State"):
    """Display the current session state in a formatted way"""
    try:
        session = await session_service.get_session(
            app_name=app_name, user_id=user_id, session_id=session_id
        )
        
        if not session:
            print(f"\n{'-' * 10} {label} {'-' * 10}")
            print("❌ Session not found")
            print("-" * (22 + len(label)))
            return

        # Format the output with clear sections
        print(f"\n{'-' * 10} {label} {'-' * 10}")
        
        # Display session info
        print(f"🆔 Session: {session_id[:8]}...")
        print(f"👤 User: {user_id}")
        print(f"📱 App: {app_name}")
        
        # Display state information
        if session.state:
            print("📊 Session State:")
            for key, value in session.state.items():
                if isinstance(value, list):
                    print(f"  {key}: {len(value)} items")
                    for idx, item in enumerate(value[:3], 1):  # Show first 3 items
                        print(f"    {idx}. {str(item)[:50]}...")
                    if len(value) > 3:
                        print(f"    ... and {len(value) - 3} more")
                else:
                    print(f"  {key}: {str(value)[:100]}")
        else:
            print("📊 Session State: Empty")
            
        # Display timestamps
        if hasattr(session, 'created_at') and session.created_at:
            print(f"🕐 Created: {session.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        if hasattr(session, 'updated_at') and session.updated_at:
            print(f"🕑 Updated: {session.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")

        print("-" * (22 + len(label)))
        
    except Exception as e:
        print(f"❌ Error displaying state: {e}")
        logger.error(f"Error displaying session state: {e}")


async def call_agent_async(runner, user_id: str, session_id: str, query: str) -> Optional[str]:
    """
    Call the agent asynchronously with enhanced event processing and state display
    """
    try:
        # Create user message content
        content = types.Content(role="user", parts=[types.Part(text=query)])
        
        print(f"\n{Colors.BG_GREEN}{Colors.BLACK}{Colors.BOLD}🚀 Processing Query: {query}{Colors.RESET}")
        
        start_time = datetime.now()
        final_response_text = None
        agent_events = []
        
        # Display state before processing
        await display_session_state(
            runner.session_service,
            runner.app_name,
            user_id,
            session_id,
            "📊 State BEFORE Processing"
        )
        
        # Process through agent
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id, 
            new_message=content
        ):
            # Process and display each event
            response = await process_agent_event(event)
            agent_events.append(event)
            
            if response:
                final_response_text = response
        
        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Display state after processing
        await display_session_state(
            runner.session_service,
            runner.app_name,
            user_id,
            session_id,
            "📊 State AFTER Processing"
        )
        
        # Note: Conversation saving moved to web server endpoints to prevent duplicates
        # The streaming endpoint in web_server.py handles conversation persistence
        logger.debug(f"Event processing completed for session {session_id}")
        
        # Display execution summary
        print(f"\n{Colors.YELLOW}⏱️  Execution Summary:{Colors.RESET}")
        print(f"   Time: {execution_time:.2f}s")
        print(f"   Events: {len(agent_events)}")
        print(f"   Session: {session_id[:8]}...")
        
        return final_response_text
        
    except Exception as e:
        logger.error(f"Error in agent call: {e}", exc_info=True)
        print(f"❌ Error during agent execution: {e}")
        return None