# MCP (Model Context Protocol) Integration Guide

## Overview

LocalSQL Explorer now supports the Model Context Protocol (MCP), enabling AI assistants like Claude to interact with your local data files directly. This allows LLMs to explore, query, and analyze your CSV, Excel, and Parquet files without uploading data to external servers.

## What is MCP?

The Model Context Protocol is a standardized way for LLMs to connect to external tools and data sources. LocalSQL Explorer's MCP server exposes your local database operations as:

- **Resources**: Read-only access to table lists, schemas, and sample data
- **Tools**: Executable actions like running queries and importing files
- **Prompts**: Templates for common data analysis tasks

## Installation

### 1. Install MCP Dependencies

The MCP SDK is included in the standard requirements:

```bash
cd d:\code\localSQL_explorer
pip install -r requirements.txt
```

Or install the package in development mode:

```bash
pip install -e .
```

### 2. Verify Installation

Check that the MCP server command is available:

```bash
localsql-mcp --help
```

## Running the MCP Server

### Standalone Mode (Recommended)

Start the MCP server with a specific database:

```bash
localsql-mcp --db-path path/to/your/database.duckdb
```

Or with an in-memory database:

```bash
localsql-mcp
```

### Command-Line Options

```
--db-path PATH          Path to DuckDB database file (default: in-memory)
--max-rows N            Maximum rows to return from queries (default: 1000)
--disable-import        Disable file import functionality
--log-level LEVEL       Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### Example

```bash
localsql-mcp --db-path my_data.duckdb --max-rows 500 --log-level DEBUG
```

## Configuring MCP Clients

### Claude Desktop

1. Locate your Claude Desktop configuration file:
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`

2. Add LocalSQL Explorer as an MCP server:

```json
{
  "mcpServers": {
    "localsql-explorer": {
      "command": "python",
      "args": [
        "-m",
        "localsql_explorer.mcp_main",
        "--db-path",
        "C:\\path\\to\\your\\database.duckdb"
      ]
    }
  }
}
```

3. Restart Claude Desktop

4. The MCP server should appear in the MCP menu (look for the 🔌 icon)

### Claude Code (CLI Tool) - RECOMMENDED FOR EASY SETUP

Claude Code provides simple CLI commands to add MCP servers without manually editing config files.

#### Option 1: Interactive Setup (Easiest)

```bash
claude mcp add
```

This will guide you through the setup interactively. When prompted:
- **Name**: `localsql-explorer`
- **Transport**: `stdio`
- **Command**: `python -m localsql_explorer.mcp_main`
- **Args**: `--db-path C:\path\to\your\database.duckdb` (or leave empty for in-memory)

#### Option 2: One-Line Command

```bash
claude mcp add --transport stdio localsql-explorer python -m localsql_explorer.mcp_main --db-path C:\path\to\database.duckdb
```

Or for an in-memory database:

```bash
claude mcp add --transport stdio localsql-explorer python -m localsql_explorer.mcp_main
```

#### Option 3: Add with Scope

To make the server available across all your projects:

```bash
claude mcp add --transport stdio --scope user localsql-explorer python -m localsql_explorer.mcp_main --db-path C:\path\to\database.duckdb
```

**Scope options:**
- `--scope local` (default): Available only in current session
- `--scope user`: Available across all your projects (stored in `~/.claude.json`)
- `--scope project`: Available to anyone working on the project (stored in `.mcp.json`)

#### Verify Installation

```bash
# List all configured MCP servers
claude mcp list

# Test the connection (run this in Claude Code)
/mcp
```

#### Remove Server (if needed)

```bash
claude mcp remove localsql-explorer
```

### VS Code with MCP Extension

If using VS Code with an MCP extension:

```json
{
  "mcp.servers": [
    {
      "name": "LocalSQL Explorer",
      "command": "localsql-mcp",
      "args": ["--db-path", "/path/to/database.duckdb"]
    }
  ]
}
```

## Available MCP Features

### Resources

Resources provide read-only access to database information:

- `localsql://tables/list` - List all tables with metadata
- `localsql://tables/{table_name}` - Get schema for a specific table
- `localsql://tables/{table_name}/sample` - Get sample rows (first 10)

### Tools

Tools allow the LLM to perform actions:

#### 1. execute_query
Execute SQL queries against the database.

**Parameters:**
- `sql` (required): SQL query to execute
- `limit` (optional): Maximum rows to return (default: 1000)

**Example:**
```
Execute this query: SELECT * FROM customers WHERE age > 30 LIMIT 10
```

#### 2. list_tables
List all tables in the database with metadata.

**Example:**
```
What tables are available in the database?
```

#### 3. get_table_info
Get detailed information about a specific table.

**Parameters:**
- `table_name` (required): Name of the table

