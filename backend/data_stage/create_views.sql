-- Adventure Works OLTP - Denormalized Views
-- Creates 25 analytics-ready views for agent consumption

-- ===========================================
-- SALES VIEWS (9)
-- ===========================================

-- 1. vw_sales_order_header: Denormalized orders with customer, territory, salesperson
DROP VIEW IF EXISTS vw_sales_order_header;
CREATE VIEW vw_sales_order_header AS
SELECT 
    soh.SalesOrderID as sales_order_id,
    soh.RevisionNumber as revision_number,
    soh.OrderDate as order_date,
    soh.DueDate as due_date,
    soh.ShipDate as ship_date,
    soh.Status as status,
    CASE soh.Status
        WHEN 1 THEN 'In Process'
        WHEN 2 THEN 'Approved'
        WHEN 3 THEN 'Backordered'
        WHEN 4 THEN 'Rejected'
        WHEN 5 THEN 'Shipped'
        WHEN 6 THEN 'Cancelled'
        ELSE 'Unknown'
    END as status_name,
    soh.OnlineOrderFlag as online_order_flag,
    soh.SalesOrderNumber as sales_order_number,
    soh.PurchaseOrderNumber as purchase_order_number,
    soh.AccountNumber as account_number,
    soh.CustomerID as customer_id,
    COALESCE(p.FirstName || ' ' || p.LastName, s.Name) as customer_name,
    soh.SalesPersonID as salesperson_id,
    sp.FirstName || ' ' || sp.LastName as salesperson_name,
    soh.TerritoryID as territory_id,
    st.Name as territory_name,
    st.CountryRegionCode as territory_country,
    st."Group" as territory_group,
    soh.SubTotal as subtotal,
    soh.TaxAmt as tax_amt,
    soh.Freight as freight,
    soh.TotalDue as total_due,
    soh.Comment as comment
FROM Sales_SalesOrderHeader soh
LEFT JOIN Sales_Customer c ON soh.CustomerID = c.CustomerID
LEFT JOIN Person_Person p ON c.PersonID = p.BusinessEntityID
LEFT JOIN Sales_Store s ON c.StoreID = s.BusinessEntityID
LEFT JOIN Sales_SalesPerson sp_table ON soh.SalesPersonID = sp_table.BusinessEntityID
LEFT JOIN Person_Person sp ON sp_table.BusinessEntityID = sp.BusinessEntityID
LEFT JOIN Sales_SalesTerritory st ON soh.TerritoryID = st.TerritoryID;


-- 2. vw_sales_order_detail: Line items with product, category, order info
DROP VIEW IF EXISTS vw_sales_order_detail;
CREATE VIEW vw_sales_order_detail AS
SELECT 
    sod.SalesOrderID as sales_order_id,
    sod.SalesOrderDetailID as sales_order_detail_id,
    soh.OrderDate as order_date,
    sod.OrderQty as order_qty,
    sod.ProductID as product_id,
    p.Name as product_name,
    p.ProductNumber as product_number,
    ps.Name as product_subcategory,
    pc.Name as product_category,
    sod.UnitPrice as unit_price,
    sod.UnitPriceDiscount as unit_price_discount,
    sod.LineTotal as line_total,
    soh.CustomerID as customer_id,
    soh.TerritoryID as territory_id,
    st.Name as territory_name
FROM Sales_SalesOrderDetail sod
JOIN Sales_SalesOrderHeader soh ON sod.SalesOrderID = soh.SalesOrderID
JOIN Production_Product p ON sod.ProductID = p.ProductID
LEFT JOIN Production_ProductSubcategory ps ON p.ProductSubcategoryID = ps.ProductSubcategoryID
LEFT JOIN Production_ProductCategory pc ON ps.ProductCategoryID = pc.ProductCategoryID
LEFT JOIN Sales_SalesTerritory st ON soh.TerritoryID = st.TerritoryID;


