"""
Main entry point for running LocalSQL Explorer as an MCP server.

This module provides a command-line interface for starting the MCP server
in standalone mode, allowing MCP clients like Claude Desktop to connect.

Usage:
    python -m localsql_explorer.mcp_main [--db-path PATH] [--max-rows N]
    
Or after installation:
    localsql-mcp [--db-path PATH] [--max-rows N]
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

from .mcp_server import LocalSQLMCPServer, MCPServerConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)  # MCP uses stdout for protocol, stderr for logs
    ]
)

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="LocalSQL Explorer MCP Server - Expose local data files to LLMs via Model Context Protocol"
    )
    
    parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        help="Path to DuckDB database file (default: in-memory database)"
    )
    
    parser.add_argument(
        "--max-rows",
        type=int,
        default=1000,
        help="Maximum number of rows to return from queries (default: 1000)"
    )
    
    parser.add_argument(
        "--disable-import",
        action="store_true",
        help="Disable file import functionality"
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: INFO)"
    )
    
    return parser.parse_args()


async def run_server(config: MCPServerConfig) -> None:
    """
    Run the MCP server.
    
    Args:
        config: Server configuration
    """
    server = None
    try:
        server = LocalSQLMCPServer(config)
        logger.info("LocalSQL MCP Server initialized")
        logger.info(f"Database: {config.db_path or 'in-memory'}")
        logger.info(f"Max query rows: {config.max_query_rows}")
        logger.info(f"File import: {'enabled' if config.enable_file_import else 'disabled'}")
        
        await server.run()
        
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        raise
    finally:
        if server:
            server.cleanup()
            logger.info("Server shutdown complete")


def main() -> int:
    """
    Main entry point for the MCP server.
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        args = parse_args()
        
        # Update logging level
        logging.getLogger().setLevel(getattr(logging, args.log_level))
        
        # Create server configuration
        config = MCPServerConfig(
            db_path=args.db_path,
            max_query_rows=args.max_rows,
            enable_file_import=not args.disable_import,
            log_level=args.log_level
        )
        
        # Run the server
        asyncio.run(run_server(config))
        
        return 0
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
