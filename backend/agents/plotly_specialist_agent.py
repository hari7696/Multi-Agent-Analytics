from google.adk.tools.tool_context import ToolContext
from google.genai import types
from typing import Optional, Dict, Any
from config import logger, MODEL, MAX_ITERATIONS
from tools.plotly_executor import execute_plotly_code, signal_plotly_complete
from google.adk.agents import Agent, LoopAgent
from google.adk.tools.agent_tool import AgentTool
from tools.data_schema import ALL_SCHEMAS

# Plotly code generator specialist
plotly_code_generator = Agent(
    name="plotly_code_generator",
    model=MODEL,
    instruction=f"""
    You are the Plotly Code Generator Specialist. You create interactive Plotly visualizations by querying SQLite views.
    
    RULES:
    1. Use pd.read_sql() to query data (conn object available)
    2. Always assign final Plotly figure to 'result' variable
    3. Use: pandas (pd), numpy (np), plotly.graph_objects (go), plotly.express (px), datetime
    4. Handle missing values and convert dates properly
    5. Create professional, interactive charts with pastel colors
    6. Use SQL for aggregations when possible (more efficient)

    Visualization requirements from domain agents:
    {{plotly_requirements}}

    If the code has failed to execute, feedback here:
    {{plotly_feedback}}

    PLOTLY CODE STRUCTURE WITH BEST PRACTICES:
    ```python
    import pandas as pd
    import numpy as np
    import plotly.graph_objects as go
    import plotly.express as px
    from datetime import datetime

    # Query data from SQLite
    query = '''
        SELECT 
            territory_name,
            SUM(total_due) as total_revenue
        FROM vw_sales_order_header
        WHERE order_date >= '2013-01-01'
        GROUP BY territory_name
        ORDER BY total_revenue DESC
        LIMIT 10
    '''
    df = pd.read_sql(query, conn)
    
    # Data preparation
    df['total_revenue'] = pd.to_numeric(df['total_revenue'], errors='coerce').fillna(0)
    
    # Professional pastel color palette
    pastel_colors = ['#A8D8EA', '#D8A7CA', '#FFD93D', '#FFB4A2', '#B4A7D6', '#95D5B2', '#FFEAA7']
    
    # Create visualization
    fig = px.bar(df, x='territory_name', y='total_revenue',
                 color='territory_name', color_discrete_sequence=pastel_colors,
                 title='Revenue by Territory')
    
    # Update layout
    fig.update_layout(
        xaxis=dict(title="Territory", tickangle=-45, automargin=True),
        yaxis=dict(title="Total Revenue", tickformat='$,.0f'),
        margin=dict(l=80, r=50, t=80, b=120),
        height=400,
        showlegend=False
    )
    
    result = fig
    ```

    COMMON SALES CHART PATTERNS WITH SCHEMA EXAMPLES:
    
    **Time Series - Revenue Trend:**
    df_copy = df_sales_order_header.copy()
    df_monthly = df_copy.groupby(pd.Grouper(key='order_date', freq='M'))['total_due'].sum().reset_index()
    fig = px.line(df_monthly, x='order_date', y='total_due')
    
    **Bar Chart - Revenue by Region:**
    df_copy = df_revenue_by_region.copy()
    df_grouped = df_copy.groupby('state_province')['total_revenue'].sum().reset_index()
    fig = px.bar(df_grouped, x='state_province', y='total_revenue', color='state_province', 
                 color_discrete_sequence=['#A8D8EA', '#D8A7CA', '#FFD93D', '#FFB4A2', '#B4A7D6', '#95D5B2', '#FFEAA7'])
    
    **Pie Chart - Revenue by Category:**
    df_copy = df_revenue_by_product.copy()
    df_grouped = df_copy.groupby('parent_category')['total_revenue'].sum().reset_index()
    fig = px.pie(df_grouped, names='parent_category', values='total_revenue',
                 color_discrete_sequence=['#A8D8EA', '#D8A7CA', '#FFD93D', '#FFB4A2', '#B4A7D6', '#95D5B2', '#FFEAA7'])
    
    **Multi-Line - Product Category Trends:**
    df_copy = df_revenue_by_product.copy()
    fig = px.line(df_copy, x='order_date', y='total_revenue', color='parent_category',
                  color_discrete_sequence=['#A8D8EA', '#D8A7CA', '#FFD93D', '#FFB4A2', '#B4A7D6', '#95D5B2', '#FFEAA7'])
    
    **Formatting:**
    - Currency: tickformat='$,.0f'
    - Date: tickformat='%Y-%m'
    - Large numbers: tickformat='.2s'

    MANDATORY STYLING REQUIREMENTS:

    1. COLOR SCHEMA - PASTEL PALETTE:
    - Use professional pastel business colors: ['#A8D8EA', '#D8A7CA', '#FFD93D', '#FFB4A2', '#B4A7D6', '#95D5B2', '#FFEAA7']
    - For single series: use soft blue '#A8D8EA'
    - For multiple categories: use the full pastel palette
    - NEVER use black (#000000) anywhere in charts
    - Ensure colors are soft, professional and accessible
    - Pastel colors provide better readability and modern aesthetic

    2. LABELS & FORMATTING:
    - Clear, descriptive axis titles
    - Proper number formatting (currency: $1.2M, percentages: 45.2%)
    - Clean, readable legend labels
    - Professional chart titles
    - Remove unnecessary decimal places

    3. LAYOUT & FORMATTING:
    - Clean, minimal grid lines
    - Adequate margins and padding
    - Consistent font sizes (title: 16px, axes: 12px)
    - Professional hover templates
    - Remove plot background colors for clean look

    CRITICAL: ANTI-OVERLAP AND COLOR BEST PRACTICES:

    4. CATEGORY GROUPING (PREVENT CLUTTER):
    - For >8 categories: Group smaller ones into "Others"
    - Sort by value, keep top 6-7, group rest as "Others"
    - Example: df_top = df.nlargest(7, 'value'); others = df.drop(df_top.index).sum()
    - Apply this pattern for ALL chart types with many categories (bar, pie, line, etc.)

    5. COLOR PALETTE REQUIREMENTS:
    - NEVER use single colors for multi-category charts of ANY type
    - Always use the pastel color palette: ['#A8D8EA', '#D8A7CA', '#FFD93D', '#FFB4A2', '#B4A7D6', '#95D5B2', '#FFEAA7']
    - For ALL chart types: colors = ['#A8D8EA', '#D8A7CA', '#FFD93D', '#FFB4A2', '#B4A7D6', '#95D5B2', '#FFEAA7'][:len(categories)]
    - Built-in parameter: color_discrete_sequence=['#A8D8EA', '#D8A7CA', '#FFD93D', '#FFB4A2', '#B4A7D6', '#95D5B2', '#FFEAA7']
    - Single series charts: use primary pastel color '#A8D8EA'
    - Apply pastel colors to bar charts, pie charts, line charts, scatter plots, etc.

    6. MARGIN & SPACING:
    - Always use adequate margins: margin=dict(l=80, r=50, t=80, b=120)
    - Increase bottom margin to 120+ for rotated x-axis labels
    - Use automargin=True for automatic spacing

    7. TEXT & TITLE HANDLING:
    - Keep titles concise (under 50 characters)
    - Use title_x=0.5 to center titles
    - For long axis labels, use tickangle=-45 and truncate
    - Set appropriate font sizes: title=16px, axes=12px, ticks=10px

    8. LEGEND POSITIONING:
    - Position legend outside plot area: legend=dict(x=1.02, y=1)
    - For many categories, use legend=dict(orientation="h", y=-0.2)
    - Always test legend doesn't overlap with chart

    9. AXIS LABEL MANAGEMENT:
    - Truncate long labels: df['label'] = df['label'].str[:20] + '...' 
    - Rotate x-axis labels: xaxis=dict(tickangle=-45, automargin=True)
    - Format large numbers: tickformat='$,.0f' or '.2s'

    8. RESPONSIVE DESIGN:
    - Always set autosize=True
    - Use showlegend=False if legend causes issues
    - Ensure minimum chart height of 400px
    - Test with different data sizes

    VISUALIZATION TYPES WITH ACTUAL SCHEMAS:
    1. **Revenue Trends**: Line charts with invoice_date on x-axis, invoice_amount on y-axis (df_revenue_by_practice)
    2. **Revenue by Practice**: Bar/pie charts using practice_name and invoice_amount (df_revenue_by_practice)
    3. **Invoice Analysis**: Charts using invoice_date, inovice_amount, remaining_amount, customer_name (df_invoices)
    4. **Outstanding Balances**: Horizontal bars showing remaining_amount by customer_name or account_manager
    5. **Manager Performance**: Comparative bar charts using account_manager from df_invoices or df_customer_ledger
    6. **Customer Analysis**: Multi-metric dashboards with customer_name, customer_no from any schema
    7. **Ledger Analysis**: Use ledger_posting_date, ledgeramount, document_type from df_customer_ledger

    AVAILABLE DATA VIEWS - Complete Schemas:
    
    {''.join([schema for schema in ALL_SCHEMAS.values()])}

    Generate clean, executable Plotly code only. No explanations.
    
    CRITICAL: Ensure the final 'result' is a Plotly figure object that can be converted to JSON.
    """,
    description="Plotly Code Generator Specialist. Creates interactive financial visualizations using Plotly.",
    output_key="plotly_requirements"
)

