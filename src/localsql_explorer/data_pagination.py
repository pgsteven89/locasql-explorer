"""
Data pagination system for handling large datasets efficiently.

This module provides:
- Chunked data loading with configurable page sizes
- Lazy loading for memory-efficient data access
- Progress tracking for large operations
- Adaptive pagination based on data characteristics
- Memory usage monitoring and optimization
"""

import logging
import time
from typing import Optional, Iterator, Tuple, Dict, Any, Callable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import duckdb

logger = logging.getLogger(__name__)


@dataclass
class PaginationConfig:
    """Configuration for data pagination."""
    
    # Page size settings
    default_page_size: int = 1000
    max_page_size: int = 10000
    min_page_size: int = 100
    
    # Memory thresholds (in MB)
    memory_threshold_mb: float = 100.0
    warning_threshold_mb: float = 500.0
    
    # Performance settings
    chunk_size: int = 10000
    max_memory_usage_mb: float = 1000.0
    
    # UI update frequency
    progress_update_interval: int = 1000  # Update every N rows


@dataclass
class PageInfo:
    """Information about a data page."""
    
    page_number: int
    page_size: int
    total_rows: int
    total_pages: int
    start_row: int
    end_row: int
    has_next: bool
    has_previous: bool
    memory_usage_mb: float = 0.0


@dataclass
class DataChunk:
    """A chunk of data with metadata."""
    
    data: pd.DataFrame
    chunk_number: int
    total_chunks: int
    start_row: int
    end_row: int
    memory_usage_mb: float
    load_time_seconds: float


class DataPaginator:
    """
    Handles pagination of large datasets with memory optimization.
    
    Features:
    - Adaptive page sizing based on data characteristics
    - Memory usage monitoring and warnings
    - Progress callbacks for UI updates
    - Caching of recently accessed pages
    - Lazy loading with on-demand data retrieval
    """
    
    def __init__(self, config: Optional[PaginationConfig] = None):
        """Initialize the paginator with configuration."""
        self.config = config or PaginationConfig()
        self.page_cache: Dict[int, pd.DataFrame] = {}
        self.cache_size_limit = 5  # Keep 5 pages in cache
        self.total_rows: Optional[int] = None
        self.current_page = 0
        
    def get_optimal_page_size(self, estimated_row_size_bytes: int, total_rows: int) -> int:
        """
        Calculate optimal page size based on data characteristics.
        
        Args:
            estimated_row_size_bytes: Estimated size of one row in bytes
            total_rows: Total number of rows in dataset
            
        Returns:
            int: Optimal page size
        """
        # Calculate page size to stay within memory threshold
        target_memory_bytes = self.config.memory_threshold_mb * 1024 * 1024
        optimal_size = max(
            self.config.min_page_size,
            min(
                self.config.max_page_size,
                target_memory_bytes // estimated_row_size_bytes
            )
        )
        
        # Adjust for very small datasets
        if total_rows < optimal_size:
            optimal_size = min(self.config.default_page_size, total_rows)
        
        logger.info(f"Calculated optimal page size: {optimal_size} for {total_rows} rows")
        return optimal_size
    
    def estimate_row_size(self, sample_df: pd.DataFrame) -> int:
        """
        Estimate the size of one row based on a sample.
        
        Args:
            sample_df: Sample dataframe to analyze
            
        Returns:
            int: Estimated row size in bytes
        """
        if len(sample_df) == 0:
            return 1024  # Default estimate
        
        memory_usage = sample_df.memory_usage(deep=True).sum()
        row_size = memory_usage // len(sample_df)
        
        logger.debug(f"Estimated row size: {row_size} bytes")
        return max(row_size, 64)  # Minimum 64 bytes per row
    
    def get_page_info(self, page_number: int, page_size: int, total_rows: int) -> PageInfo:
        """
        Get information about a specific page.
        
        Args:
            page_number: Zero-based page number
            page_size: Number of rows per page
            total_rows: Total number of rows
            
        Returns:
            PageInfo: Information about the page
        """
        total_pages = (total_rows + page_size - 1) // page_size
        start_row = page_number * page_size
        end_row = min(start_row + page_size, total_rows)
        
        return PageInfo(
            page_number=page_number,
            page_size=page_size,
            total_rows=total_rows,
            total_pages=total_pages,
            start_row=start_row,
            end_row=end_row,
            has_next=page_number < total_pages - 1,
            has_previous=page_number > 0
        )
    
    def clear_cache(self):
        """Clear the page cache to free memory."""
        self.page_cache.clear()
        logger.debug("Page cache cleared")
    
    def _manage_cache(self, page_number: int, data: pd.DataFrame):
        """Manage page cache size and add new data."""
        # Remove oldest entries if cache is full
        if len(self.page_cache) >= self.cache_size_limit:
            # Remove the page furthest from current page
            current_pages = list(self.page_cache.keys())
            if current_pages:
                furthest_page = max(current_pages, key=lambda p: abs(p - page_number))
                del self.page_cache[furthest_page]
        
        self.page_cache[page_number] = data


