"""
Results table view for displaying query results.

This module provides the ResultsTableView class which displays:
- Query results in a tabular format
- Sorting and scrolling capabilities
- Export functionality
- Large dataset handling with pagination
"""

import logging
import math
from decimal import Decimal
from typing import Optional

import numpy as np
import pandas as pd
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QVariant, pyqtSignal, QEvent
from PyQt6.QtWidgets import (
    QTableView,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QHeaderView,
    QAbstractItemView,
    QMenu,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QGroupBox,
    QApplication,
    QMessageBox
)
from PyQt6.QtGui import QAction

logger = logging.getLogger(__name__)


class PandasTableModel(QAbstractTableModel):
    """Table model for displaying pandas DataFrames in QTableView."""
    
    def __init__(self, dataframe: Optional[pd.DataFrame] = None):
        super().__init__()
        self._dataframe = dataframe if dataframe is not None else pd.DataFrame()
    
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return number of rows."""
        return len(self._dataframe)
    
    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return number of columns."""
        return len(self._dataframe.columns)
    
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> QVariant:
        """Return data for the given index and role."""
        if not index.isValid():
            return QVariant()
        
        if role == Qt.ItemDataRole.DisplayRole:
            value = self._dataframe.iloc[index.row(), index.column()]
            
            # Handle different data types
            if pd.isna(value):
                return "NULL"
            if isinstance(value, float):
                return self._format_float(value)
            if isinstance(value, Decimal):
                return self._format_decimal(value)
            return str(value)
        
        return QVariant()
    
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> QVariant:
        """Return header data."""
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return str(self._dataframe.columns[section])
            else:
                return str(section + 1)  # Row numbers starting from 1
        
        return QVariant()
    
    def set_dataframe(self, dataframe: pd.DataFrame):
        """Set a new dataframe."""
        self.beginResetModel()
        self._dataframe = dataframe
        self.endResetModel()

    @staticmethod
    def _format_float(value: float) -> str:
        """Format floating point numbers without losing precision."""
        if not math.isfinite(value):
            return str(value)
        formatted = np.format_float_positional(value, trim='-')
        return formatted if formatted else "0"

    @staticmethod
    def _format_decimal(value: Decimal) -> str:
        """Format Decimal values preserving their defined scale."""
        text = format(value, 'f')
        return text if text else "0"
    
    def get_dataframe(self) -> pd.DataFrame:
        """Get the current dataframe."""
        return self._dataframe.copy()
    
    def sort(self, column: int, order: Qt.SortOrder):
        """Sort the data by column."""
        if column < 0 or column >= len(self._dataframe.columns):
            return
        
        self.layoutAboutToBeChanged.emit()
        
        column_name = self._dataframe.columns[column]
        ascending = order == Qt.SortOrder.AscendingOrder
        
        self._dataframe = self._dataframe.sort_values(
            by=column_name,
            ascending=ascending,
            na_position='last'
        ).reset_index(drop=True)
        
        self.layoutChanged.emit()