**Example:**
```
Show me information about the sales table
```

#### 4. get_columns
Get column information for tables.

**Parameters:**
- `table_name` (optional): Specific table name, or all tables if omitted

**Example:**
```
What columns does the customers table have?
```

#### 5. import_file
Import a CSV, Excel, or Parquet file as a new table.

**Parameters:**
- `file_path` (required): Path to the file
- `table_name` (optional): Name for the table (defaults to filename)

**Example:**
```
Import this file: C:\data\sales_2024.csv
```

### Prompts

Prompts are templates for common data analysis tasks:

#### analyze_table
Generate comprehensive analysis of a table including summary statistics, missing values, and data types.

#### find_correlations
Identify correlations between numeric columns in a table.

#### data_quality_check
Check for data quality issues like nulls, duplicates, and outliers.

## Example Workflows

### Workflow 1: Exploring a New Dataset

```
User: What tables are in the database?
Claude: [Uses list_tables tool]

User: Show me the schema for the customers table
Claude: [Uses get_table_info tool]

User: Give me a sample of the data
Claude: [Uses execute_query tool with SELECT * FROM customers LIMIT 10]
```

### Workflow 2: Data Analysis

```
User: Analyze the sales table
Claude: [Uses analyze_table prompt, then executes multiple queries]

User: Find correlations between price and quantity
Claude: [Uses find_correlations prompt or executes correlation queries]
```

### Workflow 3: Importing and Querying

```
User: Import this file: C:\data\new_customers.csv
Claude: [Uses import_file tool]

User: How many customers are in each city?
Claude: [Uses execute_query with GROUP BY query]
```

## Security Considerations

### File System Access

The MCP server can:
- ✅ Read files you explicitly import
- ✅ Query data in the connected database
- ❌ Cannot access files outside specified paths
- ❌ Cannot modify or delete files

### Query Limits

- Queries are automatically limited to prevent memory issues (default: 1000 rows)
- You can adjust with `--max-rows` parameter
- Non-SELECT queries (INSERT, UPDATE, DELETE) work on the database only

### Disabling File Import

For read-only access, disable file import:

```bash
localsql-mcp --db-path data.duckdb --disable-import
```

## Troubleshooting

### Server Won't Start

**Problem**: `ModuleNotFoundError: No module named 'mcp'`

**Solution**: Install dependencies:
```bash
pip install mcp>=0.9.0
```

### Claude Desktop Can't Connect

**Problem**: Server not appearing in MCP menu

**Solutions**:
1. Check config file path is correct
2. Verify JSON syntax in config file
3. Check server logs in Claude Desktop console
4. Restart Claude Desktop completely

### Query Timeout

**Problem**: Large queries timing out

**Solutions**:
1. Add LIMIT clause to queries
2. Increase `--max-rows` parameter
3. Optimize query with WHERE clauses

### Import Fails

**Problem**: File import returns error

**Solutions**:
1. Verify file path is absolute
2. Check file format is supported (CSV, XLSX, Parquet)
3. Ensure file is not corrupted
4. Check file permissions

## Advanced Usage

### Multiple Databases

Run multiple MCP servers for different databases:

```json
{
  "mcpServers": {
    "sales-db": {
      "command": "localsql-mcp",
      "args": ["--db-path", "C:\\data\\sales.duckdb"]
    },
    "customer-db": {
      "command": "localsql-mcp",
      "args": ["--db-path", "C:\\data\\customers.duckdb"]
    }
  }
}
```

### Custom Row Limits

For large datasets, adjust row limits:

```bash
localsql-mcp --db-path large_data.duckdb --max-rows 5000
```

### Debug Mode

Enable detailed logging:

```bash
localsql-mcp --db-path data.duckdb --log-level DEBUG
```

## API Reference

### MCPServerConfig

Configuration class for the MCP server.

**Fields:**
- `db_path` (str, optional): Path to DuckDB database
- `max_query_rows` (int): Maximum rows to return (default: 1000)
- `enable_file_import` (bool): Allow file imports (default: True)
- `log_level` (str): Logging level (default: "INFO")

### LocalSQLMCPServer

Main MCP server class.

**Methods:**
- `__init__(config: MCPServerConfig)`: Initialize server
- `run()`: Start the server (async)
- `cleanup()`: Close database connections

## Support

For issues or questions:
- GitHub Issues: https://github.com/pgsteven89/localsql-explorer/issues
- Documentation: https://localsql-explorer.readthedocs.io/
- MCP Specification: https://modelcontextprotocol.io/

## Next Steps

- Explore the [MCP Specification](https://modelcontextprotocol.io/)
- Try the example workflows above
- Build custom prompts for your use cases
- Integrate with other MCP-compatible tools
