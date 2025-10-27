"""
Tabbed SQL Editor widget supporting multiple query tabs.

This module provides the TabbedSQLEditor class which offers:
- Multiple SQL editor tabs for different queries
- Tab management (create, close, rename, reorder)
- Keyboard shortcuts (Ctrl+T, Ctrl+W, Ctrl+Tab)
- Multi-query support within each tab
- Run current query at cursor position
- Run all queries in current tab
- Ctrl+Enter shortcut for query execution
- Tab state persistence
"""

import logging
from typing import Optional, Dict, List
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal, QSettings
from PyQt6.QtGui import QKeySequence, QShortcut, QAction
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QPushButton,
    QInputDialog, QMessageBox, QMenu, QToolButton
)

from ..models import UserPreferences
from ..query_parser import QueryParser, QueryInfo, get_query_parser
from .enhanced_sql_editor import EnhancedSQLEditor

logger = logging.getLogger(__name__)


class SQLEditorTab(QWidget):
    """
    A single SQL editor tab with multi-query support.
    
    Features:
    - Enhanced SQL editor
    - Multi-query parsing and execution
    - Current query highlighting
    - Modified state tracking
    """
    
    query_requested = pyqtSignal(str)  # Single query
    all_queries_requested = pyqtSignal(list)  # List of queries
    modified_changed = pyqtSignal(bool)
    
    def __init__(self, preferences: Optional[UserPreferences] = None, tab_name: str = "Query"):
        """
        Initialize the SQL editor tab.
        
        Args:
            preferences: User preferences
            tab_name: Name of the tab
        """
        super().__init__()
        
        self.preferences = preferences or UserPreferences()
        self.tab_name = tab_name
        self.query_parser = get_query_parser()
        self.is_modified = False
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create the enhanced SQL editor
        self.editor = EnhancedSQLEditor(self.preferences)
        
        # Override the query_requested signal to handle multi-query
        # Try to disconnect first if there are connections
        try:
            self.editor.query_requested.disconnect()
        except TypeError:
            # No connections to disconnect
            pass
        self.editor.query_requested.connect(self._on_run_current_query)
        
        # Connect text changed signal for modified tracking
        if hasattr(self.editor, 'text_edit'):
            self.editor.text_edit.textChanged.connect(self._on_text_changed)
        
        layout.addWidget(self.editor)
        
        # Add custom toolbar for multi-query support
        toolbar_layout = QHBoxLayout()
        
        self.run_current_button = QPushButton("▶ Run Current Query (Ctrl+Enter)")
        self.run_current_button.setToolTip("Execute the query at cursor position (Ctrl+Enter)")
        self.run_current_button.clicked.connect(self._on_run_current_query)
        toolbar_layout.addWidget(self.run_current_button)
        
        self.run_all_button = QPushButton("▶▶ Run All Queries")
        self.run_all_button.setToolTip("Execute all queries in sequence (Ctrl+Shift+Enter)")
        self.run_all_button.clicked.connect(self._on_run_all_queries)
        toolbar_layout.addWidget(self.run_all_button)
        
        toolbar_layout.addStretch()
        
        # Query count label
        self.query_count_label = QPushButton("Queries: 0")
        self.query_count_label.setFlat(True)
        self.query_count_label.setToolTip("Number of queries in this editor")
        toolbar_layout.addWidget(self.query_count_label)
        
        # Insert toolbar at the top of the editor
        layout.insertLayout(0, toolbar_layout)
        
        self.setLayout(layout)
        
        # Update query count
        self._update_query_count()
    
    def _on_text_changed(self):
        """Handle text changed event."""
        self.is_modified = True
        self.modified_changed.emit(True)
        self._update_query_count()
    
    def _update_query_count(self):
        """Update the query count label."""
        text = self.get_sql()
        queries = self.query_parser.parse_queries(text)
        count = len(queries)
        self.query_count_label.setText(f"Queries: {count}")
    
    def _on_run_current_query(self):
        """Handle run current query request."""
        text = self.get_sql()
        cursor_pos = self.get_cursor_position()
        
        query_info = self.query_parser.get_query_at_cursor(text, cursor_pos)
        
        if query_info:
            logger.info(f"Running query {query_info.query_number} at cursor position")
            self.query_requested.emit(query_info.text)
        else:
            # Fallback: run entire text if no query found
            if text.strip():
                logger.info("No specific query found at cursor, running entire text")
                self.query_requested.emit(text)
            else:
                QMessageBox.warning(self, "No Query", "No query found to execute.")
    
    def _on_run_all_queries(self):
        """Handle run all queries request."""
        text = self.get_sql()
        queries = self.query_parser.parse_queries(text)
        
        if not queries:
            QMessageBox.warning(self, "No Queries", "No queries found to execute.")
            return
        
        logger.info(f"Running all {len(queries)} queries")
        query_texts = [q.text for q in queries]
        self.all_queries_requested.emit(query_texts)
    
    def get_sql(self) -> str:
        """Get the SQL text from the editor."""
        return self.editor.get_sql()
    
    def set_sql(self, sql: str):
        """Set the SQL text in the editor."""
        self.editor.set_sql(sql)
        self.is_modified = False
        self.modified_changed.emit(False)
        self._update_query_count()
    
    def get_cursor_position(self) -> int:
        """Get the current cursor position."""
        if hasattr(self.editor, 'text_edit'):
            return self.editor.text_edit.textCursor().position()
        return 0
    
    def clear(self):
        """Clear the editor."""
        self.editor.clear()
        self.is_modified = False
        self.modified_changed.emit(False)
    
    def set_modified(self, modified: bool):
        """Set the modified state."""
        self.is_modified = modified
        self.modified_changed.emit(modified)


