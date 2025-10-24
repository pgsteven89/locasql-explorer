"""
Models module for data structures and configuration.

This module contains Pydantic models for:
- Application configuration
- User preferences
- Data validation schemas
- API request/response models
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class AppTheme(BaseModel):
    """Application theme configuration."""
    
    name: str = Field("light", description="Theme name")
    is_dark: bool = Field(False, description="Whether this is a dark theme")
    colors: Dict[str, str] = Field(default_factory=dict, description="Theme color definitions")


class QueryHistory(BaseModel):
    """SQL query history entry."""
    
    id: str = Field(..., description="Unique query ID")
    sql: str = Field(..., description="SQL query text")
    timestamp: datetime = Field(default_factory=datetime.now, description="Execution timestamp")
    execution_time: float = Field(0.0, description="Execution time in seconds")
    success: bool = Field(True, description="Whether query executed successfully")
    row_count: Optional[int] = Field(None, description="Number of rows returned")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    @field_validator('sql')
    @classmethod
    def sql_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("SQL query cannot be empty")
        return v.strip()


class UserPreferences(BaseModel):
    """User preferences and settings."""
    
    # UI Preferences
    theme: str = Field("dark", description="Current theme name")
    dark_theme: bool = Field(True, description="Use dark theme")
    font_size: int = Field(12, description="Editor font size")
    font_family: str = Field("Consolas", description="Editor font family")
    
    # Editor Preferences
    auto_complete: bool = Field(True, description="Enable SQL auto-completion")
    syntax_highlight: bool = Field(True, description="Enable syntax highlighting")
    line_numbers: bool = Field(True, description="Show line numbers in editor")
    word_wrap: bool = Field(False, description="Enable word wrapping")
    
    # Query Preferences
    auto_limit: bool = Field(True, description="Automatically limit large result sets")
    default_limit: int = Field(1000, description="Default row limit for large results")
    query_timeout: int = Field(30, description="Query timeout in seconds")
    
    # File Preferences
    default_import_encoding: str = Field("utf-8", description="Default file encoding for imports")
    default_export_format: str = Field("csv", description="Default export format")
    
    # Window Preferences
    window_size: tuple = Field((1200, 800), description="Default window size")
    window_maximized: bool = Field(False, description="Start window maximized")
    remember_layout: bool = Field(True, description="Remember panel layout")
    
    @field_validator('font_size')
    @classmethod
    def font_size_valid(cls, v):
        if v < 8 or v > 24:
            raise ValueError("Font size must be between 8 and 24")
        return v
    
    @field_validator('default_limit')
    @classmethod
    def default_limit_valid(cls, v):
        if v < 100 or v > 100000:
            raise ValueError("Default limit must be between 100 and 100,000")
        return v


class DatabaseConfig(BaseModel):
    """Database configuration settings."""
    
    memory_limit: str = Field("1GB", description="DuckDB memory limit")
    thread_count: Optional[int] = Field(None, description="Number of threads (None for auto)")
    enable_profiling: bool = Field(False, description="Enable query profiling")
    auto_checkpoint: bool = Field(True, description="Enable automatic checkpointing")
    
    # Backup settings
    auto_backup: bool = Field(True, description="Enable automatic backups")
    backup_interval: int = Field(30, description="Backup interval in minutes")
    max_backups: int = Field(5, description="Maximum number of backups to keep")


class AppConfig(BaseModel):
    """Main application configuration."""
    
    # Application metadata
    app_name: str = Field("LocalSQL Explorer", description="Application name")
    version: str = Field("0.1.0", description="Application version")
    
    # Paths
    config_dir: Path = Field(..., description="Configuration directory path")
    data_dir: Path = Field(..., description="Data directory path")
    log_dir: Path = Field(..., description="Log directory path")
    
    # Logging
    log_level: str = Field("INFO", description="Logging level")
    log_to_file: bool = Field(True, description="Enable logging to file")
    max_log_size: int = Field(10 * 1024 * 1024, description="Maximum log file size in bytes")
    
    # User preferences
    preferences: UserPreferences = Field(default_factory=UserPreferences, description="User preferences")
    
    # Database configuration
    database: DatabaseConfig = Field(default_factory=DatabaseConfig, description="Database configuration")
    
    # Recent files
    recent_files: List[str] = Field(default_factory=list, description="Recently opened files")
    recent_databases: List[str] = Field(default_factory=list, description="Recently opened databases")
    max_recent_items: int = Field(10, description="Maximum number of recent items to remember")
    
    @field_validator('log_level')
    @classmethod
    def log_level_valid(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()
    
    def add_recent_file(self, file_path: Union[str, Path]) -> None:
        """Add a file to the recent files list."""
        file_path = str(Path(file_path).resolve())
        
        # Remove if already exists
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        
        # Add to beginning
        self.recent_files.insert(0, file_path)
        
        # Trim to max size
        if len(self.recent_files) > self.max_recent_items:
            self.recent_files = self.recent_files[:self.max_recent_items]
    
    def add_recent_database(self, db_path: Union[str, Path]) -> None:
        """Add a database to the recent databases list."""
        db_path = str(Path(db_path).resolve())
        
        # Remove if already exists
        if db_path in self.recent_databases:
            self.recent_databases.remove(db_path)
        
        # Add to beginning
        self.recent_databases.insert(0, db_path)
        
        # Trim to max size
        if len(self.recent_databases) > self.max_recent_items:
            self.recent_databases = self.recent_databases[:self.max_recent_items]


class TableSchema(BaseModel):
    """Schema information for a table."""
    
    table_name: str = Field(..., description="Table name")
    columns: List[Dict[str, Any]] = Field(..., description="Column information")
    row_count: int = Field(0, description="Number of rows")
    size_bytes: Optional[int] = Field(None, description="Table size in bytes")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    modified_at: datetime = Field(default_factory=datetime.now, description="Last modification timestamp")


class WorkspaceState(BaseModel):
    """Current workspace state for persistence."""
    
    # Database state
    database_path: Optional[str] = Field(None, description="Current database file path")
    tables: List[TableSchema] = Field(default_factory=list, description="Loaded tables")
    
    # Editor state
    current_sql: str = Field("", description="Current SQL in editor")
    query_history: List[QueryHistory] = Field(default_factory=list, description="Query execution history")
    
    # UI state
    selected_table: Optional[str] = Field(None, description="Currently selected table")
    panel_sizes: Dict[str, int] = Field(default_factory=dict, description="Panel size configuration")
    
    # Last activity
    last_saved: datetime = Field(default_factory=datetime.now, description="Last save timestamp")
    
    def add_query_to_history(self, query: QueryHistory) -> None:
        """Add a query to the history."""
        # Remove duplicates
        self.query_history = [q for q in self.query_history if q.sql != query.sql]
        
        # Add to beginning
        self.query_history.insert(0, query)
        
        # Limit history size
        if len(self.query_history) > 100:
            self.query_history = self.query_history[:100]