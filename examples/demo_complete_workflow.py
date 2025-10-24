#!/usr/bin/env python3
"""
LocalSQL Explorer - Complete End-to-End Demo
Demonstrates the full workflow from GUI launch to data analysis
"""

import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
import pandas as pd

# Add the src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from localsql_explorer.ui.main_window import MainWindow

def run_demo():
    """Run a complete demo of LocalSQL Explorer functionality"""
    app = QApplication(sys.argv)
    app.setApplicationName("LocalSQL Explorer Demo")
    
    # Create main window
    window = MainWindow()
    
    print("🚀 LocalSQL Explorer Demo Starting...")
    print("=" * 50)
    
    # Create sample datasets for demo
    print("📊 Creating sample datasets...")
    
    # Sales data
    sales_data = pd.DataFrame({
        'sale_id': [1, 2, 3, 4, 5],
        'product_id': [101, 102, 101, 103, 102],
        'quantity': [2, 1, 3, 1, 2],
        'price': [25.00, 50.00, 25.00, 75.00, 50.00],
        'sale_date': ['2024-01-15', '2024-01-16', '2024-01-17', '2024-01-18', '2024-01-19']
    })
    sales_data.to_csv('demo_sales.csv', index=False)
    
    # Products data
    products_data = pd.DataFrame({
        'product_id': [101, 102, 103],
        'product_name': ['Widget A', 'Widget B', 'Widget C'],
        'category': ['Electronics', 'Electronics', 'Accessories'],
        'cost': [15.00, 30.00, 45.00]
    })
    products_data.to_excel('demo_products.xlsx', index=False)
    
    # Import first file
    print("\n📁 Importing sales data (CSV)...")
    sales_result = window.file_importer.import_file('demo_sales.csv')
    if sales_result.success:
        sales_metadata = window.db_manager.register_table(
            'sales', sales_result.dataframe, 'demo_sales.csv', 'csv'
        )
        window.table_list.add_table(sales_metadata)
        print(f"✅ Imported {sales_metadata.row_count} sales records")
    
    # Import second file
    print("\n📁 Importing products data (Excel)...")
    products_result = window.file_importer.import_file('demo_products.xlsx')
    if products_result.success:
        products_metadata = window.db_manager.register_table(
            'products', products_result.dataframe, 'demo_products.xlsx', 'xlsx'
        )
        window.table_list.add_table(products_metadata)
        print(f"✅ Imported {products_metadata.row_count} products")
    
    # Show available tables
    print(f"\n📋 Available tables: {len(window.table_list.get_all_tables())}")
    for table in window.table_list.get_all_tables():
        print(f"   • {table.name}: {table.row_count} rows, {len(table.columns)} columns")
    
    # Demo queries
    demo_queries = [
        {
            'name': 'Basic Sales Query',
            'sql': 'SELECT * FROM sales ORDER BY sale_date DESC',
            'description': 'Show all sales data ordered by date'
        },
        {
            'name': 'Product Catalog',
            'sql': 'SELECT * FROM products ORDER BY product_name',
            'description': 'Show all products'
        },
        {
            'name': 'Sales with Product Names (JOIN)',
            'sql': '''
                SELECT 
                    s.sale_id,
                    p.product_name,
                    s.quantity,
                    s.price,
                    s.sale_date,
                    (s.quantity * s.price) as total_amount
                FROM sales s
                JOIN products p ON s.product_id = p.product_id
                ORDER BY s.sale_date DESC
            ''',
            'description': 'Join sales and products to show detailed sales information'
        },
        {
            'name': 'Sales Summary by Product',
            'sql': '''
                SELECT 
                    p.product_name,
                    COUNT(*) as total_sales,
                    SUM(s.quantity) as total_quantity,
                    SUM(s.quantity * s.price) as total_revenue,
                    AVG(s.price) as avg_price
                FROM sales s
                JOIN products p ON s.product_id = p.product_id
                GROUP BY p.product_name
                ORDER BY total_revenue DESC
            ''',
            'description': 'Aggregate sales data by product'
        }
    ]
    
    print(f"\n🔍 Executing {len(demo_queries)} demo queries...")
    
    for i, query in enumerate(demo_queries, 1):
        print(f"\n{i}. {query['name']}")
        print(f"   {query['description']}")
        
        # Set SQL in editor
        window.sql_editor.set_sql(query['sql'].strip())
        
        # Execute query
        result = window.db_manager.execute_query(query['sql'].strip())
        
        if result.success:
            # Display results
            window.results_view.set_dataframe(result.data)
            print(f"   ✅ Success: {result.row_count} rows in {result.execution_time:.3f}s")
            print("   📊 Results:")
            print(result.data.to_string(index=False, max_rows=10, max_cols=10))
        else:
            print(f"   ❌ Error: {result.error}")
    
    # Final status
    print(f"\n🎯 Demo Summary:")
    print(f"   • Tables loaded: {len(window.table_list.get_all_tables())}")
    print(f"   • Results displayed: {window.results_view.has_data()}")
    print(f"   • Database connected: {window.db_manager is not None}")
    
    print(f"\n✨ LocalSQL Explorer is fully functional!")
    print(f"   You can now manually test the GUI by running:")
    print(f"   python -m localsql_explorer gui")
    
    # Cleanup and quit
    QTimer.singleShot(100, app.quit)
    app.exec()
    
    # Cleanup demo files
    for file in ['demo_sales.csv', 'demo_products.xlsx']:
        if os.path.exists(file):
            os.remove(file)
    
    return True

if __name__ == "__main__":
    run_demo()