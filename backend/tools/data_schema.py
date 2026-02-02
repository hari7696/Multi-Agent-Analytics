"""
Adventure Works OLTP - Data Schema Documentation
Documents all 25 SQLite views for agent consumption
"""

# ===== SALES VIEWS (9) =====

vw_sales_order_header_schema = """
VIEW: vw_sales_order_header
Denormalized sales orders with customer, salesperson, territory info

Columns:
- sales_order_id (int): Unique order ID
- order_date (datetime): Order date
- due_date (datetime): Expected delivery
- ship_date (datetime): Actual ship date
- status (int): Order status code (1-6)
- status_name (string): Status description
- online_order_flag (bool): True if online order
- customer_id (int): Customer ID
- customer_name (string): Customer or store name
- salesperson_id (int): Sales rep ID
- salesperson_name (string): Sales rep full name
- territory_id (int): Territory ID
- territory_name (string): Territory name
- territory_country (string): Country code
- subtotal, tax_amt, freight, total_due (float): Financial amounts

SQL: SELECT * FROM vw_sales_order_header WHERE territory_name = 'Southwest'
"""

vw_sales_order_detail_schema = """
VIEW: vw_sales_order_detail
Line-item level product sales with denormalized order and product info

Columns:
- sales_order_id (int): Parent order ID
- sales_order_detail_id (int): Line item ID
- order_date (datetime): Order date (denormalized)
- order_qty (int): Quantity ordered
- product_id (int): Product ID
- product_name (string): Product name
- product_number (string): Product SKU
- product_subcategory (string): Subcategory name
- product_category (string): Category name
- unit_price, unit_price_discount, line_total (float): Pricing
- customer_id, territory_id, territory_name: Denormalized fields

SQL: SELECT * FROM vw_sales_order_detail WHERE product_category = 'Bikes'
"""

vw_customers_master_schema = """
VIEW: vw_customers_master
Complete customer profiles with territory

Columns:
- customer_id (int): Unique customer ID
- customer_name (string): Full name or store name
- customer_type (string): 'Person' or 'Store'
- person_type (string): Person type code
- title, first_name, last_name (string): Name components
- store_name (string): Store name if applicable
- territory_id (int): Territory ID
- territory_name (string): Territory name
- account_number (string): Account number

SQL: SELECT * FROM vw_customers_master WHERE customer_type = 'Store'
"""

vw_salesperson_master_schema = """
VIEW: vw_salesperson_master
Sales representative profiles with performance metrics

Columns:
- salesperson_id (int): Rep ID
- salesperson_name (string): Full name
- territory_id (int): Territory ID
- territory_name (string): Territory name
- sales_quota (float): Quota amount
- bonus (float): Bonus earned
- commission_pct (float): Commission percentage
- sales_ytd (float): Year-to-date sales
- sales_last_year (float): Prior year sales

SQL: SELECT * FROM vw_salesperson_master WHERE sales_ytd > 1000000
"""

vw_sales_territory_master_schema = """
VIEW: vw_sales_territory_master
Territory reference data

Columns:
- territory_id (int): Territory ID
- territory_name (string): Territory name
- country_code (string): Country code
- territory_group (string): Group name
- sales_ytd, sales_last_year, cost_ytd, cost_last_year (float): Metrics

SQL: SELECT * FROM vw_sales_territory_master
"""

vw_sales_by_territory_month_schema = """
VIEW: vw_sales_by_territory_month
Pre-aggregated monthly territory performance metrics

Columns:
- order_month (string): YYYY-MM format
- territory_id (int): Territory ID
- territory_name (string): Territory name
- country_code (string): Country code
- order_count (int): Number of orders
- total_revenue (float): Total revenue
- avg_order_value (float): Average order size
- unique_customers (int): Distinct customers

SQL: SELECT * FROM vw_sales_by_territory_month WHERE order_month >= '2013-01'
"""

vw_sales_by_salesperson_month_schema = """
VIEW: vw_sales_by_salesperson_month
Pre-aggregated monthly salesperson performance

Columns:
- order_month (string): YYYY-MM
- salesperson_id (int): Rep ID
- salesperson_name (string): Full name
- order_count (int): Orders
- total_revenue (float): Revenue
- avg_order_value (float): Avg order
- unique_customers (int): Customers

SQL: SELECT * FROM vw_sales_by_salesperson_month WHERE salesperson_name = 'Linda Mitchell'
"""

vw_sales_by_product_month_schema = """
VIEW: vw_sales_by_product_month
Pre-aggregated monthly product sales

Columns:
- order_month (string): YYYY-MM
- product_id (int): Product ID
- product_name (string): Product name
- product_subcategory (string): Subcategory
- product_category (string): Category
- order_count (int): Orders
- total_quantity (int): Units sold
- total_revenue (float): Revenue
- avg_unit_price (float): Avg price

SQL: SELECT * FROM vw_sales_by_product_month WHERE product_category = 'Bikes'
"""

