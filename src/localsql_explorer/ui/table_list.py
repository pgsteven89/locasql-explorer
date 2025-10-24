"""
Table list widget for displaying and managing database tables.

This module provides the TableListWidget class which shows:
- List of all loaded tables
- Table metadata (row count, column count)
- Context menu for table operations
- Table selection and preview functionality
"""

import logging
from typing import List, Optional
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtWidgets import (
    QListWidget,
    QListWidgetItem,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QInputDialog,
    QMessageBox
)
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPalette, QFont

from ..database import TableMetadata

logger = logging.getLogger(__name__)


class TableListItem(QListWidgetItem):
    """Custom list item for table metadata."""
    
    def __init__(self, metadata: TableMetadata):
        super().__init__()
        
        self.metadata = metadata
        self.update_display()
    
    def update_display(self):
        """Update the display text for this item."""
        text = f"{self.metadata.name}"
        detail = f"({self.metadata.row_count} rows, {self.metadata.column_count} cols)"
        
        self.setText(f"{text}\n{detail}")
        
        # Enhanced tooltip with column information
        tooltip_parts = [
            f"<b>Table:</b> {self.metadata.name}",
            f"<b>Rows:</b> {self.metadata.row_count:,}",
            f"<b>Columns:</b> {self.metadata.column_count}",
            f"<b>File:</b> {self.metadata.file_path or 'N/A'}",
            f"<b>Type:</b> {self.metadata.file_type or 'N/A'}",
            f"<b>Created:</b> {self.metadata.created_at}"
        ]
        
        # Add column preview
        if self.metadata.columns:
            tooltip_parts.append("<br><b>Columns:</b>")
            for i, col in enumerate(self.metadata.columns[:5]):  # Show first 5 columns
                col_name = col.get('name', 'N/A')
                col_type = col.get('type', 'N/A')
                tooltip_parts.append(f"• {col_name} ({col_type})")
            
            if len(self.metadata.columns) > 5:
                tooltip_parts.append(f"... and {len(self.metadata.columns) - 5} more")
        
        tooltip_text = "<br>".join(tooltip_parts)
        self.setToolTip(f"<div style='max-width: 300px;'>{tooltip_text}</div>")


