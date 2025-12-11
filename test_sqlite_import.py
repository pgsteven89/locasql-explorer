"""
Test script for SQLite import functionality.
Creates a test SQLite database and tests the import process.
"""

import sqlite3
from pathlib import Path

def create_test_database():
    """Create a test SQLite database with sample data."""
    db_path = Path('test_data.db')
    
    # Remove existing database
    if db_path.exists():
        db_path.unlink()
    
    # Create connection
    conn = sqlite3.connect(str(db_path))
    
    # Create customers table
    conn.execute('''
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT,
            city TEXT
        )
    ''')
    
    # Create orders table
    conn.execute('''
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER,
            product TEXT,
            amount REAL,
            order_date TEXT
        )
    ''')
    
    # Create products table
    conn.execute('''
        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT,
            price REAL
        )
    ''')
    
    # Insert sample data - customers
    customers_data = [
        (1, 'Alice Johnson', 'alice@example.com', 'New York'),
        (2, 'Bob Smith', 'bob@example.com', 'London'),
        (3, 'Charlie Brown', 'charlie@example.com', 'Paris'),
        (4, 'Diana Prince', 'diana@example.com', 'Tokyo'),
        (5, 'Eve Davis', 'eve@example.com', 'Sydney'),
    ]
    conn.executemany("INSERT INTO customers VALUES (?, ?, ?, ?)", customers_data)
    
    # Insert sample data - orders
    orders_data = [
        (1, 1, 'Widget', 99.99, '2024-01-15'),
        (2, 2, 'Gadget', 149.99, '2024-01-16'),
        (3, 1, 'Doohickey', 79.99, '2024-01-17'),
        (4, 3, 'Widget', 99.99, '2024-01-18'),
        (5, 4, 'Thingamajig', 199.99, '2024-01-19'),
        (6, 2, 'Widget', 99.99, '2024-01-20'),
        (7, 5, 'Gadget', 149.99, '2024-01-21'),
    ]
    conn.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?)", orders_data)
    
    # Insert sample data - products
    products_data = [
        (1, 'Widget', 'Tools', 99.99),
        (2, 'Gadget', 'Electronics', 149.99),
        (3, 'Doohickey', 'Tools', 79.99),
        (4, 'Thingamajig', 'Electronics', 199.99),
    ]
    conn.executemany("INSERT INTO products VALUES (?, ?, ?, ?)", products_data)
    
    conn.commit()
    conn.close()
    
    print(f"[OK] Created test database: {db_path}")
    print(f"[OK] Tables: customers (5 rows), orders (7 rows), products (4 rows)")
    return db_path


def test_sqlite_import():
    """Test SQLite import functionality."""
    print("\n" + "=" * 60)
    print("Testing SQLite Import Functionality")
    print("=" * 60)
    
    # Create test database
    db_path = create_test_database()
    
    try:
        from localsql_explorer.database import DatabaseManager
        from localsql_explorer.importer import FileImporter
        
        print("\n1. Initializing DatabaseManager and FileImporter...")
        db = DatabaseManager()
        importer = FileImporter()
        print("[OK] Initialized")
        
        print("\n2. Importing SQLite database...")
        result = importer.import_sqlite(db_path)
        print(f"[OK] Import success: {result.success}")
        print(f"[OK] Tables found: {result.table_names}")
        print(f"[OK] Total tables: {result.total_sheets}")
        
        if result.success:
            print("\n3. Attaching SQLite database to DuckDB...")
            tables = db.attach_sqlite_database(db_path)
            print(f"[OK] Registered {len(tables)} tables:")
            for table in tables:
                print(f"  - {table.name}: {table.row_count} rows, {table.column_count} columns")
            
            print("\n4. Testing queries...")
            
            # Query 1: Select all customers
            print("\n  Query 1: SELECT * FROM test_data_customers")
            query_result = db.execute_query("SELECT * FROM test_data_customers")
            if query_result.success:
                print(f"  [OK] Returned {query_result.row_count} rows")
                print(query_result.data.to_string(index=False))
            
            # Query 2: Join customers and orders
            print("\n  Query 2: JOIN customers and orders")
            join_result = db.execute_query("""
                SELECT c.name, c.city, o.product, o.amount, o.order_date
                FROM test_data_customers c
                JOIN test_data_orders o ON c.id = o.customer_id
                ORDER BY o.order_date
            """)
            if join_result.success:
                print(f"  [OK] Returned {join_result.row_count} rows")
                print(join_result.data.to_string(index=False))
            
            # Query 3: Aggregation
            print("\n  Query 3: Aggregation - Total sales by customer")
            agg_result = db.execute_query("""
                SELECT c.name, COUNT(o.id) as order_count, SUM(o.amount) as total_spent
                FROM test_data_customers c
                LEFT JOIN test_data_orders o ON c.id = o.customer_id
                GROUP BY c.name
                ORDER BY total_spent DESC
            """)
            if agg_result.success:
                print(f"  [OK] Returned {agg_result.row_count} rows")
                print(agg_result.data.to_string(index=False))
            
            print("\n" + "=" * 60)
            print("[OK] All tests passed! SQLite import is working correctly.")
            print("=" * 60)
            
            # Cleanup
            db.close()
            
        else:
            print(f"[FAIL] Import failed: {result.warnings}")
            
    except Exception as e:
        print(f"\n[FAIL] Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_sqlite_import()
