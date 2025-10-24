"""
Enhanced query error and metrics dialog for LocalSQL Explorer.

Provides detailed information about:
- Query execution results and timing
- Detailed error messages with suggestions
- Query performance metrics
- Result statistics
"""

import logging
import re
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QTextEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QDialogButtonBox, QGroupBox, QFormLayout, QProgressBar
)
from PyQt6.QtGui import QFont

import pandas as pd

from .styling import setup_text_selection_colors

logger = logging.getLogger(__name__)


class QueryErrorDialog(QDialog):
    """Dialog for displaying detailed query error information."""
    
    def __init__(self, parent=None, sql: str = "", error_message: str = ""):
        super().__init__(parent)
        self.sql = sql
        self.error_message = error_message
        
        self.setWindowTitle("Query Error Details")
        self.setModal(True)
        self.resize(600, 450)
        
        self.init_ui()
        self.analyze_error()
        
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Error summary
        summary_group = QGroupBox("Error Summary")
        summary_layout = QVBoxLayout(summary_group)
        
        self.error_label = QLabel("Query execution failed")
        self.error_label.setStyleSheet("color: red; font-weight: bold; font-size: 14px;")
        summary_layout.addWidget(self.error_label)
        
        # Error details
        self.error_text = QTextEdit()
        self.error_text.setMaximumHeight(100)
        self.error_text.setReadOnly(True)
        self.error_text.setStyleSheet("font-family: monospace; background-color: #ffe6e6;")
        setup_text_selection_colors(self.error_text, False)  # Assume light theme for error dialog
        summary_layout.addWidget(self.error_text)
        
        layout.addWidget(summary_group)
        
        # Tabbed details
        self.tabs = QTabWidget()
        
        # Query tab
        self.create_query_tab()
        
        # Suggestions tab
        self.create_suggestions_tab()
        
        # Help tab
        self.create_help_tab()
        
        layout.addWidget(self.tabs)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)
        
    def create_query_tab(self):
        """Create query details tab."""
        query_widget = QWidget()
        layout = QVBoxLayout(query_widget)
        
        layout.addWidget(QLabel("SQL Query:"))
        
        self.query_text = QTextEdit()
        self.query_text.setReadOnly(True)
        self.query_text.setMaximumHeight(150)
        self.query_text.setStyleSheet("font-family: monospace; background-color: #f5f5f5;")
        self.query_text.setPlainText(self.sql)
        setup_text_selection_colors(self.query_text, False)  # Assume light theme
        layout.addWidget(self.query_text)
        
        # Highlight problematic line if possible
        self.highlight_error_line()
        
        self.tabs.addTab(query_widget, "Query")
        
    def create_suggestions_tab(self):
        """Create suggestions tab."""
        suggestions_widget = QWidget()
        layout = QVBoxLayout(suggestions_widget)
        
        layout.addWidget(QLabel("Suggestions to fix this error:"))
        
        self.suggestions_text = QTextEdit()
        self.suggestions_text.setReadOnly(True)
        setup_text_selection_colors(self.suggestions_text, False)  # Assume light theme
        layout.addWidget(self.suggestions_text)
        
        self.tabs.addTab(suggestions_widget, "Suggestions")
        
    def create_help_tab(self):
        """Create help tab."""
        help_widget = QWidget()
        layout = QVBoxLayout(help_widget)
        
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        setup_text_selection_colors(help_text, False)  # Assume light theme
        help_text.setHtml("""
        <h3>Common SQL Error Types:</h3>
        <ul>
        <li><b>Syntax Error:</b> Check for missing commas, quotes, or keywords</li>
        <li><b>Column Not Found:</b> Verify column names exist in the table</li>
        <li><b>Table Not Found:</b> Check table name spelling and that table exists</li>
        <li><b>Type Mismatch:</b> Ensure data types are compatible in operations</li>
        <li><b>Aggregate Error:</b> Use GROUP BY when mixing aggregate and non-aggregate columns</li>
        </ul>
        
        <h3>Tips:</h3>
        <ul>
        <li>Use <code>DESCRIBE table_name</code> to see column details</li>
        <li>Use <code>SELECT * FROM table_name LIMIT 5</code> to preview data</li>
        <li>Check for case sensitivity in table and column names</li>
        </ul>
        """)
        layout.addWidget(help_text)
        
        self.tabs.addTab(help_widget, "Help")
        
    def analyze_error(self):
        """Analyze the error and provide suggestions."""
        self.error_text.setPlainText(self.error_message)
        
        suggestions = []
        error_lower = self.error_message.lower()
        
        # Common error patterns and suggestions
        if "column" in error_lower and "not found" in error_lower:
            suggestions.append("• Check column name spelling and case sensitivity")
            suggestions.append("• Use DESCRIBE table_name to see available columns")
            suggestions.append("• Verify you're querying the correct table")
            suggestions.append("• Check if column names in your query match the actual table schema")
            
            # Try to extract the problematic column name
            column_match = re.search(r"column['\s]*(['\"]?)(\w+)\1", self.error_message, re.IGNORECASE)
            if column_match:
                problematic_column = column_match.group(2)
                suggestions.append(f"• The column '{problematic_column}' was not found - check if it exists")
            
        elif "binder error" in error_lower and "column" in error_lower:
            suggestions.append("• This is a column binding error - the column doesn't exist")
            suggestions.append("• Use DESCRIBE table_name; to see available columns")
            suggestions.append("• Check for typos in column names")
            suggestions.append("• Verify the table alias is correct if using table aliases")
            
        elif "table" in error_lower and ("not found" in error_lower or "does not exist" in error_lower):
            suggestions.append("• Check table name spelling and case sensitivity") 
            suggestions.append("• Verify the table has been imported or created")
            suggestions.append("• Check the Tables panel to see available tables")
            suggestions.append("• Use File → Import Data to import required tables")
            suggestions.append("• Use 'SHOW TABLES;' to list all available tables")
            
        elif "catalog error" in error_lower:
            suggestions.append("• This is a DuckDB catalog error - usually table/column not found")
            suggestions.append("• Check that all referenced tables exist in the database")
            suggestions.append("• Verify table names match exactly (case sensitive)")
            suggestions.append("• Import missing tables using File → Import Data")
            
        elif "syntax error" in error_lower:
            suggestions.append("• Check for missing commas between column names")
            suggestions.append("• Verify all quotes are properly closed")
            suggestions.append("• Check for reserved keywords used as column names")
            suggestions.append("• Ensure proper parentheses matching")
            
        elif "group by" in error_lower:
            suggestions.append("• Include all non-aggregate columns in GROUP BY clause")
            suggestions.append("• Or use aggregate functions (COUNT, SUM, AVG) for all columns")
            
        elif "binder error" in error_lower:
            suggestions.append("• This is typically a column or table reference error")
            suggestions.append("• Check that all referenced columns exist")
            suggestions.append("• Verify table aliases are used correctly")
            
        else:
            suggestions.append("• Review the SQL syntax carefully")
            suggestions.append("• Try running a simpler version of the query first")
            suggestions.append("• Check the Help tab for common error patterns")
        
        if suggestions:
            self.suggestions_text.setPlainText("\\n".join(suggestions))
        else:
            self.suggestions_text.setPlainText("No specific suggestions available for this error type.")
            
    def highlight_error_line(self):
        """Attempt to highlight the line with the error."""
        # Look for line number in error message
        line_match = re.search(r"line (\d+)", self.error_message, re.IGNORECASE)
        if line_match:
            line_num = int(line_match.group(1))
            # Could implement line highlighting here
            logger.debug(f"Error on line {line_num}")


