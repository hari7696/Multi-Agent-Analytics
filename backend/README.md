# 🎯 Adventure Works Analytics System - Backend

**An AI-powered business intelligence platform built on hierarchical multi-agent architecture**

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Google ADK](https://img.shields.io/badge/Google-ADK-4285F4.svg)](https://cloud.google.com/vertex-ai)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57.svg)](https://www.sqlite.org/)

---

## 🌟 Overview

The Adventure Works Analytics System is a **sophisticated multi-agent AI platform** that transforms natural language questions into actionable business insights. Built on Microsoft's Adventure Works OLTP dataset (759,195 rows across 66 tables), it showcases enterprise-grade agent orchestration, intelligent routing, and domain-specific expertise.

### 🎭 What Makes This Special?

This isn't just another chatbot—it's a **hierarchical agent ecosystem** where:

- 🧠 **Master Agent** intelligently routes queries to specialized domain experts
- 🎯 **4 Domain Agents** (Sales, Production, Purchasing, HR) provide deep domain expertise
- 🛠️ **2 Specialist Agents** (Tech, Plotly) handle code generation and visualizations
- ✅ **Entity Verification** validates 20,835+ cached entities (customers, products, vendors, employees)
- 📊 **25 Analytical Views** power efficient querying across 759K+ database rows
- 🔄 **Smart Context** maintains conversation state and agent coordination

---

## 🏗️ Agent Architecture

### The Agent Hierarchy

```
                           User Query
                                ↓
                    ┌───────────────────────┐
                    │   MASTER AGENT        │
                    │  (Router/Orchestrator)│
                    └───────────┬───────────┘
                                ↓
              ┌─────────────────┴─────────────────┐
              ↓                 ↓                  ↓
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │ SALES AGENT  │  │PRODUCTION AGT│  │PURCHASING AGT│  │   HR AGENT   │
    │              │  │              │  │              │  │              │
    │ • Orders     │  │ • Inventory  │  │ • Vendors    │  │ • Employees  │
    │ • Customers  │  │ • Products   │  │ • POs        │  │ • Departments│
    │ • Territories│  │ • Work Orders│  │ • Procurement│  │ • Compensation│
    │ • Revenue    │  │ • BOM        │  │ • Suppliers  │  │ • Org Charts │
    └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
           │                 │                  │                  │
           └─────────────────┴──────────────────┴──────────────────┘
                                      ↓
                        ┌─────────────────────────┐
                        │  TECH SPECIALIST AGENT  │
                        │  (Code Generation)      │
                        │                         │
                        │  • SQL Query Generator  │
                        │  • Pandas Operations    │
                        │  • Aggregations         │
                        │  • Data Transformations │
                        └─────────────┬───────────┘
                                      ↓
                        ┌─────────────────────────┐
                        │  PLOTLY SPECIALIST AGT  │
                        │  (Visualization)        │
                        │                         │
                        │  • Interactive Charts   │
                        │  • Time Series Plots    │
                        │  • Comparative Analysis │
                        │  • Dynamic Dashboards   │
                        └─────────────────────────┘
                                      ↓
                              Results + Insights
```

### 🎯 Agent Workflow Example

**User Query:** *"Show me top 10 customers by revenue in 2013"*

```
1. 🎯 Master Agent
   ├─ Analyzes query intent
   ├─ Identifies keywords: "customers", "revenue"
   └─ Routes to → Sales Agent

2. 🛒 Sales Agent
   ├─ Validates query scope (sales domain ✓)
   ├─ Checks for entity names (none to verify)
   ├─ Generates technical instructions:
   │  "Query vw_sales_order_header, group by customer_name,
   │   SUM total_due, filter year=2013, ORDER BY DESC, LIMIT 10"
   └─ Calls → Tech Specialist Agent

3. 🛠️ Tech Specialist Agent
   ├─ Receives instructions from Sales Agent
   ├─ Generates executable Python code:
   │  query = "SELECT customer_name, SUM(total_due) as revenue..."
   │  df = pd.read_sql(query, conn)
   ├─ Executes against SQLite database
   └─ Returns DataFrame with results

4. 🛒 Sales Agent (receives results)
   ├─ Analyzes top 10 customers
   ├─ Calculates summary statistics
   ├─ Generates business insights
   └─ Returns formatted response to user

Result: "Here are the top 10 customers by revenue in 2013:
        1. Action Bicycle Specialists - $108,597.95
        2. Metropolitan Bicycle Supply - $95,555.84
        ..."
```

---

## 🤖 The Agent Team

### 1. 🎯 Master Agent (`adventure_works_master_agent`)

**Role:** Traffic controller and conversation orchestrator

**Responsibilities:**
- Greet users and understand intent
- Route queries to appropriate domain experts
- Maintain conversation context
- Handle general queries and clarifications

**Routing Keywords:**
```python
{
    "sales": ["orders", "customers", "revenue", "sales", "territories", "salespeople"],
    "production": ["products", "inventory", "manufacturing", "work orders", "BOM"],
    "purchasing": ["purchase orders", "vendors", "suppliers", "procurement"],
    "hr": ["employees", "departments", "compensation", "payroll", "headcount"]
}
```

**Does NOT:** Access data directly or generate code

---

### 2. 🛒 Sales Agent (`sales_agent`)

**Domain:** Sales analytics, customer insights, revenue tracking

**Expertise:**
- 📊 Order analysis and tracking
- 👥 Customer purchase patterns and behavior
- 🗺️ Territory performance comparisons
- 💰 Salesperson quota attainment
- 📈 Revenue trends and forecasting
- 🎯 Product category sales breakdown

**Data Views (9):**
- `vw_sales_order_header` - Order-level data
- `vw_sales_order_detail` - Line-item details
- `vw_customers_master` - Customer profiles (19,717 customers)
- `vw_salesperson_master` - Sales rep info (17 salespeople)
- `vw_sales_territory_master` - Territory data (10 territories)
- `vw_sales_by_territory_month` - Monthly territory metrics
- `vw_sales_by_salesperson_month` - Monthly rep performance
- `vw_sales_by_product_month` - Product sales trends
- `vw_sales_reasons_analysis` - Purchase reasons

**Sample Questions:**
```
✓ "Show me top 10 customers by revenue in 2023"
✓ "Compare sales performance across all territories"
✓ "Which salespeople met their quota in 2013?"
✓ "What are the top best-selling products?"
✓ "Show me month-over-month revenue growth"
```

---

### 3. 🏭 Production Agent (`production_agent`)

**Domain:** Product catalog, inventory, manufacturing, quality control

**Expertise:**
- 📦 Inventory level monitoring and alerts
- 💡 Product profitability analysis
- ⚙️ Work order efficiency tracking
- 🔍 Manufacturing scrap analysis
- 🛠️ Bill of materials (BOM) exploration
- 📊 Product transaction history
- 💵 Cost and margin calculations

**Data Views (7):**
- `vw_products_master` - Product catalog (504 products)
- `vw_inventory_current` - Current stock levels
- `vw_work_orders_summary` - Manufacturing orders
- `vw_product_transactions_summary` - Transaction history
- `vw_manufacturing_costs` - Cost and margin data
- `vw_bill_of_materials` - Product components
- `vw_product_reviews` - Customer feedback

**Sample Questions:**
```
✓ "Which products have low inventory below 100 units?"
✓ "What are the top 20 most profitable products?"
✓ "What is the scrap rate for completed work orders?"
✓ "Show me the components for 'Mountain-100 Black, 42'"
✓ "Which products are no longer selling?"
```

---

### 4. 💰 Purchasing Agent (`purchasing_agent`)

**Domain:** Procurement, vendor management, supplier performance

**Expertise:**
- 📋 Purchase order tracking and status
- 🏆 Vendor quality and performance analysis
- 💰 Supplier spend concentration
- 📈 Procurement trend analysis
- ⚖️ Vendor comparison and benchmarking
- ❌ Rejection rate tracking
- ✅ Fulfillment performance metrics

**Data Views (5):**
- `vw_purchase_order_header` - PO tracking
- `vw_purchase_order_detail` - PO line items
- `vw_vendors_master` - Vendor profiles (104 vendors)
- `vw_procurement_by_vendor` - Vendor performance metrics
- `vw_purchase_trends_monthly` - Procurement trends

**Sample Questions:**
```
✓ "Show me vendor quality metrics and rejection rates"
✓ "Which vendors have rejection rates above 5%?"
✓ "Who are our top 10 vendors by spend?"
✓ "Show me monthly procurement trends for 2013"
✓ "Compare spend patterns between major vendors"
```

---

### 5. 👥 HR Agent (`hr_agent`)

**Domain:** Employee analytics, compensation, organizational structure

**Expertise:**
- 📊 Department headcount analysis
- 💵 Compensation analysis and benchmarking
- 🔄 Employee movement tracking
- 👔 Manager vs IC comparisons
- ⏱️ Tenure and retention analysis
- 🏢 Organizational patterns
- 📈 Pay rate distributions

**Data Views (4):**
- `vw_employees_master` - Employee profiles (290 employees)
- `vw_departments_master` - Organization structure (16 departments)
- `vw_employee_pay_history` - Compensation history
- `vw_employee_dept_history` - Department movement

**Sample Questions:**
```
✓ "Compare average pay rates between departments"
✓ "How many employees are in each department?"
✓ "Which employees have transferred between departments?"
✓ "Compare pay rates between managers and individual contributors"
✓ "What is the average employee tenure?"
```

---

### 6. 🛠️ Tech Specialist Agent (`unified_tech_specialist`)

**Role:** Universal code generator for all domain agents

**Responsibilities:**
- Convert natural language instructions into executable Python/SQL code
- Generate SQL queries using `pd.read_sql()`
- Implement aggregations, transformations, and calculations
- Ensure results are in DataFrame format
- Generate summary statistics dictionaries

**Schema Access:**
- Has ALL 25 view schemas (14,694 chars instruction)
- Can write queries for ANY domain (Sales, Production, Purchasing, HR)
- Knows all column names, data types, and relationships
- Receives instructions from any domain agent

**Code Generation Example:**
```python
import pandas as pd
import numpy as np
from datetime import datetime

# Query the database
query = '''
    SELECT 
        territory_name,
        SUM(total_due) as total_revenue,
        COUNT(*) as order_count,
        AVG(total_due) as avg_order_value
    FROM vw_sales_order_header
    WHERE order_date >= '2013-01-01'
    GROUP BY territory_name
    ORDER BY total_revenue DESC
'''
result = pd.read_sql(query, conn)

# Calculate percentages
result['revenue_pct'] = (result['total_revenue'] / result['total_revenue'].sum() * 100)

# Summary statistics
data_summary = {
    'total_territories': len(result),
    'total_revenue': result['total_revenue'].sum(),
    'top_territory': result.iloc[0]['territory_name'],
    'avg_orders_per_territory': result['order_count'].mean()
}
```

**Does NOT:** Interact with users, make business decisions, or validate entities

---

### 7. 📊 Plotly Specialist Agent (`plotly_code_generator`)

**Role:** Interactive visualization generator

**Responsibilities:**
- Create interactive Plotly charts and graphs
- Query SQLite views for visualization data
- Generate professional charts with proper formatting
- Handle categorical data and time series
- Support multi-axis and complex visualizations

**Schema Access:**
- Has ALL 25 view schemas (18,823 chars instruction)
- Can create visualizations for any domain
- Knows all column names and data types
- Receives visualization requirements from domain agents

**Visualization Types:**
- 📊 Bar charts (categorical comparisons)
- 📈 Line charts (time series trends)
- 🔵 Scatter plots (correlations)
- 🥧 Pie charts (proportional breakdowns)
- 📉 Multi-axis charts (complex metrics)
- 🎨 Custom dashboards (combined visualizations)

**Example Visualization:**
```python
import plotly.graph_objects as go
import pandas as pd

# Query data
query = "SELECT order_month, territory_name, total_revenue FROM vw_sales_by_territory_month"
df = pd.read_sql(query, conn)

# Create interactive line chart
fig = go.Figure()
for territory in df['territory_name'].unique():
    territory_data = df[df['territory_name'] == territory]
    fig.add_trace(go.Scatter(
        x=territory_data['order_month'],
        y=territory_data['total_revenue'],
        mode='lines+markers',
        name=territory
    ))

fig.update_layout(
    title='Revenue Trends by Territory',
    xaxis_title='Month',
    yaxis_title='Total Revenue ($)',
    hovermode='x unified'
)
```

---

## 🎯 Key Features

### ✨ Natural Language Processing
- Ask questions in plain English—no SQL required
- Context-aware conversations with memory
- Intelligent query interpretation and routing
- Follow-up question handling

### 🔍 Entity Verification System
- **20,835 cached entities** across 12 types
- Instant validation without database queries
- Smart fuzzy matching for similar names
- Entity types: customers, products, vendors, employees, departments, territories, etc.

### 📊 View-Based Architecture
- **25 pre-built analytical views** denormalize complex schemas
- Optimized for common analytical patterns
- Monthly pre-aggregated views for time series
- Human-friendly column names (`customer_name` vs `CustomerID`)

### 🚀 Performance Features
- **Entity caching:** 20K+ entities in memory for instant validation
- **SQLite indexes:** 20+ indexes on frequently queried columns
- **Pre-aggregated views:** Monthly computations cached
- **Connection pooling:** Singleton pattern for efficiency
- **Query optimization:** Efficient JOINs and WHERE clauses

### 🛡️ Safety & Validation
- Code guardrails prevent dangerous operations
- Input sanitization and SQL injection prevention
- Entity validation before query execution
- Error handling with helpful user messages

---

## 📊 Data Overview

### Database Statistics

| Metric | Value |
|--------|-------|
| **Total Tables** | 66 |
| **Total Views** | 25 |
| **Total Rows** | 759,195 |
| **Database Size** | ~500 MB |
| **Cached Entities** | 20,835 |
| **Entity Types** | 12 |

### Schema Distribution

| Schema | Tables | Total Rows | Description |
|--------|--------|------------|-------------|
| **Sales** | 19 | 253,735 | Orders, customers, territories |
| **Production** | 23 | 349,850 | Products, work orders, inventory |
| **Purchasing** | 5 | 13,426 | Purchase orders, vendors |
| **HumanResources** | 6 | 934 | Employees, departments, pay |
| **Person** | 13 | 141,250 | People, addresses, contacts |

### View Categories

**📈 Sales Views (9):** Customer analysis, order tracking, territory performance, salesperson metrics

**🏭 Production Views (7):** Product catalog, inventory, work orders, BOM, costs

**💰 Purchasing Views (5):** Purchase orders, vendor management, procurement trends

**👥 HR Views (4):** Employees, departments, compensation, organizational history

---

## 🚀 Quick Start

### Prerequisites

- Python 3.13+
- SQLite 3
- Google ADK (Agent Development Kit)
- Adventure Works OLTP database (included)

### Installation

```bash
# Clone repository
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment (optional - uses defaults)
export GOOGLE_API_KEY="your_gemini_api_key"
```

### Running the System

**Option 1: Web Application (Recommended)**
```bash
python main.py
# Opens web interface at http://localhost:8000
```

**Option 2: Interactive CLI**
```bash
python runner.py
# Start chatting in terminal
```

**Option 3: Programmatic Usage**
```python
from agents.agent import root_agent
from google.adk.sessions import InMemorySessionService

# Initialize session
session_service = InMemorySessionService()
session = session_service.create_session()

# Ask a question
response = root_agent.run(
    "Show me top 10 customers by revenue in 2013",
    session=session
)

print(response.output)
```

---

## 💡 Usage Examples

### Sales Queries

```python
# Customer Analysis
"Show me top 10 customers by revenue in 2013"
"What is the total revenue from 'Alpine Ski House'?"
"Which customers have ordered more than $50,000 worth?"

# Territory Performance
"Compare sales performance across all territories"
"Which territory had the highest growth rate in 2013?"
"Show me monthly revenue trends for Southwest territory"

# Revenue Analysis
"What is our total revenue for 2013?"
"Show me month-over-month revenue growth"
"Calculate quota attainment for all salespeople"
```

### Production Queries

```python
# Inventory Management
"Which products have low inventory below 100 units?"
"Show me inventory levels for 'Mountain-100 Black' bikes"
"Which location has the most inventory?"

# Product Profitability
"What are the top 20 most profitable products?"
"Show me products with margins above 30%"
"Compare cost vs list price for all bike products"

# Manufacturing
"What is the scrap rate for completed work orders?"
"Which products have the highest scrap rates?"
"Show me work order efficiency by product"
```

### Purchasing Queries

```python
# Vendor Performance
"Show me vendor quality metrics and rejection rates"
"Which vendors have rejection rates above 5%?"
"Compare fulfillment rates across all vendors"

# Spend Analysis
"Who are our top 10 vendors by spend?"
"What percentage of spend goes to top 3 vendors?"
"Show me spend concentration analysis"

# Procurement Trends
"Show me monthly procurement trends for 2013"
"Which months had the highest spending?"
"Is our procurement spend increasing or decreasing?"
```

### HR Queries

```python
# Department Analysis
"Compare average pay rates between departments"
"How many employees are in each department?"
"Which department has the most employees?"

# Compensation
"What is the average pay rate by department?"
"Compare pay rates between managers and ICs"
"Show me the pay range across the company"

# Employee Movement
"Which employees have transferred between departments?"
"Show me department transfer patterns"
"What is the average tenure by department?"
```

---

## 🏛️ Technical Architecture

### Schema Distribution Strategy

**Domain Agents (Focused):**
- Each has only **relevant view schemas** (7-9 views)
- Instruction size: 6-10K characters
- Faster token processing
- Domain-specific expertise

**Specialist Agents (Comprehensive):**
- Have **ALL 25 view schemas**
- Instruction size: 15-19K characters
- Universal code generation capability
- Can handle instructions from any domain

This design ensures:
✅ Domain agents stay focused and efficient
✅ Specialist agents can generate correct code for any domain
✅ No query limitations based on routing path
✅ Optimal token usage and response times

### View Design Principles

1. **Denormalization:** Pre-join related tables for simplified querying
2. **Naming Convention:** Lowercase with underscores (`customer_name`)
3. **Aggregated Views:** Monthly pre-aggregations for time series
4. **Performance:** Indexed on common filter columns
5. **Readability:** Human-friendly column names

### Entity Caching System

```python
# Cached at startup for instant validation
entity_cache = {
    "customers": 19717,      # Customer names
    "products": 504,         # Product names
    "vendors": 104,          # Vendor names
    "employees": 290,        # Employee names
    "departments": 16,       # Department names
    "territories": 10,       # Territory names
    "categories": 4,         # Product categories
    "subcategories": 37,     # Product subcategories
    "locations": 14,         # Inventory locations
    "models": 119,           # Product models
    "shifts": 3,             # Work shifts
    "salespeople": 17        # Sales representatives
}
```

Benefits:
- ⚡ Zero database queries for validation
- 🎯 Instant fuzzy matching for typos
- 💾 Memory-efficient (string deduplication)
- 🔄 Auto-refreshes on database changes

---

## 📂 Project Structure

```
backend/
├── agents/
│   ├── agent.py                    # Master agent (router)
│   ├── sales_agent.py              # Sales domain expert
│   ├── production_agent.py         # Production domain expert
│   ├── purchasing_agent.py         # Purchasing domain expert
│   ├── hr_agent.py                 # HR domain expert
│   ├── tech_specialist_agent.py    # Code generator
│   └── plotly_specialist_agent.py  # Visualization generator
│
├── tools/
│   ├── code_executor.py            # Safe code execution
│   ├── plotly_executor.py          # Plotly code execution
│   ├── data_loader.py              # Data loading utilities
│   ├── data_schema.py              # View schema definitions
│   ├── entity_cache.py             # Entity caching system
│   ├── entity_verifier.py          # Entity validation
│   └── gaurdrails.py               # Code safety checks
│
├── data_stage/
│   ├── data/
│   │   └── adventureworks.db       # SQLite database (759K rows)
│   ├── db_connection.py            # Connection management
│   ├── sqlite_importer.py          # Data import scripts
│   └── create_views.sql            # View definitions
│
├── cosmosservice/
│   ├── cosmos_client.py            # Azure Cosmos DB client
│   ├── cosmos_session_service.py   # Session management
│   └── data_converters.py          # Data serialization
│
├── routes/
│   ├── messages.py                 # Chat endpoints
│   ├── sessions.py                 # Session management
│   ├── download.py                 # File downloads
│   └── health.py                   # Health checks
│
├── utils/
│   ├── event_processor.py          # Event streaming
│   └── title_generator.py          # Session title generation
│
├── main.py                         # FastAPI application
├── runner.py                       # CLI runner
├── config.py                       # Configuration
└── requirements.txt                # Python dependencies
```

---

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_basic_endpoints.py

# Run with coverage
python -m pytest --cov=. tests/
```

---

## 🔧 Configuration

### Environment Variables

```bash
# Google Gemini API
GOOGLE_API_KEY=your_api_key_here

# Database (uses local SQLite by default)
DATABASE_PATH=data_stage/data/adventureworks.db

# Azure Cosmos DB (optional)
AZURE_COSMOS_ENDPOINT=https://your-account.documents.azure.com:443/
AZURE_COSMOS_KEY=your_cosmos_key

# Storage (optional)
AZURE_STORAGE_CONNECTION_STRING=your_connection_string
```

### Default Configuration

The system works out-of-the-box with:
- ✅ Local SQLite database (pre-loaded with Adventure Works data)
- ✅ In-memory session service
- ✅ Local file storage for downloads
- ✅ Google Gemini 2.0 Flash (via ADK)

---

## 🎓 Migration Story: Version 1.0 → 2.0

### The Evolution

**Version 1.0:**
- 📊 In-memory pandas DataFrames
- 📦 SalesLT subset only (7 tables, 308 rows)
- 🤖 3 simple agents
- 🔍 No entity validation
- 📈 Basic aggregations

**Version 2.0:**
- 🗄️ SQLite database with full OLTP schema
- 📦 Complete Adventure Works (66 tables, 759,195 rows)
- 🤖 6 sophisticated agents in hierarchy
- 🔍 Entity cache with 20,835 entities
- 📊 25 pre-built analytical views
- 🎯 Smart routing and domain expertise

### Why This Matters

This migration demonstrates:
- ✅ Scaling from toy dataset to enterprise data
- ✅ Agent specialization and orchestration
- ✅ Performance optimization techniques
- ✅ Real-world business intelligence patterns
- ✅ Production-ready architecture

---

## 🚀 Performance Benchmarks

| Operation | Average Time | Details |
|-----------|--------------|---------|
| Entity Validation | < 1ms | Cached lookup |
| Simple Query | 50-100ms | Single table, < 1K rows |
| Complex Aggregation | 200-500ms | Multi-table JOIN |
| Visualization | 300-800ms | Query + chart generation |
| Full Agent Response | 2-5 seconds | Including LLM inference |

---

## 🤝 Contributing

This is a showcase project demonstrating advanced agent architecture patterns. Key learnings:

- **Agent Specialization:** Domain experts + universal specialists
- **Schema Distribution:** Focused vs comprehensive instructions
- **Entity Validation:** Cached validation for instant feedback
- **View-Based Design:** Pre-aggregated analytical views
- **Hierarchical Routing:** Master agent → Domain → Specialist

---

## 📄 License

See `LICENSE` file for details.

---

## 📚 Additional Resources

- **System Documentation:** `SYSTEM_DOCUMENTATION.md` - Complete system reference
- **Migration Plan:** `MIGRATION_PLAN.md` - Version 1.0 → 2.0 journey
- **View Definitions:** `data_stage/create_views.sql` - All 25 analytical views
- **Agent Instructions:** See individual agent files for detailed prompts

---

## 🎯 What's Next?

Future enhancements could include:
- 🔄 Real-time data updates and streaming
- 📊 Custom dashboard builder
- 📤 Advanced export formats (Excel, PDF)
- 📧 Scheduled reports and alerts
- 🤖 Additional domain agents (Finance, Marketing)
- 🌍 Multi-language support
- 🔐 Enterprise security features

---

**Built with ❤️ using Google ADK, Gemini 2.0, and Adventure Works OLTP**

*For questions, issues, or discussions about the agent architecture, please refer to the code and documentation.*