class TabbedSQLEditor(QWidget):
    """
    Tabbed SQL Editor widget with multi-query support.
    
    Features:
    - Multiple editor tabs
    - Tab management (create, close, rename)
    - Keyboard shortcuts
    - Multi-query execution
    - Tab state persistence
    """
    
    query_requested = pyqtSignal(str, int)  # query text, tab index
    all_queries_requested = pyqtSignal(list, int)  # list of queries, tab index
    
    def __init__(self, preferences: Optional[UserPreferences] = None):
        """
        Initialize the tabbed SQL editor.
        
        Args:
            preferences: User preferences
        """
        super().__init__()
        
        self.preferences = preferences or UserPreferences()
        self.tab_counter = 1
        
        self.init_ui()
        self.setup_shortcuts()
        
        # Create first tab
        self.add_new_tab()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.setDocumentMode(True)
        
        # Add "+" button for new tab
        self.new_tab_button = QToolButton()
        self.new_tab_button.setText("+")
        self.new_tab_button.setToolTip("New Tab (Ctrl+T)")
        self.new_tab_button.clicked.connect(self.add_new_tab)
        self.tab_widget.setCornerWidget(self.new_tab_button, Qt.Corner.TopRightCorner)
        
        # Connect signals
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        self.tab_widget.tabBarDoubleClicked.connect(self._on_tab_double_clicked)
        
        # Context menu
        self.tab_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tab_widget.customContextMenuRequested.connect(self._show_tab_context_menu)
        
        layout.addWidget(self.tab_widget)
        self.setLayout(layout)
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        # Ctrl+T: New tab
        new_tab_shortcut = QShortcut(QKeySequence("Ctrl+T"), self)
        new_tab_shortcut.activated.connect(self.add_new_tab)
        
        # Ctrl+W: Close tab
        close_tab_shortcut = QShortcut(QKeySequence("Ctrl+W"), self)
        close_tab_shortcut.activated.connect(lambda: self.close_tab(self.tab_widget.currentIndex()))
        
        # Ctrl+Tab: Next tab
        next_tab_shortcut = QShortcut(QKeySequence("Ctrl+Tab"), self)
        next_tab_shortcut.activated.connect(self.next_tab)
        
        # Ctrl+Shift+Tab: Previous tab
        prev_tab_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Tab"), self)
        prev_tab_shortcut.activated.connect(self.previous_tab)
        
        # Ctrl+Enter: Run current query
        run_query_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        run_query_shortcut.activated.connect(self._run_current_query_in_active_tab)
        
        # Ctrl+Shift+Enter: Run all queries
        run_all_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Return"), self)
        run_all_shortcut.activated.connect(self._run_all_queries_in_active_tab)
    
    def add_new_tab(self) -> int:
        """
        Add a new editor tab.
        
        Returns:
            Index of the new tab
        """
        tab_name = f"Query {self.tab_counter}"
        self.tab_counter += 1
        
        tab = SQLEditorTab(self.preferences, tab_name)
        tab.query_requested.connect(lambda q: self._emit_query_requested(q))
        tab.all_queries_requested.connect(lambda qs: self._emit_all_queries_requested(qs))
        tab.modified_changed.connect(lambda m: self._update_tab_title(self.tab_widget.indexOf(tab)))
        
        index = self.tab_widget.addTab(tab, tab_name)
        self.tab_widget.setCurrentIndex(index)
        
        logger.info(f"Added new tab: {tab_name} at index {index}")
        
        return index
    
    def close_tab(self, index: int):
        """
        Close a tab at the specified index.
        
        Args:
            index: Index of the tab to close
        """
        # Always keep at least one tab open
        if self.tab_widget.count() <= 1:
            logger.info("Cannot close last tab")
            return
        
        tab = self.tab_widget.widget(index)
        
        # Check if modified
        if isinstance(tab, SQLEditorTab) and tab.is_modified:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                f"Tab '{self.tab_widget.tabText(index)}' has unsaved changes. Close anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                return
        
        self.tab_widget.removeTab(index)
        logger.info(f"Closed tab at index {index}")
    
    def rename_tab(self, index: int):
        """
        Rename a tab at the specified index.
        
        Args:
            index: Index of the tab to rename
        """
        current_name = self.tab_widget.tabText(index).rstrip(" *")
        
        new_name, ok = QInputDialog.getText(
            self,
            "Rename Tab",
            "Enter new tab name:",
            text=current_name
        )
        
        if ok and new_name:
            tab = self.tab_widget.widget(index)
            if isinstance(tab, SQLEditorTab):
                tab.tab_name = new_name
                self._update_tab_title(index)
                logger.info(f"Renamed tab {index} to '{new_name}'")
    
    def _update_tab_title(self, index: int):
        """Update tab title with modified indicator."""
        tab = self.tab_widget.widget(index)
        if isinstance(tab, SQLEditorTab):
            title = tab.tab_name
            if tab.is_modified:
                title += " *"
            self.tab_widget.setTabText(index, title)
    
    def _on_tab_changed(self, index: int):
        """Handle tab change event."""
        if index >= 0:
            logger.debug(f"Switched to tab {index}")
    
    def _on_tab_double_clicked(self, index: int):
        """Handle tab double-click event."""
        if index >= 0:
            self.rename_tab(index)
    
    def _show_tab_context_menu(self, position):
        """Show context menu for tab bar."""
        index = self.tab_widget.tabBar().tabAt(position)
        if index < 0:
            return
        
        menu = QMenu(self)
        
        rename_action = QAction("Rename", self)
        rename_action.triggered.connect(lambda: self.rename_tab(index))
        menu.addAction(rename_action)
        
        menu.addSeparator()
        
        close_action = QAction("Close", self)
        close_action.triggered.connect(lambda: self.close_tab(index))
        menu.addAction(close_action)
        
        close_others_action = QAction("Close Others", self)
        close_others_action.triggered.connect(lambda: self.close_other_tabs(index))
        menu.addAction(close_others_action)
        
        close_right_action = QAction("Close Tabs to the Right", self)
        close_right_action.triggered.connect(lambda: self.close_tabs_to_right(index))
        menu.addAction(close_right_action)
        
        menu.exec(self.tab_widget.tabBar().mapToGlobal(position))
    
    def close_other_tabs(self, keep_index: int):
        """Close all tabs except the specified one."""
        for i in range(self.tab_widget.count() - 1, -1, -1):
            if i != keep_index:
                self.close_tab(i)
    
    def close_tabs_to_right(self, from_index: int):
        """Close all tabs to the right of the specified index."""
        for i in range(self.tab_widget.count() - 1, from_index, -1):
            self.close_tab(i)
    
    def next_tab(self):
        """Switch to the next tab."""
        current = self.tab_widget.currentIndex()
        next_index = (current + 1) % self.tab_widget.count()
        self.tab_widget.setCurrentIndex(next_index)
    
    def previous_tab(self):
        """Switch to the previous tab."""
        current = self.tab_widget.currentIndex()
        prev_index = (current - 1) % self.tab_widget.count()
        self.tab_widget.setCurrentIndex(prev_index)
    
    def _emit_query_requested(self, query: str):
        """Emit query_requested signal with current tab index."""
        self.query_requested.emit(query, self.tab_widget.currentIndex())
    
    def _emit_all_queries_requested(self, queries: List[str]):
        """Emit all_queries_requested signal with current tab index."""
        self.all_queries_requested.emit(queries, self.tab_widget.currentIndex())
    
    def _run_current_query_in_active_tab(self):
        """Run current query in the active tab."""
        tab = self.tab_widget.currentWidget()
        if isinstance(tab, SQLEditorTab):
            tab._on_run_current_query()
    
    def _run_all_queries_in_active_tab(self):
        """Run all queries in the active tab."""
        tab = self.tab_widget.currentWidget()
        if isinstance(tab, SQLEditorTab):
            tab._on_run_all_queries()
    
    # Public API methods for compatibility with existing code
    
    def get_sql(self) -> str:
        """Get SQL from the current tab."""
        tab = self.tab_widget.currentWidget()
        if isinstance(tab, SQLEditorTab):
            return tab.get_sql()
        return ""
    
    def set_sql(self, sql: str):
        """Set SQL in the current tab."""
        tab = self.tab_widget.currentWidget()
        if isinstance(tab, SQLEditorTab):
            tab.set_sql(sql)
    
    def clear(self):
        """Clear the current tab."""
        tab = self.tab_widget.currentWidget()
        if isinstance(tab, SQLEditorTab):
            tab.clear()
    
    def request_query_execution(self):
        """Request query execution for current tab."""
        self._run_current_query_in_active_tab()
    
    # Methods for compatibility with EnhancedSQLEditor interface
    
    def undo(self):
        """Undo in current tab."""
        tab = self.tab_widget.currentWidget()
        if isinstance(tab, SQLEditorTab):
            tab.editor.undo()
    
    def redo(self):
        """Redo in current tab."""
        tab = self.tab_widget.currentWidget()
        if isinstance(tab, SQLEditorTab):
            tab.editor.redo()
    
    def cut(self):
        """Cut in current tab."""
        tab = self.tab_widget.currentWidget()
        if isinstance(tab, SQLEditorTab):
            tab.editor.cut()
    
    def copy(self):
        """Copy in current tab."""
        tab = self.tab_widget.currentWidget()
        if isinstance(tab, SQLEditorTab):
            tab.editor.copy()
    
    def paste(self):
        """Paste in current tab."""
        tab = self.tab_widget.currentWidget()
        if isinstance(tab, SQLEditorTab):
            tab.editor.paste()
    
    def toggle_comment(self):
        """Toggle SQL line comments in current tab."""
        tab = self.tab_widget.currentWidget()
        if isinstance(tab, SQLEditorTab):
            tab.editor.toggle_comment()
    
    def set_tables(self, tables: List[str]):
        """Set available tables for auto-completion in all tabs."""
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if isinstance(tab, SQLEditorTab) and hasattr(tab.editor, 'set_tables'):
                tab.editor.set_tables(tables)
    
    def save_state(self):
        """Save the state of all tabs."""
        settings = QSettings("LocalSQL Explorer", "TabbedEditor")
        settings.beginGroup("Tabs")
        
        settings.setValue("count", self.tab_widget.count())
        settings.setValue("current", self.tab_widget.currentIndex())
        settings.setValue("counter", self.tab_counter)
        
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if isinstance(tab, SQLEditorTab):
                settings.beginGroup(f"Tab{i}")
                settings.setValue("name", tab.tab_name)
                settings.setValue("sql", tab.get_sql())
                settings.endGroup()
        
        settings.endGroup()
        logger.info(f"Saved state of {self.tab_widget.count()} tabs")
    
    def restore_state(self):
        """Restore the state of all tabs."""
        settings = QSettings("LocalSQL Explorer", "TabbedEditor")
        settings.beginGroup("Tabs")
        
        count = settings.value("count", 0, type=int)
        if count == 0:
            settings.endGroup()
            return
        
        current_index = settings.value("current", 0, type=int)
        self.tab_counter = settings.value("counter", 1, type=int)
        
        # Remove default tab
        if self.tab_widget.count() > 0:
            self.tab_widget.clear()
        
        # Restore tabs
        for i in range(count):
            settings.beginGroup(f"Tab{i}")
            tab_name = settings.value("name", f"Query {i+1}")
            sql = settings.value("sql", "")
            settings.endGroup()
            
            tab = SQLEditorTab(self.preferences, tab_name)
            tab.set_sql(sql)
            tab.query_requested.connect(lambda q: self._emit_query_requested(q))
            tab.all_queries_requested.connect(lambda qs: self._emit_all_queries_requested(qs))
            tab.modified_changed.connect(lambda m: self._update_tab_title(self.tab_widget.indexOf(tab)))
            
            self.tab_widget.addTab(tab, tab_name)
        
        self.tab_widget.setCurrentIndex(current_index)
        
        settings.endGroup()
        logger.info(f"Restored {count} tabs")
