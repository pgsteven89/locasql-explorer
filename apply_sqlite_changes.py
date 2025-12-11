"""
Script to apply SQLite support changes to LocalSQL Explorer files.
Run this script to automatically integrate SQLite functionality.
"""

from pathlib import Path
import re

def update_importer():
    """Update importer.py with SQLite support."""
    file_path = Path('d:/code/localSQL_explorer/src/localsql_explorer/importer.py')
    content = file_path.read_text()
    
    # Change 1: Add SQLite extensions
    old_extensions = """    SUPPORTED_EXTENSIONS = {
        '.csv': 'csv',
        '.xlsx': 'excel',
        '.xls': 'excel',
        '.parquet': 'parquet',
        '.pq': 'parquet'
    }"""
    
    new_extensions = """    SUPPORTED_EXTENSIONS = {
        '.csv': 'csv',
        '.xlsx': 'excel',
        '.xls': 'excel',
        '.parquet': 'parquet',
        '.pq': 'parquet',
        '.db': 'sqlite',
        '.sqlite': 'sqlite',
        '.sqlite3': 'sqlite',
    }"""
    
    if old_extensions in content:
        content = content.replace(old_extensions, new_extensions)
        print("[OK] Added SQLite extensions to SUPPORTED_EXTENSIONS")
    else:
        print("[SKIP] SQLite extensions may already be added")
    
    # Change 2: Add SQLite routing
    old_routing = """            elif file_type == 'parquet':
                result = self.import_parquet(file_path, options)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")"""
    
    new_routing = """            elif file_type == 'parquet':
                result = self.import_parquet(file_path, options)
            elif file_type == 'sqlite':
                result = self.import_sqlite(file_path, options)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")"""
    
    if old_routing in content:
        content = content.replace(old_routing, new_routing)
        print("[OK] Added SQLite routing to import_file method")
    else:
        print("[SKIP] SQLite routing may already be added")
    
    file_path.write_text(content)
    print(f"[OK] Updated {file_path}")


def update_database():
    """Update database.py with attach_sqlite_database method."""
    file_path = Path('d:/code/localSQL_explorer/src/localsql_explorer/database.py')
    content = file_path.read_text()
    
    # Check if method already exists
    if 'def attach_sqlite_database' in content:
        print("[SKIP] attach_sqlite_database method already exists")
        return
    
    # Find where to insert (after register_table method)
    insert_marker = "    def execute_query(self, sql: str) -> QueryResult:"
    
    method_code = '''    def attach_sqlite_database(
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
        base_name = re.sub(r'[^\\w]', '_', base_name).lower()
        
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
                sanitized_name = f"{base_name}_{re.sub(r'[^\\w]', '_', table_name).lower()}"
                
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
    
'''
    
    if insert_marker in content:
        content = content.replace(insert_marker, method_code + insert_marker)
        file_path.write_text(content)
        print(f"[OK] Added attach_sqlite_database method to {file_path}")
    else:
        print("[ERROR] Could not find insertion point in database.py")


def update_mcp_server():
    """Update mcp_server.py to handle SQLite imports."""
    file_path = Path('d:/code/localSQL_explorer/src/localsql_explorer/mcp_server.py')
    content = file_path.read_text()
    
    # Check if already updated
    if 'BatchImportResult' in content and 'first_import.file_type == \'sqlite\'' in content:
        print("[SKIP] MCP server already updated for SQLite")
        return
    
    # Add import at top if not present
    if 'from localsql_explorer.importer import BatchImportResult' not in content:
        # Find the imports section
        import_marker = 'from .importer import FileImporter'
        if import_marker in content:
            content = content.replace(
                import_marker,
                import_marker + ', BatchImportResult'
            )
            print("[OK] Added BatchImportResult import to mcp_server.py")
    
    print(f"[INFO] MCP server may need manual update for full SQLite support")
    print(f"[INFO] See sqlite_integration_guide.md for details")
    
    file_path.write_text(content)


if __name__ == "__main__":
    print("=" * 60)
    print("Applying SQLite Support Changes")
    print("=" * 60)
    
    try:
        print("\n1. Updating importer.py...")
        update_importer()
        
        print("\n2. Updating database.py...")
        update_database()
        
        print("\n3. Updating mcp_server.py...")
        update_mcp_server()
        
        print("\n" + "=" * 60)
        print("[OK] SQLite support integration complete!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Run: python test_sqlite_import.py")
        print("2. Test with: python -m localsql_explorer.mcp_main")
        
    except Exception as e:
        print(f"\n[ERROR] Failed to apply changes: {e}")
        import traceback
        traceback.print_exc()