class TableListWidget(QWidget):
    """
    Widget for displaying and managing database tables.
    
    Features:
    - List view of all tables with metadata
    - Context menu for table operations (rename, drop, export)
    - Double-click to preview table
    - Signals for table selection and operations
    """
    
    # Signals
    table_selected = pyqtSignal(str)  # Table name
    table_preview_requested = pyqtSignal(str)  # Table name
    table_renamed = pyqtSignal(str, str)  # Old name, new name
    table_dropped = pyqtSignal(str)  # Table name
    table_export_requested = pyqtSignal(str)  # Table name
    table_column_analysis_requested = pyqtSignal(str)  # Table name
    table_profiling_requested = pyqtSignal(str)  # Table name
    
    # New drag-and-drop signals
    files_dropped = pyqtSignal(list)  # List of file paths for import
    import_files_requested = pyqtSignal()  # Request multi-file import dialog
    
    def __init__(self):
        """Initialize the table list widget."""
        super().__init__()
        
        self.tables: dict[str, TableMetadata] = {}
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        
        self.title_label = QLabel("Tables")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        # Add import button for multi-file selection
        self.import_button = QPushButton("📁")
        self.import_button.setToolTip("Import multiple files")
        self.import_button.setMaximumWidth(30)
        self.import_button.clicked.connect(self.request_import_files)
        header_layout.addWidget(self.import_button)
        
        self.refresh_button = QPushButton("⟳")
        self.refresh_button.setToolTip("Refresh table list")
        self.refresh_button.setMaximumWidth(30)
        self.refresh_button.clicked.connect(self.refresh_tables)
        header_layout.addWidget(self.refresh_button)
        
        layout.addLayout(header_layout)
        
        # Drag-and-drop instructions
        self.drop_label = QLabel("📥 Drop files here to import")
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #888;
                border-radius: 8px;
                padding: 20px;
                margin: 10px;
                color: #888;
                font-style: italic;
                background-color: rgba(136, 136, 136, 0.1);
            }
        """)
        self.drop_label.setMinimumHeight(60)
        
        # Table list
        self.list_widget = QListWidget()
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        layout.addWidget(self.drop_label)
        layout.addWidget(self.list_widget)
        
        # Status label
        self.status_label = QLabel("No tables loaded")
        self.status_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        
        # Enable drag and drop
        self.setAcceptDrops(True)
        self.list_widget.setAcceptDrops(True)
    
    def add_table(self, metadata: TableMetadata):
        """
        Add a table to the list.
        
        Args:
            metadata: Table metadata
        """
        # Remove existing item if it exists
        if metadata.name in self.tables:
            self.remove_table(metadata.name)
        
        # Store metadata
        self.tables[metadata.name] = metadata
        
        # Create list item
        item = TableListItem(metadata)
        self.list_widget.addItem(item)
        
        # Update status
        self.update_status()
        
        # Update drop zone visibility
        self.update_drop_zone_visibility()
        
        logger.info(f"Added table '{metadata.name}' to list")
    
    def remove_table(self, table_name: str):
        """
        Remove a table from the list.
        
        Args:
            table_name: Name of the table to remove
        """
        if table_name not in self.tables:
            return
        
        # Find and remove the item
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if isinstance(item, TableListItem) and item.metadata.name == table_name:
                self.list_widget.takeItem(i)
                break
        
        # Remove from storage
        del self.tables[table_name]
        
        # Update status
        self.update_status()
        
        # Update drop zone visibility
        self.update_drop_zone_visibility()
        
        logger.info(f"Removed table '{table_name}' from list")
    
    def update_table(self, metadata: TableMetadata):
        """
        Update table metadata.
        
        Args:
            metadata: Updated table metadata
        """
        if metadata.name not in self.tables:
            self.add_table(metadata)
            return
        
        # Update stored metadata
        self.tables[metadata.name] = metadata
        
        # Find and update the item
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if isinstance(item, TableListItem) and item.metadata.name == metadata.name:
                item.metadata = metadata
                item.update_display()
                break
        
        logger.info(f"Updated table '{metadata.name}' metadata")
    
    def clear(self):
        """Clear all tables from the list."""
        self.list_widget.clear()
        self.tables.clear()
        self.update_status()
        
        logger.info("Cleared table list")
    
    def get_selected_table(self) -> Optional[str]:
        """Get the currently selected table name."""
        current_item = self.list_widget.currentItem()
        if isinstance(current_item, TableListItem):
            return current_item.metadata.name
        return None
    
    def select_table(self, table_name: str):
        """Select a specific table in the list."""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if isinstance(item, TableListItem) and item.metadata.name == table_name:
                self.list_widget.setCurrentItem(item)
                break
    
    def get_table_metadata(self, table_name: str) -> Optional[TableMetadata]:
        """Get metadata for a specific table."""
        return self.tables.get(table_name)
    
    def get_all_tables(self) -> List[TableMetadata]:
        """Get metadata for all tables."""
        return list(self.tables.values())
    
    def update_status(self):
        """Update the status label."""
        count = len(self.tables)
        if count == 0:
            self.status_label.setText("No tables loaded")
        elif count == 1:
            self.status_label.setText("1 table loaded")
        else:
            self.status_label.setText(f"{count} tables loaded")
    
    def refresh_tables(self):
        """Refresh the table list (placeholder for future implementation)."""
        # This would typically refresh from the database manager
        logger.info("Table list refresh requested")
    
    def on_item_clicked(self, item: QListWidgetItem):
        """Handle item click."""
        if isinstance(item, TableListItem):
            self.table_selected.emit(item.metadata.name)
    
    def on_item_double_clicked(self, item: QListWidgetItem):
        """Handle item double-click."""
        if isinstance(item, TableListItem):
            self.table_preview_requested.emit(item.metadata.name)
    
    def show_context_menu(self, position):
        """Show context menu for table operations."""
        item = self.list_widget.itemAt(position)
        if not isinstance(item, TableListItem):
            return
        
        table_name = item.metadata.name
        
        menu = QMenu(self)
        
        # Preview action
        preview_action = menu.addAction("Preview Table")
        preview_action.triggered.connect(lambda: self.table_preview_requested.emit(table_name))
        
        menu.addSeparator()
        
        # Rename action
        rename_action = menu.addAction("Rename Table...")
        rename_action.triggered.connect(lambda: self.rename_table(table_name))
        
        # Drop action
        drop_action = menu.addAction("Drop Table")
        drop_action.triggered.connect(lambda: self.drop_table(table_name))
        
        menu.addSeparator()
        
        # Export action
        export_action = menu.addAction("Export Table...")
        export_action.triggered.connect(lambda: self.table_export_requested.emit(table_name))
        
        menu.addSeparator()
        
        # Column analysis action
        analysis_action = menu.addAction("Column Analysis...")
        analysis_action.triggered.connect(lambda: self.table_column_analysis_requested.emit(table_name))
        
        # Table profiling action
        profiling_action = menu.addAction("Table Profiling...")
        profiling_action.triggered.connect(lambda: self.table_profiling_requested.emit(table_name))
        
        menu.addSeparator()
        
        # Show properties action
        properties_action = menu.addAction("Properties...")
        properties_action.triggered.connect(lambda: self.show_table_properties(table_name))
        
        # Show menu
        menu.exec(self.list_widget.mapToGlobal(position))
    
    def rename_table(self, table_name: str):
        """Rename a table."""
        new_name, ok = QInputDialog.getText(
            self,
            "Rename Table",
            f"Enter new name for table '{table_name}':",
            text=table_name
        )
        
        if ok and new_name and new_name != table_name:
            if new_name in self.tables:
                QMessageBox.warning(
                    self,
                    "Rename Error",
                    f"Table '{new_name}' already exists"
                )
                return
            
            # Emit signal for actual rename operation
            self.table_renamed.emit(table_name, new_name)
    
    def drop_table(self, table_name: str):
        """Drop a table."""
        reply = QMessageBox.question(
            self,
            "Drop Table",
            f"Are you sure you want to drop table '{table_name}'?\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Emit signal for actual drop operation
            self.table_dropped.emit(table_name)
    
    def show_table_properties(self, table_name: str):
        """Show table properties dialog."""
        metadata = self.tables.get(table_name)
        if not metadata:
            return
        
        # Create properties text
        properties = f"""
        <h3>Table Properties</h3>
        <table>
        <tr><td><b>Name:</b></td><td>{metadata.name}</td></tr>
        <tr><td><b>Rows:</b></td><td>{metadata.row_count:,}</td></tr>
        <tr><td><b>Columns:</b></td><td>{metadata.column_count}</td></tr>
        <tr><td><b>Source File:</b></td><td>{metadata.file_path or 'N/A'}</td></tr>
        <tr><td><b>File Type:</b></td><td>{metadata.file_type or 'N/A'}</td></tr>
        <tr><td><b>Created:</b></td><td>{metadata.created_at}</td></tr>
        </table>
        
        <h4>Columns:</h4>
        <table border="1" cellpadding="3">
        <tr><th>Name</th><th>Type</th></tr>
        """
        
        for col in metadata.columns:
            properties += f"<tr><td>{col.get('name', 'N/A')}</td><td>{col.get('type', 'N/A')}</td></tr>"
        
        properties += "</table>"
        
        # Show dialog
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(f"Properties - {table_name}")
        msg_box.setText(properties)
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        msg_box.exec()
    
    def request_import_files(self):
        """Request multi-file import dialog."""
        self.import_files_requested.emit()
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter events."""
        if event.mimeData().hasUrls():
            # Check if any of the dragged items are files we can import
            urls = event.mimeData().urls()
            valid_files = []
            
            for url in urls:
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    file_ext = Path(file_path).suffix.lower()
                    if file_ext in ['.csv', '.xlsx', '.xls', '.parquet', '.pq']:
                        valid_files.append(file_path)
            
            if valid_files:
                event.acceptProposedAction()
                self._highlight_drop_zone(True)
            else:
                event.ignore()
        else:
            event.ignore()
    
    def dragMoveEvent(self, event):
        """Handle drag move events."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dragLeaveEvent(self, event):
        """Handle drag leave events."""
        self._highlight_drop_zone(False)
        super().dragLeaveEvent(event)
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop events."""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            file_paths = []
            
            for url in urls:
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    file_ext = Path(file_path).suffix.lower()
                    if file_ext in ['.csv', '.xlsx', '.xls', '.parquet', '.pq']:
                        file_paths.append(file_path)
            
            if file_paths:
                # Emit signal with the dropped file paths
                self.files_dropped.emit(file_paths)
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()
        
        self._highlight_drop_zone(False)
    
    def _highlight_drop_zone(self, highlight: bool):
        """Highlight or unhighlight the drop zone."""
        if highlight:
            self.drop_label.setStyleSheet("""
                QLabel {
                    border: 2px dashed #4A9EFF;
                    border-radius: 8px;
                    padding: 20px;
                    margin: 10px;
                    color: #4A9EFF;
                    font-style: italic;
                    font-weight: bold;
                    background-color: rgba(74, 158, 255, 0.2);
                }
            """)
            self.drop_label.setText("📥 Drop files to import them!")
        else:
            self.drop_label.setStyleSheet("""
                QLabel {
                    border: 2px dashed #888;
                    border-radius: 8px;
                    padding: 20px;
                    margin: 10px;
                    color: #888;
                    font-style: italic;
                    background-color: rgba(136, 136, 136, 0.1);
                }
            """)
            self.drop_label.setText("📥 Drop files here to import")
    
    def update_drop_zone_visibility(self):
        """Update drop zone visibility based on whether tables exist."""
        if len(self.tables) == 0:
            self.drop_label.show()
        else:
            self.drop_label.hide()