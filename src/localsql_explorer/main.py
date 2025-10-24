"""
Main entry point for LocalSQL Explorer application.

This module provides the main entry points for both GUI and CLI modes:
- GUI mode: Launch the PyQt6 desktop application
- CLI mode: Command-line interface for batch operations (future)
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from PyQt6.QtWidgets import QApplication

from .models import AppConfig, UserPreferences
from .ui.main_window import MainWindow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# CLI app using Typer
cli_app = typer.Typer(
    name="localsql-explorer",
    help="LocalSQL Explorer - A desktop application for querying CSV, Excel, and Parquet files with SQL",
    add_completion=False
)


def setup_app_config() -> AppConfig:
    """Set up application configuration."""
    # Create config directories
    config_dir = Path.home() / ".localsql_explorer"
    data_dir = config_dir / "data"
    log_dir = config_dir / "logs"
    
    # Ensure directories exist
    config_dir.mkdir(exist_ok=True)
    data_dir.mkdir(exist_ok=True)
    log_dir.mkdir(exist_ok=True)
    
    # Create configuration
    config = AppConfig(
        config_dir=config_dir,
        data_dir=data_dir,
        log_dir=log_dir
    )
    
    # Set up file logging
    if config.log_to_file:
        log_file = log_dir / "localsql_explorer.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, config.log_level))
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        logging.getLogger().addHandler(file_handler)
    
    return config


def gui_main(config: Optional[AppConfig] = None) -> int:
    """
    Launch the GUI application.
    
    Args:
        config: Optional application configuration
        
    Returns:
        int: Exit code
    """
    try:
        # Set up configuration
        if config is None:
            config = setup_app_config()
        
        # Create QApplication
        app = QApplication(sys.argv)
        app.setApplicationName("LocalSQL Explorer")
        app.setApplicationVersion(config.version)
        app.setApplicationDisplayName("LocalSQL Explorer")
        
        # Set application properties
        app.setOrganizationName("LocalSQL Explorer")
        app.setOrganizationDomain("localsql-explorer.com")
        
        # Create main window
        main_window = MainWindow(config)
        main_window.show()
        
        # Handle command line arguments for file opening
        if len(sys.argv) > 1:
            file_path = Path(sys.argv[1])
            if file_path.exists() and file_path.suffix.lower() in ['.csv', '.xlsx', '.xls', '.parquet', '.pq']:
                # TODO: Implement automatic file import on startup
                logger.info(f"File specified on command line: {file_path}")
        
        logger.info("Starting LocalSQL Explorer GUI")
        
        # Run the application
        return app.exec()
        
    except Exception as e:
        logger.error(f"Failed to start GUI application: {e}")
        return 1


@cli_app.command("gui")
def gui_command():
    """Launch the graphical user interface."""
    sys.exit(gui_main())


@cli_app.command("version")
def version_command():
    """Show version information."""
    config = setup_app_config()
    typer.echo(f"LocalSQL Explorer {config.version}")
    typer.echo(f"Python {sys.version}")


@cli_app.command("info")
def info_command():
    """Show application information and configuration."""
    config = setup_app_config()
    
    typer.echo("LocalSQL Explorer - Application Information")
    typer.echo("=" * 50)
    typer.echo(f"Version: {config.version}")
    typer.echo(f"Config Directory: {config.config_dir}")
    typer.echo(f"Data Directory: {config.data_dir}")
    typer.echo(f"Log Directory: {config.log_dir}")
    typer.echo(f"Log Level: {config.log_level}")
    typer.echo("")
    typer.echo("Supported File Formats:")
    typer.echo("  - CSV (.csv)")
    typer.echo("  - Excel (.xlsx, .xls)")
    typer.echo("  - Parquet (.parquet, .pq)")


@cli_app.command("query")
def query_command(
    file_path: str = typer.Argument(..., help="Path to data file"),
    sql: str = typer.Argument(..., help="SQL query to execute"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    format_type: str = typer.Option("csv", "--format", "-f", help="Output format (csv, xlsx, parquet)")
):
    """Execute a SQL query against a data file (CLI mode)."""
    try:
        # Import dependencies
        from .database import DatabaseManager
        from .importer import FileImporter
        from .exporter import ResultExporter
        
        # Initialize components
        db_manager = DatabaseManager()
        file_importer = FileImporter()
        result_exporter = ResultExporter()
        
        # Import file
        typer.echo(f"Importing file: {file_path}")
        import_result = file_importer.import_file(file_path)
        
        if not import_result.success:
            typer.echo(f"Error importing file: {import_result.error}", err=True)
            raise typer.Exit(1)
        
        # Register table
        table_name = file_importer.get_suggested_table_name(file_path)
        db_manager.register_table(table_name, import_result.dataframe)
        typer.echo(f"Registered table: {table_name}")
        
        # Execute query
        typer.echo(f"Executing query: {sql}")
        query_result = db_manager.execute_query(sql)
        
        if not query_result.success:
            typer.echo(f"Error executing query: {query_result.error}", err=True)
            raise typer.Exit(1)
        
        # Display or export results
        if output:
            # Export to file
            export_result = result_exporter.export_result(
                query_result.data,
                output,
                format_type
            )
            
            if export_result.success:
                typer.echo(f"Results exported to: {output}")
                typer.echo(f"Rows exported: {export_result.row_count}")
            else:
                typer.echo(f"Error exporting results: {export_result.error}", err=True)
                raise typer.Exit(1)
        else:
            # Display results to console
            typer.echo(f"Query executed successfully in {query_result.execution_time:.3f}s")
            typer.echo(f"Rows returned: {query_result.row_count}")
            typer.echo("")
            
            if query_result.data is not None and not query_result.data.empty:
                # Show first few rows
                typer.echo("Results (first 10 rows):")
                typer.echo(query_result.data.head(10).to_string(index=False))
                
                if len(query_result.data) > 10:
                    typer.echo(f"... and {len(query_result.data) - 10} more rows")
            else:
                typer.echo("No results returned")
        
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@cli_app.command("convert")
def convert_command(
    input_file: str = typer.Argument(..., help="Input file path"),
    output_file: str = typer.Argument(..., help="Output file path"),
    format_type: Optional[str] = typer.Option(None, "--format", "-f", help="Output format (auto-detect if not specified)")
):
    """Convert between different file formats."""
    try:
        from .importer import FileImporter
        from .exporter import ResultExporter
        
        # Initialize components
        file_importer = FileImporter()
        result_exporter = ResultExporter()
        
        # Import file
        typer.echo(f"Reading: {input_file}")
        import_result = file_importer.import_file(input_file)
        
        if not import_result.success:
            typer.echo(f"Error reading file: {import_result.error}", err=True)
            raise typer.Exit(1)
        
        # Export to new format
        typer.echo(f"Converting to: {output_file}")
        export_result = result_exporter.export_result(
            import_result.dataframe,
            output_file,
            format_type
        )
        
        if export_result.success:
            typer.echo(f"Conversion completed successfully")
            typer.echo(f"Rows: {export_result.row_count}")
            typer.echo(f"Output file: {export_result.file_path}")
        else:
            typer.echo(f"Error during conversion: {export_result.error}", err=True)
            raise typer.Exit(1)
            
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


def main():
    """Main entry point for the application."""
    # If no arguments provided, launch GUI
    if len(sys.argv) == 1:
        sys.exit(gui_main())
    else:
        # Use CLI
        cli_app()


if __name__ == "__main__":
    main()