class QueryPaginator(DataPaginator):
    """
    Paginator for SQL query results.
    
    Handles pagination of query results with lazy loading from database.
    """
    
    def __init__(self, connection: duckdb.DuckDBPyConnection, 
                 sql: str, config: Optional[PaginationConfig] = None):
        """
        Initialize query paginator.
        
        Args:
            connection: DuckDB connection
            sql: SQL query to paginate
            config: Pagination configuration
        """
        super().__init__(config)
        self.connection = connection
        self.sql = sql.strip().rstrip(';')
        self.base_sql = self._prepare_base_sql(sql)
        self.total_rows = None
        self._sample_data = None
        
    def _prepare_base_sql(self, sql: str) -> str:
        """Prepare base SQL for pagination by wrapping in subquery if needed."""
        sql_upper = sql.upper().strip()
        
        # If it's a simple SELECT without ORDER BY, we can add LIMIT/OFFSET directly
        if (sql_upper.startswith('SELECT') and 
            'ORDER BY' not in sql_upper and 
            'LIMIT' not in sql_upper and
            'OFFSET' not in sql_upper):
            return sql
        
        # For complex queries, wrap in subquery
        return f"SELECT * FROM ({sql}) AS paginated_query"
    
    def get_total_rows(self) -> int:
        """Get total number of rows in query result."""
        if self.total_rows is None:
            try:
                count_sql = f"SELECT COUNT(*) as row_count FROM ({self.sql}) AS count_query"
                result = self.connection.execute(count_sql).fetchone()
                self.total_rows = result[0] if result else 0
                logger.info(f"Query result has {self.total_rows} total rows")
            except Exception as e:
                logger.error(f"Failed to get row count: {e}")
                self.total_rows = 0
        
        return self.total_rows
    
    def get_sample_data(self, sample_size: int = 100) -> pd.DataFrame:
        """Get a small sample of data for analysis."""
        if self._sample_data is None:
            try:
                sample_sql = f"{self.base_sql} LIMIT {sample_size}"
                self._sample_data = self.connection.execute(sample_sql).df()
                logger.debug(f"Retrieved sample data: {len(self._sample_data)} rows")
            except Exception as e:
                logger.error(f"Failed to get sample data: {e}")
                self._sample_data = pd.DataFrame()
        
        return self._sample_data
    
    def get_page(self, page_number: int, page_size: int, 
                 progress_callback: Optional[Callable[[str, int], None]] = None) -> Tuple[pd.DataFrame, PageInfo]:
        """
        Get a specific page of data.
        
        Args:
            page_number: Zero-based page number
            page_size: Number of rows per page
            progress_callback: Optional callback for progress updates
            
        Returns:
            Tuple[pd.DataFrame, PageInfo]: Page data and metadata
        """
        # Check cache first
        if page_number in self.page_cache:
            logger.debug(f"Retrieved page {page_number} from cache")
            total_rows = self.get_total_rows()
            page_info = self.get_page_info(page_number, page_size, total_rows)
            page_info.memory_usage_mb = self.page_cache[page_number].memory_usage(deep=True).sum() / (1024 * 1024)
            return self.page_cache[page_number], page_info
        
        if progress_callback:
            progress_callback(f"Loading page {page_number + 1}...", 10)
        
        try:
            # Calculate offset
            offset = page_number * page_size
            
            # Build paginated query
            paginated_sql = f"{self.base_sql} LIMIT {page_size} OFFSET {offset}"
            
            if progress_callback:
                progress_callback("Executing query...", 50)
            
            start_time = time.time()
            data = self.connection.execute(paginated_sql).df()
            load_time = time.time() - start_time
            
            if progress_callback:
                progress_callback("Processing results...", 80)
            
            # Get page info
            total_rows = self.get_total_rows()
            page_info = self.get_page_info(page_number, page_size, total_rows)
            page_info.memory_usage_mb = data.memory_usage(deep=True).sum() / (1024 * 1024)
            
            # Cache the page
            self._manage_cache(page_number, data)
            
            if progress_callback:
                progress_callback("Page loaded successfully", 100)
            
            logger.info(f"Loaded page {page_number}: {len(data)} rows in {load_time:.2f}s")
            return data, page_info
            
        except Exception as e:
            logger.error(f"Failed to load page {page_number}: {e}")
            if progress_callback:
                progress_callback(f"Error loading page: {e}", 0)
            raise
    
    def get_page_iterator(self, page_size: int, 
                         progress_callback: Optional[Callable[[str, int], None]] = None) -> Iterator[DataChunk]:
        """
        Get an iterator that yields data chunks.
        
        Args:
            page_size: Size of each chunk
            progress_callback: Optional callback for progress updates
            
        Yields:
            DataChunk: Chunks of data with metadata
        """
        total_rows = self.get_total_rows()
        total_chunks = (total_rows + page_size - 1) // page_size
        
        for chunk_number in range(total_chunks):
            if progress_callback:
                progress = int((chunk_number / total_chunks) * 100)
                progress_callback(f"Loading chunk {chunk_number + 1} of {total_chunks}", progress)
            
            start_time = time.time()
            data, page_info = self.get_page(chunk_number, page_size)
            load_time = time.time() - start_time
            
            yield DataChunk(
                data=data,
                chunk_number=chunk_number,
                total_chunks=total_chunks,
                start_row=page_info.start_row,
                end_row=page_info.end_row,
                memory_usage_mb=page_info.memory_usage_mb,
                load_time_seconds=load_time
            )


