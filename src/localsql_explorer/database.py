"""
Database module for managing DuckDB connections and table operations.

This module provides the DatabaseManager class which handles:
- DuckDB connection management (in-memory and persistent)
- Table registration and metadata
- SQL query execution
- Error handling and validation
"""

import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Union

import duckdb
import pandas as pd
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TableMetadata(BaseModel):
    """Metadata for a registered table."""
    
    name: str = Field(..., description="Table name")
    file_path: Optional[str] = Field(None, description="Source file path")
    file_type: Optional[str] = Field(None, description="File type (csv, xlsx, parquet)")
    row_count: int = Field(0, description="Number of rows")
    column_count: int = Field(0, description="Number of columns")
    columns: List[Dict[str, str]] = Field(default_factory=list, description="Column metadata")
    created_at: str = Field(..., description="Creation timestamp")


class QueryResult(BaseModel):
    """Result of a SQL query execution."""
    
    model_config = {"arbitrary_types_allowed": True}
    
    success: bool = Field(..., description="Whether query executed successfully")
    data: Optional[pd.DataFrame] = Field(None, description="Query result data")
    error: Optional[str] = Field(None, description="Error message if failed")
    execution_time: float = Field(0.0, description="Execution time in seconds")
    row_count: int = Field(0, description="Number of rows returned")
    affected_rows: Optional[int] = Field(None, description="Number of affected rows for non-select queries")


