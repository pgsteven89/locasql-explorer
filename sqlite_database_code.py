"""
SQLite database attachment functionality to add to database.py

Add this method to the DatabaseManager class after the register_table method (around line 150).
"""

def attach_sqlite_database(
    self,
    sqlite_path: Union[str, Path],
    base_name: Optional[str] = None
) -> List[TableMetadata]:
    """
    Attach a SQLite database and register all its tables as views.
    
    Args:
        sqlite_path: Path to SQLite database file
        base_name: Optional base name for table prefixes (defaults to filename)
        
    Returns:
        List of TableMetadata for registered tables
    """
    sqlite_path = Path(sqlite_path)
    
    if not base_name:
        base_name = sqlite_path.stem
    
    # Sanitize base name
    import re
    base_name = re.sub(r'[^\w]', '_', base_name).lower()
    
    registered_tables = []
    
    try:
        # Install and load SQLite extension if needed
        try:
            self.connection.execute("INSTALL sqlite")
            self.connection.execute("LOAD sqlite")
            logger.info("Loaded SQLite extension for DuckDB")
        except Exception as e:
            logger.debug(f"SQLite extension may already be loaded: {e}")
        
        # Attach the SQLite database
        alias = f"sqlite_{base_name}"
        attach_query = f"ATTACH '{sqlite_path}' AS {alias} (TYPE SQLITE)"
        self.connection.execute(attach_query)
        logger.info(f"Attached SQLite database '{sqlite_path}' as '{alias}'")
        
        # Get list of tables
        tables_result = self.connection.execute(
            f"SELECT name FROM {alias}.sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        
        # Create views for each table in main database
        from datetime import datetime
        
        for (table_name,) in tables_result:
            # Create sanitized table name
            sanitized_name = f"{base_name}_{re.sub(r'[^\w]', '_', table_name).lower()}"
            
            # Create view in main database
            create_view_query = f"CREATE OR REPLACE VIEW {sanitized_name} AS SELECT * FROM {alias}.{table_name}"
            self.connection.execute(create_view_query)
            logger.info(f"Created view '{sanitized_name}' for SQLite table '{table_name}'")
            
            # Get row count and column info
            row_count_result = self.connection.execute(
                f"SELECT COUNT(*) FROM {sanitized_name}"
            ).fetchone()
            row_count = row_count_result[0] if row_count_result else 0
            
            # Get column information
            columns_result = self.connection.execute(f"DESCRIBE {sanitized_name}").fetchall()
            columns = [
                {"name": col[0], "type": col[1]}
                for col in columns_result
            ]
            
            # Create metadata
            metadata = TableMetadata(
                name=sanitized_name,
                file_path=str(sqlite_path),
                file_type="sqlite",
                row_count=row_count,
                column_count=len(columns),
                columns=columns,
                created_at=datetime.now().isoformat()
            )
            
            self.tables[sanitized_name] = metadata
            registered_tables.append(metadata)
            
            logger.info(f"Registered SQLite table '{table_name}' as '{sanitized_name}' ({row_count} rows, {len(columns)} columns)")
        
        return registered_tables
        
    except Exception as e:
        logger.error(f"Failed to attach SQLite database {sqlite_path}: {e}")
        raise
