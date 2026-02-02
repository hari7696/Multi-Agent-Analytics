"""
SQLite Database Importer for Adventure Works OLTP
Imports all CSV files into SQLite database with proper schema
"""

import sqlite3
import pandas as pd
from pathlib import Path
import logging
from typing import Dict, List

logger = logging.getLogger("fin_agent")


# Table mapping: table_name -> csv_filename
TABLES_MAP = {
    # Sales Schema
    'Sales_SalesOrderHeader': 'Sales_SalesOrderHeader.csv',
    'Sales_SalesOrderDetail': 'Sales_SalesOrderDetail.csv',
    'Sales_Customer': 'Sales_Customer.csv',
    'Sales_SalesPerson': 'Sales_SalesPerson.csv',
    'Sales_SalesTerritory': 'Sales_SalesTerritory.csv',
    'Sales_SalesOrderHeaderSalesReason': 'Sales_SalesOrderHeaderSalesReason.csv',
    'Sales_SalesReason': 'Sales_SalesReason.csv',
    'Sales_SalesPersonQuotaHistory': 'Sales_SalesPersonQuotaHistory.csv',
    'Sales_SalesTerritoryHistory': 'Sales_SalesTerritoryHistory.csv',
    'Sales_Store': 'Sales_Store.csv',
    'Sales_CreditCard': 'Sales_CreditCard.csv',
    'Sales_PersonCreditCard': 'Sales_PersonCreditCard.csv',
    'Sales_SpecialOffer': 'Sales_SpecialOffer.csv',
    'Sales_SpecialOfferProduct': 'Sales_SpecialOfferProduct.csv',
    'Sales_Currency': 'Sales_Currency.csv',
    'Sales_CurrencyRate': 'Sales_CurrencyRate.csv',
    'Sales_CountryRegionCurrency': 'Sales_CountryRegionCurrency.csv',
    'Sales_SalesTaxRate': 'Sales_SalesTaxRate.csv',
    'Sales_ShoppingCartItem': 'Sales_ShoppingCartItem.csv',
    
    # Production Schema
    'Production_Product': 'Production_Product.csv',
    'Production_ProductCategory': 'Production_ProductCategory.csv',
    'Production_ProductSubcategory': 'Production_ProductSubcategory.csv',
    'Production_ProductModel': 'Production_ProductModel.csv',
    'Production_ProductInventory': 'Production_ProductInventory.csv',
    'Production_WorkOrder': 'Production_WorkOrder.csv',
    'Production_WorkOrderRouting': 'Production_WorkOrderRouting.csv',
    'Production_TransactionHistory': 'Production_TransactionHistory.csv',
    'Production_TransactionHistoryArchive': 'Production_TransactionHistoryArchive.csv',
    'Production_ProductCostHistory': 'Production_ProductCostHistory.csv',
    'Production_ProductListPriceHistory': 'Production_ProductListPriceHistory.csv',
    'Production_BillOfMaterials': 'Production_BillOfMaterials.csv',
    'Production_ProductReview': 'Production_ProductReview.csv',
    'Production_ProductDescription': 'Production_ProductDescription.csv',
    'Production_ProductModelProductDescriptionCulture': 'Production_ProductModelProductDescriptionCulture.csv',
    'Production_ProductPhoto': 'Production_ProductPhoto.csv',
    'Production_ProductProductPhoto': 'Production_ProductProductPhoto.csv',
    'Production_ProductModelIllustration': 'Production_ProductModelIllustration.csv',
    'Production_Illustration': 'Production_Illustration.csv',
    'Production_Location': 'Production_Location.csv',
    'Production_ScrapReason': 'Production_ScrapReason.csv',
    'Production_Culture': 'Production_Culture.csv',
    'Production_UnitMeasure': 'Production_UnitMeasure.csv',
    
    # Purchasing Schema
    'Purchasing_PurchaseOrderHeader': 'Purchasing_PurchaseOrderHeader.csv',
    'Purchasing_PurchaseOrderDetail': 'Purchasing_PurchaseOrderDetail.csv',
    'Purchasing_Vendor': 'Purchasing_Vendor.csv',
    'Purchasing_ProductVendor': 'Purchasing_ProductVendor.csv',
    'Purchasing_ShipMethod': 'Purchasing_ShipMethod.csv',
    
    # HumanResources Schema
    'HumanResources_Employee': 'HumanResources_Employee.csv',
    'HumanResources_Department': 'HumanResources_Department.csv',
    'HumanResources_EmployeeDepartmentHistory': 'HumanResources_EmployeeDepartmentHistory.csv',
    'HumanResources_EmployeePayHistory': 'HumanResources_EmployeePayHistory.csv',
    'HumanResources_JobCandidate': 'HumanResources_JobCandidate.csv',
    'HumanResources_Shift': 'HumanResources_Shift.csv',
    
    # Person Schema
    'Person_Person': 'Person_Person.csv',
    'Person_BusinessEntity': 'Person_BusinessEntity.csv',
    'Person_BusinessEntityAddress': 'Person_BusinessEntityAddress.csv',
    'Person_BusinessEntityContact': 'Person_BusinessEntityContact.csv',
    'Person_Address': 'Person_Address.csv',
    'Person_AddressType': 'Person_AddressType.csv',
    'Person_StateProvince': 'Person_StateProvince.csv',
    'Person_CountryRegion': 'Person_CountryRegion.csv',
    'Person_EmailAddress': 'Person_EmailAddress.csv',
    'Person_PersonPhone': 'Person_PersonPhone.csv',
    'Person_PhoneNumberType': 'Person_PhoneNumberType.csv',
    'Person_ContactType': 'Person_ContactType.csv',
    'Person_Password': 'Person_Password.csv',
}


