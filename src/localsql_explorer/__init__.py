"""
LocalSQL Explorer - A local desktop application for exploring and querying CSV, XLSX, and Parquet files using SQL.

This package provides the core functionality for importing datasets, treating them as tables
within an embedded DuckDB database, and running SQL queries with an interactive interface.
"""

__version__ = "0.1.0"
__author__ = "Phillip Stevens"
__license__ = "MIT"

from .database import DatabaseManager
from .importer import FileImporter
from .exporter import ResultExporter

__all__ = ["DatabaseManager", "FileImporter", "ResultExporter"]