class DatabaseManager:
    """
    Manages DuckDB database connections and operations.
    
    Provides functionality for:
    - Creating and managing database connections
    - Registering tables from DataFrames
    - Executing SQL queries
    - Managing table metadata
    - Persistence operations
    """
    
    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        """
        Initialize the database manager.
        
        Args:
            db_path: Optional path to persistent database file. If None, uses in-memory database.
        """
        self.db_path = Path(db_path) if db_path else None
        self.connection: Optional[duckdb.DuckDBPyConnection] = None
        self.tables: Dict[str, TableMetadata] = {}
        self._connect()
    
    def _connect(self) -> None:
        """Establish connection to DuckDB."""
        try:
            if self.db_path:
                self.connection = duckdb.connect(str(self.db_path))
                logger.info(f"Connected to persistent database: {self.db_path}")
            else:
                self.connection = duckdb.connect(":memory:")
                logger.info("Connected to in-memory database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def register_table(
        self,
        name: str,
        dataframe: pd.DataFrame,
        file_path: Optional[str] = None,
        file_type: Optional[str] = None
    ) -> TableMetadata:
        """
        Register a DataFrame as a table in the database.
        
        Args:
            name: Table name
            dataframe: Pandas DataFrame to register
            file_path: Optional source file path
            file_type: Optional file type (csv, xlsx, parquet)
            
        Returns:
            TableMetadata: Metadata for the registered table
            
        Raises:
            ValueError: If table name is invalid or already exists
            Exception: If registration fails
        """
        if not name or not name.strip():
            raise ValueError(f"Invalid table name: {name}")
        
        # Check for valid SQL identifier (more permissive than original)
        import re
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
            raise ValueError(f"Invalid table name: {name}")
        
        if name in self.tables:
            raise ValueError(f"Table '{name}' already exists")
        
        try:
            # Create a proper table instead of just registering a view
            # First register as view for DuckDB to understand the schema
            self.connection.register(f"temp_{name}", dataframe)
            
            # Then create a proper table from the view
            self.connection.execute(f"CREATE TABLE {name} AS SELECT * FROM temp_{name}")
            
            # Clean up the temporary view
            self.connection.execute(f"DROP VIEW temp_{name}")
            
            # Create metadata
            from datetime import datetime
            columns = [
                {"name": col, "type": str(dataframe[col].dtype)}
                for col in dataframe.columns
            ]
            
            metadata = TableMetadata(
                name=name,
                file_path=file_path,
                file_type=file_type,
                row_count=len(dataframe),
                column_count=len(dataframe.columns),
                columns=columns,
                created_at=datetime.now().isoformat()
            )
            
            self.tables[name] = metadata
            logger.info(f"Registered table '{name}' with {len(dataframe)} rows, {len(dataframe.columns)} columns")
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to register table '{name}': {e}")
            raise
    
    def execute_query(self, sql: str) -> QueryResult:
        """
        Execute a SQL query against the database.
        
        Args:
            sql: SQL query string
            
        Returns:
            QueryResult: Result of the query execution
        """
        import time
        
        start_time = time.time()
        
        try:
            # Execute the query
            result = self.connection.execute(sql)
            
            # Get the result as DataFrame for queries that return data
            sql_trimmed = sql.strip().upper()
            is_select_query = (
                sql_trimmed.startswith('SELECT') or 
                sql_trimmed.startswith('WITH') or
                sql_trimmed.startswith('EXPLAIN') or
                sql_trimmed.startswith('DESCRIBE') or
                sql_trimmed.startswith('SHOW')
            )
            
            if is_select_query:
                data = result.df()
                row_count = len(data) if data is not None else 0
                affected_rows = None
            else:
                # For non-SELECT queries, get affected rows if available
                data = None
                row_count = 0
                affected_rows = result.rowcount if hasattr(result, 'rowcount') else None
            
            execution_time = time.time() - start_time
            
            logger.info(f"Query executed successfully in {execution_time:.3f}s")
            
            return QueryResult(
                success=True,
                data=data,
                execution_time=execution_time,
                row_count=row_count,
                affected_rows=affected_rows
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            logger.error(f"Query failed after {execution_time:.3f}s: {error_msg}")
            
            return QueryResult(
                success=False,
                error=error_msg,
                execution_time=execution_time
            )
    
    def get_table_metadata(self, table_name: str) -> Optional[TableMetadata]:
        """Get metadata for a specific table."""
        return self.tables.get(table_name)
    
    def list_tables(self) -> List[TableMetadata]:
        """List all registered tables."""
        return list(self.tables.values())
    
    def get_table_metadata(self, table_name: str) -> Optional[TableMetadata]:
        """
        Get metadata for a specific table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            TableMetadata: Table metadata or None if not found
        """
        return self.tables.get(table_name)
    
    def get_table_columns(self, table_name: str) -> List[Dict[str, str]]:
        """
        Get column information for a specific table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List[Dict[str, str]]: List of column metadata dicts with 'name' and 'type' keys
        """
        metadata = self.get_table_metadata(table_name)
        if metadata is None:
            logger.warning(f"Table '{table_name}' not found")
            return []
        
        # If we don't have column metadata stored, try to get it from DuckDB
        if not metadata.columns:
            try:
                # Query DuckDB's information schema to get column information
                result = self.execute_query(f"DESCRIBE {table_name}")
                if result.success and result.data is not None:
                    columns = []
                    for _, row in result.data.iterrows():
                        columns.append({
                            'name': str(row['column_name']),
                            'type': str(row['column_type'])
                        })
                    return columns
            except Exception as e:
                logger.warning(f"Could not get column info from DuckDB for table {table_name}: {e}")
                return []
        
        return metadata.columns
    
    def drop_table(self, table_name: str) -> bool:
        """
        Drop a table from the database.
        
        Args:
            table_name: Name of the table to drop
            
        Returns:
            bool: True if table was dropped successfully
        """
        try:
            if table_name not in self.tables:
                logger.warning(f"Table '{table_name}' not found")
                return False
            
            # Drop from DuckDB
            self.connection.execute(f"DROP TABLE IF EXISTS {table_name}")
            
            # Remove from metadata
            del self.tables[table_name]
            
            logger.info(f"Dropped table '{table_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to drop table '{table_name}': {e}")
            return False
    
    def rename_table(self, old_name: str, new_name: str) -> bool:
        """
        Rename a table in the database.
        
        Args:
            old_name: Current table name
            new_name: New table name
            
        Returns:
            bool: True if table was renamed successfully
        """
        try:
            if old_name not in self.tables:
                logger.warning(f"Table '{old_name}' not found")
                return False
            
            if new_name in self.tables:
                logger.warning(f"Table '{new_name}' already exists")
                return False
            
            # Rename in DuckDB
            self.connection.execute(f"ALTER TABLE {old_name} RENAME TO {new_name}")
            
            # Update metadata
            metadata = self.tables[old_name]
            metadata.name = new_name
            self.tables[new_name] = metadata
            del self.tables[old_name]
            
            logger.info(f"Renamed table '{old_name}' to '{new_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rename table '{old_name}' to '{new_name}': {e}")
            return False
    
    def save_database(self, file_path: Union[str, Path]) -> bool:
        """
        Save the current database to a file.
        
        Args:
            file_path: Path where to save the database
            
        Returns:
            bool: True if saved successfully
        """
        try:
            file_path = Path(file_path)
            
            # If we're already using a persistent database, just return True
            if self.db_path and self.db_path == file_path:
                logger.info("Database already persisted to this file")
                return True
            
            # Create a new connection to the target file
            target_conn = duckdb.connect(str(file_path))
            
            # Copy all tables to the new database
            for table_name in self.tables:
                # Get the table data
                df = self.connection.execute(f"SELECT * FROM {table_name}").df()
                # Create table in target database
                target_conn.register(f"temp_{table_name}", df)
                target_conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM temp_{table_name}")
                target_conn.execute(f"DROP VIEW temp_{table_name}")
            
            target_conn.close()
            
            # If successful and this was an in-memory database, switch to persistent
            if not self.db_path:
                self.connection.close()
                self.db_path = file_path
                self._connect()
            
            logger.info(f"Database saved to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save database to {file_path}: {e}")
            return False
    
    def load_database(self, file_path: Union[str, Path]) -> bool:
        """
        Load a database from a file.
        
        Args:
            file_path: Path to the database file
            
        Returns:
            bool: True if loaded successfully
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                logger.error(f"Database file not found: {file_path}")
                return False
            
            # Close current connection
            if self.connection:
                self.connection.close()
            
            # Connect to the new database
            self.db_path = file_path
            self._connect()
            
            # Rebuild table metadata
            self.tables.clear()
            
            # Get list of tables from database
            tables_df = self.connection.execute("SHOW TABLES").df()
            
            for _, row in tables_df.iterrows():
                table_name = row['name']
                
                # Get table info
                info_df = self.connection.execute(f"DESCRIBE {table_name}").df()
                row_count_result = self.connection.execute(f"SELECT COUNT(*) as count FROM {table_name}").df()
                row_count = row_count_result.iloc[0]['count']
                
                columns = [
                    {"name": col_row['column_name'], "type": col_row['column_type']}
                    for _, col_row in info_df.iterrows()
                ]
                
                from datetime import datetime
                metadata = TableMetadata(
                    name=table_name,
                    row_count=row_count,
                    column_count=len(columns),
                    columns=columns,
                    created_at=datetime.now().isoformat()
                )
                
                self.tables[table_name] = metadata
            
            logger.info(f"Loaded database from {file_path} with {len(self.tables)} tables")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load database from {file_path}: {e}")
            return False
    
    def close(self) -> None:
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Database connection closed")
    
    def rename_table(self, old_name: str, new_name: str) -> bool:
        """
        Rename a table in the database.
        
        Args:
            old_name: Current table name
            new_name: New table name
            
        Returns:
            bool: True if renamed successfully
        """
        try:
            if old_name not in self.tables:
                logger.error(f"Table '{old_name}' not found")
                return False
            
            if new_name in self.tables:
                logger.error(f"Table '{new_name}' already exists")
                return False
            
            # Rename table in database
            self.connection.execute(f"ALTER TABLE {old_name} RENAME TO {new_name}")
            
            # Update metadata
            metadata = self.tables[old_name]
            metadata.name = new_name
            
            # Update tables dictionary
            self.tables[new_name] = metadata
            del self.tables[old_name]
            
            logger.info(f"Table renamed from '{old_name}' to '{new_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rename table from '{old_name}' to '{new_name}': {e}")
            return False
    
    def drop_table(self, table_name: str) -> bool:
        """
        Drop a table from the database.
        
        Args:
            table_name: Name of table to drop
            
        Returns:
            bool: True if dropped successfully
        """
        try:
            if table_name not in self.tables:
                logger.error(f"Table '{table_name}' not found")
                return False
            
            # Drop table from database
            self.connection.execute(f"DROP TABLE {table_name}")
            
            # Remove from metadata
            del self.tables[table_name]
            
            logger.info(f"Table '{table_name}' dropped")
            return True
            
        except Exception as e:
            logger.error(f"Failed to drop table '{table_name}': {e}")
            return False
    
    def analyze_table_columns(self, table_name: str):
        """
        Perform detailed column analysis for a table.
        
        Args:
            table_name: Name of the table to analyze
            
        Returns:
            TableColumnAnalysis: Detailed column analysis or None if table not found
        """
        from .column_analysis import column_analyzer
        
        if table_name not in self.tables:
            logger.error(f"Table '{table_name}' not found")
            return None
        
        try:
            # Get table data
            query_result = self.execute_query(f"SELECT * FROM {table_name}")
            
            if not query_result.success or query_result.data is None:
                logger.error(f"Failed to retrieve data for table '{table_name}'")
                return None
            
            # Perform column analysis
            analysis = column_analyzer.analyze_table(query_result.data, table_name)
            logger.info(f"Column analysis completed for table '{table_name}'")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze columns for table '{table_name}': {e}")
            return None
    
    def get_table_dataframe(self, table_name: str) -> Optional[pd.DataFrame]:
        """
        Get the complete dataframe for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            pd.DataFrame: Table data or None if table not found
        """
        if table_name not in self.tables:
            logger.error(f"Table '{table_name}' not found")
            return None
        
        try:
            # Execute query to get all table data
            query_result = self.execute_query(f"SELECT * FROM {table_name}")
            
            if not query_result.success or query_result.data is None:
                logger.error(f"Failed to retrieve data for table '{table_name}'")
                return None
            
            logger.info(f"Retrieved {len(query_result.data)} rows for table '{table_name}'")
            return query_result.data
            
        except Exception as e:
            logger.error(f"Failed to get dataframe for table '{table_name}': {e}")
            return None
    
    def create_query_paginator(self, sql: str, config=None):
        """
        Create a paginator for a SQL query.
        
        Args:
            sql: SQL query to paginate
            config: Optional pagination configuration
            
        Returns:
            QueryPaginator: Paginator for the query
        """
        from .data_pagination import QueryPaginator, PaginationConfig
        
        if not self.connection:
            raise RuntimeError("Database not connected")
        
        pagination_config = config or PaginationConfig()
        return QueryPaginator(self.connection, sql, pagination_config)
    
    def create_table_paginator(self, table_name: str, config=None):
        """
        Create a paginator for a table.
        
        Args:
            table_name: Name of the table
            config: Optional pagination configuration
            
        Returns:
            QueryPaginator: Paginator for the table
        """
        if table_name not in self.tables:
            raise ValueError(f"Table '{table_name}' not found")
        
        sql = f"SELECT * FROM {table_name}"
        return self.create_query_paginator(sql, config)