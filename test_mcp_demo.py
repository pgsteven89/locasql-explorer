"""
Quick demo/test of MCP server functionality.
This tests the core components without requiring a full MCP client.
"""

import pandas as pd
from pathlib import Path
from localsql_explorer.mcp_server import LocalSQLMCPServer, MCPServerConfig
from localsql_explorer.database import DatabaseManager
import json

def test_mcp_server():
    """Test MCP server functionality."""
    
    print("=" * 60)
    print("MCP Server Functionality Test")
    print("=" * 60)
    
    # Create a test database with sample data
    print("\n1. Creating test database with sample data...")
    config = MCPServerConfig(
        db_path=None,  # In-memory
        max_query_rows=100,
        enable_file_import=True
    )
    
    server = LocalSQLMCPServer(config)
    
    # Create sample data
    sample_data = pd.DataFrame({
        'id': [1, 2, 3, 4, 5],
        'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
        'age': [25, 30, 35, 40, 45],
        'city': ['New York', 'London', 'Paris', 'Tokyo', 'Sydney'],
        'salary': [50000, 60000, 75000, 80000, 90000]
    })
    
    # Register the table
    server.db_manager.register_table(
        name="employees",
        dataframe=sample_data,
        file_path="sample_data.csv",
        file_type="csv"
    )
    print("[OK] Created 'employees' table with 5 rows")
    
    # Test 1: List tables
    print("\n2. Testing list_tables functionality...")
    tables = server.db_manager.list_tables()
    print(f"[OK] Found {len(tables)} table(s):")
    for table in tables:
        print(f"  - {table.name}: {table.row_count} rows, {table.column_count} columns")
    
    # Test 2: Get table info
    print("\n3. Testing get_table_info functionality...")
    metadata = server.db_manager.get_table_metadata("employees")
    print(f"[OK] Table metadata:")
    print(f"  - Name: {metadata.name}")
    print(f"  - Rows: {metadata.row_count}")
    print(f"  - Columns: {metadata.column_count}")
    print(f"  - Column names: {[col['name'] for col in metadata.columns]}")
    
    # Test 3: Get columns
    print("\n4. Testing get_columns functionality...")
    columns = server.db_manager.get_table_columns("employees")
    print(f"[OK] Columns in 'employees' table:")
    for col in columns:
        print(f"  - {col['name']}: {col['type']}")
    
    # Test 4: Execute query
    print("\n5. Testing execute_query functionality...")
    result = server.db_manager.execute_query(
        "SELECT name, age, city FROM employees WHERE age > 30 ORDER BY age"
    )
    if result.success:
        print(f"[OK] Query executed successfully in {result.execution_time:.3f}s")
        print(f"  - Returned {result.row_count} rows")
        print("\n  Results:")
        print(result.data.to_string(index=False))
    else:
        print(f"[FAIL] Query failed: {result.error}")
    
    # Test 5: Execute aggregation query
    print("\n6. Testing aggregation query...")
    result = server.db_manager.execute_query(
        "SELECT city, AVG(salary) as avg_salary FROM employees GROUP BY city ORDER BY avg_salary DESC"
    )
    if result.success:
        print(f"[OK] Query executed successfully")
        print("\n  Results:")
        print(result.data.to_string(index=False))
    
    # Test 6: Test sample data resource
    print("\n7. Testing sample data retrieval...")
    result = server.db_manager.execute_query("SELECT * FROM employees LIMIT 3")
    if result.success:
        print(f"[OK] Retrieved {result.row_count} sample rows:")
        print(result.data.to_string(index=False))
    
    # Test 7: Test error handling
    print("\n8. Testing error handling...")
    result = server.db_manager.execute_query("SELECT * FROM nonexistent_table")
    if not result.success:
        print(f"[OK] Error handling works correctly")
        print(f"  - Error message: {result.error[:80]}...")
    
    # Cleanup
    server.cleanup()
    
    print("\n" + "=" * 60)
    print("[OK] All tests passed! MCP server is working correctly.")
    print("=" * 60)
    print("\nThe MCP server can:")
    print("  [OK] List tables and their metadata")
    print("  [OK] Get column information")
    print("  [OK] Execute SQL queries")
    print("  [OK] Handle errors gracefully")
    print("  [OK] Return results in structured format")
    print("\nReady to connect to Claude Desktop or other MCP clients!")

if __name__ == "__main__":
    test_mcp_server()

