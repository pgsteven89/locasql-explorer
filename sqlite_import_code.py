"""
SQLite import functionality to add to importer.py

Add this method to the FileImporter class after the import_parquet method (around line 502).
Also update SUPPORTED_EXTENSIONS to include SQLite extensions.
"""

# 1. UPDATE SUPPORTED_EXTENSIONS (around line 93-99)
# Change from:
SUPPORTED_EXTENSIONS = {
    '.csv': 'csv',
    '.xlsx': 'excel',
    '.xls': 'excel',
    '.parquet': 'parquet',
    '.pq': 'parquet'
}

# To:
SUPPORTED_EXTENSIONS = {
    '.csv': 'csv',
    '.xlsx': 'excel',
    '.xls': 'excel',
    '.parquet': 'parquet',
    '.pq': 'parquet',
    '.db': 'sqlite',
    '.sqlite': 'sqlite',
    '.sqlite3': 'sqlite',
}

# 2. ADD THIS METHOD after import_parquet (around line 502):

def import_sqlite(
    self,
    file_path: Union[str, Path],
    options: Optional[ImportOptions] = None
) -> BatchImportResult:
    """
    Import all tables from a SQLite database.
    
    Args:
        file_path: Path to SQLite database file
        options: Import options (unused for SQLite)
        
    Returns:
        BatchImportResult: Result containing all imported tables
    """
    file_path = Path(file_path)
    warnings = []
    successful_imports = []
    failed_imports = []
    table_names = []
    
    try:
        # Verify file exists
        if not file_path.exists():
            raise FileNotFoundError(f"SQLite file not found: {file_path}")
        
        # Get base name for table prefixes
        base_name = self._sanitize_name(file_path.stem)
        
        # Read table list using sqlite3 module
        import sqlite3
        conn = sqlite3.connect(str(file_path))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        sqlite_tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if not sqlite_tables:
            warnings.append("No tables found in SQLite database")
        
        logger.info(f"Found {len(sqlite_tables)} tables in SQLite database: {sqlite_tables}")
        
        # Create import results for each table
        for table_name in sqlite_tables:
            # Table will be registered by DatabaseManager via attach_sqlite_database
            sanitized_name = f"{base_name}_{self._sanitize_name(table_name)}"
            table_names.append(sanitized_name)
            
            # Create a placeholder ImportResult
            result = ImportResult(
                success=True,
                dataframe=None,  # No dataframe for SQLite - handled by DuckDB attachment
                file_path=str(file_path),
                file_type='sqlite',
                metadata={
                    'original_table_name': table_name,
                    'sqlite_database': str(file_path),
                    'table_name': sanitized_name
                }
            )
            successful_imports.append(result)
        
        batch_result = BatchImportResult(
            success=True,
            file_path=str(file_path),
            total_sheets=len(sqlite_tables),
            successful_imports=successful_imports,
            failed_imports=failed_imports,
            warnings=warnings,
            table_names=table_names
        )
        
        self.import_history.append(batch_result)
        return batch_result
        
    except Exception as e:
        error_msg = f"Failed to import SQLite database {file_path}: {str(e)}"
        logger.error(error_msg)
        
        batch_result = BatchImportResult(
            success=False,
            file_path=str(file_path),
            total_sheets=0,
            successful_imports=[],
            failed_imports=[("database", error_msg)],
            warnings=[error_msg],
            table_names=[]
        )
        
        self.import_history.append(batch_result)
        return batch_result


# 3. UPDATE import_file method routing (around line 540):
# Add this elif clause before the final else:

elif file_type == 'sqlite':
    result = self.import_sqlite(file_path, options)
