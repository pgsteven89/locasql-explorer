"""
SQL Editor widget with syntax highlighting and query execution.

This module provides the SQLEditor class which offers:
- Syntax highlighting for SQL
- Query execution shortcuts
- Auto-completion (future)
- Query history integration
"""

import logging
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat, QTextDocument
from PyQt6.QtWidgets import QPlainTextEdit, QWidget, QVBoxLayout, QPushButton, QHBoxLayout

from ..models import UserPreferences

logger = logging.getLogger(__name__)


class SQLSyntaxHighlighter(QSyntaxHighlighter):
    """SQL syntax highlighter for the text editor."""
    
    def __init__(self, document: QTextDocument):
        super().__init__(document)
        
        # Define SQL keywords
        self.sql_keywords = [
            'SELECT', 'FROM', 'WHERE', 'JOIN', 'INNER', 'LEFT', 'RIGHT', 'FULL', 'OUTER',
            'ON', 'AS', 'GROUP', 'BY', 'ORDER', 'HAVING', 'DISTINCT', 'UNION', 'ALL',
            'INSERT', 'INTO', 'VALUES', 'UPDATE', 'SET', 'DELETE', 'CREATE', 'TABLE',
            'ALTER', 'DROP', 'INDEX', 'VIEW', 'DATABASE', 'SCHEMA', 'PRIMARY', 'KEY',
            'FOREIGN', 'REFERENCES', 'CONSTRAINT', 'NOT', 'NULL', 'DEFAULT', 'UNIQUE',
            'CHECK', 'AND', 'OR', 'IN', 'BETWEEN', 'LIKE', 'IS', 'EXISTS', 'CASE',
            'WHEN', 'THEN', 'ELSE', 'END', 'IF', 'CAST', 'CONVERT', 'COUNT', 'SUM',
            'AVG', 'MIN', 'MAX', 'LIMIT', 'OFFSET', 'WITH', 'RECURSIVE'
        ]
        
        # Define formatting styles
        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(Qt.GlobalColor.blue)
        self.keyword_format.setFontWeight(QFont.Weight.Bold)
        
        self.string_format = QTextCharFormat()
        self.string_format.setForeground(Qt.GlobalColor.darkGreen)
        
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(Qt.GlobalColor.gray)
        self.comment_format.setFontItalic(True)
        
        self.number_format = QTextCharFormat()
        self.number_format.setForeground(Qt.GlobalColor.darkMagenta)
    
    def highlightBlock(self, text: str):
        """Highlight a block of text."""
        # Highlight SQL keywords
        for keyword in self.sql_keywords:
            import re
            pattern = r'\b' + keyword + r'\b'
            for match in re.finditer(pattern, text, re.IGNORECASE):
                self.setFormat(match.start(), match.end() - match.start(), self.keyword_format)
        
        # Highlight strings
        import re
        string_pattern = r"'[^']*'"
        for match in re.finditer(string_pattern, text):
            self.setFormat(match.start(), match.end() - match.start(), self.string_format)
        
        # Highlight comments
        comment_pattern = r'--.*$'
        for match in re.finditer(comment_pattern, text, re.MULTILINE):
            self.setFormat(match.start(), match.end() - match.start(), self.comment_format)
        
        # Highlight numbers
        number_pattern = r'\b\d+\.?\d*\b'
        for match in re.finditer(number_pattern, text):
            self.setFormat(match.start(), match.end() - match.start(), self.number_format)


class SQLEditor(QWidget):
    """
    SQL Editor widget with syntax highlighting and execution controls.
    
    Features:
    - Syntax highlighting for SQL
    - Query execution via F5 or button
    - Configurable font and appearance
    - Text editing operations (undo, redo, cut, copy, paste)
    """
    
    # Signals
    query_requested = pyqtSignal()  # Emitted when user wants to execute query
    
    def __init__(self, preferences: Optional[UserPreferences] = None):
        """
        Initialize the SQL editor.
        
        Args:
            preferences: User preferences for editor configuration
        """
        super().__init__()
        
        self.preferences = preferences or UserPreferences()
        
        # Create UI
        self.init_ui()
        self.apply_preferences()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        
        # Create toolbar
        toolbar_layout = QHBoxLayout()
        
        self.run_button = QPushButton("Run Query (F5)")
        self.run_button.clicked.connect(self.request_query_execution)
        toolbar_layout.addWidget(self.run_button)
        
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear)
        toolbar_layout.addWidget(self.clear_button)
        
        toolbar_layout.addStretch()  # Push buttons to the left
        
        layout.addLayout(toolbar_layout)
        
        # Create text editor
        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText("Enter SQL query here...")
        
        # Set up syntax highlighting
        if self.preferences.syntax_highlight:
            self.highlighter = SQLSyntaxHighlighter(self.text_edit.document())
        else:
            self.highlighter = None
        
        layout.addWidget(self.text_edit)
        
        self.setLayout(layout)
        
        # Connect signals
        self.text_edit.keyPressEvent = self.key_press_event
    
    def apply_preferences(self):
        """Apply user preferences to the editor."""
        # Font settings
        font = QFont(self.preferences.font_family, self.preferences.font_size)
        self.text_edit.setFont(font)
        
        # Line numbers
        if self.preferences.line_numbers:
            # Note: QPlainTextEdit doesn't have built-in line numbers
            # This would require a custom implementation or QsciScintilla
            pass
        
        # Word wrap
        if self.preferences.word_wrap:
            self.text_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        else:
            self.text_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
    
    def key_press_event(self, event):
        """Handle key press events."""
        # Check for F5 (execute query)
        if event.key() == Qt.Key.Key_F5:
            self.request_query_execution()
            return
        
        # Let the base class handle other keys
        QPlainTextEdit.keyPressEvent(self.text_edit, event)
    
    def request_query_execution(self):
        """Request query execution."""
        self.query_requested.emit()
    
    def get_sql(self) -> str:
        """Get the current SQL text."""
        return self.text_edit.toPlainText()
    
    def set_sql(self, sql: str):
        """Set the SQL text."""
        self.text_edit.setPlainText(sql)
    
    def insert_text(self, text: str):
        """Insert text at the current cursor position."""
        cursor = self.text_edit.textCursor()
        cursor.insertText(text)
    
    def clear(self):
        """Clear the editor."""
        self.text_edit.clear()
    
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