vw_sales_reasons_analysis_schema = """
VIEW: vw_sales_reasons_analysis
Purchase reasons aggregated

Columns:
- sales_reason_id (int): Reason ID
- reason_name (string): Reason description
- reason_type (string): Reason type
- order_count (int): Orders
- total_revenue (float): Revenue

SQL: SELECT * FROM vw_sales_reasons_analysis ORDER BY total_revenue DESC
"""

# ===== PRODUCTION VIEWS (7) =====

vw_products_master_schema = """
VIEW: vw_products_master
Complete product catalog with hierarchy

Columns:
- product_id (int): Product ID
- product_name (string): Product name
- product_number (string): SKU
- color (string): Color
- standard_cost, list_price (float): Pricing
- size, weight (string/float): Dimensions
- subcategory_id, product_subcategory (string): Subcategory
- category_id, product_category (string): Category
- model_id, model_name (string): Model info
- sell_start_date, sell_end_date, discontinued_date (datetime): Dates
- product_status (string): 'Active' or 'Discontinued'

SQL: SELECT * FROM vw_products_master WHERE product_category = 'Bikes'
"""

vw_inventory_current_schema = """
VIEW: vw_inventory_current
Current inventory levels by location

Columns:
- product_id (int): Product ID
- product_name (string): Product name
- location_id (int): Location ID
- location_name (string): Location name
- shelf, bin (string): Storage location
- quantity (int): Stock quantity

SQL: SELECT * FROM vw_inventory_current WHERE quantity < 10
"""

vw_work_orders_summary_schema = """
VIEW: vw_work_orders_summary
Manufacturing work orders

Columns:
- work_order_id (int): Work order ID
- product_id (int): Product ID
- product_name (string): Product name
- order_qty, stocked_qty, scrapped_qty (int): Quantities
- start_date, end_date, due_date (datetime): Dates
- scrap_reason_id, scrap_reason (string): Scrap info
- work_order_status (string): Status description

SQL: SELECT * FROM vw_work_orders_summary WHERE work_order_status = 'In Progress'
"""

vw_product_transactions_summary_schema = """
VIEW: vw_product_transactions_summary
Product transaction history aggregated by month

Columns:
- transaction_month (string): YYYY-MM
- product_id (int): Product ID
- product_name (string): Product name
- transaction_type (string): Transaction type
- transaction_count (int): Count
- total_quantity (int): Quantity
- total_cost (float): Cost

SQL: SELECT * FROM vw_product_transactions_summary WHERE transaction_month >= '2013-01'
"""

vw_manufacturing_costs_schema = """
VIEW: vw_manufacturing_costs
Cost analysis and margins

Columns:
- product_id (int): Product ID
- product_name (string): Product name
- current_standard_cost, current_list_price (float): Current pricing
- current_margin, current_margin_pct (float): Margin metrics
- cost_start_date, cost_end_date (datetime): Historical dates
- historical_cost (float): Historical cost

SQL: SELECT * FROM vw_manufacturing_costs WHERE current_margin_pct > 30
"""

vw_bill_of_materials_schema = """
VIEW: vw_bill_of_materials
Product structure and components

Columns:
- bom_id (int): BOM ID
- assembly_product_id, assembly_product_name (string): Assembly
- component_product_id, component_product_name (string): Component
- bom_level (int): BOM level
- per_assembly_qty (float): Quantity per assembly
- unit_measure (string): Unit
- start_date, end_date (datetime): Dates

SQL: SELECT * FROM vw_bill_of_materials WHERE assembly_product_name = 'Mountain-100'
"""

vw_product_reviews_schema = """
VIEW: vw_product_reviews
Customer product reviews

Columns:
- review_id (int): Review ID
- product_id (int): Product ID
- product_name (string): Product name
- reviewer_name (string): Reviewer
- review_date (datetime): Date
- email_address (string): Email
- rating (int): Rating 1-5
- comments (string): Comments

SQL: SELECT * FROM vw_product_reviews WHERE rating >= 4
"""

# ===== PURCHASING VIEWS (5) =====

vw_purchase_order_header_schema = """
VIEW: vw_purchase_order_header
Purchase order tracking

Columns:
- purchase_order_id (int): PO ID
- revision_number (int): Revision
- status (int): Status code
- status_name (string): Status description
- order_date, ship_date (datetime): Dates
- vendor_id (int): Vendor ID
- vendor_name (string): Vendor name
- ship_method_id, ship_method_name (string): Shipping
- subtotal, tax_amt, freight, total_due (float): Amounts

SQL: SELECT * FROM vw_purchase_order_header WHERE status_name = 'Pending'
"""

vw_purchase_order_detail_schema = """
VIEW: vw_purchase_order_detail
PO line items

Columns:
- purchase_order_id (int): PO ID
- purchase_order_detail_id (int): Line ID
- order_date, due_date (datetime): Dates
- product_id (int): Product ID
- product_name (string): Product name
- order_qty, received_qty, rejected_qty, stocked_qty (int): Quantities
- unit_price, line_total (float): Pricing
- vendor_id (int): Vendor ID
- vendor_name (string): Vendor name

SQL: SELECT * FROM vw_purchase_order_detail WHERE vendor_name = 'Litware'
"""