-- 3. vw_customers_master: Complete customer profiles
DROP VIEW IF EXISTS vw_customers_master;
CREATE VIEW vw_customers_master AS
SELECT 
    c.CustomerID as customer_id,
    COALESCE(p.FirstName || ' ' || p.LastName, s.Name) as customer_name,
    CASE WHEN p.BusinessEntityID IS NOT NULL THEN 'Person' ELSE 'Store' END as customer_type,
    p.PersonType as person_type,
    p.Title as title,
    p.FirstName as first_name,
    p.LastName as last_name,
    s.Name as store_name,
    c.TerritoryID as territory_id,
    st.Name as territory_name,
    c.AccountNumber as account_number
FROM Sales_Customer c
LEFT JOIN Person_Person p ON c.PersonID = p.BusinessEntityID
LEFT JOIN Sales_Store s ON c.StoreID = s.BusinessEntityID
LEFT JOIN Sales_SalesTerritory st ON c.TerritoryID = st.TerritoryID;


-- 4. vw_salesperson_master: Sales rep profiles
DROP VIEW IF EXISTS vw_salesperson_master;
CREATE VIEW vw_salesperson_master AS
SELECT 
    sp.BusinessEntityID as salesperson_id,
    p.FirstName || ' ' || p.LastName as salesperson_name,
    sp.TerritoryID as territory_id,
    st.Name as territory_name,
    sp.SalesQuota as sales_quota,
    sp.Bonus as bonus,
    sp.CommissionPct as commission_pct,
    sp.SalesYTD as sales_ytd,
    sp.SalesLastYear as sales_last_year
FROM Sales_SalesPerson sp
JOIN Person_Person p ON sp.BusinessEntityID = p.BusinessEntityID
LEFT JOIN Sales_SalesTerritory st ON sp.TerritoryID = st.TerritoryID;


-- 5. vw_sales_territory_master: Territory reference
DROP VIEW IF EXISTS vw_sales_territory_master;
CREATE VIEW vw_sales_territory_master AS
SELECT 
    TerritoryID as territory_id,
    Name as territory_name,
    CountryRegionCode as country_code,
    "Group" as territory_group,
    SalesYTD as sales_ytd,
    SalesLastYear as sales_last_year,
    CostYTD as cost_ytd,
    CostLastYear as cost_last_year
FROM Sales_SalesTerritory;


-- 6. vw_sales_by_territory_month: Monthly territory metrics
DROP VIEW IF EXISTS vw_sales_by_territory_month;
CREATE VIEW vw_sales_by_territory_month AS
SELECT 
    strftime('%Y-%m', soh.OrderDate) as order_month,
    soh.TerritoryID as territory_id,
    st.Name as territory_name,
    st.CountryRegionCode as country_code,
    COUNT(DISTINCT soh.SalesOrderID) as order_count,
    SUM(soh.TotalDue) as total_revenue,
    AVG(soh.TotalDue) as avg_order_value,
    COUNT(DISTINCT soh.CustomerID) as unique_customers
FROM Sales_SalesOrderHeader soh
LEFT JOIN Sales_SalesTerritory st ON soh.TerritoryID = st.TerritoryID
GROUP BY strftime('%Y-%m', soh.OrderDate), soh.TerritoryID, st.Name, st.CountryRegionCode;


-- 7. vw_sales_by_salesperson_month: Monthly salesperson metrics
DROP VIEW IF EXISTS vw_sales_by_salesperson_month;
CREATE VIEW vw_sales_by_salesperson_month AS
SELECT 
    strftime('%Y-%m', soh.OrderDate) as order_month,
    soh.SalesPersonID as salesperson_id,
    p.FirstName || ' ' || p.LastName as salesperson_name,
    COUNT(DISTINCT soh.SalesOrderID) as order_count,
    SUM(soh.TotalDue) as total_revenue,
    AVG(soh.TotalDue) as avg_order_value,
    COUNT(DISTINCT soh.CustomerID) as unique_customers
