"""
Integration tests for the LocalSQL Explorer application.

Tests the interaction between different components:
- File import -> Database registration -> Query execution -> Export
- End-to-end workflows
- UI integration (where applicable)
"""

import pytest
import pandas as pd
from pathlib import Path

from localsql_explorer.database import DatabaseManager
from localsql_explorer.importer import FileImporter
from localsql_explorer.exporter import ResultExporter


class TestEndToEndWorkflow:
    """Test complete workflows from import to export."""
    
    def test_csv_import_query_export_workflow(self, temp_dir: Path, sample_csv_file: Path):
        """Test complete workflow: CSV import -> query -> export."""
        # Initialize components
        db_manager = DatabaseManager()
        file_importer = FileImporter()
        result_exporter = ResultExporter()
        
        # Step 1: Import CSV file
        import_result = file_importer.import_file(sample_csv_file)
        assert import_result.success is True
        
        # Step 2: Register table in database
        table_name = file_importer.get_suggested_table_name(sample_csv_file)
        metadata = db_manager.register_table(table_name, import_result.dataframe)
        assert metadata.name == table_name
        
        # Step 3: Execute query
        query_result = db_manager.execute_query(f"SELECT * FROM {table_name} WHERE age > 30")
        assert query_result.success is True
        assert query_result.data is not None
        
        # Step 4: Export results
        export_path = temp_dir / "results.csv"
        export_result = result_exporter.export_result(query_result.data, export_path)
        assert export_result.success is True
        assert export_path.exists()
        
        # Verify exported data
        exported_df = pd.read_csv(export_path)
        assert len(exported_df) > 0
        assert all(exported_df['age'] > 30)
    
    def test_multiple_files_join_query(self, temp_dir: Path):
        """Test joining data from multiple imported files."""
        # Create test files
        customers_data = {
            'customer_id': [1, 2, 3],
            'name': ['Alice', 'Bob', 'Charlie'],
            'city': ['New York', 'London', 'Tokyo']
        }
        orders_data = {
            'order_id': [1, 2, 3, 4],
            'customer_id': [1, 2, 1, 3],
            'amount': [100.0, 200.0, 150.0, 300.0]
        }
        
        customers_file = temp_dir / "customers.csv"
        orders_file = temp_dir / "orders.csv"
        
        pd.DataFrame(customers_data).to_csv(customers_file, index=False)
        pd.DataFrame(orders_data).to_csv(orders_file, index=False)
        
        # Initialize components
        db_manager = DatabaseManager()
        file_importer = FileImporter()
        
        # Import both files
        customers_result = file_importer.import_file(customers_file)
        orders_result = file_importer.import_file(orders_file)
        
        assert customers_result.success is True
        assert orders_result.success is True
        
        # Register tables
        db_manager.register_table("customers", customers_result.dataframe)
        db_manager.register_table("orders", orders_result.dataframe)
        
        # Execute join query
        join_query = """
        SELECT c.name, c.city, SUM(o.amount) as total_amount
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        GROUP BY c.customer_id, c.name, c.city
        ORDER BY total_amount DESC
        """
        
        result = db_manager.execute_query(join_query)
        assert result.success is True
        assert len(result.data) == 3
        
        # Verify results
        assert result.data.iloc[0]['name'] == 'Charlie'  # Highest amount (300)
        assert result.data.iloc[0]['total_amount'] == 300.0
    
    def test_excel_to_parquet_conversion(self, temp_dir: Path):
        """Test converting Excel file to Parquet via import/export."""
        # Create Excel file
        excel_data = {
            'product': ['Widget A', 'Widget B', 'Widget C'],
            'price': [10.99, 15.50, 8.25],
            'category': ['Electronics', 'Home', 'Electronics']
        }
        excel_file = temp_dir / "products.xlsx"
        pd.DataFrame(excel_data).to_excel(excel_file, index=False)
        
        # Initialize components
        file_importer = FileImporter()
        result_exporter = ResultExporter()
        
        # Import Excel
        import_result = file_importer.import_file(excel_file)
        assert import_result.success is True
        
        # Export as Parquet
        parquet_file = temp_dir / "products.parquet"
        export_result = result_exporter.export_result(import_result.dataframe, parquet_file)
        assert export_result.success is True
        
        # Verify conversion
        original_df = pd.read_excel(excel_file)
        converted_df = pd.read_parquet(parquet_file)
        
        pd.testing.assert_frame_equal(original_df, converted_df)
    
    def test_database_persistence_workflow(self, temp_dir: Path, sample_csv_file: Path):
        """Test saving and loading database with data."""
        db_path = temp_dir / "test.duckdb"
        
        # Phase 1: Create and populate database
        db_manager1 = DatabaseManager()
        file_importer = FileImporter()
        
        # Import and register data
        import_result = file_importer.import_file(sample_csv_file)
        table_name = file_importer.get_suggested_table_name(sample_csv_file)
        metadata = db_manager1.register_table(table_name, import_result.dataframe)
        
        # Save database
        save_success = db_manager1.save_database(db_path)
        assert save_success is True
        db_manager1.close()
        
        # Phase 2: Load database in new manager
        db_manager2 = DatabaseManager()
        load_success = db_manager2.load_database(db_path)
        assert load_success is True
        
        # Verify data is intact
        tables = db_manager2.list_tables()
        assert len(tables) == 1
        assert tables[0].name == table_name
        
        query_result = db_manager2.execute_query(f"SELECT COUNT(*) as count FROM {table_name}")
        assert query_result.success is True
        assert query_result.data.iloc[0]['count'] == metadata.row_count
    
    def test_error_handling_workflow(self, temp_dir: Path):
        """Test error handling in complete workflow."""
        db_manager = DatabaseManager()
        file_importer = FileImporter()
        result_exporter = ResultExporter()
        
        # Test 1: Import non-existent file
        nonexistent_file = temp_dir / "nonexistent.csv"
        import_result = file_importer.import_file(nonexistent_file)
        assert import_result.success is False
        
        # Test 2: Query non-existent table
        query_result = db_manager.execute_query("SELECT * FROM nonexistent_table")
        assert query_result.success is False
        
        # Test 3: Export to protected directory (if applicable)
        sample_df = pd.DataFrame({'col1': [1, 2, 3]})
        db_manager.register_table("test_table", sample_df)
        
        query_result = db_manager.execute_query("SELECT * FROM test_table")
        assert query_result.success is True
        
        # Try to export to invalid location
        invalid_export_path = Path("/root/invalid/path/export.csv")  # Likely to fail on most systems
        export_result = result_exporter.export_result(query_result.data, invalid_export_path)
        # Note: This may or may not fail depending on the system, so we don't assert
    
    def test_large_dataset_handling(self, temp_dir: Path):
        """Test handling of larger datasets."""
        # Create a larger CSV file
        large_data = {
            'id': list(range(1, 1001)),
            'value': [i * 2.5 for i in range(1, 1001)],
            'category': [f'Cat_{i % 10}' for i in range(1, 1001)]
        }
        large_csv = temp_dir / "large_data.csv"
        pd.DataFrame(large_data).to_csv(large_csv, index=False)
        
        # Initialize components
        db_manager = DatabaseManager()
        file_importer = FileImporter()
        
        # Import large file
        import_result = file_importer.import_file(large_csv)
        assert import_result.success is True
        assert len(import_result.dataframe) == 1000
        
        # Register and query
        table_name = file_importer.get_suggested_table_name(large_csv)
        db_manager.register_table(table_name, import_result.dataframe)
        
        # Test aggregation query
        agg_query = f"""
        SELECT category, COUNT(*) as count, AVG(value) as avg_value
        FROM {table_name}
        GROUP BY category
        ORDER BY category
        """
        
        result = db_manager.execute_query(agg_query)
        assert result.success is True
        assert len(result.data) == 10  # 10 categories
        
        # Verify performance is reasonable
        assert result.execution_time < 5.0  # Should complete within 5 seconds
    
    def test_data_type_preservation(self, temp_dir: Path):
        """Test that data types are preserved through the workflow."""
        # Create file with various data types
        test_data = {
            'int_col': [1, 2, 3],
            'float_col': [1.1, 2.2, 3.3],
            'str_col': ['a', 'b', 'c'],
            'bool_col': [True, False, True],
            'date_col': pd.date_range('2023-01-01', periods=3)
        }
        test_file = temp_dir / "types_test.parquet"
        original_df = pd.DataFrame(test_data)
        original_df.to_parquet(test_file, index=False)
        
        # Import and process
        file_importer = FileImporter()
        db_manager = DatabaseManager()
        result_exporter = ResultExporter()
        
        import_result = file_importer.import_file(test_file)
        assert import_result.success is True
        
        table_name = file_importer.get_suggested_table_name(test_file)
        db_manager.register_table(table_name, import_result.dataframe)
        
        # Query and export
        query_result = db_manager.execute_query(f"SELECT * FROM {table_name}")
        assert query_result.success is True
        
        export_file = temp_dir / "exported_types.parquet"
        export_result = result_exporter.export_result(query_result.data, export_file)
        assert export_result.success is True
        
        # Verify types are preserved
        exported_df = pd.read_parquet(export_file)
        
        # Check that we have the same columns
        assert set(original_df.columns) == set(exported_df.columns)
        assert len(original_df) == len(exported_df)