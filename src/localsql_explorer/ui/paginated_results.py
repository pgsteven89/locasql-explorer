"""
Paginated results viewer for handling large datasets efficiently.

This module provides:
- Paginated table view with navigation controls
- Lazy loading of data pages
- Memory usage monitoring
- Export functionality for large datasets
- Search and filtering within pages
"""

import logging
import math
from decimal import Decimal
from typing import Optional, Callable, Dict, Any

import numpy as np

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QEvent
from PyQt6.QtGui import QFont, QAction
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QPushButton, QSpinBox, QProgressBar, QGroupBox, QFrame,
    QComboBox, QLineEdit, QCheckBox, QMessageBox, QSplitter,
    QHeaderView, QAbstractItemView, QMenu, QApplication
)

import pandas as pd

from ..data_pagination import QueryPaginator, PaginationConfig, PageInfo, format_memory_size, get_memory_usage_mb

logger = logging.getLogger(__name__)


class PaginationWorker(QThread):
    """Worker thread for loading data pages."""
    
    page_loaded = pyqtSignal(object, object)  # DataFrame, PageInfo
    progress_updated = pyqtSignal(str, int)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, paginator: QueryPaginator, page_number: int, page_size: int):
        super().__init__()
        self.paginator = paginator
        self.page_number = page_number
        self.page_size = page_size
    
    def run(self):
        """Load the data page in background thread."""
        try:
            def progress_callback(message: str, progress: int):
                self.progress_updated.emit(message, progress)
            
            data, page_info = self.paginator.get_page(
                self.page_number, 
                self.page_size, 
                progress_callback
            )
            self.page_loaded.emit(data, page_info)
            
        except Exception as e:
            logger.error(f"Failed to load page {self.page_number}: {e}")
            self.error_occurred.emit(str(e))


