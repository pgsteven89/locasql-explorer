"""
Results table view for displaying query results.

This module provides the ResultsTableView class which displays:
- Query results in a tabular format
- Sorting and scrolling capabilities
- Export functionality
- Large dataset handling with pagination
"""

import logging
from typing import Optional

import pandas as pd
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QVariant, pyqtSignal
from PyQt6.QtWidgets import (
    QTableView,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QHeaderView,
    QAbstractItemView,
    QMenu
)
from PyQt6.QtGui import QAction

logger = logging.getLogger(__name__)


class PandasTableModel(QAbstractTableModel):
    """Table model for displaying pandas DataFrames in QTableView."""
    
    def __init__(self, dataframe: Optional[pd.DataFrame] = None):
        super().__init__()
        self._dataframe = dataframe or pd.DataFrame()
    
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
            elif isinstance(value, float):
                return f"{value:.6g}"  # Format floats nicely
            else:
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
    export_requested = pyqtSignal()  # Emitted when export is requested
    
    def __init__(self):
        """Initialize the results table view."""
        super().__init__()
        
        self.model = PandasTableModel()
        
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
        
        self.export_button = QPushButton("Export...")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.export_results)
        header_layout.addWidget(self.export_button)
        
        layout.addLayout(header_layout)
        
        # Table view
        self.table_view = QTableView()
        self.table_view.setModel(self.model)
        
        # Configure table view
        self.table_view.setSortingEnabled(True)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        
        # Enable context menu
        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self.show_context_menu)
        
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
    
    def set_dataframe(self, dataframe: pd.DataFrame):
        """
        Set the dataframe to display.
        
        Args:
            dataframe: Pandas DataFrame to display
        """
        # Update model
        self.model.set_dataframe(dataframe)
        
        # Update info labels
        self.update_info_labels(dataframe)
        
        # Enable export button
        self.export_button.setEnabled(not dataframe.empty)
        
        # Auto-resize columns to content (with limits)
        self.table_view.resizeColumnsToContents()
        
        # Set maximum column width to prevent excessive stretching
        header = self.table_view.horizontalHeader()
        for i in range(self.model.columnCount()):
            width = header.sectionSize(i)
            if width > 200:
                header.resizeSection(i, 200)
        
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
        """Get the current dataframe."""
        if self.model.rowCount() == 0:
            return None
        return self.model.get_dataframe()
    
    def has_data(self) -> bool:
        """Check if there is data to display."""
        return self.model.rowCount() > 0
    
    def clear(self):
        """Clear the results view."""
        self.set_dataframe(pd.DataFrame())
    
    def export_results(self):
        """Export results (placeholder - would be connected to parent)."""
        # Emit signal to parent window to handle export
        self.export_requested.emit()
        logger.info("Export results requested")
    
    def show_context_menu(self, position):
        """Show context menu at the given position."""
        if not self.has_data():
            return
            
        menu = QMenu(self)
        
        # Export action
        export_action = QAction("Export Results...", self)
        export_action.triggered.connect(self.export_results)
        menu.addAction(export_action)
        
        # Copy selected action
        copy_action = QAction("Copy Selected Rows", self)
        copy_action.triggered.connect(self.copy_selected_rows)
        copy_action.setEnabled(len(self.get_selected_rows()) > 0)
        menu.addAction(copy_action)
        
        menu.addSeparator()
        
        # Row count info
        row_count = self.model.rowCount()
        selected_count = len(self.get_selected_rows())
        if selected_count > 0:
            info_action = QAction(f"Selected: {selected_count} of {row_count} rows", self)
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
            from PyQt6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(clipboard_text)
            
            logger.info(f"Copied {len(selected_data)} rows to clipboard")
    
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