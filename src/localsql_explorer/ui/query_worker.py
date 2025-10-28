"""
Background query execution worker for LocalSQL Explorer.

Provides non-blocking query execution using Qt threading to prevent UI freezing
during long-running queries.
"""

import logging
from typing import Optional, List, Dict, Any

from PyQt6.QtCore import QThread, pyqtSignal

from ..database import DatabaseManager, QueryResult

logger = logging.getLogger(__name__)


class QueryWorker(QThread):
    """
    Background worker thread for executing SQL queries.
    
    Signals:
        progress_update: Emitted with (message: str, percentage: int) during execution
        query_finished: Emitted with QueryResult when query completes
        query_error: Emitted with (sql: str, error_message: str) on error
    """
    
    # Signals
    progress_update = pyqtSignal(str, int)  # message, percentage
    query_finished = pyqtSignal(object)  # QueryResult
    query_error = pyqtSignal(str, str)  # sql, error_message
    
    def __init__(self, db_manager: DatabaseManager, sql: str, parent=None):
        """
        Initialize the query worker.
        
        Args:
            db_manager: Database manager instance
            sql: SQL query to execute
            parent: Optional parent QObject
        """
        super().__init__(parent)
        self.db_manager = db_manager
        self.sql = sql
        self._is_cancelled = False
    
    def run(self):
        """Execute the query in a background thread."""
        try:
            logger.info(f"Starting background query execution: {self.sql[:100]}...")
            
            # Update progress
            self.progress_update.emit("Executing query...", 30)
            
            # Execute the query
            result = self.db_manager.execute_query(self.sql)
            
            # Check if cancelled
            if self._is_cancelled:
                logger.info("Query execution was cancelled")
                return
            
            # Update progress
            self.progress_update.emit("Processing results...", 70)
            
            # Check for errors
            if not result.success:
                self.query_error.emit(self.sql, result.error or "Query failed")
                return
            
            # Update progress
            self.progress_update.emit("Finalizing...", 90)
            
            # Emit success signal
            self.query_finished.emit(result)
            
            logger.info(f"Background query completed successfully: {result.row_count} rows")
            
        except Exception as e:
            logger.error(f"Background query execution failed: {e}", exc_info=True)
            self.query_error.emit(self.sql, str(e))
    
    def cancel(self):
        """Request cancellation of the query."""
        self._is_cancelled = True
        logger.info("Query cancellation requested")


class PaginatedQueryWorker(QThread):
    """
    Background worker thread for setting up paginated query execution.
    
    Signals:
        progress_update: Emitted with (message: str, percentage: int) during execution
        paginator_ready: Emitted with paginator when setup completes
        query_error: Emitted with (sql: str, error_message: str) on error
    """
    
    # Signals
    progress_update = pyqtSignal(str, int)  # message, percentage
    paginator_ready = pyqtSignal(object)  # paginator
    query_error = pyqtSignal(str, str)  # sql, error_message
    
    def __init__(self, db_manager: DatabaseManager, sql: str, parent=None):
        """
        Initialize the paginated query worker.
        
        Args:
            db_manager: Database manager instance
            sql: SQL query to execute
            parent: Optional parent QObject
        """
        super().__init__(parent)
        self.db_manager = db_manager
        self.sql = sql
        self._is_cancelled = False
    
    def run(self):
        """Set up paginated query execution in a background thread."""
        try:
            logger.info(f"Setting up paginated query: {self.sql[:100]}...")
            
            # Update progress
            self.progress_update.emit("Setting up pagination...", 30)
            
            # Create paginator
            paginator = self.db_manager.create_query_paginator(self.sql)
            
            # Check if cancelled
            if self._is_cancelled:
                logger.info("Paginator setup was cancelled")
                return
            
            # Update progress
            self.progress_update.emit("Loading first page...", 70)
            
            # Emit success signal
            self.paginator_ready.emit(paginator)
            
            logger.info("Paginated query setup completed successfully")
            
        except Exception as e:
            logger.error(f"Paginated query setup failed: {e}", exc_info=True)
            self.query_error.emit(self.sql, str(e))
    
    def cancel(self):
        """Request cancellation of the paginator setup."""
        self._is_cancelled = True
        logger.info("Paginator setup cancellation requested")


