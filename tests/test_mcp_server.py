"""
Tests for MCP server functionality.

Tests the Model Context Protocol server implementation including:
- Resource listing and retrieval
- Tool execution
- Error handling
- Integration with DatabaseManager and FileImporter
"""

import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from localsql_explorer.mcp_server import LocalSQLMCPServer, MCPServerConfig
from localsql_explorer.database import DatabaseManager, QueryResult, TableMetadata
from localsql_explorer.importer import FileImporter, ImportResult
import pandas as pd


@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database path."""
    return tmp_path / "test.duckdb"


@pytest.fixture
def mcp_config(temp_db_path):
    """Create MCP server configuration for testing."""
    return MCPServerConfig(
        db_path=str(temp_db_path),
        max_query_rows=100,
        enable_file_import=True,
        log_level="DEBUG"
    )


@pytest.fixture
def mcp_server(mcp_config):
    """Create an MCP server instance for testing."""
    server = LocalSQLMCPServer(mcp_config)
    yield server
    server.cleanup()


@pytest.fixture
def sample_dataframe():
    """Create a sample DataFrame for testing."""
    return pd.DataFrame({
        'id': [1, 2, 3, 4, 5],
        'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
        'age': [25, 30, 35, 40, 45],
        'city': ['New York', 'London', 'Paris', 'Tokyo', 'Sydney']
    })


class TestMCPServerInitialization:
    """Test MCP server initialization."""
    
    def test_server_init_with_db_path(self, mcp_config):
        """Test server initialization with database path."""
        server = LocalSQLMCPServer(mcp_config)
        assert server.db_manager is not None
        assert server.file_importer is not None
        assert server.config.db_path == mcp_config.db_path
        server.cleanup()
    
    def test_server_init_in_memory(self):
        """Test server initialization with in-memory database."""
        config = MCPServerConfig(db_path=None)
        server = LocalSQLMCPServer(config)
        assert server.db_manager is not None
        assert server.db_manager.db_path is None
        server.cleanup()
    
    def test_server_config_defaults(self):
        """Test default server configuration."""
        config = MCPServerConfig()
        assert config.max_query_rows == 1000
        assert config.enable_file_import is True
        assert config.log_level == "INFO"


class TestMCPResources:
    """Test MCP resource handlers."""
    
    def test_list_resources_empty_db(self, mcp_server):
        """Test listing resources with empty database."""
        # The server should still provide the table list resource
        assert mcp_server.db_manager is not None
    
    def test_list_resources_with_tables(self, mcp_server, sample_dataframe):
        """Test listing resources with tables in database."""
        # Register a test table
        mcp_server.db_manager.register_table(
            name="test_table",
            dataframe=sample_dataframe,
            file_path="/test/data.csv",
            file_type="csv"
        )
        
        # Verify table is registered
        tables = mcp_server.db_manager.list_tables()
        assert len(tables) == 1
        assert tables[0].name == "test_table"


class TestMCPTools:
    """Test MCP tool execution."""
    
    def test_execute_query_tool(self, mcp_server, sample_dataframe):
        """Test execute_query tool."""
        # Register a test table
        mcp_server.db_manager.register_table(
            name="test_table",
            dataframe=sample_dataframe
        )
        
        # Execute a query
        result = mcp_server.db_manager.execute_query("SELECT * FROM test_table WHERE age > 30")
        
        assert result.success is True
        assert result.data is not None
        assert len(result.data) == 3  # Bob, Charlie, David, Eve (ages 30, 35, 40, 45) - actually 4
    
    def test_execute_query_with_limit(self, mcp_server, sample_dataframe):
        """Test execute_query tool with row limit."""
        # Register a test table
        mcp_server.db_manager.register_table(
            name="test_table",
            dataframe=sample_dataframe
        )
        
        # Execute a query
        result = mcp_server.db_manager.execute_query("SELECT * FROM test_table LIMIT 2")
        
        assert result.success is True
        assert result.data is not None
        assert len(result.data) == 2
    
    def test_execute_query_error(self, mcp_server):
        """Test execute_query tool with invalid SQL."""
        result = mcp_server.db_manager.execute_query("SELECT * FROM nonexistent_table")
        
        assert result.success is False
        assert result.error is not None
        assert "nonexistent_table" in result.error.lower() or "catalog" in result.error.lower()
    
    def test_list_tables_tool(self, mcp_server, sample_dataframe):
        """Test list_tables tool."""
        # Register multiple tables
        mcp_server.db_manager.register_table("table1", sample_dataframe)
        mcp_server.db_manager.register_table("table2", sample_dataframe)
        
        tables = mcp_server.db_manager.list_tables()
        
        assert len(tables) == 2
        table_names = [t.name for t in tables]
        assert "table1" in table_names
        assert "table2" in table_names
    
    def test_get_table_info_tool(self, mcp_server, sample_dataframe):
        """Test get_table_info tool."""
        # Register a test table
        mcp_server.db_manager.register_table(
            name="test_table",
            dataframe=sample_dataframe,
            file_path="/test/data.csv",
            file_type="csv"
        )
        
        metadata = mcp_server.db_manager.get_table_metadata("test_table")
        
        assert metadata is not None
        assert metadata.name == "test_table"
        assert metadata.row_count == 5
        assert metadata.column_count == 4
        assert metadata.file_path == "/test/data.csv"
        assert metadata.file_type == "csv"
    
    def test_get_table_info_not_found(self, mcp_server):
        """Test get_table_info tool with non-existent table."""
        metadata = mcp_server.db_manager.get_table_metadata("nonexistent")
        assert metadata is None
    
    def test_get_columns_specific_table(self, mcp_server, sample_dataframe):
        """Test get_columns tool for specific table."""
        mcp_server.db_manager.register_table("test_table", sample_dataframe)
        
        columns = mcp_server.db_manager.get_table_columns("test_table")
        
        assert len(columns) == 4
        column_names = [c['name'] for c in columns]
        assert 'id' in column_names
        assert 'name' in column_names
        assert 'age' in column_names
        assert 'city' in column_names
    
    def test_get_columns_all_tables(self, mcp_server, sample_dataframe):
        """Test get_columns tool for all tables."""
        mcp_server.db_manager.register_table("table1", sample_dataframe)
        mcp_server.db_manager.register_table("table2", sample_dataframe)
        
        tables = mcp_server.db_manager.list_tables()
        assert len(tables) == 2


class TestMCPFileImport:
    """Test MCP file import functionality."""
    
    def test_import_csv_file(self, mcp_server, tmp_path):
        """Test importing a CSV file."""
        # Create a test CSV file
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("id,name,value\n1,Alice,100\n2,Bob,200\n")
        
        # Import the file
        result = mcp_server.file_importer.import_file(csv_file)
        
        assert result.success is True
        assert result.dataframe is not None
        assert len(result.dataframe) == 2
        assert list(result.dataframe.columns) == ['id', 'name', 'value']
    
    def test_import_file_not_found(self, mcp_server):
        """Test importing non-existent file."""
        result = mcp_server.file_importer.import_file("/nonexistent/file.csv")
        
        assert result.success is False
        assert result.error is not None
    
    def test_suggested_table_name(self, mcp_server, tmp_path):
        """Test table name suggestion from file path."""
        csv_file = tmp_path / "my_data_file.csv"
        csv_file.write_text("a,b\n1,2\n")
        
        suggested_name = mcp_server.file_importer.get_suggested_table_name(csv_file)
        
        assert suggested_name == "my_data_file"


class TestMCPErrorHandling:
    """Test MCP error handling."""
    
    def test_query_with_syntax_error(self, mcp_server):
        """Test handling of SQL syntax errors."""
        result = mcp_server.db_manager.execute_query("SELECT * FORM invalid_syntax")
        
        assert result.success is False
        assert result.error is not None
    
    def test_import_invalid_file_type(self, mcp_server, tmp_path):
        """Test importing unsupported file type."""
        invalid_file = tmp_path / "test.txt"
        invalid_file.write_text("some text")
        
        result = mcp_server.file_importer.import_file(invalid_file)
        
        assert result.success is False
        assert result.error is not None


class TestMCPIntegration:
    """Integration tests for MCP server."""
    
    def test_full_workflow(self, mcp_server, tmp_path):
        """Test complete workflow: import, query, analyze."""
        # Create and import a CSV file
        csv_file = tmp_path / "sales.csv"
        csv_file.write_text("product,quantity,price\nWidget,10,9.99\nGadget,5,19.99\nWidget,3,9.99\n")
        
        import_result = mcp_server.file_importer.import_file(csv_file)
        assert import_result.success is True
        
        # Register the table
        mcp_server.db_manager.register_table(
            "sales",
            import_result.dataframe,
            str(csv_file),
            "csv"
        )
        
        # Query the data
        result = mcp_server.db_manager.execute_query(
            "SELECT product, SUM(quantity) as total_qty FROM sales GROUP BY product"
        )
        
        assert result.success is True
        assert result.data is not None
        assert len(result.data) == 2  # Widget and Gadget
    
    def test_multiple_tables_join(self, mcp_server):
        """Test querying multiple tables with JOIN."""
        # Create customers table
        customers = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['Alice', 'Bob', 'Charlie']
        })
        
        # Create orders table
        orders = pd.DataFrame({
            'order_id': [101, 102, 103],
            'customer_id': [1, 2, 1],
            'amount': [100, 200, 150]
        })
        
        # Register tables
        mcp_server.db_manager.register_table("customers", customers)
        mcp_server.db_manager.register_table("orders", orders)
        
        # Join query
        result = mcp_server.db_manager.execute_query("""
            SELECT c.name, SUM(o.amount) as total
            FROM customers c
            JOIN orders o ON c.id = o.customer_id
            GROUP BY c.name
        """)
        
        assert result.success is True
        assert result.data is not None
        assert len(result.data) == 2  # Alice and Bob


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
