"""
Enhanced SQL Editor widget with intelligent features and syntax highlighting.

This module provides the EnhancedSQLEditor class which offers:
- Intelligent auto-completion
- Auto-closing brackets and quotes
- Smart indentation
- Bracket matching and highlighting
- CTE (Common Table Expression) support
- Enhanced syntax highlighting
- Query execution shortcuts
- Query history integration
"""

import logging
from typing import Optional, Dict, List

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QAction, QKeySequence
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSplitter,
    QLabel, QFrame, QCheckBox, QComboBox, QToolBar, QMenu
)

from ..models import UserPreferences
from .intelligent_sql_editor import IntelligentSQLEditor

logger = logging.getLogger(__name__)


class EnhancedSQLEditor(QWidget):
    """
    Enhanced SQL Editor widget with intelligent features.
    
    Features:
    - Intelligent auto-completion for SQL keywords, tables, and columns
    - Auto-closing brackets and quotes
    - Smart indentation
    - Bracket matching and highlighting
    - Enhanced syntax highlighting with CTE support
    - Query execution (F5)
    - Query formatting
    - Find and replace
    - Multi-cursor editing
    """
    
    query_requested = pyqtSignal()
    
    def __init__(self, preferences: Optional[UserPreferences] = None):
        """
        Initialize the enhanced SQL editor.
        
        Args:
            preferences: User preferences for editor configuration
        """
        super().__init__()
        
        self.preferences = preferences or UserPreferences()
        
        # Create UI
        self.init_ui()
        self.setup_actions()
        self.apply_preferences()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        
        # Create toolbar
        self.toolbar = self.create_toolbar()
        layout.addWidget(self.toolbar)
        
        # Create the intelligent SQL editor
        self.text_edit = IntelligentSQLEditor(self.preferences)
        self.text_edit.query_requested.connect(self.query_requested.emit)
        
        layout.addWidget(self.text_edit)
        
        # Create status bar
        self.status_bar = self.create_status_bar()
        layout.addWidget(self.status_bar)
        
        self.setLayout(layout)
    
    def create_toolbar(self) -> QToolBar:
        """Create the editor toolbar."""
        toolbar = QToolBar()
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        
        # Run query button
        self.run_button = QPushButton("▶ Run Query (F5)")
        self.run_button.setToolTip("Execute the SQL query (F5)")
        self.run_button.clicked.connect(self.request_query_execution)
        toolbar.addWidget(self.run_button)
        
        toolbar.addSeparator()
        
        # Clear button
        self.clear_button = QPushButton("🗑 Clear")
        self.clear_button.setToolTip("Clear the editor")
        self.clear_button.clicked.connect(self.clear)
        toolbar.addWidget(self.clear_button)
        
        # Format button
        self.format_button = QPushButton("📐 Format")
        self.format_button.setToolTip("Format SQL (Ctrl+Shift+F)")
        self.format_button.clicked.connect(self.format_sql)
        toolbar.addWidget(self.format_button)
        
        toolbar.addSeparator()
        
        # Auto-completion toggle
        self.auto_complete_cb = QCheckBox("Auto-complete")
        self.auto_complete_cb.setChecked(True)
        self.auto_complete_cb.setToolTip("Enable/disable auto-completion (Ctrl+Space)")
        toolbar.addWidget(self.auto_complete_cb)
        
        # Smart indentation toggle
        self.smart_indent_cb = QCheckBox("Smart Indent")
        self.smart_indent_cb.setChecked(True)
        self.smart_indent_cb.setToolTip("Enable/disable smart indentation")
        toolbar.addWidget(self.smart_indent_cb)
        
        # Bracket matching toggle
        self.bracket_match_cb = QCheckBox("Bracket Match")
        self.bracket_match_cb.setChecked(True)
        self.bracket_match_cb.setToolTip("Enable/disable bracket matching")
        toolbar.addWidget(self.bracket_match_cb)
        
        toolbar.addSeparator()
        
        # CTE Analysis button
        self.cte_analysis_button = QPushButton("🔍 CTE Analysis")
        self.cte_analysis_button.setToolTip("Analyze CTE structure and get optimization suggestions")
        self.cte_analysis_button.clicked.connect(self.show_cte_analysis)
        toolbar.addWidget(self.cte_analysis_button)
        
        # CTE Help button
        self.cte_help_button = QPushButton("❓ CTE Help")
        self.cte_help_button.setToolTip("Show CTE syntax help and examples")
        self.cte_help_button.clicked.connect(self.show_cte_help)
        toolbar.addWidget(self.cte_help_button)
        
        return toolbar
    
    def create_status_bar(self) -> QFrame:
        """Create the status bar."""
        status_frame = QFrame()
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(5, 2, 5, 2)
        
        # Cursor position
        self.cursor_label = QLabel("Line: 1, Col: 1")
        status_layout.addWidget(self.cursor_label)
        
        status_layout.addStretch()
        
        # Selection info
        self.selection_label = QLabel("")
        status_layout.addWidget(self.selection_label)
        
        # Query info
        self.query_info_label = QLabel("Ready")
        status_layout.addWidget(self.query_info_label)
        
        status_frame.setLayout(status_layout)
        status_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        
        return status_frame
    
    def setup_actions(self):
        """Set up keyboard shortcuts and actions."""
        # Connect cursor position changes to status updates
        self.text_edit.cursorPositionChanged.connect(self.update_cursor_position)
        self.text_edit.selectionChanged.connect(self.update_selection_info)
    
    def apply_preferences(self):
        """Apply user preferences to the editor."""
        # The IntelligentSQLEditor handles most preferences internally
        pass
    
    def update_cursor_position(self):
        """Update cursor position in status bar."""
        cursor = self.text_edit.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.columnNumber() + 1
        self.cursor_label.setText(f"Line: {line}, Col: {col}")
    
    def update_selection_info(self):
        """Update selection information in status bar."""
        cursor = self.text_edit.textCursor()
        if cursor.hasSelection():
            selected_text = cursor.selectedText()
            char_count = len(selected_text)
            line_count = selected_text.count('\u2029') + 1  # Qt line separator
            self.selection_label.setText(f"Selected: {char_count} chars, {line_count} lines")
        else:
            self.selection_label.setText("")
    
    def request_query_execution(self):
        """Request query execution."""
        self.query_info_label.setText("Executing...")
        self.query_requested.emit()
    
    def set_query_result_info(self, info: str):
        """Set query result information in status bar."""
        self.query_info_label.setText(info)
    
    def get_sql(self) -> str:
        """Get the current SQL text."""
        return self.text_edit.get_sql()
    
    def set_sql(self, sql: str):
        """Set the SQL text."""
        self.text_edit.set_sql(sql)
    
    def insert_text(self, text: str):
        """Insert text at the current cursor position."""
        cursor = self.text_edit.textCursor()
        cursor.insertText(text)
    
    def clear(self):
        """Clear the editor."""
        self.text_edit.clear()
        self.query_info_label.setText("Ready")
    
    def format_sql(self):
        """Format the SQL text."""
        self.text_edit.format_sql()
        self.query_info_label.setText("Formatted")
    
    def undo(self):
        """Undo the last operation."""
        self.text_edit.undo()
    
    def redo(self):
        """Redo the last undone operation."""
        self.text_edit.redo()
    
    def cut(self):
        """Cut selected text."""
        self.text_edit.cut()
    
    def copy(self):
        """Copy selected text."""
        self.text_edit.copy()
    
    def paste(self):
        """Paste text from clipboard."""
        self.text_edit.paste()
    
    def select_all(self):
        """Select all text."""
        self.text_edit.selectAll()
    
    def has_selection(self) -> bool:
        """Check if there is selected text."""
        return self.text_edit.textCursor().hasSelection()
    
    def get_selected_text(self) -> str:
        """Get the selected text."""
        return self.text_edit.textCursor().selectedText()
    
    def set_font(self, font: QFont):
        """Set the editor font."""
        self.text_edit.setFont(font)
    
    def set_font_size(self, size: int):
        """Set the font size."""
        font = self.text_edit.font()
        font.setPointSize(size)
        self.text_edit.setFont(font)
    
    def zoom_in(self):
        """Increase font size."""
        current_size = self.text_edit.font().pointSize()
        self.set_font_size(min(current_size + 1, 24))
    
    def zoom_out(self):
        """Decrease font size."""
        current_size = self.text_edit.font().pointSize()
        self.set_font_size(max(current_size - 1, 8))
    
    def set_read_only(self, read_only: bool):
        """Set the editor read-only state."""
        self.text_edit.setReadOnly(read_only)
        self.run_button.setEnabled(not read_only)
        self.clear_button.setEnabled(not read_only)
        self.format_button.setEnabled(not read_only)
    
    def toggle_comment(self):
        """Toggle SQL line comments (--) for current line or selected lines."""
        self.text_edit.toggle_comment()
    
    def update_schema_info(self, tables: Dict[str, List[str]]):
        """Update table and column information for auto-completion."""
        self.text_edit.update_schema_info(tables)
        logger.info(f"Updated schema info for {len(tables)} tables")
    
    def set_theme(self, theme: str):
        """Set the editor theme (light/dark)."""
        if hasattr(self.text_edit, 'highlighter') and self.text_edit.highlighter:
            self.text_edit.highlighter.theme = theme
            self.text_edit.highlighter.setup_formats()
            self.text_edit.highlighter.rehighlight()
    
    def show_find_replace(self):
        """Show find and replace dialog."""
        # This would open a find/replace dialog
        # For now, we'll just focus on the editor
        self.text_edit.setFocus()
    
    def insert_cte_template(self):
        """Insert a CTE template at the cursor position."""
        if hasattr(self.text_edit, 'insert_cte_template'):
            self.text_edit.insert_cte_template("simple")
        else:
            # Fallback for older text_edit versions
            template = """WITH cte_name AS (
    -- Your CTE query here
    SELECT 
        column1,
        column2
    FROM table_name
    WHERE condition
)
SELECT *
FROM cte_name"""
            
            cursor = self.text_edit.textCursor()
            cursor.insertText(template)
            
            # Position cursor at the CTE name for easy editing
            cursor.movePosition(cursor.MoveOperation.StartOfBlock)
            cursor.movePosition(cursor.MoveOperation.NextWord)  # Move to "cte_name"
            cursor.select(cursor.SelectionType.WordUnderCursor)
            self.text_edit.setTextCursor(cursor)
    
    def insert_recursive_cte_template(self):
        """Insert a recursive CTE template at the cursor position."""
        if hasattr(self.text_edit, 'insert_cte_template'):
            self.text_edit.insert_cte_template("recursive")
        else:
            # Fallback for older text_edit versions
            template = """WITH RECURSIVE cte_name AS (
    -- Base case
    SELECT 
        id,
        parent_id,
        name,
        1 as level
    FROM table_name
    WHERE parent_id IS NULL
    
    UNION ALL
    
    -- Recursive case
    SELECT 
        t.id,
        t.parent_id,
        t.name,
        c.level + 1
    FROM table_name t
    INNER JOIN cte_name c ON t.parent_id = c.id
)
SELECT *
FROM cte_name
ORDER BY level, name"""
            
            cursor = self.text_edit.textCursor()
            cursor.insertText(template)
            
            # Position cursor at the CTE name for easy editing
            cursor.movePosition(cursor.MoveOperation.StartOfBlock)
            cursor.movePosition(cursor.MoveOperation.NextWord, cursor.MoveMode.MoveAnchor, 2)  # Move to "cte_name"
            cursor.select(cursor.SelectionType.WordUnderCursor)
            self.text_edit.setTextCursor(cursor)
    
    def show_cte_analysis(self):
        """Show CTE analysis results."""
        if hasattr(self.text_edit, 'analyze_cte_structure'):
            analysis_result = self.text_edit.analyze_cte_structure()
            
            # Create a simple dialog to show the analysis
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QDialogButtonBox
            
            dialog = QDialog(self)
            dialog.setWindowTitle("CTE Analysis")
            dialog.resize(600, 400)
            
            layout = QVBoxLayout()
            
            # Analysis text
            analysis_text = QTextEdit()
            analysis_text.setPlainText(analysis_result)
            analysis_text.setReadOnly(True)
            layout.addWidget(analysis_text)
            
            # Close button
            button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
            button_box.accepted.connect(dialog.accept)
            layout.addWidget(button_box)
            
            dialog.setLayout(layout)
            dialog.exec()
        else:
            self.set_query_result_info("CTE analysis not available")
    
    def show_cte_help(self):
        """Show CTE help information."""
        if hasattr(self.text_edit, 'show_cte_help'):
            help_text = self.text_edit.show_cte_help()
            
            # Create a simple dialog to show the help
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QDialogButtonBox
            
            dialog = QDialog(self)
            dialog.setWindowTitle("CTE Help")
            dialog.resize(700, 500)
            
            layout = QVBoxLayout()
            
            # Help text
            help_display = QTextEdit()
            help_display.setPlainText(help_text)
            help_display.setReadOnly(True)
            layout.addWidget(help_display)
            
            # Close button
            button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
            button_box.accepted.connect(dialog.accept)
            layout.addWidget(button_box)
            
            dialog.setLayout(layout)
            dialog.exec()
        else:
            self.set_query_result_info("CTE help not available")