FROM Sales_SalesOrderHeader soh
LEFT JOIN Person_Person p ON soh.SalesPersonID = p.BusinessEntityID
WHERE soh.SalesPersonID IS NOT NULL
GROUP BY strftime('%Y-%m', soh.OrderDate), soh.SalesPersonID, p.FirstName, p.LastName;


-- 8. vw_sales_by_product_month: Monthly product sales
DROP VIEW IF EXISTS vw_sales_by_product_month;
CREATE VIEW vw_sales_by_product_month AS
SELECT 
    strftime('%Y-%m', soh.OrderDate) as order_month,
    sod.ProductID as product_id,
    p.Name as product_name,
    ps.Name as product_subcategory,
    pc.Name as product_category,
    COUNT(DISTINCT sod.SalesOrderID) as order_count,
    SUM(sod.OrderQty) as total_quantity,
    SUM(sod.LineTotal) as total_revenue,
    AVG(sod.UnitPrice) as avg_unit_price
FROM Sales_SalesOrderDetail sod
JOIN Sales_SalesOrderHeader soh ON sod.SalesOrderID = soh.SalesOrderID
JOIN Production_Product p ON sod.ProductID = p.ProductID
LEFT JOIN Production_ProductSubcategory ps ON p.ProductSubcategoryID = ps.ProductSubcategoryID
LEFT JOIN Production_ProductCategory pc ON ps.ProductCategoryID = pc.ProductCategoryID
GROUP BY strftime('%Y-%m', soh.OrderDate), sod.ProductID, p.Name, ps.Name, pc.Name;


-- 9. vw_sales_reasons_analysis: Purchase reasons aggregated
DROP VIEW IF EXISTS vw_sales_reasons_analysis;
CREATE VIEW vw_sales_reasons_analysis AS
SELECT 
    sr.SalesReasonID as sales_reason_id,
    sr.Name as reason_name,
    sr.ReasonType as reason_type,
    COUNT(DISTINCT sosr.SalesOrderID) as order_count,
    SUM(soh.TotalDue) as total_revenue
FROM Sales_SalesReason sr
JOIN Sales_SalesOrderHeaderSalesReason sosr ON sr.SalesReasonID = sosr.SalesReasonID
JOIN Sales_SalesOrderHeader soh ON sosr.SalesOrderID = soh.SalesOrderID
GROUP BY sr.SalesReasonID, sr.Name, sr.ReasonType;


-- ===========================================
-- PRODUCTION VIEWS (7)
-- ===========================================

-- 10. vw_products_master: Complete product catalog
DROP VIEW IF EXISTS vw_products_master;
CREATE VIEW vw_products_master AS
SELECT 
    p.ProductID as product_id,
    p.Name as product_name,
    p.ProductNumber as product_number,
    p.Color as color,
    p.StandardCost as standard_cost,
    p.ListPrice as list_price,
    p.Size as size,
    p.Weight as weight,
    p.ProductSubcategoryID as subcategory_id,
    ps.Name as product_subcategory,
    pc.ProductCategoryID as category_id,
    pc.Name as product_category,
    pm.ProductModelID as model_id,
    pm.Name as model_name,
    p.SellStartDate as sell_start_date,
    p.SellEndDate as sell_end_date,
    p.DiscontinuedDate as discontinued_date,
    CASE WHEN p.DiscontinuedDate IS NULL THEN 'Active' ELSE 'Discontinued' END as product_status
FROM Production_Product p
LEFT JOIN Production_ProductSubcategory ps ON p.ProductSubcategoryID = ps.ProductSubcategoryID
LEFT JOIN Production_ProductCategory pc ON ps.ProductCategoryID = pc.ProductCategoryID
LEFT JOIN Production_ProductModel pm ON p.ProductModelID = pm.ProductModelID;


-- 11. vw_inventory_current: Current stock levels
DROP VIEW IF EXISTS vw_inventory_current;
CREATE VIEW vw_inventory_current AS
SELECT 
    pi.ProductID as product_id,
    p.Name as product_name,
    pi.LocationID as location_id,
    l.Name as location_name,
    pi.Shelf as shelf,
    pi.Bin as bin,
    pi.Quantity as quantity