class QueryMetricsDialog(QDialog):
    """Dialog for displaying detailed query execution metrics."""
    
    def __init__(self, parent=None, sql: str = "", result_data: pd.DataFrame = None, 
                 execution_time: float = 0.0):
        super().__init__(parent)
        self.sql = sql
        self.result_data = result_data
        self.execution_time = execution_time
        
        self.setWindowTitle("Query Execution Metrics")
        self.setModal(True)
        self.resize(700, 500)
        
        self.init_ui()
        self.populate_metrics()
        
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Summary section
        summary_group = QGroupBox("Execution Summary")
        summary_layout = QFormLayout(summary_group)
        
        self.execution_time_label = QLabel()
        self.rows_label = QLabel()
        self.columns_label = QLabel()
        self.memory_label = QLabel()
        
        summary_layout.addRow("Execution Time:", self.execution_time_label)
        summary_layout.addRow("Rows Returned:", self.rows_label)
        summary_layout.addRow("Columns:", self.columns_label)
        summary_layout.addRow("Estimated Memory:", self.memory_label)
        
        layout.addWidget(summary_group)
        
        # Tabbed details
        self.tabs = QTabWidget()
        
        # Column statistics tab
        self.create_column_stats_tab()
        
        # Data types tab
        self.create_data_types_tab()
        
        # Query details tab
        self.create_query_details_tab()
        
        layout.addWidget(self.tabs)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)
        
    def create_column_stats_tab(self):
        """Create column statistics tab."""
        stats_widget = QWidget()
        layout = QVBoxLayout(stats_widget)
        
        self.stats_table = QTableWidget()
        layout.addWidget(self.stats_table)
        
        self.tabs.addTab(stats_widget, "Column Statistics")
        
    def create_data_types_tab(self):
        """Create data types tab."""
        types_widget = QWidget()
        layout = QVBoxLayout(types_widget)
        
        self.types_table = QTableWidget()
        layout.addWidget(self.types_table)
        
        self.tabs.addTab(types_widget, "Data Types")
        
    def create_query_details_tab(self):
        """Create query details tab."""
        query_widget = QWidget()
        layout = QVBoxLayout(query_widget)
        
        layout.addWidget(QLabel("Executed SQL Query:"))
        
        query_text = QTextEdit()
        query_text.setReadOnly(True)
        query_text.setPlainText(self.sql)
        query_text.setStyleSheet("font-family: monospace; background-color: #f5f5f5;")
        setup_text_selection_colors(query_text, False)  # Assume light theme
        layout.addWidget(query_text)
        
        self.tabs.addTab(query_widget, "Query")
        
    def populate_metrics(self):
        """Populate the metrics with actual data."""
        if self.result_data is None:
            return
            
        # Summary metrics
        self.execution_time_label.setText(f"{self.execution_time:.3f} seconds")
        self.rows_label.setText(f"{len(self.result_data):,}")
        self.columns_label.setText(str(len(self.result_data.columns)))
        
        # Estimate memory usage
        memory_bytes = self.result_data.memory_usage(deep=True).sum()
        memory_mb = memory_bytes / (1024 * 1024)
        self.memory_label.setText(f"{memory_mb:.2f} MB")
        
        # Column statistics
        self.populate_column_stats()
        
        # Data types
        self.populate_data_types()
        
    def populate_column_stats(self):
        """Populate column statistics table."""
        if self.result_data is None or self.result_data.empty:
            return
            
        numeric_cols = self.result_data.select_dtypes(include=['number']).columns
        
        if len(numeric_cols) == 0:
            self.stats_table.setRowCount(1)
            self.stats_table.setColumnCount(1)
            self.stats_table.setItem(0, 0, QTableWidgetItem("No numeric columns for statistics"))
            return
            
        stats = self.result_data[numeric_cols].describe()
        
        self.stats_table.setRowCount(len(stats.index))
        self.stats_table.setColumnCount(len(stats.columns))
        
        # Set headers
        self.stats_table.setVerticalHeaderLabels(stats.index.astype(str))
        self.stats_table.setHorizontalHeaderLabels(stats.columns.astype(str))
        
        # Populate data
        for i, stat_name in enumerate(stats.index):
            for j, col_name in enumerate(stats.columns):
                value = stats.loc[stat_name, col_name]
                if pd.isna(value):
                    item_text = "N/A"
                else:
                    item_text = f"{value:.3f}" if isinstance(value, float) else str(value)
                    
                self.stats_table.setItem(i, j, QTableWidgetItem(item_text))
                
        self.stats_table.resizeColumnsToContents()
        
    def populate_data_types(self):
        """Populate data types table."""
        if self.result_data is None:
            return
            
        dtypes = self.result_data.dtypes
        null_counts = self.result_data.isnull().sum()
        
        self.types_table.setRowCount(len(dtypes))
        self.types_table.setColumnCount(4)
        self.types_table.setHorizontalHeaderLabels([
            "Column", "Data Type", "Null Count", "Non-Null %"
        ])
        
        total_rows = len(self.result_data)
        
        for i, (col_name, dtype) in enumerate(dtypes.items()):
            # Column name
            self.types_table.setItem(i, 0, QTableWidgetItem(str(col_name)))
            
            # Data type
            self.types_table.setItem(i, 1, QTableWidgetItem(str(dtype)))
            
            # Null count
            null_count = null_counts[col_name]
            self.types_table.setItem(i, 2, QTableWidgetItem(str(null_count)))
            
            # Non-null percentage
            non_null_pct = ((total_rows - null_count) / total_rows * 100) if total_rows > 0 else 0
            self.types_table.setItem(i, 3, QTableWidgetItem(f"{non_null_pct:.1f}%"))
            
        self.types_table.resizeColumnsToContents()