class PaginatedTableWidget(QWidget):
    """
    Table widget with pagination support for large datasets.
    
    Features:
    - Lazy loading of data pages
    - Navigation controls (first, previous, next, last)
    - Page size selection
    - Memory usage monitoring
    - Search within current page
    - Export functionality
    """
    
    # Signals
    export_requested = pyqtSignal(object)  # DataFrame (current page)
    export_all_requested = pyqtSignal()  # Request export of all results
    export_filtered_requested = pyqtSignal(object)  # DataFrame (filtered results)
    metrics_requested = pyqtSignal(str, object, str)  # SQL query, DataFrame, metrics_type ("original" or "filtered")
    status_updated = pyqtSignal(str)  # Status message for main window
    
    def __init__(self, paginator: Optional[QueryPaginator] = None, 
                 config: Optional[PaginationConfig] = None, parent=None):
        super().__init__(parent)
        
        self.paginator = paginator
        self.config = config or PaginationConfig()
        self.current_page = 0
        self.current_page_size = self.config.default_page_size
        self.current_data: Optional[pd.DataFrame] = None
        self.current_page_info: Optional[PageInfo] = None
        self.worker: Optional[PaginationWorker] = None
        
        # Filter state
        self.original_paginator: Optional[QueryPaginator] = None
        self.is_filtered = False
        self.filter_sql_condition = ""
        
        # Memory monitoring
        self.memory_timer = QTimer()
        self.memory_timer.timeout.connect(self.update_memory_usage)
        self.memory_timer.start(2000)  # Update every 2 seconds
        
        self.setup_ui()
        
        if self.paginator:
            self.load_initial_page()
    
    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Header with controls
        header_frame = self.create_header_section()
        layout.addWidget(header_frame)
        
        # Main content area
        content_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Table widget
        self.table_widget = QTableWidget()
        self.table_widget.setAlternatingRowColors(True)
        self.table_widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)  # Allow cell selection
        self.table_widget.setSortingEnabled(True)
        
        # Context menu for table
        self.table_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_widget.customContextMenuRequested.connect(self.show_table_context_menu)
        
        # Install event filter for keyboard shortcuts
        self.table_widget.installEventFilter(self)
        
        content_splitter.addWidget(self.table_widget)
        
        # Status and navigation
        nav_frame = self.create_navigation_section()
        content_splitter.addWidget(nav_frame)
        
        content_splitter.setStretchFactor(0, 1)
        content_splitter.setStretchFactor(1, 0)
        
        layout.addWidget(content_splitter)
    
    def create_header_section(self) -> QWidget:
        """Create header section with search and controls."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QHBoxLayout(frame)
        
        # Search controls
        search_group = QGroupBox("Search & Filter")
        search_main_layout = QVBoxLayout(search_group)
        
        # First row: Column selection and search input
        search_row1 = QHBoxLayout()
        
        # Column selector
        column_label = QLabel("Column:")
        column_label.setMinimumWidth(50)
        search_row1.addWidget(column_label)
        
        self.column_dropdown = QComboBox()
        self.column_dropdown.setMinimumWidth(140)
        self.column_dropdown.setMaximumWidth(200)
        self.column_dropdown.addItem("All Columns")
        search_row1.addWidget(self.column_dropdown)
        
        search_row1.addSpacing(10)  # Add some space
        
        # Search input
        search_label = QLabel("Search:")
        search_label.setMinimumWidth(50)
        search_row1.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search term...")
        self.search_input.setMinimumWidth(200)
        self.search_input.returnPressed.connect(self.apply_dataset_filter)
        search_row1.addWidget(self.search_input)
        
        search_row1.addStretch()  # Push everything to the left
        search_main_layout.addLayout(search_row1)
        
        # Second row: Options and buttons
        search_row2 = QHBoxLayout()
        
        # Case sensitivity checkbox
        self.case_sensitive_cb = QCheckBox("Case sensitive")
        search_row2.addWidget(self.case_sensitive_cb)
        
        search_row2.addSpacing(15)  # Add space between checkbox and buttons
        
        # Apply filter button
        self.apply_filter_btn = QPushButton("Apply Filter")
        self.apply_filter_btn.setToolTip("Apply filter to entire dataset and re-paginate")
        self.apply_filter_btn.clicked.connect(self.apply_dataset_filter)
        self.apply_filter_btn.setMinimumWidth(90)
        search_row2.addWidget(self.apply_filter_btn)
        
        # Clear filter button
        self.clear_filter_btn = QPushButton("Clear Filter")
        self.clear_filter_btn.setToolTip("Remove all filters and show complete dataset")
        self.clear_filter_btn.clicked.connect(self.clear_dataset_filter)
        self.clear_filter_btn.setEnabled(False)
        self.clear_filter_btn.setMinimumWidth(90)
        search_row2.addWidget(self.clear_filter_btn)
        
        search_row2.addSpacing(15)  # Add space before status
        
        # Filter status label
        self.filter_status_label = QLabel("")
        self.filter_status_label.setStyleSheet("QLabel { color: #666666; font-style: italic; }")
        search_row2.addWidget(self.filter_status_label)
        
        search_row2.addStretch()  # Push everything to the left
        search_main_layout.addLayout(search_row2)
        
        layout.addWidget(search_group)
        
        # Page size controls
        page_size_group = QGroupBox("Page Size")
        page_size_layout = QHBoxLayout(page_size_group)
        
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["100", "500", "1000", "2500", "5000", "10000"])
        self.page_size_combo.setCurrentText(str(self.current_page_size))
        self.page_size_combo.currentTextChanged.connect(self.on_page_size_changed)
        page_size_layout.addWidget(self.page_size_combo)
        
        layout.addWidget(page_size_group)
        
        # Memory usage
        self.memory_label = QLabel("Memory: --")
        self.memory_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.memory_label)
        
        layout.addStretch()
        
        # Export & Analysis group
        export_group = QGroupBox("Export & Analysis")
        export_main_layout = QVBoxLayout(export_group)
        
        # First row: Export buttons
        export_row1 = QHBoxLayout()
        
        self.export_page_btn = QPushButton("Export Page")
        self.export_page_btn.clicked.connect(self.export_current_page)
        self.export_page_btn.setEnabled(False)
        self.export_page_btn.setMinimumWidth(110)
        self.export_page_btn.setToolTip("Export only the current page of results")
        export_row1.addWidget(self.export_page_btn)
        
        self.export_all_btn = QPushButton("Export All Results")
        self.export_all_btn.clicked.connect(self.export_all_results)
        self.export_all_btn.setEnabled(False)
        self.export_all_btn.setMinimumWidth(130)
        self.export_all_btn.setToolTip("Export the complete dataset (all pages)")
        export_row1.addWidget(self.export_all_btn)
        
        self.export_filtered_btn = QPushButton("Export Filtered")
        self.export_filtered_btn.clicked.connect(self.export_filtered_results)
        self.export_filtered_btn.setEnabled(False)
        self.export_filtered_btn.setMinimumWidth(120)
        self.export_filtered_btn.setToolTip("Export only records matching the current search filter")
        export_row1.addWidget(self.export_filtered_btn)
        
        export_row1.addStretch()  # Push buttons to the left
        export_main_layout.addLayout(export_row1)
        
        # Second row: Metrics buttons
        export_row2 = QHBoxLayout()
        
        self.show_original_metrics_btn = QPushButton("Query Metrics")
        self.show_original_metrics_btn.clicked.connect(self.show_original_metrics)
        self.show_original_metrics_btn.setEnabled(False)
        self.show_original_metrics_btn.setMinimumWidth(120)
        self.show_original_metrics_btn.setToolTip("Show detailed metrics for the entire original query result")
        export_row2.addWidget(self.show_original_metrics_btn)
        
        self.show_filtered_metrics_btn = QPushButton("Filter Metrics")
        self.show_filtered_metrics_btn.clicked.connect(self.show_filtered_metrics)
        self.show_filtered_metrics_btn.setEnabled(False)
        self.show_filtered_metrics_btn.setMinimumWidth(120)
        self.show_filtered_metrics_btn.setToolTip("Show detailed metrics for the filtered dataset only")
        export_row2.addWidget(self.show_filtered_metrics_btn)
        
        export_row2.addStretch()  # Push buttons to the left
        export_main_layout.addLayout(export_row2)
        
        layout.addWidget(export_group)
        
        return frame
    
    def create_navigation_section(self) -> QWidget:
        """Create navigation controls and status."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(frame)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status and navigation row
        nav_layout = QHBoxLayout()
        
        # Status info
        self.status_label = QLabel("Ready")
        nav_layout.addWidget(self.status_label)
        
        nav_layout.addStretch()
        
        # Navigation buttons
        self.first_btn = QPushButton("⏮ First")
        self.first_btn.clicked.connect(self.go_to_first_page)
        self.first_btn.setEnabled(False)
        nav_layout.addWidget(self.first_btn)
        
        self.prev_btn = QPushButton("◀ Previous")
        self.prev_btn.clicked.connect(self.go_to_previous_page)
        self.prev_btn.setEnabled(False)
        nav_layout.addWidget(self.prev_btn)
        
        # Page selector
        nav_layout.addWidget(QLabel("Page:"))
        self.page_spinbox = QSpinBox()
        self.page_spinbox.setMinimum(1)
        self.page_spinbox.valueChanged.connect(self.on_page_changed)
        nav_layout.addWidget(self.page_spinbox)
        
        self.page_info_label = QLabel("of --")
        nav_layout.addWidget(self.page_info_label)
        
        self.next_btn = QPushButton("Next ▶")
        self.next_btn.clicked.connect(self.go_to_next_page)
        self.next_btn.setEnabled(False)
        nav_layout.addWidget(self.next_btn)
        
        self.last_btn = QPushButton("Last ⏭")
        self.last_btn.clicked.connect(self.go_to_last_page)
        self.last_btn.setEnabled(False)
        nav_layout.addWidget(self.last_btn)
        
        layout.addLayout(nav_layout)
        
        return frame
    
    def set_paginator(self, paginator: QueryPaginator):
        """Set the data paginator."""
        self.paginator = paginator
        self.current_page = 0
        self.load_initial_page()
    
    def load_initial_page(self):
        """Load the first page of data."""
        if not self.paginator:
            return
        
        # Get optimal page size
        try:
            sample_data = self.paginator.get_sample_data()
            if not sample_data.empty:
                total_rows = self.paginator.get_total_rows()
                row_size = self.paginator.estimate_row_size(sample_data)
                optimal_size = self.paginator.get_optimal_page_size(row_size, total_rows)
                
                # Update page size if needed
                if optimal_size != self.current_page_size:
                    self.current_page_size = optimal_size
                    self.page_size_combo.setCurrentText(str(optimal_size))
                
                # Update page controls
                total_pages = (total_rows + self.current_page_size - 1) // self.current_page_size
                self.page_spinbox.setMaximum(max(1, total_pages))
                self.page_info_label.setText(f"of {total_pages:,}")
        except Exception as e:
            logger.error(f"Failed to initialize pagination: {e}")
        
        self.load_page(0)
    
    def load_page(self, page_number: int):
        """Load a specific page of data."""
        if not self.paginator:
            return
        
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait(1000)
        
        self.current_page = page_number
        self.page_spinbox.setValue(page_number + 1)
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText(f"Loading page {page_number + 1}...")
        
        # Disable controls during loading
        self.set_navigation_enabled(False)
        
        # Start worker thread
        self.worker = PaginationWorker(self.paginator, page_number, self.current_page_size)
        self.worker.page_loaded.connect(self.on_page_loaded)
        self.worker.progress_updated.connect(self.on_progress_updated)
        self.worker.error_occurred.connect(self.on_error_occurred)
        self.worker.start()
    
    def on_page_loaded(self, data: pd.DataFrame, page_info: PageInfo):
        """Handle successful page loading."""
        self.current_data = data
        self.current_page_info = page_info
        
        # Update table
        self.populate_table(data)
        
        # Update column dropdown for search
        self.update_column_dropdown()
        
        # Update navigation
        self.update_navigation_state()
        
        # Update status
        self.status_label.setText(
            f"Page {page_info.page_number + 1} of {page_info.total_pages:,} "
            f"({page_info.start_row + 1:,}-{page_info.end_row:,} of {page_info.total_rows:,} rows)"
        )
        
        # Hide progress
        self.progress_bar.setVisible(False)
        
        # Enable export buttons
        self.export_page_btn.setEnabled(True)
        self.export_all_btn.setEnabled(True)
        self.export_filtered_btn.setEnabled(bool(self.search_input.text().strip()))
        
        # Enable metrics buttons
        self.show_original_metrics_btn.setEnabled(True)
        self.show_filtered_metrics_btn.setEnabled(self.is_filtered)
        
        logger.info(f"Page {page_info.page_number + 1} loaded successfully")
    
    def on_progress_updated(self, message: str, progress: int):
        """Handle progress updates."""
        self.progress_bar.setValue(progress)
        self.status_label.setText(message)
    
    def on_error_occurred(self, error_message: str):
        """Handle loading errors."""
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Error: {error_message}")
        self.set_navigation_enabled(True)
        
        QMessageBox.critical(self, "Loading Error", f"Failed to load page: {error_message}")
    
    def populate_table(self, data: pd.DataFrame):
        """Populate the table widget with data."""
        if data.empty:
            self.table_widget.setRowCount(0)
            self.table_widget.setColumnCount(0)
            return
        
        # Set up table structure
        self.table_widget.setRowCount(len(data))
        self.table_widget.setColumnCount(len(data.columns))
        self.table_widget.setHorizontalHeaderLabels(data.columns.tolist())
        
        # Populate data
        for row in range(len(data)):
            for col in range(len(data.columns)):
                value = data.iloc[row, col]
                
                # Handle different data types
                if pd.isna(value):
                    item_text = ""
                    item = QTableWidgetItem(item_text)
                    item.setForeground(Qt.GlobalColor.gray)
                    item.setFont(QFont("", -1, QFont.Weight.Normal, True))  # Italic
                else:
                    item_text = self._format_value(value)
                    item = QTableWidgetItem(item_text)
                    if isinstance(value, (int, float, Decimal)):
                        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                
                # Make items read-only
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                
                self.table_widget.setItem(row, col, item)
        
        # Auto-resize columns to content
        self.table_widget.resizeColumnsToContents()
        
        # Limit column width to reasonable size
        header = self.table_widget.horizontalHeader()
        for col in range(len(data.columns)):
            width = header.sectionSize(col)
            if width > 300:
                header.resizeSection(col, 300)

    @staticmethod
    def _format_value(value: Any) -> str:
        """Format cell values for display without losing precision."""
        if isinstance(value, float):
            if not math.isfinite(value):
                return str(value)
            formatted = np.format_float_positional(value, trim='-')
            return formatted if formatted else "0"
        if isinstance(value, Decimal):
            text = format(value, 'f')
            return text if text else "0"
        return str(value)
    
    def update_column_dropdown(self):
        """Update the column dropdown with current data columns."""
        if self.current_data is None or self.current_data.empty:
            return
        
        # Store current selection
        current_selection = self.column_dropdown.currentText()
        
        # Clear and repopulate dropdown
        self.column_dropdown.clear()
        self.column_dropdown.addItem("All Columns")
        
        # Add all column names
        for column in self.current_data.columns:
            self.column_dropdown.addItem(str(column))
        
        # Restore selection if it still exists
        index = self.column_dropdown.findText(current_selection)
        if index >= 0:
            self.column_dropdown.setCurrentIndex(index)
        else:
            self.column_dropdown.setCurrentIndex(0)  # Default to "All Columns"
    

    
    def update_navigation_state(self):
        """Update navigation button states."""
        if not self.current_page_info:
            return
        
        self.first_btn.setEnabled(self.current_page_info.has_previous)
        self.prev_btn.setEnabled(self.current_page_info.has_previous)
        self.next_btn.setEnabled(self.current_page_info.has_next)
        self.last_btn.setEnabled(self.current_page_info.has_next)
        
        self.page_spinbox.setEnabled(True)
    
    def set_navigation_enabled(self, enabled: bool):
        """Enable or disable navigation controls."""
        self.first_btn.setEnabled(enabled)
        self.prev_btn.setEnabled(enabled)
        self.next_btn.setEnabled(enabled)
        self.last_btn.setEnabled(enabled)
        self.page_spinbox.setEnabled(enabled)
        self.page_size_combo.setEnabled(enabled)
    
    def go_to_first_page(self):
        """Go to the first page."""
        self.load_page(0)
    
    def go_to_previous_page(self):
        """Go to the previous page."""
        if self.current_page > 0:
            self.load_page(self.current_page - 1)
    
    def go_to_next_page(self):
        """Go to the next page."""
        if self.current_page_info and self.current_page_info.has_next:
            self.load_page(self.current_page + 1)
    
    def go_to_last_page(self):
        """Go to the last page."""
        if self.current_page_info:
            last_page = self.current_page_info.total_pages - 1
            self.load_page(last_page)
    
    def on_page_changed(self, page_number: int):
        """Handle page number change from spinbox."""
        target_page = page_number - 1  # Convert to 0-based
        if target_page != self.current_page:
            self.load_page(target_page)
    
    def on_page_size_changed(self, size_text: str):
        """Handle page size change."""
        try:
            new_size = int(size_text)
            if new_size != self.current_page_size:
                self.current_page_size = new_size
                # Recalculate current page to maintain relative position
                if self.current_page_info:
                    current_row = self.current_page_info.start_row
                    new_page = current_row // new_size
                    self.load_page(new_page)
        except ValueError:
            pass
    
    def update_memory_usage(self):
        """Update memory usage display."""
        try:
            memory_mb = get_memory_usage_mb()
            memory_text = format_memory_size(memory_mb)
            
            # Color based on usage
            if memory_mb > self.config.warning_threshold_mb:
                color = "red"
            elif memory_mb > self.config.memory_threshold_mb:
                color = "orange"
            else:
                color = "green"
            
            self.memory_label.setText(f"Memory: {memory_text}")
            self.memory_label.setStyleSheet(f"font-weight: bold; color: {color};")
            
        except Exception:
            self.memory_label.setText("Memory: --")
    
    def show_table_context_menu(self, position):
        """Show context menu for table."""
        if self.current_data is None or self.current_data.empty:
            return
        
        menu = QMenu(self)
        selected_items = self.table_widget.selectedItems()
        
        # Cell-level copy actions
        if len(selected_items) == 1:
            # Single cell selected
            copy_cell_action = QAction("Copy Cell Value", self)
            copy_cell_action.triggered.connect(self.copy_selected_cell)
            menu.addAction(copy_cell_action)
        elif len(selected_items) > 1:
            # Multiple cells selected
            copy_cells_action = QAction(f"Copy {len(selected_items)} Cells", self)
            copy_cells_action.triggered.connect(self.copy_selected_cells)
            menu.addAction(copy_cells_action)
        
        # Row-level copy action
        current_row = self.table_widget.currentRow()
        if current_row >= 0:
            copy_row_action = QAction("Copy Row", self)
            copy_row_action.triggered.connect(self.copy_selected_row)
            menu.addAction(copy_row_action)
        
        if selected_items or current_row >= 0:
            menu.addSeparator()
        
        # Export actions
        export_page_action = QAction("Export Current Page", self)
        export_page_action.triggered.connect(self.export_current_page)
        menu.addAction(export_page_action)
        
        export_all_action = QAction("Export All Data...", self)
        export_all_action.triggered.connect(self.export_all_results)
        menu.addAction(export_all_action)
        
        menu.addSeparator()
        
        # Selection info
        if len(selected_items) > 0:
            info_action = QAction(f"Selected: {len(selected_items)} cells", self)
        else:
            total_cells = self.table_widget.rowCount() * self.table_widget.columnCount()
            info_action = QAction(f"Total: {total_cells} cells", self)
        info_action.setEnabled(False)
        menu.addAction(info_action)
        
        menu.exec(self.table_widget.mapToGlobal(position))
    
    def copy_selected_cell(self):
        """Copy selected cell to clipboard."""
        current_item = self.table_widget.currentItem()
        if current_item:
            cell_value = current_item.text()
            QApplication.clipboard().setText(cell_value)
            logger.info(f"Copied cell value to clipboard: '{cell_value}'")
    
    def copy_selected_cells(self):
        """Copy multiple selected cells to clipboard as tab-delimited text."""
        selected_items = self.table_widget.selectedItems()
        if not selected_items:
            return
        
        # Group by row to maintain table structure
        rows_dict = {}
        for item in selected_items:
            row = item.row()
            col = item.column()
            if row not in rows_dict:
                rows_dict[row] = {}
            rows_dict[row][col] = item.text()
        
        # Build tab-delimited string
        lines = []
        for row in sorted(rows_dict.keys()):
            row_data = rows_dict[row]
            # Fill in empty cells for proper alignment
            max_col = max(row_data.keys()) if row_data else 0
            row_values = []
            for col in range(max_col + 1):
                row_values.append(row_data.get(col, ""))
            lines.append("\t".join(row_values))
        
        clipboard_text = "\n".join(lines)
        QApplication.clipboard().setText(clipboard_text)
        logger.info(f"Copied {len(selected_items)} cells to clipboard")
    
    def copy_selected_row(self):
        """Copy selected row to clipboard."""
        current_row = self.table_widget.currentRow()
        if current_row >= 0 and self.current_data is not None:
            row_data = []
            for col in range(self.table_widget.columnCount()):
                item = self.table_widget.item(current_row, col)
                row_data.append(item.text() if item else "")
            
            clipboard_text = "\t".join(row_data)
            QApplication.clipboard().setText(clipboard_text)
            logger.info(f"Copied row to clipboard")
    
    def eventFilter(self, obj, event):
        """Handle keyboard events for copy functionality."""
        if obj == self.table_widget and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_C and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                # Ctrl+C pressed
                selected_items = self.table_widget.selectedItems()
                if len(selected_items) == 1:
                    self.copy_selected_cell()
                elif len(selected_items) > 1:
                    self.copy_selected_cells()
                else:
                    # Fall back to row copy
                    self.copy_selected_row()
                return True
        
        return super().eventFilter(obj, event)
    
    def export_current_page(self):
        """Export current page data."""
        if self.current_data is not None:
            self.export_requested.emit(self.current_data)
    
    def export_all_results(self):
        """Export all query results (all pages)."""
        if not self.paginator or not self.current_page_info:
            return
        
        total_rows = self.current_page_info.total_rows
        if total_rows > 100000:  # Warn for large datasets
            reply = QMessageBox.question(
                self,
                "Large Dataset Export", 
                f"This will export {total_rows:,} rows which may take some time and use significant memory. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        # Signal to parent to handle the full export via database manager
        self.export_all_requested.emit()
    
    def export_filtered_results(self):
        """Export only the filtered results based on current search."""
        if self.current_data is None or self.current_data.empty:
            return
        
        search_text = self.search_input.text().strip()
        if not search_text:
            # No filter applied, export current page
            QMessageBox.information(
                self,
                "No Filter Applied",
                "No search filter is currently active. Use 'Export Page' to export current page data, or 'Export All Results' for the complete dataset."
            )
            return
        
        # Get filtered data from current page
        filtered_data = self.get_filtered_data()
        if filtered_data.empty:
            QMessageBox.information(
                self,
                "No Matching Data",
                f"No data matches the search filter '{search_text}'."
            )
            return
        
        # Show confirmation with exact count
        selected_column = self.column_dropdown.currentText()
        column_info = f" in '{selected_column}'" if selected_column != "All Columns" else " (all columns)"
        
        reply = QMessageBox.question(
            self,
            "Export Filtered Results",
            f"Export {len(filtered_data):,} records matching '{search_text}'{column_info} from this page?\n\n"
            f"Note: This exports only matches from the current page. For complete filtered results across all pages, "
            f"consider refining your SQL query.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Emit filtered page data. In future, could implement cross-page filtering
            self.export_filtered_requested.emit(filtered_data)
    
    def get_filtered_data(self) -> pd.DataFrame:
        """Get all filtered data from the entire dataset (not just current page)."""
        if not self.is_filtered or not self.paginator:
            # No filter applied, return current page data
            return self.current_data.copy() if self.current_data is not None else pd.DataFrame()
        
        try:
            # Execute the full filtered query to get all matching data
            filtered_sql = self.paginator.sql
            result = self.paginator.connection.execute(filtered_sql).df()
            logger.info(f"Retrieved {len(result)} filtered rows for export")
            return result
        except Exception as e:
            logger.error(f"Error getting filtered data: {e}")
            # Fallback to current page data
            return self.current_data.copy() if self.current_data is not None else pd.DataFrame()
    
    def clear_data(self):
        """Clear all data and reset the widget."""
        self.table_widget.setRowCount(0)
        self.table_widget.setColumnCount(0)
        self.current_data = None
        self.current_page_info = None
        self.current_page = 0
        
        self.status_label.setText("Ready")
        self.page_info_label.setText("of --")
        self.page_spinbox.setValue(1)
        self.page_spinbox.setMaximum(1)
        
        self.set_navigation_enabled(False)
        self.export_page_btn.setEnabled(False)
        self.export_all_btn.setEnabled(False)
        self.export_filtered_btn.setEnabled(False)
        
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait(1000)
    
    def update_status_with_filter_info(self, total_rows: int, filtered_rows: int):
        """Update the status bar with filter information."""
        status = f"Showing {filtered_rows} of {total_rows} rows"
        if filtered_rows != total_rows:
            status += f" (filtered)"
        
        # Emit signal to main window to update status bar
        self.status_updated.emit(status)
    
    def apply_dataset_filter(self):
        """Apply filter to the entire dataset by modifying the SQL query."""
        if not self.paginator:
            return
            
        search_text = self.search_input.text().strip()
        if not search_text:
            return
            
        selected_column = self.column_dropdown.currentText()
        case_sensitive = self.case_sensitive_cb.isChecked()
        
        try:
            # Store original paginator if this is the first filter
            if not self.is_filtered:
                self.original_paginator = self.paginator
            
            # Build SQL WHERE condition
            where_condition = self._build_sql_filter_condition(search_text, selected_column, case_sensitive)
            
            if where_condition:
                # Create new filtered SQL
                original_sql = self.original_paginator.sql
                filtered_sql = f"SELECT * FROM ({original_sql}) AS filtered_data WHERE {where_condition}"
                
                # Create new paginator with filtered SQL
                from ..data_pagination import QueryPaginator
                filtered_paginator = QueryPaginator(
                    self.original_paginator.connection, 
                    filtered_sql, 
                    self.config
                )
                
                # Replace current paginator
                self.paginator = filtered_paginator
                self.is_filtered = True
                self.filter_sql_condition = where_condition
                
                # Update UI state
                self.clear_filter_btn.setEnabled(True)
                self.export_filtered_btn.setEnabled(True)
                self.show_filtered_metrics_btn.setEnabled(True)
                self.filter_status_label.setText(f"Filter applied: {search_text}")
                
                # Reload first page with filtered data
                self.current_page = 0
                self.load_page(0)
                
                logger.info(f"Applied dataset filter: {where_condition}")
                
        except Exception as e:
            logger.error(f"Error applying dataset filter: {e}")
            self.filter_status_label.setText(f"Filter error: {str(e)}")
    
    def clear_dataset_filter(self):
        """Clear the dataset filter and restore original data."""
        if not self.is_filtered or not self.original_paginator:
            return
            
        try:
            # Restore original paginator
            self.paginator = self.original_paginator
            self.is_filtered = False
            self.filter_sql_condition = ""
            
            # Update UI state
            self.clear_filter_btn.setEnabled(False)
            self.export_filtered_btn.setEnabled(False)
            self.show_filtered_metrics_btn.setEnabled(False)
            self.filter_status_label.setText("")
            self.search_input.clear()
            
            # Reload first page with original data
            self.current_page = 0
            self.load_page(0)
            
            logger.info("Cleared dataset filter")
            
        except Exception as e:
            logger.error(f"Error clearing dataset filter: {e}")
            self.filter_status_label.setText(f"Clear filter error: {str(e)}")
    
    def _build_sql_filter_condition(self, search_text: str, selected_column: str, case_sensitive: bool) -> str:
        """Build SQL WHERE condition for filtering."""
        if not search_text:
            return ""
            
        # Escape single quotes in search text
        escaped_text = search_text.replace("'", "''")
        
        if selected_column == "All Columns":
            # Search all columns - we'll need to get column names from sample data
            sample_data = self.original_paginator.get_sample_data(1)
            if sample_data.empty:
                return ""
                
            conditions = []
            for col in sample_data.columns:
                col_condition = self._build_column_condition(col, escaped_text, case_sensitive)
                if col_condition:
                    conditions.append(col_condition)
            
            return " OR ".join(conditions) if conditions else ""
        else:
            # Search specific column
            return self._build_column_condition(selected_column, escaped_text, case_sensitive)
    
    def _build_column_condition(self, column_name: str, escaped_text: str, case_sensitive: bool) -> str:
        """Build SQL condition for a specific column."""
        # Escape column name with double quotes to handle special characters/spaces
        safe_column = f'"{column_name}"'
        
        if case_sensitive:
            return f"CAST({safe_column} AS VARCHAR) LIKE '%{escaped_text}%'"
        else:
            return f"UPPER(CAST({safe_column} AS VARCHAR)) LIKE UPPER('%{escaped_text}%')"
    
    def show_original_metrics(self):
        """Show metrics for the original (unfiltered) query result."""
        if not self.original_paginator:
            return
        
        try:
            # Get the original SQL and execute it to get the full result for metrics
            original_sql = self.original_paginator.sql
            full_result = self.original_paginator.connection.execute(original_sql).df()
            
            # Emit signal to main window to show metrics
            self.metrics_requested.emit(original_sql, full_result, "original")
            
        except Exception as e:
            logger.error(f"Error getting original query metrics: {e}")
            QMessageBox.warning(
                self,
                "Metrics Error",
                f"Unable to generate original query metrics: {str(e)}"
            )
    
    def show_filtered_metrics(self):
        """Show metrics for the filtered dataset."""
        if not self.is_filtered or not self.paginator:
            return
        
        try:
            # Get the filtered SQL and execute it to get the full filtered result
            filtered_sql = self.paginator.sql
            filtered_result = self.paginator.connection.execute(filtered_sql).df()
            
            # Emit signal to main window to show metrics
            self.metrics_requested.emit(filtered_sql, filtered_result, "filtered")
            
        except Exception as e:
            logger.error(f"Error getting filtered query metrics: {e}")
            QMessageBox.warning(
                self,
                "Metrics Error",
                f"Unable to generate filtered query metrics: {str(e)}"
            )