FROM Production_ProductInventory pi
JOIN Production_Product p ON pi.ProductID = p.ProductID
JOIN Production_Location l ON pi.LocationID = l.LocationID;


-- 12. vw_work_orders_summary: Manufacturing orders
DROP VIEW IF EXISTS vw_work_orders_summary;
CREATE VIEW vw_work_orders_summary AS
SELECT 
    wo.WorkOrderID as work_order_id,
    wo.ProductID as product_id,
    p.Name as product_name,
    wo.OrderQty as order_qty,
    wo.StockedQty as stocked_qty,
    wo.ScrappedQty as scrapped_qty,
    wo.StartDate as start_date,
    wo.EndDate as end_date,
    wo.DueDate as due_date,
    wo.ScrapReasonID as scrap_reason_id,
    sr.Name as scrap_reason,
    CASE 
        WHEN wo.EndDate IS NULL THEN 'In Progress'
        WHEN wo.ScrappedQty > 0 THEN 'Completed with Scrap'
        ELSE 'Completed'
    END as work_order_status
FROM Production_WorkOrder wo
JOIN Production_Product p ON wo.ProductID = p.ProductID
LEFT JOIN Production_ScrapReason sr ON wo.ScrapReasonID = sr.ScrapReasonID;


-- 13. vw_product_transactions_summary: Transaction history aggregated by month
DROP VIEW IF EXISTS vw_product_transactions_summary;
CREATE VIEW vw_product_transactions_summary AS
SELECT 
    strftime('%Y-%m', th.TransactionDate) as transaction_month,
    th.ProductID as product_id,
    p.Name as product_name,
    th.TransactionType as transaction_type,
    COUNT(*) as transaction_count,
    SUM(th.Quantity) as total_quantity,
    SUM(th.ActualCost * th.Quantity) as total_cost
FROM Production_TransactionHistory th
JOIN Production_Product p ON th.ProductID = p.ProductID
GROUP BY strftime('%Y-%m', th.TransactionDate), th.ProductID, p.Name, th.TransactionType;


-- 14. vw_manufacturing_costs: Cost analysis over time
DROP VIEW IF EXISTS vw_manufacturing_costs;
CREATE VIEW vw_manufacturing_costs AS
SELECT 
    p.ProductID as product_id,
    p.Name as product_name,
    p.StandardCost as current_standard_cost,
    p.ListPrice as current_list_price,
    (p.ListPrice - p.StandardCost) as current_margin,
    CASE WHEN p.ListPrice > 0 THEN ((p.ListPrice - p.StandardCost) / p.ListPrice * 100) ELSE 0 END as current_margin_pct,
    pch.StartDate as cost_start_date,
    pch.EndDate as cost_end_date,
    pch.StandardCost as historical_cost
FROM Production_Product p
LEFT JOIN Production_ProductCostHistory pch ON p.ProductID = pch.ProductID;


-- 15. vw_bill_of_materials: Product structure
DROP VIEW IF EXISTS vw_bill_of_materials;
CREATE VIEW vw_bill_of_materials AS
SELECT 
    bom.BillOfMaterialsID as bom_id,
    bom.ProductAssemblyID as assembly_product_id,
    p1.Name as assembly_product_name,
    bom.ComponentID as component_product_id,
    p2.Name as component_product_name,
    bom.BOMLevel as bom_level,
    bom.PerAssemblyQty as per_assembly_qty,
    bom.UnitMeasureCode as unit_measure,
    bom.StartDate as start_date,
    bom.EndDate as end_date
FROM Production_BillOfMaterials bom
LEFT JOIN Production_Product p1 ON bom.ProductAssemblyID = p1.ProductID
JOIN Production_Product p2 ON bom.ComponentID = p2.ProductID;


