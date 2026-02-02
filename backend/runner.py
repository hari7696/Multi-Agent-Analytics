#!/usr/bin/env python3

import warnings
warnings.filterwarnings("ignore", message=".*config_type.*shadows.*", category=UserWarning)

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.genai import types

from config import setup_logging
from agents.agent import root_agent
from cosmosservice.cosmos_session_service import cosmos_session_service
from utils.event_processor import call_agent_async

load_dotenv()


class FinancialAgentRunner:
    
    def __init__(self, app_name: str = "FinancialAgent"):
        self.app_name = app_name
        self.session_service = cosmos_session_service
        
        self.runner = Runner(
            agent=root_agent,
            app_name=app_name,
            session_service=self.session_service,
        )
    
    async def get_or_create_session(self, user_id: str, 
                                   initial_state: Optional[Dict[str, Any]] = None) -> str:
        existing_sessions = await self.session_service.list_sessions(
            app_name=self.app_name,
            user_id=user_id,
        )
        
        if existing_sessions.sessions and len(existing_sessions.sessions) > 0:
            session_id = existing_sessions.sessions[0].id
            return session_id
        else:
            return await self.create_new_session(user_id, initial_state)
    
    async def create_new_session(self, user_id: str, 
                                initial_state: Optional[Dict[str, Any]] = None) -> str:
        default_state = {
            "user_id": user_id,
            "conversation_count": 0,
            "last_query_time": datetime.now().isoformat(),
            "preferences": {},
            "analysis_history": []
        }
        
        if initial_state:
            default_state.update(initial_state)
        
        new_session = await self.session_service.create_session(
            app_name=self.app_name,
            user_id=user_id,
            state=default_state,
        )
        
        return new_session.id
    
    async def process_query(self, user_id: str, query: str, 
                          session_id: Optional[str] = None) -> Optional[str]:
        try:
            if not session_id:
                session_id = await self.get_or_create_session(user_id)
            
            response = await call_agent_async(
                runner=self.runner,
                user_id=user_id,
                session_id=session_id,
                query=query
            )
            
            session = await self.session_service.get_session(app_name=self.app_name, user_id=user_id, session_id=session_id)
            if session:
                updated_state = session.state.copy()
                updated_state["conversation_count"] = updated_state.get("conversation_count", 0) + 1
                updated_state["last_query_time"] = datetime.now().isoformat()
                updated_state["last_query"] = query[:100]
                
                self.session_service.update_session_state(
                    self.app_name, user_id, session_id, updated_state
                )
            
            return response
            
        except Exception as e:
            return f"I apologize, but I encountered an error processing your request: {str(e)}"
    
    def get_conversation_history(self, user_id: str, session_id: str, limit: int = 10) -> list:  # user_id kept for API compatibility
        try:
            return self.session_service.cosmos_client.get_conversation_history(session_id, limit)
        except Exception:
            return []
    
    def get_user_sessions(self, user_id: str, limit: int = 20, offset: int = 0) -> list:
        try:
            return self.session_service.cosmos_client.get_user_sessions(user_id, limit, offset)
        except Exception:
            return []
    
    async def close_session(self, user_id: str, session_id: str) -> bool:
        try:
            await self.session_service.delete_session(app_name=self.app_name, user_id=user_id, session_id=session_id)
            return True
        except Exception:
            return False


async def main():
    """Main entry point"""
    import sys
    
    # Setup logging
    setup_logging()
    
    if len(sys.argv) >= 3:
        # Single query mode: python financial_agent_runner.py <user_id> <query>
        user_id = sys.argv[1]
        query = " ".join(sys.argv[2:])
        
        runner = FinancialAgentRunner()
        response = await runner.process_query(user_id, query)
        return response
    
    else:
        # Return usage information without printing
        return "Usage: python financial_agent_runner.py <user_id> <query>"


if __name__ == "__main__":
    asyncio.run(main())