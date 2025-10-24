"""
Query history UI components for LocalSQL Explorer.

This module provides:
- Query history panel with search and filtering
- Favorites management interface
- Query details and editing dialogs
- Quick access to recent queries
"""

import logging
from datetime import datetime
from typing import List, Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QFont, QIcon
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFrame, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMenu, QPushButton, QSizePolicy, QSplitter, QTabWidget, QTableWidget,
    QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget
)

from ..query_history import QueryEntry, QueryHistory

logger = logging.getLogger(__name__)


class QueryHistoryPanel(QWidget):
    """
    Main query history panel widget.
    
    Features:
    - Tabbed interface for Recent/Favorites
    - Search and filtering
    - Quick access buttons
    - Context menus for query management
    """
    
    query_selected = pyqtSignal(str)  # Emitted when user selects a query to run
    query_edited = pyqtSignal(str, str)  # Emitted when user edits a query (old_sql, new_sql)
    
    def __init__(self, query_history: QueryHistory, parent=None):
        super().__init__(parent)
        self.query_history = query_history
        self.current_queries: List[QueryEntry] = []
        self.setup_ui()
        self.refresh_history()
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_history)
        self.refresh_timer.start(30000)  # Refresh every 30 seconds
    
    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Search and filter section
        search_frame = QFrame()
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(0, 0, 0, 0)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search queries...")
        self.search_input.textChanged.connect(self.on_search_changed)
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All", "Recent", "Favorites", "Successful", "Failed"])
        self.filter_combo.currentTextChanged.connect(self.on_filter_changed)
        
        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.search_input, 1)
        search_layout.addWidget(QLabel("Filter:"))
        search_layout.addWidget(self.filter_combo)
        
        layout.addWidget(search_frame)
        
        # Main content area
        self.tab_widget = QTabWidget()
        
        # Recent queries tab
        self.recent_tab = self.create_queries_tab()
        self.tab_widget.addTab(self.recent_tab, "Recent")
        
        # Favorites tab
        self.favorites_tab = self.create_queries_tab()
        self.tab_widget.addTab(self.favorites_tab, "Favorites")
        
        layout.addWidget(self.tab_widget, 1)
        
        # Action buttons
        button_frame = QFrame()
        button_layout = QHBoxLayout(button_frame)
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        self.clear_btn = QPushButton("Clear History")
        self.clear_btn.clicked.connect(self.clear_history)
        
        self.stats_btn = QPushButton("Statistics")
        self.stats_btn.clicked.connect(self.show_statistics)
        
        button_layout.addWidget(self.clear_btn)
        button_layout.addWidget(self.stats_btn)
        button_layout.addStretch()
        
        layout.addWidget(button_frame)
    
    def create_queries_tab(self) -> QWidget:
        """Create a tab widget for displaying queries."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create table widget
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Time", "SQL", "Duration", "Rows", "Status"])
        
        # Configure table
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Time
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)           # SQL
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Duration
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Rows
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Status
        
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(self.show_context_menu)
        table.cellDoubleClicked.connect(self.on_query_double_clicked)
        
        layout.addWidget(table)
        
        # Store reference to table in tab
        tab.table = table
        
        return tab
    
    def refresh_history(self):
        """Refresh the query history display."""
        current_filter = self.filter_combo.currentText()
        search_text = self.search_input.text()
        
        # Get queries based on current tab
        if self.tab_widget.currentIndex() == 0:  # Recent tab
            if current_filter == "Favorites":
                queries = self.query_history.get_favorites()
            else:
                queries = self.query_history.get_recent_queries(100)
        else:  # Favorites tab
            queries = self.query_history.get_favorites()
        
        # Apply filters
        if current_filter == "Successful":
            queries = [q for q in queries if q.success]
        elif current_filter == "Failed":
            queries = [q for q in queries if not q.success]
        
        # Apply search
        if search_text:
            queries = [q for q in queries if self.match_query(q, search_text)]
        
        self.current_queries = queries
        self.populate_table(self.get_current_table(), queries)
    
    def match_query(self, query: QueryEntry, search_text: str) -> bool:
        """Check if query matches search criteria."""
        search_text = search_text.lower()
        return (
            search_text in query.sql.lower() or
            (query.description and search_text in query.description.lower()) or
            any(search_text in tag.lower() for tag in query.tags)
        )
    
    def populate_table(self, table: QTableWidget, queries: List[QueryEntry]):
        """Populate table with query entries."""
        table.setRowCount(len(queries))
        
        for row, query in enumerate(queries):
            # Time
            try:
                dt = datetime.fromisoformat(query.timestamp)
                time_str = dt.strftime("%H:%M:%S")
            except:
                time_str = "Unknown"
            
            time_item = QTableWidgetItem(time_str)
            time_item.setData(Qt.ItemDataRole.UserRole, query.id)
            table.setItem(row, 0, time_item)
            
            # SQL (truncated)
            sql_preview = query.sql[:100] + "..." if len(query.sql) > 100 else query.sql
            sql_item = QTableWidgetItem(sql_preview)
            sql_item.setToolTip(query.sql)
            if query.is_favorite:
                font = sql_item.font()
                font.setBold(True)
                sql_item.setFont(font)
            table.setItem(row, 1, sql_item)
            
            # Duration
            duration_str = f"{query.execution_time:.3f}s"
            table.setItem(row, 2, QTableWidgetItem(duration_str))
            
            # Rows
            rows_str = str(query.row_count) if query.success else "N/A"
            table.setItem(row, 3, QTableWidgetItem(rows_str))
            
            # Status
            status_str = "✓" if query.success else "✗"
            status_item = QTableWidgetItem(status_str)
            if query.success:
                status_item.setForeground(Qt.GlobalColor.darkGreen)
            else:
                status_item.setForeground(Qt.GlobalColor.red)
                if query.error_message:
                    status_item.setToolTip(query.error_message)
            table.setItem(row, 4, status_item)
    
    def get_current_table(self) -> QTableWidget:
        """Get the currently active table widget."""
        current_tab = self.tab_widget.currentWidget()
        return current_tab.table
    
    def get_selected_query(self) -> Optional[QueryEntry]:
        """Get the currently selected query."""
        table = self.get_current_table()
        current_row = table.currentRow()
        
        if current_row >= 0 and current_row < len(self.current_queries):
            return self.current_queries[current_row]
        return None
    
    def on_search_changed(self):
        """Handle search text changes."""
        self.refresh_history()
    
    def on_filter_changed(self):
        """Handle filter changes."""
        self.refresh_history()
    
    def on_query_double_clicked(self, row: int, column: int):
        """Handle double-click on query."""
        if row < len(self.current_queries):
            query = self.current_queries[row]
            self.query_selected.emit(query.sql)
    
    def show_context_menu(self, position):
        """Show context menu for query management."""
        table = self.get_current_table()
        item = table.itemAt(position)
        if not item:
            return
        
        query = self.get_selected_query()
        if not query:
            return
        
        menu = QMenu(self)
        
        # Run query action
        run_action = QAction("Run Query", self)
        run_action.triggered.connect(lambda: self.query_selected.emit(query.sql))
        menu.addAction(run_action)
        
        # Edit query action
        edit_action = QAction("Edit Query", self)
        edit_action.triggered.connect(lambda: self.edit_query(query))
        menu.addAction(edit_action)
        
        menu.addSeparator()
        
        # Favorite actions
        if query.is_favorite:
            fav_action = QAction("Remove from Favorites", self)
            fav_action.triggered.connect(lambda: self.toggle_favorite(query, False))
        else:
            fav_action = QAction("Add to Favorites", self)
            fav_action.triggered.connect(lambda: self.toggle_favorite(query, True))
        menu.addAction(fav_action)
        
        # Details action
        details_action = QAction("View Details", self)
        details_action.triggered.connect(lambda: self.show_query_details(query))
        menu.addAction(details_action)
        
        menu.addSeparator()
        
        # Delete action
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(lambda: self.delete_query(query))
        menu.addAction(delete_action)
        
        menu.exec(table.mapToGlobal(position))
    
    def toggle_favorite(self, query: QueryEntry, is_favorite: bool):
        """Toggle query favorite status."""
        self.query_history.mark_favorite(query.id, is_favorite)
        self.refresh_history()
    
    def edit_query(self, query: QueryEntry):
        """Open query edit dialog."""
        dialog = QueryEditDialog(query, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_sql = dialog.get_sql()
            if new_sql != query.sql:
                self.query_edited.emit(query.sql, new_sql)
    
    def show_query_details(self, query: QueryEntry):
        """Show detailed query information."""
        dialog = QueryDetailsDialog(query, self.query_history, self)
        dialog.exec()
    
    def delete_query(self, query: QueryEntry):
        """Delete a query from history."""
        self.query_history.delete_query(query.id)
        self.refresh_history()
    
    def clear_history(self):
        """Clear query history."""
        from PyQt6.QtWidgets import QMessageBox
        
        reply = QMessageBox.question(
            self, "Clear History",
            "Clear query history? Favorites will be preserved.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            deleted_count = self.query_history.clear_history(keep_favorites=True)
            self.refresh_history()
            QMessageBox.information(self, "History Cleared", f"Deleted {deleted_count} queries.")
    
    def show_statistics(self):
        """Show query statistics."""
        dialog = QueryStatisticsDialog(self.query_history, self)
        dialog.exec()


class QueryEditDialog(QDialog):
    """Dialog for editing a query."""
    
    def __init__(self, query: QueryEntry, parent=None):
        super().__init__(parent)
        self.query = query
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Edit Query")
        self.setModal(True)
        self.resize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # SQL editor
        layout.addWidget(QLabel("SQL Query:"))
        self.sql_edit = QTextEdit()
        self.sql_edit.setPlainText(self.query.sql)
        self.sql_edit.setFont(QFont("Courier New", 10))
        layout.addWidget(self.sql_edit)
        
        # Description
        layout.addWidget(QLabel("Description (optional):"))
        self.description_edit = QLineEdit()
        if self.query.description:
            self.description_edit.setText(self.query.description)
        layout.addWidget(self.description_edit)
        
        # Tags
        layout.addWidget(QLabel("Tags (comma-separated):"))
        self.tags_edit = QLineEdit()
        self.tags_edit.setText(", ".join(self.query.tags))
        layout.addWidget(self.tags_edit)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def get_sql(self) -> str:
        """Get the edited SQL."""
        return self.sql_edit.toPlainText().strip()
    
    def accept(self):
        """Accept the dialog and save changes."""
        # Update query metadata
        if self.description_edit.text().strip():
            self.query.query_history.set_description(self.query.id, self.description_edit.text().strip())
        
        # Update tags
        tags_text = self.tags_edit.text().strip()
        if tags_text:
            new_tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]
            # Clear existing tags and add new ones
            for tag in self.query.tags[:]:
                self.query.query_history.remove_tag(self.query.id, tag)
            for tag in new_tags:
                self.query.query_history.add_tag(self.query.id, tag)
        
        super().accept()


class QueryDetailsDialog(QDialog):
    """Dialog showing detailed query information."""
    
    def __init__(self, query: QueryEntry, query_history: QueryHistory, parent=None):
        super().__init__(parent)
        self.query = query
        self.query_history = query_history
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Query Details")
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # Basic info
        info_group = QGroupBox("Query Information")
        info_layout = QVBoxLayout(info_group)
        
        # Timestamp
        try:
            dt = datetime.fromisoformat(self.query.timestamp)
            time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            time_str = self.query.timestamp
        
        info_layout.addWidget(QLabel(f"<b>Executed:</b> {time_str}"))
        info_layout.addWidget(QLabel(f"<b>Duration:</b> {self.query.execution_time:.3f} seconds"))
        info_layout.addWidget(QLabel(f"<b>Rows Returned:</b> {self.query.row_count}"))
        
        status_text = "Success" if self.query.success else f"Failed: {self.query.error_message}"
        info_layout.addWidget(QLabel(f"<b>Status:</b> {status_text}"))
        
        if self.query.tables_used:
            info_layout.addWidget(QLabel(f"<b>Tables Used:</b> {', '.join(self.query.tables_used)}"))
        
        if self.query.tags:
            info_layout.addWidget(QLabel(f"<b>Tags:</b> {', '.join(self.query.tags)}"))
        
        if self.query.description:
            info_layout.addWidget(QLabel(f"<b>Description:</b> {self.query.description}"))
        
        layout.addWidget(info_group)
        
        # SQL text
        sql_group = QGroupBox("SQL Query")
        sql_layout = QVBoxLayout(sql_group)
        
        sql_text = QTextEdit()
        sql_text.setPlainText(self.query.sql)
        sql_text.setFont(QFont("Courier New", 10))
        sql_text.setReadOnly(True)
        sql_layout.addWidget(sql_text)
        
        layout.addWidget(sql_group)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class QueryStatisticsDialog(QDialog):
    """Dialog showing query usage statistics."""
    
    def __init__(self, query_history: QueryHistory, parent=None):
        super().__init__(parent)
        self.query_history = query_history
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Query Statistics")
        self.setModal(True)
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        
        stats = self.query_history.get_query_stats()
        
        # Overall statistics
        overview_group = QGroupBox("Overview")
        overview_layout = QVBoxLayout(overview_group)
        
        overview_layout.addWidget(QLabel(f"<b>Total Queries:</b> {stats['total_queries']}"))
        overview_layout.addWidget(QLabel(f"<b>Successful:</b> {stats['successful_queries']}"))
        overview_layout.addWidget(QLabel(f"<b>Favorites:</b> {stats['favorite_count']}"))
        overview_layout.addWidget(QLabel(f"<b>Success Rate:</b> {stats['success_rate']:.1%}"))
        overview_layout.addWidget(QLabel(f"<b>Avg. Execution Time:</b> {stats['average_execution_time']:.3f}s"))
        
        layout.addWidget(overview_group)
        
        # Most used tables
        if stats['most_used_tables']:
            tables_group = QGroupBox("Most Used Tables")
            tables_layout = QVBoxLayout(tables_group)
            
            for table, count in stats['most_used_tables']:
                tables_layout.addWidget(QLabel(f"<b>{table}:</b> {count} queries"))
            
            layout.addWidget(tables_group)
        
        # Close button
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)