-- 16. vw_product_reviews: Customer feedback
DROP VIEW IF EXISTS vw_product_reviews;
CREATE VIEW vw_product_reviews AS
SELECT 
    pr.ProductReviewID as review_id,
    pr.ProductID as product_id,
    p.Name as product_name,
    pr.ReviewerName as reviewer_name,
    pr.ReviewDate as review_date,
    pr.EmailAddress as email_address,
    pr.Rating as rating,
    pr.Comments as comments
FROM Production_ProductReview pr
JOIN Production_Product p ON pr.ProductID = p.ProductID;


-- ===========================================
-- PURCHASING VIEWS (5)
-- ===========================================

-- 17. vw_purchase_order_header: PO tracking
DROP VIEW IF EXISTS vw_purchase_order_header;
CREATE VIEW vw_purchase_order_header AS
SELECT 
    poh.PurchaseOrderID as purchase_order_id,
    poh.RevisionNumber as revision_number,
    poh.Status as status,
    CASE poh.Status
        WHEN 1 THEN 'Pending'
        WHEN 2 THEN 'Approved'
        WHEN 3 THEN 'Rejected'
        WHEN 4 THEN 'Complete'
        ELSE 'Unknown'
    END as status_name,
    poh.OrderDate as order_date,
    poh.ShipDate as ship_date,
    poh.VendorID as vendor_id,
    v.Name as vendor_name,
    poh.ShipMethodID as ship_method_id,
    sm.Name as ship_method_name,
    poh.SubTotal as subtotal,
    poh.TaxAmt as tax_amt,
    poh.Freight as freight,
    poh.TotalDue as total_due
FROM Purchasing_PurchaseOrderHeader poh
JOIN Purchasing_Vendor v ON poh.VendorID = v.BusinessEntityID
JOIN Purchasing_ShipMethod sm ON poh.ShipMethodID = sm.ShipMethodID;


-- 18. vw_purchase_order_detail: PO line items
DROP VIEW IF EXISTS vw_purchase_order_detail;
CREATE VIEW vw_purchase_order_detail AS
SELECT 
    pod.PurchaseOrderID as purchase_order_id,
    pod.PurchaseOrderDetailID as purchase_order_detail_id,
    poh.OrderDate as order_date,
    pod.DueDate as due_date,
    pod.ProductID as product_id,
    p.Name as product_name,
    pod.OrderQty as order_qty,
    pod.UnitPrice as unit_price,
    pod.LineTotal as line_total,
    pod.ReceivedQty as received_qty,
    pod.RejectedQty as rejected_qty,
    pod.StockedQty as stocked_qty,
    poh.VendorID as vendor_id,
    v.Name as vendor_name
FROM Purchasing_PurchaseOrderDetail pod
JOIN Purchasing_PurchaseOrderHeader poh ON pod.PurchaseOrderID = poh.PurchaseOrderID
JOIN Production_Product p ON pod.ProductID = p.ProductID
JOIN Purchasing_Vendor v ON poh.VendorID = v.BusinessEntityID;


-- 19. vw_vendors_master: Supplier profiles
DROP VIEW IF EXISTS vw_vendors_master;
CREATE VIEW vw_vendors_master AS
SELECT 
    v.BusinessEntityID as vendor_id,
    v.AccountNumber as account_number,
    v.Name as vendor_name,
    v.CreditRating as credit_rating,
    v.PreferredVendorStatus as preferred_vendor,
    v.ActiveFlag as active_flag,
    CASE WHEN v.ActiveFlag = 1 THEN 'Active' ELSE 'Inactive' END as vendor_status
FROM Purchasing_Vendor v;


-- 20. vw_procurement_by_vendor: Vendor performance metrics
DROP VIEW IF EXISTS vw_procurement_by_vendor;
CREATE VIEW vw_procurement_by_vendor AS
SELECT 
    strftime('%Y-%m', poh.OrderDate) as order_month,
    poh.VendorID as vendor_id,
    v.Name as vendor_name,
    COUNT(DISTINCT poh.PurchaseOrderID) as po_count,
    SUM(poh.TotalDue) as total_spend,
    AVG(poh.TotalDue) as avg_po_value,
    SUM(pod.OrderQty) as total_quantity,
    SUM(pod.ReceivedQty) as total_received,
    SUM(pod.RejectedQty) as total_rejected
