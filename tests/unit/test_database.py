"""
Unit tests for the database module.

Tests for DatabaseManager class including:
- Connection management
- Table registration
- Query execution
- Error handling
- Persistence operations
"""

import pytest
import pandas as pd
from pathlib import Path

from localsql_explorer.database import DatabaseManager, TableMetadata, QueryResult


class TestDatabaseManager:
    """Test suite for DatabaseManager class."""
    
    def test_init_memory_database(self):
        """Test initialization with in-memory database."""
        db = DatabaseManager()
        assert db.connection is not None
        assert db.db_path is None
        assert len(db.tables) == 0
    
    def test_init_persistent_database(self, temp_dir: Path):
        """Test initialization with persistent database."""
        db_path = temp_dir / "test.duckdb"
        db = DatabaseManager(str(db_path))
        assert db.connection is not None
        assert db.db_path == db_path
        assert len(db.tables) == 0
    
    def test_register_table_success(self, db_manager: DatabaseManager, sample_dataframe: pd.DataFrame):
        """Test successful table registration."""
        table_name = "test_table"
        
        metadata = db_manager.register_table(table_name, sample_dataframe)
        
        assert metadata.name == table_name
        assert metadata.row_count == len(sample_dataframe)
        assert metadata.column_count == len(sample_dataframe.columns)
        assert table_name in db_manager.tables
    
    def test_register_table_invalid_name(self, db_manager: DatabaseManager, sample_dataframe: pd.DataFrame):
        """Test table registration with invalid name."""
        with pytest.raises(ValueError, match="Invalid table name"):
            db_manager.register_table("", sample_dataframe)
        
        with pytest.raises(ValueError, match="Invalid table name"):
            db_manager.register_table("123-invalid", sample_dataframe)  # Contains hyphen
        
        with pytest.raises(ValueError, match="Invalid table name"):
            db_manager.register_table("invalid table", sample_dataframe)  # Contains space
    
    def test_register_table_duplicate_name(self, db_manager: DatabaseManager, sample_dataframe: pd.DataFrame):
        """Test registering table with duplicate name."""
        table_name = "test_table"
        
        # Register first table
        db_manager.register_table(table_name, sample_dataframe)
        
        # Try to register another table with same name
        with pytest.raises(ValueError, match="already exists"):
            db_manager.register_table(table_name, sample_dataframe)
    
    def test_execute_query_select_success(self, db_manager: DatabaseManager, sample_dataframe: pd.DataFrame):
        """Test successful SELECT query execution."""
        table_name = "test_table"
        db_manager.register_table(table_name, sample_dataframe)
        
        result = db_manager.execute_query(f"SELECT * FROM {table_name}")
        
        assert result.success is True
        assert result.data is not None
        assert len(result.data) == len(sample_dataframe)
        assert result.row_count == len(sample_dataframe)
        assert result.execution_time > 0
    
    def test_execute_query_with_filter(self, db_manager: DatabaseManager, sample_dataframe: pd.DataFrame):
        """Test SELECT query with WHERE clause."""
        table_name = "test_table"
        db_manager.register_table(table_name, sample_dataframe)
        
        result = db_manager.execute_query(f"SELECT * FROM {table_name} WHERE id = 1")
        
        assert result.success is True
        assert result.data is not None
        assert len(result.data) == 1
        assert result.data.iloc[0]['id'] == 1
    
    def test_execute_query_invalid_sql(self, db_manager: DatabaseManager):
        """Test query execution with invalid SQL."""
        result = db_manager.execute_query("INVALID SQL STATEMENT")
        
        assert result.success is False
        assert result.error is not None
        assert result.data is None
    
    def test_execute_query_nonexistent_table(self, db_manager: DatabaseManager):
        """Test query on non-existent table."""
        result = db_manager.execute_query("SELECT * FROM nonexistent_table")
        
        assert result.success is False
        assert result.error is not None
    
    def test_get_table_metadata(self, db_manager: DatabaseManager, sample_dataframe: pd.DataFrame):
        """Test getting table metadata."""
        table_name = "test_table"
        db_manager.register_table(table_name, sample_dataframe)
        
        metadata = db_manager.get_table_metadata(table_name)
        
        assert metadata is not None
        assert metadata.name == table_name
        assert metadata.row_count == len(sample_dataframe)
    
    def test_get_table_metadata_nonexistent(self, db_manager: DatabaseManager):
        """Test getting metadata for non-existent table."""
        metadata = db_manager.get_table_metadata("nonexistent")
        assert metadata is None
    
    def test_list_tables(self, db_manager: DatabaseManager, sample_dataframe: pd.DataFrame):
        """Test listing all tables."""
        # Initially empty
        tables = db_manager.list_tables()
        assert len(tables) == 0
        
        # Add tables
        db_manager.register_table("table1", sample_dataframe)
        db_manager.register_table("table2", sample_dataframe)
        
        tables = db_manager.list_tables()
        assert len(tables) == 2
        table_names = [t.name for t in tables]
        assert "table1" in table_names
        assert "table2" in table_names
    
    def test_drop_table_success(self, db_manager: DatabaseManager, sample_dataframe: pd.DataFrame):
        """Test successful table drop."""
        table_name = "test_table"
        db_manager.register_table(table_name, sample_dataframe)
        
        success = db_manager.drop_table(table_name)
        
        assert success is True
        assert table_name not in db_manager.tables
        
        # Verify table is gone from database
        result = db_manager.execute_query(f"SELECT * FROM {table_name}")
        assert result.success is False
    
    def test_drop_table_nonexistent(self, db_manager: DatabaseManager):
        """Test dropping non-existent table."""
        success = db_manager.drop_table("nonexistent")
        assert success is False
    
    def test_rename_table_success(self, db_manager: DatabaseManager, sample_dataframe: pd.DataFrame):
        """Test successful table rename."""
        old_name = "old_table"
        new_name = "new_table"
        
        db_manager.register_table(old_name, sample_dataframe)
        
        success = db_manager.rename_table(old_name, new_name)
        
        assert success is True
        assert old_name not in db_manager.tables
        assert new_name in db_manager.tables
        
        # Verify table is accessible by new name
        result = db_manager.execute_query(f"SELECT * FROM {new_name}")
        assert result.success is True
    
    def test_rename_table_nonexistent(self, db_manager: DatabaseManager):
        """Test renaming non-existent table."""
        success = db_manager.rename_table("nonexistent", "new_name")
        assert success is False
    
    def test_rename_table_name_conflict(self, db_manager: DatabaseManager, sample_dataframe: pd.DataFrame):
        """Test renaming table to existing name."""
        db_manager.register_table("table1", sample_dataframe)
        db_manager.register_table("table2", sample_dataframe)
        
        success = db_manager.rename_table("table1", "table2")
        assert success is False
    
    def test_save_database(self, db_manager: DatabaseManager, sample_dataframe: pd.DataFrame, temp_dir: Path):
        """Test saving database to file."""
        # Register some tables
        db_manager.register_table("table1", sample_dataframe)
        
        db_path = temp_dir / "saved.duckdb"
        success = db_manager.save_database(db_path)
        
        assert success is True
        assert db_path.exists()
    
    def test_load_database(self, temp_dir: Path, sample_dataframe: pd.DataFrame):
        """Test loading database from file."""
        # Create and save a database
        db_path = temp_dir / "test.duckdb"
        db1 = DatabaseManager(str(db_path))
        db1.register_table("test_table", sample_dataframe)
        db1.close()
        
        # Load the database
        db2 = DatabaseManager()
        success = db2.load_database(db_path)
        
        assert success is True
        assert "test_table" in db2.tables
        
        # Verify data is intact
        result = db2.execute_query("SELECT * FROM test_table")
        assert result.success is True
        assert len(result.data) == len(sample_dataframe)
    
    def test_load_nonexistent_database(self, db_manager: DatabaseManager, temp_dir: Path):
        """Test loading non-existent database file."""
        nonexistent_path = temp_dir / "nonexistent.duckdb"
        success = db_manager.load_database(nonexistent_path)
        assert success is False
    
    def test_close_connection(self, db_manager: DatabaseManager):
        """Test closing database connection."""
        assert db_manager.connection is not None
        
        db_manager.close()
        
        assert db_manager.connection is None


