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
from typing import Optional, Callable, Dict, Any

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QAction
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QPushButton, QSpinBox, QProgressBar, QGroupBox, QFrame,
    QComboBox, QLineEdit, QCheckBox, QMessageBox, QSplitter,
    QHeaderView, QAbstractItemView, QMenu
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
    export_requested = pyqtSignal(object)  # DataFrame
    
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
        self.table_widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_widget.setSortingEnabled(True)
        
        # Context menu for table
        self.table_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_widget.customContextMenuRequested.connect(self.show_table_context_menu)
        
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
        search_group = QGroupBox("Search")
        search_layout = QHBoxLayout(search_group)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search in selected column or all columns...")
        self.search_input.textChanged.connect(self.filter_current_page)
        search_layout.addWidget(self.search_input)

        # Column selector dropdown
        self.column_dropdown = QComboBox()
        self.column_dropdown.setMinimumWidth(120)
        self.column_dropdown.addItem("All Columns")
        self.column_dropdown.currentTextChanged.connect(self.filter_current_page)
        search_layout.addWidget(self.column_dropdown)

        self.case_sensitive_cb = QCheckBox("Case sensitive")
        self.case_sensitive_cb.stateChanged.connect(self.filter_current_page)
        search_layout.addWidget(self.case_sensitive_cb)
        
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
        
        # Export button
        self.export_btn = QPushButton("Export Page")
        self.export_btn.clicked.connect(self.export_current_page)
        self.export_btn.setEnabled(False)
        layout.addWidget(self.export_btn)
        
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
        
        # Enable export
        self.export_btn.setEnabled(True)
        
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
                elif isinstance(value, (int, float)):
                    item_text = str(value)
                    item = QTableWidgetItem(item_text)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                else:
                    item_text = str(value)
                    item = QTableWidgetItem(item_text)
                
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
    
    def filter_current_page(self):
        """Filter the current page based on search text."""
        if self.current_data is None or self.current_data.empty:
            return
        
        search_text = self.search_input.text().strip()
        
        if not search_text:
            # Show all rows
            for row in range(self.table_widget.rowCount()):
                self.table_widget.setRowHidden(row, False)
            return
        
        # Apply filter
        case_sensitive = self.case_sensitive_cb.isChecked()
        selected_column = self.column_dropdown.currentText()
        
        if not case_sensitive:
            search_text = search_text.lower()
        
        for row in range(self.table_widget.rowCount()):
            row_matches = False
            
            if selected_column == "All Columns":
                # Search all columns
                for col in range(self.table_widget.columnCount()):
                    item = self.table_widget.item(row, col)
                    if item:
                        cell_text = item.text()
                        if not case_sensitive:
                            cell_text = cell_text.lower()
                        
                        if search_text in cell_text:
                            row_matches = True
                            break
            else:
                # Search only selected column
                try:
                    col_index = list(self.current_data.columns).index(selected_column)
                    if col_index < self.table_widget.columnCount():
                        item = self.table_widget.item(row, col_index)
                        if item:
                            cell_text = item.text()
                            if not case_sensitive:
                                cell_text = cell_text.lower()
                            
                            if search_text in cell_text:
                                row_matches = True
                except (ValueError, IndexError):
                    # Column not found, skip this row
                    pass
            
            self.table_widget.setRowHidden(row, not row_matches)
    
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
        
        # Copy cell action
        copy_action = QAction("Copy Cell", self)
        copy_action.triggered.connect(self.copy_selected_cell)
        menu.addAction(copy_action)
        
        # Copy row action
        copy_row_action = QAction("Copy Row", self)
        copy_row_action.triggered.connect(self.copy_selected_row)
        menu.addAction(copy_row_action)
        
        menu.addSeparator()
        
        # Export actions
        export_page_action = QAction("Export Current Page", self)
        export_page_action.triggered.connect(self.export_current_page)
        menu.addAction(export_page_action)
        
        export_all_action = QAction("Export All Data...", self)
        export_all_action.triggered.connect(self.export_all_data)
        menu.addAction(export_all_action)
        
        menu.exec(self.table_widget.mapToGlobal(position))
    
    def copy_selected_cell(self):
        """Copy selected cell to clipboard."""
        current_item = self.table_widget.currentItem()
        if current_item:
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText(current_item.text())
    
    def copy_selected_row(self):
        """Copy selected row to clipboard."""
        current_row = self.table_widget.currentRow()
        if current_row >= 0 and self.current_data is not None:
            row_data = []
            for col in range(self.table_widget.columnCount()):
                item = self.table_widget.item(current_row, col)
                row_data.append(item.text() if item else "")
            
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText("\t".join(row_data))
    
    def export_current_page(self):
        """Export current page data."""
        if self.current_data is not None:
            self.export_requested.emit(self.current_data)
    
    def export_all_data(self):
        """Export all data (show warning for large datasets)."""
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
        
        # TODO: Implement chunked export for very large datasets
        QMessageBox.information(
            self,
            "Export All Data",
            "Full dataset export for large data is not yet implemented. Please use the main export functionality."
        )
    
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
        self.export_btn.setEnabled(False)
        
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait(1000)