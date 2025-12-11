"""
MCP (Model Context Protocol) Server for LocalSQL Explorer.

This module provides an MCP server that exposes LocalSQL Explorer's functionality
to LLMs and AI assistants, enabling them to:
- List and explore tables in the database
- Execute SQL queries
- Import data files (CSV, Excel, Parquet)
- Get table schemas and metadata

The server runs standalone and can be connected to by MCP clients like Claude Desktop.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    Prompt,
    PromptMessage,
    GetPromptResult,
)
from pydantic import BaseModel, Field

from .database import DatabaseManager, QueryResult, TableMetadata
from .importer import FileImporter, BatchImportResult, ImportOptions

logger = logging.getLogger(__name__)


class MCPServerConfig(BaseModel):
    """Configuration for MCP server."""
    
    db_path: Optional[str] = Field(None, description="Path to DuckDB database file")
    max_query_rows: int = Field(1000, description="Maximum rows to return from queries")
    enable_file_import: bool = Field(True, description="Allow file imports via MCP")
    log_level: str = Field("INFO", description="Logging level")


class LocalSQLMCPServer:
    """
    MCP Server for LocalSQL Explorer.
    
    Exposes database operations as MCP resources and tools.
    """
    
    def __init__(self, config: MCPServerConfig):
        """
        Initialize the MCP server.
        
        Args:
            config: Server configuration
        """
        self.config = config
        self.server = Server("localsql-explorer")
        self.db_manager: Optional[DatabaseManager] = None
        self.file_importer = FileImporter()
        
        # Initialize database if path provided
        if config.db_path:
            self.db_manager = DatabaseManager(config.db_path)
            logger.info(f"Initialized database: {config.db_path}")
        else:
            self.db_manager = DatabaseManager()  # In-memory database
            logger.info("Initialized in-memory database")
        
        # Register handlers
        self._register_handlers()
    
    def _register_handlers(self) -> None:
        """Register all MCP handlers for resources, tools, and prompts."""
        
        # Resource handlers
        @self.server.list_resources()
        async def list_resources() -> List[Resource]:
            """List all available resources (tables)."""
            resources = []
            
            if self.db_manager:
                tables = self.db_manager.list_tables()
                
                # Add a resource for the table list
                resources.append(
                    Resource(
                        uri="localsql://tables/list",
                        name="Table List",
                        description="List of all tables in the database",
                        mimeType="application/json"
                    )
                )
                
                # Add resources for each table
                for table in tables:
                    resources.append(
                        Resource(
                            uri=f"localsql://tables/{table.name}",
                            name=f"Table: {table.name}",
                            description=f"Schema and metadata for table {table.name} ({table.row_count} rows, {table.column_count} columns)",
                            mimeType="application/json"
                        )
                    )
                    
                    # Add sample data resource
                    resources.append(
                        Resource(
                            uri=f"localsql://tables/{table.name}/sample",
                            name=f"Sample Data: {table.name}",
                            description=f"Sample rows from table {table.name}",
                            mimeType="application/json"
                        )
                    )
            
            return resources
        
        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            """Read a specific resource."""
            if not self.db_manager:
                return "Error: Database not initialized"
            
            try:
                # Parse the URI
                if uri == "localsql://tables/list":
                    # Return list of all tables
                    tables = self.db_manager.list_tables()
                    table_info = [
                        {
                            "name": t.name,
                            "row_count": t.row_count,
                            "column_count": t.column_count,
                            "file_path": t.file_path,
                            "file_type": t.file_type,
                            "created_at": t.created_at
                        }
                        for t in tables
                    ]
                    import json
                    return json.dumps({"tables": table_info}, indent=2)
                
                elif uri.startswith("localsql://tables/") and uri.endswith("/sample"):
                    # Return sample data from table
                    table_name = uri.split("/")[-2]
                    result = self.db_manager.execute_query(
                        f"SELECT * FROM {table_name} LIMIT 10"
                    )
                    
                    if result.success and result.data is not None:
                        import json
                        return json.dumps({
                            "table": table_name,
                            "rows": result.data.to_dict(orient="records"),
                            "columns": list(result.data.columns)
                        }, indent=2, default=str)
                    else:
                        return f"Error: {result.error}"
                
                elif uri.startswith("localsql://tables/"):
                    # Return table schema
                    table_name = uri.split("/")[-1]
                    metadata = self.db_manager.get_table_metadata(table_name)
                    
                    if metadata:
                        import json
                        return json.dumps({
                            "name": metadata.name,
                            "row_count": metadata.row_count,
                            "column_count": metadata.column_count,
                            "columns": metadata.columns,
                            "file_path": metadata.file_path,
                            "file_type": metadata.file_type,
                            "created_at": metadata.created_at
                        }, indent=2)
                    else:
                        return f"Error: Table '{table_name}' not found"
                
                else:
                    return f"Error: Unknown resource URI: {uri}"
                    
            except Exception as e:
                logger.error(f"Error reading resource {uri}: {e}")
                return f"Error: {str(e)}"
        
        # Tool handlers
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List all available tools."""
            return [
                Tool(
                    name="execute_query",
                    description="Execute a SQL query against the database. Returns results with optional row limit.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "sql": {
                                "type": "string",
                                "description": "SQL query to execute"
                            },
                            "limit": {
                                "type": "integer",
                                "description": f"Maximum number of rows to return (default: {self.config.max_query_rows})",
                                "default": self.config.max_query_rows
                            }
                        },
                        "required": ["sql"]
                    }
                ),
                Tool(
                    name="list_tables",
                    description="List all tables in the database with metadata",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="get_table_info",
                    description="Get detailed information about a specific table including schema and statistics",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "table_name": {
                                "type": "string",
                                "description": "Name of the table"
                            }
                        },
                        "required": ["table_name"]
                    }
                ),
                Tool(
                    name="get_columns",
                    description="Get column information for all tables or a specific table",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "table_name": {
                                "type": "string",
                                "description": "Optional table name. If not provided, returns columns for all tables"
                            }
                        }
                    }
                ),
                Tool(
                    name="import_file",
                    description="Import a CSV, Excel, or Parquet file as a new table",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file to import"
                            },
                            "table_name": {
                                "type": "string",
                                "description": "Optional name for the table. If not provided, uses filename"
                            }
                        },
                        "required": ["file_path"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> Sequence[TextContent]:
            """Execute a tool."""
            if not self.db_manager:
                return [TextContent(
                    type="text",
                    text="Error: Database not initialized"
                )]
            
            try:
                if name == "execute_query":
                    sql = arguments.get("sql", "")
                    limit = arguments.get("limit", self.config.max_query_rows)
                    
                    if not sql:
                        return [TextContent(type="text", text="Error: SQL query is required")]
                    
                    # Add LIMIT clause if not present and this is a SELECT query
                    sql_upper = sql.strip().upper()
                    if sql_upper.startswith("SELECT") and "LIMIT" not in sql_upper:
                        sql = f"{sql.rstrip(';')} LIMIT {limit}"
                    
                    result = self.db_manager.execute_query(sql)
                    
                    if result.success:
                        if result.data is not None:
                            import json
                            response = {
                                "success": True,
                                "row_count": result.row_count,
                                "execution_time": result.execution_time,
                                "columns": list(result.data.columns),
                                "rows": result.data.to_dict(orient="records")
                            }
                            return [TextContent(
                                type="text",
                                text=json.dumps(response, indent=2, default=str)
                            )]
                        else:
                            return [TextContent(
                                type="text",
                                text=f"Query executed successfully. Affected rows: {result.affected_rows}"
                            )]
                    else:
                        return [TextContent(
                            type="text",
                            text=f"Error executing query: {result.error}"
                        )]
                
                elif name == "list_tables":
                    tables = self.db_manager.list_tables()
                    import json
                    table_info = [
                        {
                            "name": t.name,
                            "row_count": t.row_count,
                            "column_count": t.column_count,
                            "file_path": t.file_path,
                            "file_type": t.file_type
                        }
                        for t in tables
                    ]
                    return [TextContent(
                        type="text",
                        text=json.dumps({"tables": table_info}, indent=2)
                    )]
                
                elif name == "get_table_info":
                    table_name = arguments.get("table_name", "")
                    if not table_name:
                        return [TextContent(type="text", text="Error: table_name is required")]
                    
                    metadata = self.db_manager.get_table_metadata(table_name)
                    if metadata:
                        import json
                        info = {
                            "name": metadata.name,
                            "row_count": metadata.row_count,
                            "column_count": metadata.column_count,
                            "columns": metadata.columns,
                            "file_path": metadata.file_path,
                            "file_type": metadata.file_type,
                            "created_at": metadata.created_at
                        }
                        return [TextContent(
                            type="text",
                            text=json.dumps(info, indent=2)
                        )]
                    else:
                        return [TextContent(
                            type="text",
                            text=f"Error: Table '{table_name}' not found"
                        )]
                
                elif name == "get_columns":
                    table_name = arguments.get("table_name")
                    import json
                    
                    if table_name:
                        # Get columns for specific table
                        columns = self.db_manager.get_table_columns(table_name)
                        return [TextContent(
                            type="text",
                            text=json.dumps({
                                "table": table_name,
                                "columns": columns
                            }, indent=2)
                        )]
                    else:
                        # Get columns for all tables
                        tables = self.db_manager.list_tables()
                        all_columns = {}
                        for table in tables:
                            all_columns[table.name] = self.db_manager.get_table_columns(table.name)
                        
                        return [TextContent(
                            type="text",
                            text=json.dumps(all_columns, indent=2)
                        )]
                
                elif name == "import_file":
                    if not self.config.enable_file_import:
                        return [TextContent(
                            type="text",
                            text="Error: File import is disabled in server configuration"
                        )]
                    
                    file_path = arguments.get("file_path", "")
                    table_name = arguments.get("table_name")
                    
                    if not file_path:
                        return [TextContent(type="text", text="Error: file_path is required")]
                    
                    # Import the file
                    result = self.file_importer.import_file(file_path)
                    
                    # Check if it's a BatchImportResult (SQLite or multi-sheet Excel)
                    if isinstance(result, BatchImportResult):
                        # Handle SQLite database import
                        if result.success and result.successful_imports:
                            # Get file type from first import result
                            first_import = result.successful_imports[0]
                            
                            if first_import.file_type == 'sqlite':
                                # Attach SQLite database
                                try:
                                    tables = self.db_manager.attach_sqlite_database(
                                        file_path,
                                        table_name or Path(file_path).stem
                                    )
                                    
                                    import json
                                    return [TextContent(
                                        type="text",
                                        text=json.dumps({
                                            "success": True,
                                            "file_type": "sqlite",
                                            "tables_imported": [t.name for t in tables],
                                            "total_tables": len(tables),
                                            "message": f"Successfully imported {len(tables)} tables from SQLite database"
                                        }, indent=2)
                                    )]
                                except Exception as e:
                                    return [TextContent(
                                        type="text",
                                        text=f"Error attaching SQLite database: {str(e)}"
                                    )]
                        else:
                            return [TextContent(
                                type="text",
                                text=f"Error importing file: {result.warnings[0] if result.warnings else 'Unknown error'}"
                            )]
                    
                    # Handle regular ImportResult (CSV, Parquet, single Excel sheet)
                    if result.success and result.dataframe is not None:
                        # Determine table name
                        if not table_name:
                            table_name = self.file_importer.get_suggested_table_name(file_path)
                        
                        # Register with database
                        try:
                            metadata = self.db_manager.register_table(
                                name=table_name,
                                dataframe=result.dataframe,
                                file_path=file_path,
                                file_type=result.file_type
                            )
                            
                            import json
                            return [TextContent(
                                type="text",
                                text=json.dumps({
                                    "success": True,
                                    "table_name": table_name,
                                    "row_count": metadata.row_count,
                                    "column_count": metadata.column_count,
                                    "columns": metadata.columns
                                }, indent=2)
                            )]
                        except Exception as e:
                            return [TextContent(
                                type="text",
                                text=f"Error registering table: {str(e)}"
                            )]
                    else:
                        return [TextContent(
                            type="text",
                            text=f"Error importing file: {result.error}"
                        )]
                
                else:
                    return [TextContent(
                        type="text",
                        text=f"Error: Unknown tool '{name}'"
                    )]
                    
            except Exception as e:
                logger.error(f"Error executing tool {name}: {e}")
                return [TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]
        
        # Prompt handlers
        @self.server.list_prompts()
        async def list_prompts() -> List[Prompt]:
            """List available prompts."""
            return [
                Prompt(
                    name="analyze_table",
                    description="Analyze a table and generate summary statistics",
                    arguments=[
                        {
                            "name": "table_name",
                            "description": "Name of the table to analyze",
                            "required": True
                        }
                    ]
                ),
                Prompt(
                    name="find_correlations",
                    description="Find correlations between numeric columns in a table",
                    arguments=[
                        {
                            "name": "table_name",
                            "description": "Name of the table to analyze",
                            "required": True
                        }
                    ]
                ),
                Prompt(
                    name="data_quality_check",
                    description="Check data quality (nulls, duplicates, outliers)",
                    arguments=[
                        {
                            "name": "table_name",
                            "description": "Name of the table to check",
                            "required": True
                        }
                    ]
                )
            ]
        
        @self.server.get_prompt()
        async def get_prompt(name: str, arguments: Dict[str, str]) -> GetPromptResult:
            """Get a specific prompt."""
            table_name = arguments.get("table_name", "")
            
            if name == "analyze_table":
                return GetPromptResult(
                    description=f"Analyze table {table_name}",
                    messages=[
                        PromptMessage(
                            role="user",
                            content=TextContent(
                                type="text",
                                text=f"""Please analyze the table '{table_name}' and provide:
1. Summary statistics for numeric columns (count, mean, std, min, max, quartiles)
2. Value counts for categorical columns (top 10 values)
3. Missing value analysis
4. Data type distribution
5. Any notable patterns or anomalies

Use SQL queries to gather this information."""
                            )
                        )
                    ]
                )
            
            elif name == "find_correlations":
                return GetPromptResult(
                    description=f"Find correlations in table {table_name}",
                    messages=[
                        PromptMessage(
                            role="user",
                            content=TextContent(
                                type="text",
                                text=f"""Please analyze correlations in the table '{table_name}':
1. Identify all numeric columns
2. Calculate correlation coefficients between numeric columns
3. Highlight strong correlations (|r| > 0.7)
4. Suggest potential relationships worth investigating

Use SQL queries and statistical analysis."""
                            )
                        )
                    ]
                )
            
            elif name == "data_quality_check":
                return GetPromptResult(
                    description=f"Check data quality for table {table_name}",
                    messages=[
                        PromptMessage(
                            role="user",
                            content=TextContent(
                                type="text",
                                text=f"""Please perform a data quality check on table '{table_name}':
1. Check for NULL values in each column
2. Identify duplicate rows
3. Find outliers in numeric columns (values beyond 3 standard deviations)
4. Check for inconsistent data formats
5. Identify any data integrity issues

Provide a summary report with recommendations."""
                            )
                        )
                    ]
                )
            
            else:
                raise ValueError(f"Unknown prompt: {name}")
    
    async def run(self) -> None:
        """Run the MCP server."""
        logger.info("Starting LocalSQL MCP Server...")
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )
    
    def cleanup(self) -> None:
        """Cleanup resources."""
        if self.db_manager:
            self.db_manager.close()
            logger.info("Database connection closed")