def create_database(force_recreate: bool = False) -> str:
    """
    Import all CSV files into SQLite database
    
    Args:
        force_recreate: If True, delete existing database and recreate
        
    Returns:
        Path to created database
    """
    data_folder = Path(__file__).parent / "data"
    db_path = data_folder / "adventureworks.db"
    
    # Check if database exists
    if db_path.exists():
        if force_recreate:
            logger.info("[SQLITE_IMPORTER] Deleting existing database")
            db_path.unlink()
        else:
            logger.info(f"[SQLITE_IMPORTER] Database already exists at {db_path}")
            return str(db_path)
    
    logger.info(f"[SQLITE_IMPORTER] Creating new database at {db_path}")
    conn = sqlite3.connect(db_path)
    
    tables_imported = 0
    tables_failed = 0
    
    for table_name, csv_file in TABLES_MAP.items():
        csv_path = data_folder / csv_file
        
        if not csv_path.exists():
            logger.warning(f"[SQLITE_IMPORTER] CSV file not found: {csv_file}")
            tables_failed += 1
            continue
        
        try:
            logger.info(f"[SQLITE_IMPORTER] Importing {table_name} from {csv_file}")
            
            # Read CSV with low_memory=False to handle mixed types
            df = pd.read_csv(csv_path, low_memory=False)
            
            # Import to SQLite
            df.to_sql(table_name, conn, if_exists='replace', index=False)
            
            row_count = len(df)
            col_count = len(df.columns)
            logger.info(f"[SQLITE_IMPORTER] ✓ {table_name}: {row_count} rows, {col_count} columns")
            tables_imported += 1
            
        except Exception as e:
            logger.error(f"[SQLITE_IMPORTER] ✗ Failed to import {table_name}: {e}")
            tables_failed += 1
    
    conn.close()
    
    logger.info(f"[SQLITE_IMPORTER] Database creation complete:")
    logger.info(f"[SQLITE_IMPORTER]   Tables imported: {tables_imported}")
    logger.info(f"[SQLITE_IMPORTER]   Tables failed: {tables_failed}")
    logger.info(f"[SQLITE_IMPORTER]   Database location: {db_path}")
    
    return str(db_path)