class MultiQueryWorker(QThread):
    """
    Background worker thread for executing multiple SQL queries sequentially.
    
    Signals:
        progress_update: Emitted with (message: str, current: int, total: int) during execution
        query_completed: Emitted with query result dict after each query
        all_queries_finished: Emitted with summary dict when all queries complete
        query_error: Emitted with (query_num: int, sql: str, error: str) on individual query error
    """
    
    # Signals
    progress_update = pyqtSignal(str, int, int)  # message, current, total
    query_completed = pyqtSignal(dict)  # query result summary
    all_queries_finished = pyqtSignal(dict)  # overall summary
    query_error = pyqtSignal(int, str, str)  # query_num, sql, error_message
    
    def __init__(self, db_manager: DatabaseManager, queries: List[str], parent=None):
        """
        Initialize the multi-query worker.
        
        Args:
            db_manager: Database manager instance
            queries: List of SQL queries to execute
            parent: Optional parent QObject
        """
        super().__init__(parent)
        self.db_manager = db_manager
        self.queries = queries
        self._is_cancelled = False
    
    def run(self):
        """Execute all queries sequentially in a background thread."""
        total_queries = len(self.queries)
        successful = 0
        failed = 0
        total_rows = 0
        total_time = 0.0
        results_summary = []
        
        logger.info(f"Starting background execution of {total_queries} queries")
        
        for idx, query in enumerate(self.queries, 1):
            # Check if cancelled
            if self._is_cancelled:
                logger.info(f"Multi-query execution cancelled at query {idx}/{total_queries}")
                break
            
            query = query.strip()
            if not query:
                continue
            
            # Update progress
            self.progress_update.emit(
                f"Executing query {idx} of {total_queries}...",
                idx - 1,
                total_queries
            )
            
            try:
                # Execute query
                result = self.db_manager.execute_query(query)
                
                if result.success:
                    successful += 1
                    row_count = result.row_count
                    total_rows += row_count
                    total_time += result.execution_time
                    
                    query_result = {
                        'query_num': idx,
                        'status': 'Success',
                        'rows': row_count,
                        'time': result.execution_time,
                        'query': query[:100] + ('...' if len(query) > 100 else ''),
                        'full_query': query,
                        'data': result.data,
                        'success': True
                    }
                    
                    results_summary.append(query_result)
                    self.query_completed.emit(query_result)
                    
                else:
                    failed += 1
                    error_msg = result.error or "Query failed"
                    
                    query_result = {
                        'query_num': idx,
                        'status': 'Failed',
                        'rows': 0,
                        'time': result.execution_time,
                        'query': query[:100] + ('...' if len(query) > 100 else ''),
                        'full_query': query,
                        'error': error_msg,
                        'success': False
                    }
                    
                    results_summary.append(query_result)
                    self.query_error.emit(idx, query, error_msg)
                    
            except Exception as e:
                failed += 1
                error_msg = str(e)
                logger.error(f"Query {idx} execution failed: {error_msg}", exc_info=True)
                
                query_result = {
                    'query_num': idx,
                    'status': 'Failed',
                    'rows': 0,
                    'time': 0.0,
                    'query': query[:100] + ('...' if len(query) > 100 else ''),
                    'full_query': query,
                    'error': error_msg,
                    'success': False
                }
                
                results_summary.append(query_result)
                self.query_error.emit(idx, query, error_msg)
        
        # Emit completion summary
        summary = {
            'total_queries': total_queries,
            'successful': successful,
            'failed': failed,
            'total_rows': total_rows,
            'total_time': total_time,
            'cancelled': self._is_cancelled,
            'results': results_summary
        }
        
        self.all_queries_finished.emit(summary)
        logger.info(f"Multi-query execution completed: {successful} successful, {failed} failed")
    
    def cancel(self):
        """Request cancellation of multi-query execution."""
        self._is_cancelled = True
        logger.info("Multi-query execution cancellation requested")