class FilePaginator(DataPaginator):
    """
    Paginator for large files (CSV, Parquet, etc.).
    
    Handles chunked reading of large files with memory optimization.
    """
    
    def __init__(self, file_path: Path, file_type: str, 
                 config: Optional[PaginationConfig] = None, **read_kwargs):
        """
        Initialize file paginator.
        
        Args:
            file_path: Path to the file
            file_type: Type of file (csv, parquet, excel)
            config: Pagination configuration
            **read_kwargs: Additional arguments for pandas read functions
        """
        super().__init__(config)
        self.file_path = file_path
        self.file_type = file_type.lower()
        self.read_kwargs = read_kwargs
        self.total_rows = None
        self._sample_data = None
        
    def get_total_rows(self) -> int:
        """Get total number of rows in file."""
        if self.total_rows is None:
            try:
                if self.file_type == 'csv':
                    # Quick row count for CSV
                    with open(self.file_path, 'r', encoding='utf-8') as f:
                        self.total_rows = sum(1 for _ in f) - 1  # Subtract header
                elif self.file_type == 'parquet':
                    # Use pandas to get shape
                    df = pd.read_parquet(self.file_path, **self.read_kwargs)
                    self.total_rows = len(df)
                else:
                    # Fallback: read entire file (not ideal for large files)
                    df = self._read_file()
                    self.total_rows = len(df)
                
                logger.info(f"File has {self.total_rows} total rows")
            except Exception as e:
                logger.error(f"Failed to get row count: {e}")
                self.total_rows = 0
        
        return self.total_rows
    
    def _read_file(self, **kwargs) -> pd.DataFrame:
        """Read file using appropriate pandas function."""
        read_kwargs = {**self.read_kwargs, **kwargs}
        
        if self.file_type == 'csv':
            return pd.read_csv(self.file_path, **read_kwargs)
        elif self.file_type == 'parquet':
            return pd.read_parquet(self.file_path, **read_kwargs)
        elif self.file_type in ['xlsx', 'xls']:
            return pd.read_excel(self.file_path, **read_kwargs)
        else:
            raise ValueError(f"Unsupported file type: {self.file_type}")
    
    def get_sample_data(self, sample_size: int = 100) -> pd.DataFrame:
        """Get a small sample of data for analysis."""
        if self._sample_data is None:
            try:
                if self.file_type == 'csv':
                    self._sample_data = pd.read_csv(self.file_path, nrows=sample_size, **self.read_kwargs)
                else:
                    # For other formats, read all and sample
                    full_data = self._read_file()
                    self._sample_data = full_data.head(sample_size)
                
                logger.debug(f"Retrieved sample data: {len(self._sample_data)} rows")
            except Exception as e:
                logger.error(f"Failed to get sample data: {e}")
                self._sample_data = pd.DataFrame()
        
        return self._sample_data
    
    def get_page(self, page_number: int, page_size: int,
                 progress_callback: Optional[Callable[[str, int], None]] = None) -> Tuple[pd.DataFrame, PageInfo]:
        """
        Get a specific page of data from file.
        
        Args:
            page_number: Zero-based page number
            page_size: Number of rows per page
            progress_callback: Optional callback for progress updates
            
        Returns:
            Tuple[pd.DataFrame, PageInfo]: Page data and metadata
        """
        # Check cache first
        if page_number in self.page_cache:
            logger.debug(f"Retrieved page {page_number} from cache")
            total_rows = self.get_total_rows()
            page_info = self.get_page_info(page_number, page_size, total_rows)
            page_info.memory_usage_mb = self.page_cache[page_number].memory_usage(deep=True).sum() / (1024 * 1024)
            return self.page_cache[page_number], page_info
        
        if progress_callback:
            progress_callback(f"Loading page {page_number + 1}...", 10)
        
        try:
            skip_rows = page_number * page_size
            
            if progress_callback:
                progress_callback("Reading file...", 50)
            
            start_time = time.time()
            
            if self.file_type == 'csv':
                # For CSV, we can use skiprows and nrows
                data = pd.read_csv(
                    self.file_path,
                    skiprows=range(1, skip_rows + 1) if skip_rows > 0 else None,
                    nrows=page_size,
                    **self.read_kwargs
                )
            else:
                # For other formats, read all and slice (not ideal for very large files)
                full_data = self._read_file()
                start_idx = skip_rows
                end_idx = min(start_idx + page_size, len(full_data))
                data = full_data.iloc[start_idx:end_idx].copy()
            
            load_time = time.time() - start_time
            
            if progress_callback:
                progress_callback("Processing data...", 80)
            
            # Get page info
            total_rows = self.get_total_rows()
            page_info = self.get_page_info(page_number, page_size, total_rows)
            page_info.memory_usage_mb = data.memory_usage(deep=True).sum() / (1024 * 1024)
            
            # Cache the page
            self._manage_cache(page_number, data)
            
            if progress_callback:
                progress_callback("Page loaded successfully", 100)
            
            logger.info(f"Loaded page {page_number}: {len(data)} rows in {load_time:.2f}s")
            return data, page_info
            
        except Exception as e:
            logger.error(f"Failed to load page {page_number}: {e}")
            if progress_callback:
                progress_callback(f"Error loading page: {e}", 0)
            raise


def get_memory_usage_mb() -> float:
    """Get current memory usage in MB."""
    try:
        import psutil
        import os
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 * 1024)
    except ImportError:
        # Fallback if psutil not available
        return 0.0


def format_memory_size(size_mb: float) -> str:
    """Format memory size in human-readable format."""
    if size_mb < 1:
        return f"{size_mb * 1024:.1f} KB"
    elif size_mb < 1024:
        return f"{size_mb:.1f} MB"
    else:
        return f"{size_mb / 1024:.2f} GB"