class TestTableMetadata:
    """Test suite for TableMetadata model."""
    
    def test_table_metadata_creation(self):
        """Test creating TableMetadata instance."""
        from datetime import datetime
        
        metadata = TableMetadata(
            name="test_table",
            row_count=100,
            column_count=5,
            columns=[{"name": "col1", "type": "int"}],
            created_at=datetime.now().isoformat()
        )
        
        assert metadata.name == "test_table"
        assert metadata.row_count == 100
        assert metadata.column_count == 5
        assert len(metadata.columns) == 1


class TestQueryResult:
    """Test suite for QueryResult model."""
    
    def test_query_result_success(self, sample_dataframe: pd.DataFrame):
        """Test successful QueryResult creation."""
        result = QueryResult(
            success=True,
            data=sample_dataframe,
            execution_time=0.123,
            row_count=len(sample_dataframe)
        )
        
        assert result.success is True
        assert result.data is not None
        assert result.execution_time == 0.123
        assert result.row_count == len(sample_dataframe)
        assert result.error is None
    
    def test_query_result_failure(self):
        """Test failed QueryResult creation."""
        result = QueryResult(
            success=False,
            error="Test error message",
            execution_time=0.050
        )
        
        assert result.success is False
        assert result.error == "Test error message"
        assert result.data is None
        assert result.row_count == 0