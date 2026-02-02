from google.adk.tools.tool_context import ToolContext
from google.genai import types
from typing import Optional, Dict, Any
from config import logger, MODEL, MAX_ITERATIONS
from tools.entity_verifier import verify_entity_in_dataframe
from tools.code_executor import execute_code, signal_complete
from google.adk.agents import Agent, LoopAgent
from google.adk.tools.agent_tool import AgentTool
from tools.data_schema import ALL_SCHEMAS

unified_tech_specialist = Agent(
    name="unified_tech_specialist",
    model=MODEL,
    instruction=f"""
    You are the Unified Technical Specialist Agent. You generate Python code using SQLite views to answer business questions.

    CRITICAL REQUIREMENTS:
    1. Use pd.read_sql() to query SQLite database (conn object available)
    2. MANDATORY: Always assign final output to 'result' variable and summary statistics to 'data_summary' variable
    3. MANDATORY: The 'result' variable MUST be a pandas DataFrame - never dict, list, string, or any other type
    4. MANDATORY: The 'data_summary' variable MUST be a dictionary - never int, float, string, or any other type
    5. Only use: pandas (pd), numpy (np), datetime
    6. Handle missing values and convert dates properly using pd.to_numeric() and fillna()
    7. Use vectorized operations for performance
    8. Never use print() statements - only return data through 'result' variable
    9. Provide relevant summary statistics in the 'data_summary' variable for domain agents
    10. Reference view schemas to ensure correct column names
    11. Don't apply data filters unless the question specifically asks for it
    12. Do not generate any visualization code

    Instructions from domain specialists:
    {{tech_impl_instructions}}

    If the code has failed to execute, feedback:
    {{validation_feedback}}

    MANDATORY CODE STRUCTURE:
    ```python
    import pandas as pd
    import numpy as np
    from datetime import datetime
    
    # Query the database using SQL
    query = '''
        SELECT *
        FROM vw_sales_order_header
        WHERE customer_name = 'Alpine Ski House'
        AND order_date >= '2013-01-01'
    '''
    result = pd.read_sql(query, conn)
    
    # CRITICAL FINAL STEP - Calculate summary statistics
    data_summary = {{
        'total_orders': len(result),
        'total_revenue': result['total_due'].sum(),
        'avg_order_value': result['total_due'].mean()
    }}
    ```

    EXAMPLE QUERIES:

    **Example 1: Simple filter**
    query = "SELECT * FROM vw_sales_order_header WHERE territory_name = 'Southwest'"
    result = pd.read_sql(query, conn)

    **Example 2: Aggregation in SQL**
    query = '''
        SELECT 
            territory_name,
            COUNT(*) as order_count,
            SUM(total_due) as total_revenue
        FROM vw_sales_order_header
        GROUP BY territory_name
        ORDER BY total_revenue DESC
    '''
    result = pd.read_sql(query, conn)

    **Example 3: Join multiple views**
    query = '''
        SELECT 
            p.product_name,
            p.product_category,
            SUM(sod.order_qty) as total_qty,
            SUM(sod.line_total) as total_revenue
        FROM vw_sales_order_detail sod
        JOIN vw_products_master p ON sod.product_id = p.product_id
        WHERE p.product_category = 'Bikes'
        GROUP BY p.product_name, p.product_category
    '''
    result = pd.read_sql(query, conn)

    **Example 4: Time-based analysis**
    query = '''
        SELECT 
            order_month,
            territory_name,
            total_revenue,
            order_count
        FROM vw_sales_by_territory_month
        WHERE order_month >= '2013-01'
        ORDER BY order_month
    '''
    result = pd.read_sql(query, conn)

    AVAILABLE DATA VIEWS - Complete Schemas:
    
    {''.join([schema for schema in ALL_SCHEMAS.values()])}

    FINAL REMINDERS:
    - Generate clean, executable code only
    - Use SQL for filtering and aggregations when possible (more efficient)
    - Ensure all result columns are JSON-serializable
    - Use .dt.strftime() for dates, never .dt.to_period()
    - Always test that your final result is a pandas DataFrame before assignment
    """,
    description=" Technical Specialist code writer Agent. Takes instructions from domain agents and generates SQL-based pandas code for all domains.",
    output_key = "tech_impl_instructions",
)

# Unified code quality validator
unified_code_validator = Agent(
    name="unified_code_validator",
    model=MODEL,
    description="Unified code validator and executor for all domains",
    instruction="""
    Execute code and validate results for all domain types.
    
    MANDATORY PROCESS:
    1. Call execute_code tool with the generated code
    2. Check the execution result:
       - If status = "success": 
         * Return the analysis_summary from session state to the domain agent
         * Include the summary_statistics for the domain agent to create insights
         * The domain agent will use this summary data to write connected business insights
         * Call signal_complete tool immediately
         * STOP processing - do nothing else after signal_complete
       - If status = "error": Provide specific error feedback for the code generator
    
    CRITICAL: After calling signal_complete, you must STOP all further processing. Do not continue with any other actions.
    
    EFFICIENCY NOTE: Only execute code once per iteration. If code executes successfully and returns data, call signal_complete immediately.
    """,
    tools=[execute_code, signal_complete],
    output_key="validation_feedback"
)

# Single unified technical implementation workflow loop
unified_tech_implementation_loop = LoopAgent(
    name="technical_code_specialist",
    sub_agents=[unified_tech_specialist, unified_code_validator],
    max_iterations=MAX_ITERATIONS,
    description="Unified Technical Implementation Loop for all domains, does data analysis for all domains (invoice, revenue, contracts)."
)

# Create the shared coordinator as AgentTool for all domain agents to use
tech_coordinator_tool = AgentTool(
    agent=unified_tech_implementation_loop,
    skip_summarization=False
)
