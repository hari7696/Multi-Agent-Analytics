from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.lite_llm import LiteLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from typing import Optional, Dict, Any
from config import logger, MODEL
from tools.entity_verifier import verify_entity_in_dataframe
from agents.sales_agent import sales_agent
from agents.production_agent import production_agent
from agents.purchasing_agent import purchasing_agent
from agents.hr_agent import hr_agent
from agents.tech_specialist_agent import tech_coordinator_tool

logger.debug("Starting main agent initialization")

def initialize_session_variables(callback_context: CallbackContext, llm_request: LlmRequest):
    """Initialize essential session variables for agent operation"""
    callback_context.state['tech_impl_instructions'] = "tech_impl_instructions"
    callback_context.state['validation_feedback'] = "validation_feedback"
    callback_context.state['plotly_requirements'] = "plotly_requirements"
    callback_context.state['plotly_feedback'] = "plotly_feedback"
    callback_context.state['analysis_summary'] = "NONE"
logger.debug("[MAIN_AGENT] Creating root agent")

root_agent = Agent(
    name="adventure_works_master_agent",
    model=MODEL,
    instruction="""
    You are the Adventure Works Master Agent. You greet users and delegate their business intelligence questions to specialized domain agents.

    You have the following domain agents:
    1. Sales Agent: Handles all sales-related questions including orders, customers, territories, salespeople, revenue analysis
    2. Production Agent: Handles all production-related questions including products, inventory, manufacturing, work orders, costs
    3. Purchasing Agent: Handles all procurement questions including purchase orders, vendors, supplier performance
    4. HR Agent: Handles all human resources questions including employees, departments, compensation, organization

    Routing Guidelines:
    - Questions about orders, customers, territories, salespeople, revenue → Sales Agent
    - Questions about products, inventory, manufacturing, work orders, costs → Production Agent
    - Questions about purchase orders, vendors, suppliers, procurement → Purchasing Agent
    - Questions about employees, departments, compensation, organization → HR Agent
    - For general or cross-domain questions, choose the most relevant agent based on primary focus
    
    Example Routing:
    - "Show me orders from customer X" → Sales Agent
    - "What's our inventory for product Y?" → Production Agent
    - "Which vendors have the highest spend?" → Purchasing Agent
    - "List all departments" → HR Agent
    """,
    description="Master Agent. Greets users and delegates business intelligence questions to specialized domain agents (Sales, Production, Purchasing, HR)",
    sub_agents=[sales_agent, production_agent, purchasing_agent, hr_agent],
    before_model_callback=lambda callback_context, llm_request: initialize_session_variables(callback_context, llm_request),
    after_model_callback=lambda callback_context, llm_response: logger.debug(f"Model inference completed"),
)

logger.debug("[MAIN_AGENT] Root agent created successfully")
logger.debug("[MAIN_AGENT] Main agent initialization completed")