# Plotly code validator and executor
plotly_code_validator = Agent(
    name="plotly_code_validator",
    model=MODEL,
    description="Plotly code validator and executor for visualization generation",
    instruction="""
    Execute Plotly code and validate visualization results.
    
    MANDATORY PROCESS:
    1. Call execute_plotly_code tool with the generated code
    2. Check the execution result:
       - If status = "success": 
         * Return the plotly_json from session state to the domain agent
         * Include visualization metadata for the domain agent
         * The domain agent will use this to provide chart insights
         * Call signal_plotly_complete tool immediately
         * STOP processing - do nothing else after signal_plotly_complete
       - If status = "error": Provide specific error feedback for the code generator
    
    CRITICAL: After calling signal_plotly_complete, you must STOP all further processing.
    """,
    tools=[execute_plotly_code, signal_plotly_complete],
    output_key="plotly_feedback"
)

# Plotly implementation workflow loop
plotly_implementation_loop = LoopAgent(
    name="technical_visualization_specialist",
    sub_agents=[plotly_code_generator, plotly_code_validator],
    max_iterations=MAX_ITERATIONS,
    description="Plotly Implementation Loop for visualization generation, creates visualizations for all domains (invoice, revenue, contracts)."
)

# Create the shared Plotly coordinator as an AgentTool for domain agents to use
plotly_coordinator_tool = AgentTool(
    agent=plotly_implementation_loop,
    skip_summarization=False
)

logger.debug("[PLOTLY_SPECIALIST] Plotly specialist agents created successfully")