FROM Purchasing_PurchaseOrderHeader poh
JOIN Purchasing_Vendor v ON poh.VendorID = v.BusinessEntityID
LEFT JOIN Purchasing_PurchaseOrderDetail pod ON poh.PurchaseOrderID = pod.PurchaseOrderID
GROUP BY strftime('%Y-%m', poh.OrderDate), poh.VendorID, v.Name;


-- 21. vw_purchase_trends_monthly: Procurement trends
DROP VIEW IF EXISTS vw_purchase_trends_monthly;
CREATE VIEW vw_purchase_trends_monthly AS
SELECT 
    strftime('%Y-%m', poh.OrderDate) as order_month,
    COUNT(DISTINCT poh.PurchaseOrderID) as po_count,
    COUNT(DISTINCT poh.VendorID) as vendor_count,
    SUM(poh.TotalDue) as total_spend,
    AVG(poh.TotalDue) as avg_po_value,
    SUM(pod.OrderQty) as total_quantity
FROM Purchasing_PurchaseOrderHeader poh
LEFT JOIN Purchasing_PurchaseOrderDetail pod ON poh.PurchaseOrderID = pod.PurchaseOrderID
GROUP BY strftime('%Y-%m', poh.OrderDate);


-- ===========================================
-- HR VIEWS (4)
-- ===========================================

-- Note: HumanResources_Employee table is missing, so HR views will be limited

-- 22. vw_employees_master: Employee profiles
DROP VIEW IF EXISTS vw_employees_master;
CREATE VIEW vw_employees_master AS
SELECT 
    e.BusinessEntityID as employee_id,
    p.FirstName || ' ' || p.LastName as employee_name,
    e.JobTitle as job_title,
    d.Name as department_name,
    e.HireDate as hire_date
FROM HumanResources_Employee AS e
LEFT JOIN Person_Person AS p ON e.BusinessEntityID = p.BusinessEntityID
LEFT JOIN HumanResources_EmployeeDepartmentHistory AS edh ON e.BusinessEntityID = edh.BusinessEntityID AND edh.EndDate IS NULL
LEFT JOIN HumanResources_Department AS d ON edh.DepartmentID = d.DepartmentID;


-- 23. vw_departments_master: Organization structure
DROP VIEW IF EXISTS vw_departments_master;
CREATE VIEW vw_departments_master AS
SELECT 
    d.DepartmentID as department_id,
    d.Name as department_name,
    d.GroupName as group_name
FROM HumanResources_Department d;


-- 24. vw_employee_pay_history: Compensation tracking (LIMITED - no Employee table)
DROP VIEW IF EXISTS vw_employee_pay_history;
CREATE VIEW vw_employee_pay_history AS
SELECT 
    eph.BusinessEntityID as employee_id,
    eph.RateChangeDate as rate_change_date,
    eph.Rate as rate,
    eph.PayFrequency as pay_frequency
FROM HumanResources_EmployeePayHistory eph;


-- 25. vw_employee_dept_history: Movement tracking (LIMITED - no Employee table)
DROP VIEW IF EXISTS vw_employee_dept_history;
CREATE VIEW vw_employee_dept_history AS
SELECT 
    edh.BusinessEntityID as employee_id,
    edh.DepartmentID as department_id,
    d.Name as department_name,
    edh.ShiftID as shift_id,
    s.Name as shift_name,
    edh.StartDate as start_date,
    edh.EndDate as end_date
FROM HumanResources_EmployeeDepartmentHistory edh
JOIN HumanResources_Department d ON edh.DepartmentID = d.DepartmentID
JOIN HumanResources_Shift s ON edh.ShiftID = s.ShiftID;