class ResultsTableView(QWidget):
    """
    Widget for displaying query results in a table format.
    
    Features:
    - Displays pandas DataFrames in a table view
    - Sortable columns
    - Row/column count display
    - Export functionality
    - Pagination for large datasets (future)
    """
    
    # Signals
    export_requested = pyqtSignal()  # Emitted when export is requested (current page/all data in standard view)
    export_all_requested = pyqtSignal()  # Emitted when export all is requested
    export_filtered_requested = pyqtSignal(object)  # Emitted when filtered export is requested (with DataFrame)
    
    def __init__(self):
        """Initialize the results table view."""
        super().__init__()
        
        self.model = PandasTableModel()
        self.original_data = None  # Store original data for filtering
        self.filtered_data = None  # Store filtered data
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        
        # Header with info and controls
        header_layout = QHBoxLayout()
        
        self.info_label = QLabel("No results")
        self.info_label.setStyleSheet("font-weight: bold; color: #666;")
        header_layout.addWidget(self.info_label)
        
        header_layout.addStretch()
        
        # Export buttons group
        export_buttons_layout = QHBoxLayout()
        
        self.export_button = QPushButton("Export Results")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.export_results)
        self.export_button.setToolTip("Export all results to a file")
        export_buttons_layout.addWidget(self.export_button)
        
        self.export_filtered_button = QPushButton("Export Filtered")
        self.export_filtered_button.setEnabled(False)
        self.export_filtered_button.clicked.connect(self.export_filtered_results)
        self.export_filtered_button.setToolTip("Export only filtered results matching the search")
        export_buttons_layout.addWidget(self.export_filtered_button)
        
        header_layout.addLayout(export_buttons_layout)
        
        layout.addLayout(header_layout)
        
        # Search controls
        self.search_widget = self.create_search_widget()
        layout.addWidget(self.search_widget)
        
        # Table view
        self.table_view = QTableView()
        self.table_view.setModel(self.model)
        
        # Configure table view
        self.table_view.setSortingEnabled(True)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)  # Allow cell selection
        
        # Enable context menu
        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self.show_context_menu)
        
        # Install event filter for keyboard shortcuts
        self.table_view.installEventFilter(self)
        
        # Header configuration
        horizontal_header = self.table_view.horizontalHeader()
        horizontal_header.setStretchLastSection(True)
        horizontal_header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        
        vertical_header = self.table_view.verticalHeader()
        vertical_header.setVisible(True)
        vertical_header.setDefaultSectionSize(24)
        
        layout.addWidget(self.table_view)
        
        # Footer with additional info
        footer_layout = QHBoxLayout()
        
        self.memory_label = QLabel("")
        self.memory_label.setStyleSheet("color: #999; font-size: 11px;")
        footer_layout.addWidget(self.memory_label)
        
        footer_layout.addStretch()
        
        layout.addLayout(footer_layout)
        
        self.setLayout(layout)
    
    def create_search_widget(self):
        """Create the search widget with column selection and search functionality."""
        search_group = QGroupBox("Search & Filter")
        search_layout = QHBoxLayout()
        
        # Column selection dropdown
        search_layout.addWidget(QLabel("Column:"))
        self.column_combo = QComboBox()
        self.column_combo.addItem("All Columns", "")  # Empty string means search all columns
        self.column_combo.setMinimumWidth(150)
        self.column_combo.currentTextChanged.connect(self.filter_results)
        search_layout.addWidget(self.column_combo)
        
        # Search input
        search_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search term...")
        self.search_input.textChanged.connect(self.filter_results)
        search_layout.addWidget(self.search_input)
        
        # Case sensitivity checkbox
        self.case_sensitive_checkbox = QCheckBox("Case sensitive")
        self.case_sensitive_checkbox.stateChanged.connect(self.filter_results)
        search_layout.addWidget(self.case_sensitive_checkbox)
        
        # Filter status label
        self.filter_status_label = QLabel("")
        self.filter_status_label.setStyleSheet("color: #666; font-style: italic;")
        search_layout.addWidget(self.filter_status_label)
        
        search_layout.addStretch()
        search_group.setLayout(search_layout)
        
        return search_group
    
    def set_dataframe(self, dataframe: pd.DataFrame):
        """
        Set the dataframe to display.
        
        Args:
            dataframe: Pandas DataFrame to display
        """
        # Store original data for filtering
        self.original_data = dataframe.copy() if not dataframe.empty else pd.DataFrame()
        self.filtered_data = self.original_data.copy()
        
        # Update column dropdown
        self.update_column_dropdown()
        
        # Update model
        self.model.set_dataframe(dataframe)
        
        # Update info labels
        self.update_info_labels(dataframe)
        
        # Enable export button
        self.export_button.setEnabled(not dataframe.empty)
        # Export filtered button disabled initially (will be enabled when filter is applied)
        self.export_filtered_button.setEnabled(False)
        
        # Auto-resize columns to content (with limits)
        self.table_view.resizeColumnsToContents()
        
        # Set maximum column width to prevent excessive stretching
        header = self.table_view.horizontalHeader()
        for i in range(self.model.columnCount()):
            width = header.sectionSize(i)
            if width > 200:
                header.resizeSection(i, 200)
        
        # Reset search
        self.search_input.clear()
        self.filter_status_label.setText("")
        
        logger.info(f"Displayed DataFrame with {len(dataframe)} rows, {len(dataframe.columns)} columns")
    
    def update_info_labels(self, dataframe: pd.DataFrame):
        """Update the information labels."""
        if dataframe.empty:
            self.info_label.setText("No results")
            self.memory_label.setText("")
        else:
            row_count = len(dataframe)
            col_count = len(dataframe.columns)
            
            # Format row count
            if row_count == 1:
                row_text = "1 row"
            else:
                row_text = f"{row_count:,} rows"
            
            # Format column count
            if col_count == 1:
                col_text = "1 column"
            else:
                col_text = f"{col_count} columns"
            
            self.info_label.setText(f"{row_text}, {col_text}")
            
            # Memory usage
            try:
                memory_usage = dataframe.memory_usage(deep=True).sum()
                if memory_usage < 1024:
                    memory_text = f"{memory_usage} bytes"
                elif memory_usage < 1024 * 1024:
                    memory_text = f"{memory_usage / 1024:.1f} KB"
                else:
                    memory_text = f"{memory_usage / (1024 * 1024):.1f} MB"
                
                self.memory_label.setText(f"Memory: {memory_text}")
            except Exception:
                self.memory_label.setText("")
    
    def get_dataframe(self) -> Optional[pd.DataFrame]:
        """Get the current dataframe (filtered data)."""
        if self.filtered_data is None or self.filtered_data.empty:
            return None
        return self.filtered_data.copy()
    
    def has_data(self) -> bool:
        """Check if there is data to display."""
        return self.model.rowCount() > 0
    
    def clear(self):
        """Clear the results view."""
        self.original_data = None
        self.filtered_data = None
        self.set_dataframe(pd.DataFrame())
    
    def export_results(self):
        """Export all results."""
        # Emit signal to parent window to handle export
        self.export_requested.emit()
        logger.info("Export results requested")
    
    def export_filtered_results(self):
        """Export only the filtered results based on current search."""
        if self.filtered_data is None or self.filtered_data.empty:
            QMessageBox.information(
                self,
                "No Filter Applied",
                "No search filter is currently active. Use 'Export Results' to export all data."
            )
            return
        
        # Show confirmation with count
        reply = QMessageBox.question(
            self,
            "Export Filtered Results",
            f"Export {len(self.filtered_data):,} filtered records?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Emit signal with filtered data
            self.export_filtered_requested.emit(self.filtered_data)
            logger.info(f"Export filtered results requested: {len(self.filtered_data)} rows")
    
    def show_context_menu(self, position):
        """Show context menu at the given position."""
        if not self.has_data():
            return
            
        menu = QMenu(self)
        selection_model = self.table_view.selectionModel()
        selected_indexes = selection_model.selectedIndexes() if selection_model else []
        
        # Cell-level copy actions
        if len(selected_indexes) == 1:
            # Single cell selected
            copy_cell_action = QAction("Copy Cell Value", self)
            copy_cell_action.triggered.connect(self.copy_selected_cell)
            menu.addAction(copy_cell_action)
        elif len(selected_indexes) > 1:
            # Multiple cells selected
            copy_cells_action = QAction(f"Copy {len(selected_indexes)} Cells", self)
            copy_cells_action.triggered.connect(self.copy_selected_cells)
            menu.addAction(copy_cells_action)
        
        if selected_indexes:
            menu.addSeparator()
        
        # Row-level copy action (if full rows are selected)
        selected_rows = self.get_selected_rows()
        if selected_rows:
            copy_rows_action = QAction("Copy Selected Rows", self)
            copy_rows_action.triggered.connect(self.copy_selected_rows)
            menu.addAction(copy_rows_action)
        
        if selected_indexes or selected_rows:
            menu.addSeparator()
        
        # Export action
        export_action = QAction("Export Results...", self)
        export_action.triggered.connect(self.export_results)
        menu.addAction(export_action)
        
        menu.addSeparator()
        
        # Selection info
        row_count = self.model.rowCount()
        if len(selected_indexes) > 0:
            info_action = QAction(f"Selected: {len(selected_indexes)} cells", self)
        elif len(selected_rows) > 0:
            info_action = QAction(f"Selected: {len(selected_rows)} of {row_count} rows", self)
        else:
            info_action = QAction(f"Total: {row_count} rows", self)
        info_action.setEnabled(False)
        menu.addAction(info_action)
        
        # Show menu
        menu.exec(self.table_view.mapToGlobal(position))
    
    def copy_selected_rows(self):
        """Copy selected rows to clipboard."""
        selected_data = self.get_selected_data()
        if selected_data is not None and not selected_data.empty:
            # Convert to tab-separated values for easy pasting into Excel/etc
            clipboard_text = selected_data.to_csv(sep='\t', index=False)
            
            # Copy to clipboard
            clipboard = QApplication.clipboard()
            clipboard.setText(clipboard_text)
            
            logger.info(f"Copied {len(selected_data)} rows to clipboard")
    
    def copy_selected_cell(self):
        """Copy the value of a single selected cell to clipboard."""
        selection_model = self.table_view.selectionModel()
        if not selection_model:
            return
        
        selected_indexes = selection_model.selectedIndexes()
        if len(selected_indexes) != 1:
            return
        
        index = selected_indexes[0]
        cell_data = self.model.data(index, Qt.ItemDataRole.DisplayRole)
        cell_value = str(cell_data) if cell_data is not None else ""
        
        # Copy to clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(cell_value)
        
        logger.info(f"Copied cell value to clipboard: '{cell_value}'")
    
    def copy_selected_cells(self):
        """Copy multiple selected cells to clipboard as tab-delimited text."""
        selection_model = self.table_view.selectionModel()
        if not selection_model:
            return
        
        selected_indexes = selection_model.selectedIndexes()
        if not selected_indexes:
            return
        
        # Group by row to maintain table structure
        rows_dict = {}
        for index in selected_indexes:
            row = index.row()
            col = index.column()
            if row not in rows_dict:
                rows_dict[row] = {}
            
            cell_data = self.model.data(index, Qt.ItemDataRole.DisplayRole)
            cell_value = str(cell_data) if cell_data is not None else ""
            rows_dict[row][col] = cell_value
        
        # Build tab-delimited string
        lines = []
        for row in sorted(rows_dict.keys()):
            row_data = rows_dict[row]
            # Fill in empty cells with empty string for proper alignment
            max_col = max(row_data.keys()) if row_data else 0
            row_values = []
            for col in range(max_col + 1):
                row_values.append(row_data.get(col, ""))
            lines.append("\t".join(row_values))
        
        clipboard_text = "\n".join(lines)
        
        # Copy to clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(clipboard_text)
        
        logger.info(f"Copied {len(selected_indexes)} cells to clipboard")
    
    def eventFilter(self, obj, event):
        """Handle keyboard events for copy functionality."""
        if obj == self.table_view and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_C and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                # Ctrl+C pressed
                selection_model = self.table_view.selectionModel()
                if selection_model:
                    selected_indexes = selection_model.selectedIndexes()
                    if len(selected_indexes) == 1:
                        self.copy_selected_cell()
                    elif len(selected_indexes) > 1:
                        self.copy_selected_cells()
                    else:
                        # Fall back to row copy if no cells are selected
                        self.copy_selected_rows()
                return True
        
        return super().eventFilter(obj, event)
    
    def get_selected_rows(self) -> list[int]:
        """Get the indices of selected rows."""
        selection_model = self.table_view.selectionModel()
        if not selection_model:
            return []
        
        selected_rows = []
        for index in selection_model.selectedRows():
            selected_rows.append(index.row())
        
        return sorted(selected_rows)
    
    def get_selected_data(self) -> Optional[pd.DataFrame]:
        """Get the data for selected rows."""
        selected_rows = self.get_selected_rows()
        if not selected_rows:
            return None
        
        dataframe = self.get_dataframe()
        if dataframe is None:
            return None
        
        return dataframe.iloc[selected_rows].copy()
    
    def set_font_size(self, size: int):
        """Set the font size for the table."""
        font = self.table_view.font()
        font.setPointSize(size)
        self.table_view.setFont(font)
    
    def zoom_in(self):
        """Increase font size."""
        current_size = self.table_view.font().pointSize()
        self.set_font_size(min(current_size + 1, 18))
    
    def zoom_out(self):
        """Decrease font size."""
        current_size = self.table_view.font().pointSize()
        self.set_font_size(max(current_size - 1, 8))
    
    def update_column_dropdown(self):
        """Update the column dropdown with current DataFrame columns."""
        self.column_combo.clear()
        self.column_combo.addItem("All Columns", "")  # Empty string means search all columns
        
        if self.original_data is not None and not self.original_data.empty:
            for col in self.original_data.columns:
                self.column_combo.addItem(str(col), str(col))
    
    def filter_results(self):
        """Filter results based on search criteria."""
        if self.original_data is None or self.original_data.empty:
            return
        
        search_text = self.search_input.text().strip()
        selected_column = self.column_combo.currentData()
        case_sensitive = self.case_sensitive_checkbox.isChecked()
        
        if not search_text:
            # No search text, show all data
            self.filtered_data = self.original_data.copy()
        else:
            # Apply filter
            if selected_column:  # Search specific column
                if selected_column in self.original_data.columns:
                    if case_sensitive:
                        mask = self.original_data[selected_column].astype(str).str.contains(
                            search_text, case=True, na=False, regex=False
                        )
                    else:
                        mask = self.original_data[selected_column].astype(str).str.contains(
                            search_text, case=False, na=False, regex=False
                        )
                    self.filtered_data = self.original_data[mask].copy()
                else:
                    self.filtered_data = pd.DataFrame()
            else:  # Search all columns
                mask = pd.Series([False] * len(self.original_data))
                for col in self.original_data.columns:
                    try:
                        if case_sensitive:
                            col_mask = self.original_data[col].astype(str).str.contains(
                                search_text, case=True, na=False, regex=False
                            )
                        else:
                            col_mask = self.original_data[col].astype(str).str.contains(
                                search_text, case=False, na=False, regex=False
                            )
                        mask = mask | col_mask
                    except:
                        continue
                self.filtered_data = self.original_data[mask].copy()
        
        # Update display
        self.model.set_dataframe(self.filtered_data)
        
        # Update info labels
        self.update_info_labels(self.filtered_data)
        
        # Update filter status
        total_rows = len(self.original_data)
        filtered_rows = len(self.filtered_data)
        
        if search_text:
            if filtered_rows == 0:
                self.filter_status_label.setText("No matches found")
            elif filtered_rows != total_rows:
                self.filter_status_label.setText(f"{filtered_rows} of {total_rows} rows")
            else:
                self.filter_status_label.setText(f"All {total_rows} rows match")
        else:
            self.filter_status_label.setText("")
        
        # Enable/disable export filtered button based on whether a filter is active
        has_active_filter = bool(search_text and filtered_rows < total_rows)
        self.export_filtered_button.setEnabled(has_active_filter and filtered_rows > 0)

        self.export_button.setEnabled(not self.filtered_data.empty)