vw_vendors_master_schema = """
VIEW: vw_vendors_master
Vendor/supplier profiles

Columns:
- vendor_id (int): Vendor ID
- account_number (string): Account
- vendor_name (string): Name
- credit_rating (int): Credit rating 1-5
- preferred_vendor (bool): Preferred status
- active_flag (bool): Active flag
- vendor_status (string): 'Active' or 'Inactive'

SQL: SELECT * FROM vw_vendors_master WHERE preferred_vendor = 1
"""

vw_procurement_by_vendor_schema = """
VIEW: vw_procurement_by_vendor
Monthly vendor performance metrics

Columns:
- order_month (string): YYYY-MM
- vendor_id (int): Vendor ID
- vendor_name (string): Vendor name
- po_count (int): PO count
- total_spend (float): Total spend
- avg_po_value (float): Avg PO value
- total_quantity, total_received, total_rejected (int): Quantities

SQL: SELECT * FROM vw_procurement_by_vendor WHERE order_month >= '2013-01'
"""

vw_purchase_trends_monthly_schema = """
VIEW: vw_purchase_trends_monthly
Overall procurement trends

Columns:
- order_month (string): YYYY-MM
- po_count (int): PO count
- vendor_count (int): Vendor count
- total_spend (float): Total spend
- avg_po_value (float): Avg PO
- total_quantity (int): Total quantity

SQL: SELECT * FROM vw_purchase_trends_monthly ORDER BY order_month DESC
"""

# ===== HR VIEWS (4) =====

vw_employees_master_schema = """
VIEW: vw_employees_master
Employee profiles with department info

Columns:
- employee_id (int): Employee ID (BusinessEntityID)
- employee_name (string): Full name (FirstName + LastName)
- job_title (string): Job title
- department_name (string): Current department
- hire_date (datetime): Hire date

SQL: SELECT * FROM vw_employees_master WHERE job_title LIKE '%Manager%'
"""

vw_departments_master_schema = """
VIEW: vw_departments_master
Department organization structure

Columns:
- department_id (int): Department ID
- department_name (string): Department name
- group_name (string): Group name

SQL: SELECT * FROM vw_departments_master
"""

vw_employee_pay_history_schema = """
VIEW: vw_employee_pay_history
Compensation history (LIMITED - no Employee table)

Columns:
- employee_id (int): Employee ID
- rate_change_date (datetime): Change date
- rate (float): Pay rate
- pay_frequency (int): Frequency

SQL: SELECT * FROM vw_employee_pay_history
"""

vw_employee_dept_history_schema = """
VIEW: vw_employee_dept_history
Department movement history (LIMITED - no Employee table)

Columns:
- employee_id (int): Employee ID
- department_id (int): Department ID
- department_name (string): Department name
- shift_id (int): Shift ID
- shift_name (string): Shift name
- start_date, end_date (datetime): Dates

SQL: SELECT * FROM vw_employee_dept_history
"""

# ===== ALL SCHEMAS LIST =====

ALL_SCHEMAS = {
    # Sales (9)
    'vw_sales_order_header': vw_sales_order_header_schema,
    'vw_sales_order_detail': vw_sales_order_detail_schema,
    'vw_customers_master': vw_customers_master_schema,
    'vw_salesperson_master': vw_salesperson_master_schema,
    'vw_sales_territory_master': vw_sales_territory_master_schema,
    'vw_sales_by_territory_month': vw_sales_by_territory_month_schema,
    'vw_sales_by_salesperson_month': vw_sales_by_salesperson_month_schema,
    'vw_sales_by_product_month': vw_sales_by_product_month_schema,
    'vw_sales_reasons_analysis': vw_sales_reasons_analysis_schema,
    
    # Production (7)
    'vw_products_master': vw_products_master_schema,
    'vw_inventory_current': vw_inventory_current_schema,
    'vw_work_orders_summary': vw_work_orders_summary_schema,
    'vw_product_transactions_summary': vw_product_transactions_summary_schema,
    'vw_manufacturing_costs': vw_manufacturing_costs_schema,
    'vw_bill_of_materials': vw_bill_of_materials_schema,
    'vw_product_reviews': vw_product_reviews_schema,
    
    # Purchasing (5)
    'vw_purchase_order_header': vw_purchase_order_header_schema,
    'vw_purchase_order_detail': vw_purchase_order_detail_schema,
    'vw_vendors_master': vw_vendors_master_schema,
    'vw_procurement_by_vendor': vw_procurement_by_vendor_schema,
    'vw_purchase_trends_monthly': vw_purchase_trends_monthly_schema,
    
    # HR (4)
    'vw_employees_master': vw_employees_master_schema,
    'vw_departments_master': vw_departments_master_schema,
    'vw_employee_pay_history': vw_employee_pay_history_schema,
    'vw_employee_dept_history': vw_employee_dept_history_schema,
}