def create_indexes(db_path: str = None):
    """Create indexes on primary keys and foreign keys for performance"""
    if db_path is None:
        db_path = Path(__file__).parent / "data" / "adventureworks.db"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    logger.info("[SQLITE_IMPORTER] Creating indexes...")
    
    # Define key indexes for major tables
    indexes = [
        # Sales indexes
        "CREATE INDEX IF NOT EXISTS idx_sales_order_header_customer ON Sales_SalesOrderHeader(CustomerID)",
        "CREATE INDEX IF NOT EXISTS idx_sales_order_header_date ON Sales_SalesOrderHeader(OrderDate)",
        "CREATE INDEX IF NOT EXISTS idx_sales_order_header_salesperson ON Sales_SalesOrderHeader(SalesPersonID)",
        "CREATE INDEX IF NOT EXISTS idx_sales_order_header_territory ON Sales_SalesOrderHeader(TerritoryID)",
        "CREATE INDEX IF NOT EXISTS idx_sales_order_detail_order ON Sales_SalesOrderDetail(SalesOrderID)",
        "CREATE INDEX IF NOT EXISTS idx_sales_order_detail_product ON Sales_SalesOrderDetail(ProductID)",
        
        # Production indexes
        "CREATE INDEX IF NOT EXISTS idx_product_subcategory ON Production_Product(ProductSubcategoryID)",
        "CREATE INDEX IF NOT EXISTS idx_product_model ON Production_Product(ProductModelID)",
        "CREATE INDEX IF NOT EXISTS idx_product_inventory_product ON Production_ProductInventory(ProductID)",
        "CREATE INDEX IF NOT EXISTS idx_work_order_product ON Production_WorkOrder(ProductID)",
        "CREATE INDEX IF NOT EXISTS idx_transaction_history_product ON Production_TransactionHistory(ProductID)",
        
        # Purchasing indexes
        "CREATE INDEX IF NOT EXISTS idx_po_header_vendor ON Purchasing_PurchaseOrderHeader(VendorID)",
        "CREATE INDEX IF NOT EXISTS idx_po_detail_order ON Purchasing_PurchaseOrderDetail(PurchaseOrderID)",
        "CREATE INDEX IF NOT EXISTS idx_po_detail_product ON Purchasing_PurchaseOrderDetail(ProductID)",
        
        # Person indexes
        "CREATE INDEX IF NOT EXISTS idx_person_business_entity ON Person_Person(BusinessEntityID)",
        "CREATE INDEX IF NOT EXISTS idx_address_state ON Person_Address(StateProvinceID)",
        "CREATE INDEX IF NOT EXISTS idx_business_entity_address ON Person_BusinessEntityAddress(BusinessEntityID)",
        
        # HR indexes
        "CREATE INDEX IF NOT EXISTS idx_employee_business_entity ON HumanResources_Employee(BusinessEntityID)",
        "CREATE INDEX IF NOT EXISTS idx_emp_dept_history_emp ON HumanResources_EmployeeDepartmentHistory(BusinessEntityID)",
        "CREATE INDEX IF NOT EXISTS idx_emp_dept_history_dept ON HumanResources_EmployeeDepartmentHistory(DepartmentID)",
    ]
    
    for index_sql in indexes:
        try:
            cursor.execute(index_sql)
            logger.debug(f"[SQLITE_IMPORTER] Created index: {index_sql[:50]}...")
        except Exception as e:
            logger.warning(f"[SQLITE_IMPORTER] Failed to create index: {e}")
    
    conn.commit()
    conn.close()
    
    logger.info(f"[SQLITE_IMPORTER] Created {len(indexes)} indexes")


def get_table_info(db_path: str = None) -> Dict[str, Dict]:
    """Get information about all tables in the database"""
    if db_path is None:
        db_path = Path(__file__).parent / "data" / "adventureworks.db"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get list of tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    
    table_info = {}
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        row_count = cursor.fetchone()[0]
        
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        
        table_info[table] = {
            'rows': row_count,
            'columns': len(columns),
            'column_names': columns
        }
    
    conn.close()
    return table_info


if __name__ == "__main__":
    # For testing/standalone execution
    logging.basicConfig(level=logging.INFO)
    
    print("=== Adventure Works SQLite Importer ===\n")
    
    # Create database
    db_path = create_database(force_recreate=False)
    
    # Create indexes
    create_indexes(db_path)
    
    # Show summary
    print("\n=== Database Summary ===")
    table_info = get_table_info(db_path)
    
    total_rows = sum(info['rows'] for info in table_info.values())
    print(f"Total tables: {len(table_info)}")
    print(f"Total rows: {total_rows:,}")
    
    print("\nTables by schema:")
    schemas = {}
    for table_name, info in table_info.items():
        schema = table_name.split('_')[0]
        if schema not in schemas:
            schemas[schema] = []
        schemas[schema].append((table_name, info['rows']))
    
    for schema, tables in sorted(schemas.items()):
        schema_rows = sum(rows for _, rows in tables)
        print(f"\n{schema}: {len(tables)} tables, {schema_rows:,} rows")
        for table_name, rows in sorted(tables, key=lambda x: x[1], reverse=True)[:5]:
            print(f"  - {table_name}: {rows:,} rows")

