# Adventure Works Analytics System - Documentation

**Version:** 2.0 (SQLite Architecture)  
**Last Updated:** November 2024  
**Database:** Adventure Works OLTP (759,195 rows across 66 tables)

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Agent Hierarchy](#agent-hierarchy)
4. [Domain Agents](#domain-agents)
5. [Data Views](#data-views)
6. [Sample Questions](#sample-questions)
7. [Technical Details](#technical-details)

---

## System Overview

The Adventure Works Analytics System is an AI-powered business intelligence platform built on Microsoft's Adventure Works OLTP dataset. It uses a hierarchical agent architecture powered by Google's Gemini 2.0 to provide natural language analytics across Sales, Production, Purchasing, and HR domains.

### Key Features

- **Natural Language Queries**: Ask questions in plain English
- **Multi-Domain Analytics**: Sales, Production, Purchasing, HR
- **Entity Verification**: Smart validation of customer names, products, vendors, etc.
- **Interactive Visualizations**: Plotly-powered charts and graphs
- **SQL-Powered**: Efficient SQLite backend with 25 pre-built analytical views
- **Hierarchical Agents**: Master agent routes to specialized domain agents

### Migration History

**Version 1.0 → 2.0 Migration:**
- **From:** In-memory pandas DataFrames (SalesLT subset)
- **To:** SQLite database with full Adventure Works OLTP
- **Data Growth:** 308 rows → 759,195 rows
- **Tables:** 7 → 66 tables
- **Views Created:** 25 denormalized analytical views
- **Agent Redesign:** 3 agents → 4 domain agents with detailed aggregation examples

---

## Architecture

### High-Level Architecture

```
User Question
     ↓
Master Agent (Router)
     ↓
Domain Agent (Sales/Production/Purchasing/HR)
     ↓
Entity Verification (if needed)
     ↓
Tech Specialist Agent (Generates SQL + Pandas code)
     ↓
Code Executor (Executes against SQLite)
     ↓
Plotly Specialist Agent (Optional - for visualizations)
     ↓
Results (DataFrame + Summary Statistics)
```

### Technology Stack

- **AI Framework:** Google ADK (Agent Development Kit)
- **LLM:** Gemini 2.0 Flash
- **Database:** SQLite 3
- **Data Processing:** Pandas, NumPy
- **Visualization:** Plotly
- **Backend:** Python 3.13

### Data Flow

1. **User Query** → Received by Master Agent
2. **Routing** → Master agent selects appropriate domain agent
3. **Entity Validation** → Domain agent validates entities (e.g., customer names)
4. **Instruction Generation** → Domain agent creates detailed SQL instructions
5. **Code Generation** → Tech specialist generates executable Python/SQL code
6. **Execution** → Code executor runs against SQLite database
7. **Results** → DataFrame + summary statistics returned to user

### Schema Distribution Strategy

**Domain Agents (Sales, Production, Purchasing, HR):**
- Each has only its relevant view schemas (7-9 views)
- Reduces instruction size (6-10K chars)
- Focused domain expertise

**Specialist Agents (Tech, Plotly):**
- Have ALL 25 view schemas
- Can handle instructions from any domain
- Know all columns, data types, and relationships
- Generate correct SQL queries regardless of source domain
- Larger instructions (15-19K chars) but necessary for cross-domain capability

---

## Agent Hierarchy

### 1. Master Agent (`adventure_works_master_agent`)

**Role:** Router and orchestrator

**Responsibilities:**
- Greet users
- Understand user intent
- Route questions to appropriate domain agent
- No direct data access

**Routing Logic:**
- Keywords: orders, customers, territories, salespeople → **Sales Agent**
- Keywords: products, inventory, manufacturing, work orders → **Production Agent**
- Keywords: purchase orders, vendors, suppliers → **Purchasing Agent**
- Keywords: employees, departments, compensation → **HR Agent**

---

### 2. Domain Agents (4 Specialized Agents)

Each domain agent follows a consistent workflow:

1. **Entity Validation** - Verify entities exist (customer names, product names, etc.)
2. **Generate Technical Instructions** - Create detailed SQL queries with aggregations
3. **Coordinate Execution** - Call tech specialist or plotly specialist
4. **Present Results** - Summarize findings with actionable insights

---

## Domain Agents

### 🛒 Sales Agent

**Full Name:** `sales_agent`  
**Specialization:** Sales analytics, customer analysis, revenue tracking, territory performance

**Capabilities:**
- Order analysis and tracking
- Customer purchase patterns
- Territory performance comparison
- Salesperson quota attainment
- Revenue trends and forecasting
- Product category sales breakdown

**Data Views Used:**
- `vw_sales_order_header` - Order-level data
- `vw_sales_order_detail` - Line-item details
- `vw_customers_master` - Customer profiles
- `vw_salesperson_master` - Sales rep info
- `vw_sales_territory_master` - Territory data
- `vw_sales_by_territory_month` - Monthly territory metrics
- `vw_sales_by_salesperson_month` - Monthly rep performance
- `vw_sales_by_product_month` - Product sales trends
- `vw_sales_reasons_analysis` - Purchase reasons

**Entity Types Validated:**
- Customer names (19,717 customers)
- Salesperson names (17 reps)
- Territory names (10 territories)

**Sample Questions:**

1. **Customer Analysis**
   - "Show me all orders from customer 'Alpine Ski House'"
   - "What is the total revenue from 'Bikes Unlimited' in 2013?"
   - "Which customers have ordered more than $50,000 worth of products?"

2. **Territory Performance**
   - "Compare sales performance across all territories"
   - "Which territory had the highest growth rate in 2013?"
   - "Show me monthly revenue trends for the Southwest territory"

3. **Salesperson Analytics**
   - "How many salespeople met their quota in 2013?"
   - "Who is the top performing salesperson?"
   - "Show me Linda Mitchell's sales performance"

4. **Product Sales**
   - "What are the top 10 best-selling products?"
   - "Compare revenue between Bikes and Accessories categories"
   - "Show me monthly sales trends for Road bikes"

5. **Revenue Analysis**
   - "What is our total revenue for 2013?"
   - "Show me month-over-month revenue growth"
   - "Which product category generates the most revenue?"

---

### 🏭 Production Agent

**Full Name:** `production_agent`  
**Specialization:** Product catalog, inventory management, manufacturing, quality control

**Capabilities:**
- Inventory level monitoring
- Product profitability analysis
- Work order efficiency tracking
- Manufacturing scrap analysis
- Bill of materials (BOM) analysis
- Product transaction history
- Cost and margin analysis

**Data Views Used:**
- `vw_products_master` - Complete product catalog
- `vw_inventory_current` - Current stock levels
- `vw_work_orders_summary` - Manufacturing orders
- `vw_product_transactions_summary` - Transaction history
- `vw_manufacturing_costs` - Cost and margin data
- `vw_bill_of_materials` - Product components
- `vw_product_reviews` - Customer feedback

**Entity Types Validated:**
- Product names (504 products)
- Product categories (4 categories)
- Product subcategories (37 subcategories)
- Location names (14 locations)
- Model names (119 models)

**Sample Questions:**

1. **Inventory Management**
   - "Which products have low inventory (below 100 units)?"
   - "Show me inventory levels for 'Mountain-100 Black' bikes"
   - "Which location has the most inventory?"

2. **Product Profitability**
   - "What are the top 20 most profitable products?"
   - "Show me products with margins above 30%"
   - "Compare cost vs list price for all bike products"

3. **Manufacturing**
   - "What is the scrap rate for completed work orders?"
   - "Which products have the highest scrap rates?"
   - "Show me work order efficiency by product"

4. **Bill of Materials**
   - "Show me the components for 'Mountain-100 Black, 42'"
   - "What are the most expensive components in our products?"
   - "Display the full BOM hierarchy for Road bikes"

5. **Product Performance**
   - "Which products are no longer selling?"
   - "Show me transaction history for touring bikes"
   - "What products have the highest customer ratings?"

---

### 💰 Purchasing Agent

**Full Name:** `purchasing_agent`  
**Specialization:** Procurement, vendor management, purchase orders, supplier performance

**Capabilities:**
- Purchase order tracking
- Vendor quality analysis
- Supplier spend concentration
- Procurement trend analysis
- Vendor comparison
- Rejection rate tracking
- Fulfillment performance

**Data Views Used:**
- `vw_purchase_order_header` - PO tracking
- `vw_purchase_order_detail` - PO line items
- `vw_vendors_master` - Vendor profiles
- `vw_procurement_by_vendor` - Vendor performance metrics
- `vw_purchase_trends_monthly` - Procurement trends

**Entity Types Validated:**
- Vendor names (104 vendors)

**Sample Questions:**

1. **Purchase Orders**
   - "Show me all pending purchase orders"
   - "What is the total value of open POs?"
   - "Which vendor has the most pending orders?"

2. **Vendor Performance**
   - "Which vendors have rejection rates above 5%?"
   - "Show me vendor quality metrics"
   - "Compare fulfillment rates across all vendors"

3. **Spend Analysis**
   - "Who are our top 10 vendors by spend?"
   - "What percentage of spend goes to our top 3 vendors?"
   - "Show me spend concentration analysis"

4. **Procurement Trends**
   - "Show me monthly procurement trends for 2013"
   - "Which months had the highest spending?"
   - "Is our procurement spend increasing or decreasing?"

5. **Vendor Comparison**
   - "Compare spend patterns between Litware and Proseware"
   - "Which vendor is most consistent in delivery?"
   - "Show me monthly spend by vendor"

---

### 👥 HR Agent

**Full Name:** `hr_agent`  
**Specialization:** Employee analytics, department analysis, compensation, organizational structure

**Capabilities:**
- Department headcount analysis
- Compensation analysis by department
- Employee movement tracking
- Manager vs IC comparisons
- Tenure and retention analysis
- Organizational patterns
- Pay rate analysis

**Data Views Used:**
- `vw_employees_master` - Employee profiles
- `vw_departments_master` - Organization structure
- `vw_employee_pay_history` - Compensation history
- `vw_employee_dept_history` - Department movement

**Entity Types Validated:**
- Employee names (290 employees)
- Department names (16 departments)
- Shift names (3 shifts)

**Sample Questions:**

1. **Department Analysis**
   - "How many employees are in each department?"
   - "Which department has the most employees?"
   - "Show me the organizational breakdown by department"

2. **Compensation**
   - "What is the average pay rate by department?"
   - "Compare compensation between Engineering and Production"
   - "Show me the pay range across the company"

3. **Employee Movement**
   - "Which employees have transferred between departments?"
   - "How many employees moved in the last year?"
   - "Show me department transfer patterns"

4. **Manager Analysis**
   - "How many managers do we have?"
   - "Compare pay rates between managers and individual contributors"
   - "Show me all employees with 'Manager' in their title"

5. **Tenure & Retention**
   - "What is the average employee tenure?"
   - "Which department has the highest average tenure?"
   - "Show me tenure distribution by department"

---

### 🛠️ Technical Specialist Agent

**Full Name:** `unified_tech_specialist`  
**Role:** Code generator

**Responsibilities:**
- Convert domain agent instructions into executable Python code
- Generate SQL queries using pd.read_sql()
- Implement aggregations, calculations, and transformations
- Ensure results are in DataFrame format
- Generate summary statistics

**Schema Access:**
- Has access to ALL 25 view schemas (14,694 chars instruction)
- Can write queries for any domain (Sales, Production, Purchasing, HR)
- Knows all column names, data types, and relationships
- Receives instructions from any domain agent

**Does NOT:**
- Interact directly with users
- Make business decisions
- Validate entities

---

### 📊 Plotly Specialist Agent

**Full Name:** `plotly_code_generator`  
**Role:** Visualization generator

**Responsibilities:**
- Create interactive Plotly visualizations
- Query SQLite views for data
- Generate professional charts with proper formatting
- Handle categorical data and time series

**Schema Access:**
- Has access to ALL 25 view schemas (18,823 chars instruction)
- Can create visualizations for any domain
- Knows all column names and data types for queries
- Receives visualization requirements from any domain agent

**Visualization Types:**
- Bar charts
- Line charts
- Scatter plots
- Pie charts
- Time series
- Multi-axis charts

---

## Data Views

### Overview

The system uses 25 pre-built analytical views that denormalize and aggregate data from 66 raw tables. These views simplify querying and improve performance.

### View Categories

#### 📈 Sales Views (9)

| View Name | Purpose | Key Columns | Aggregation |
|-----------|---------|-------------|-------------|
| `vw_sales_order_header` | Order-level data | sales_order_id, customer_name, total_due, order_date | No |
| `vw_sales_order_detail` | Line-item details | product_name, order_qty, unit_price, line_total | No |
| `vw_customers_master` | Customer profiles | customer_id, customer_name, territory_name | No |
| `vw_salesperson_master` | Sales rep info | salesperson_name, sales_ytd, sales_quota | No |
| `vw_sales_territory_master` | Territory reference | territory_name, country_code, sales_ytd | No |
| `vw_sales_by_territory_month` | Territory metrics | order_month, territory_name, total_revenue | Yes (Monthly) |
| `vw_sales_by_salesperson_month` | Rep performance | order_month, salesperson_name, total_revenue | Yes (Monthly) |
| `vw_sales_by_product_month` | Product sales | order_month, product_name, total_quantity | Yes (Monthly) |
| `vw_sales_reasons_analysis` | Purchase reasons | reason_name, order_count, total_revenue | Yes |

#### 🏭 Production Views (7)

| View Name | Purpose | Key Columns | Aggregation |
|-----------|---------|-------------|-------------|
| `vw_products_master` | Product catalog | product_name, list_price, standard_cost | No |
| `vw_inventory_current` | Stock levels | product_name, location_name, quantity | No |
| `vw_work_orders_summary` | Manufacturing | work_order_id, order_qty, scrapped_qty | No |
| `vw_product_transactions_summary` | Transaction history | transaction_month, transaction_type, quantity | Yes (Monthly) |
| `vw_manufacturing_costs` | Cost analysis | product_name, current_margin, margin_pct | No |
| `vw_bill_of_materials` | Product structure | assembly_product_name, component_name | No |
| `vw_product_reviews` | Customer feedback | product_name, rating, comments | No |

#### 💰 Purchasing Views (5)

| View Name | Purpose | Key Columns | Aggregation |
|-----------|---------|-------------|-------------|
| `vw_purchase_order_header` | PO tracking | purchase_order_id, vendor_name, total_due | No |
| `vw_purchase_order_detail` | PO line items | product_name, order_qty, unit_price | No |
| `vw_vendors_master` | Vendor profiles | vendor_name, credit_rating, preferred_vendor | No |
| `vw_procurement_by_vendor` | Vendor performance | order_month, vendor_name, total_spend | Yes (Monthly) |
| `vw_purchase_trends_monthly` | Procurement trends | order_month, po_count, total_spend | Yes (Monthly) |

#### 👥 HR Views (4)

| View Name | Purpose | Key Columns | Aggregation |
|-----------|---------|-------------|-------------|
| `vw_employees_master` | Employee profiles | employee_name, job_title, department_name | No |
| `vw_departments_master` | Organization | department_name, group_name | No |
| `vw_employee_pay_history` | Compensation | employee_id, rate, rate_change_date | No |
| `vw_employee_dept_history` | Department moves | employee_id, department_name, start_date | No |

### View Design Principles

1. **Denormalization**: Pre-join related tables for simplified querying
2. **Naming Convention**: Use lowercase with underscores (e.g., `customer_name`)
3. **Aggregated Views**: Monthly pre-aggregations for common analytical patterns
4. **Performance**: Indexed on common filter columns
5. **Readability**: Human-friendly column names

---

## Sample Questions

### Complete Query Examples

#### 🛒 Sales Queries

**Basic:**
```
"Show me all orders from 2013"
"What is the total revenue?"
"How many orders do we have?"
```

**Intermediate:**
```
"Compare revenue between territories"
"Which salespeople exceeded their quota?"
"Show me top 10 customers by revenue"
```

**Advanced:**
```
"Calculate month-over-month revenue growth for the Southwest territory"
"Show me quota attainment percentage for all salespeople, ordered by performance"
"Analyze customer purchase patterns: first order date, total orders, total revenue, average order value"
```

#### 🏭 Production Queries

**Basic:**
```
"How many products do we have?"
"Show me current inventory levels"
"List all bike products"
```

**Intermediate:**
```
"Which products have low inventory?"
"Show me products with margins above 30%"
"What is the average scrap rate?"
```

**Advanced:**
```
"Calculate inventory turnover ratio by product category"
"Analyze work order efficiency: scrap rate, completion rate, average production time"
"Show me the full bill of materials for Mountain-100 with component costs"
```

#### 💰 Purchasing Queries

**Basic:**
```
"List all vendors"
"Show me pending purchase orders"
"What is our total procurement spend?"
```

**Intermediate:**
```
"Which vendors have the highest spend?"
"Show me vendor rejection rates"
"Compare procurement trends over time"
```

**Advanced:**
```
"Calculate vendor concentration: what percentage of spend goes to top 3 vendors?"
"Analyze vendor quality: rejection rate, fulfillment rate, consistency"
"Show me spend patterns by vendor with month-over-month growth rates"
```

#### 👥 HR Queries

**Basic:**
```
"How many employees do we have?"
"List all departments"
"Show me all managers"
```

**Intermediate:**
```
"Compare headcount by department"
"What is the average pay rate?"
"Show me employee tenure distribution"
```

**Advanced:**
```
"Calculate average tenure by department with retention patterns"
"Analyze compensation: compare manager vs individual contributor pay with differentials"
"Show me employee movement patterns: transfer frequency, average time in department"
```

---

## Technical Details

### Database Statistics

- **Total Tables:** 66
- **Total Views:** 25
- **Total Rows:** 759,195
- **Database Size:** ~500 MB
- **Entity Cache:** 20,835 entities across 12 types

### Schema Breakdown

| Schema | Tables | Total Rows | Description |
|--------|--------|------------|-------------|
| Sales | 19 | 253,735 | Orders, customers, territories |
| Production | 23 | 349,850 | Products, work orders, inventory |
| Purchasing | 5 | 13,426 | Purchase orders, vendors |
| HumanResources | 6 | 934 | Employees, departments, pay |
| Person | 13 | 141,250 | People, addresses, contacts |

### Performance Features

1. **Entity Caching:** 20K+ entities cached in memory for instant validation
2. **SQLite Indexes:** 20+ indexes on frequently queried columns
3. **Pre-Aggregated Views:** Monthly aggregations computed once
4. **Connection Pooling:** Singleton pattern for database connections
5. **Query Optimization:** Views use efficient JOINs and WHERE clauses

### Code Execution

**Input:** Detailed SQL instructions from domain agents

**Process:**
1. Generate SQL query using `pd.read_sql(query, conn)`
2. Apply pandas transformations if needed (pct_change, rolling, pivot)
3. Calculate aggregations (SUM, COUNT, AVG, etc.)
4. Create summary statistics dictionary
5. Return DataFrame result

**Output:**
- `result`: pandas DataFrame with query results
- `data_summary`: Dictionary with key metrics

### Example Generated Code

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

---

## Getting Started

### Prerequisites

- Python 3.13+
- Google ADK
- SQLite 3
- Adventure Works OLTP database (pre-loaded)

### Quick Start

```python
from agents.agent import root_agent
from google.adk.sessions import InMemorySessionService

# Initialize session
session_service = InMemorySessionService()
session = session_service.create_session()

# Ask a question
response = root_agent.run(
    "Show me total revenue by territory",
    session=session
)

print(response.output)
```

### Example Conversation

```
User: "Which territory had the highest revenue in 2013?"

System: [Routes to Sales Agent]
        [Validates entity: territory]
        [Generates SQL query]
        [Executes and analyzes]

Response: "The Southwest territory had the highest revenue in 2013 
          with $10.8M (32% of total revenue), followed by Northwest 
          at $7.9M. Southwest also had the highest order count at 
          4,876 orders with an average order value of $2,214."
```

---

## Best Practices

### For Users

1. **Be Specific:** Include entity names, date ranges, and metrics
2. **Use Natural Language:** No need to know SQL
3. **Ask Follow-ups:** System maintains conversation context
4. **Request Visualizations:** Ask for charts when comparing data

### For Developers

1. **Entity Validation:** Always validate entities before querying
2. **Aggregation in SQL:** Prefer SQL aggregations over pandas when possible
3. **View Usage:** Use pre-built views instead of raw tables
4. **Error Handling:** Provide helpful error messages for invalid entities

---

## Troubleshooting

### Common Issues

**Issue:** "Entity not found"  
**Solution:** Check spelling, try fuzzy search suggestions

**Issue:** "No data returned"  
**Solution:** Verify date ranges, check filters

**Issue:** "Query timeout"  
**Solution:** Simplify query, use pre-aggregated views

---

## Future Enhancements

- [ ] Real-time data updates
- [ ] Custom dashboard builder
- [ ] Export to Excel/CSV
- [ ] Scheduled reports
- [ ] Alert system for thresholds
- [ ] Multi-user support
- [ ] Data lineage tracking
- [ ] Advanced forecasting

---

## Support

For questions or issues, please refer to:
- System logs: `/backend/logs/`
- Database: `/backend/data_stage/data/adventureworks.db`
- Documentation: This file

---

**Last Updated:** November 2024  
**System Version:** 2.0  
**Document Version:** 1.0

