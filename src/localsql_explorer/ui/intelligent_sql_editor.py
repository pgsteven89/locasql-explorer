"""
Enhanced SQL Editor with intelligent features and auto-completion.

This module provides advanced SQL editing capabilities including:
- Auto-closing brackets and quotes
- Smart indentation
- Bracket highlighting and matching
- Auto-completion for SQL keywords, tables, and columns
- Multi-cursor editing support
- Find and replace functionality
- Code formatting and prettification
"""

import logging
import re
from typing import List, Optional, Dict, Tuple, Set
from dataclasses import dataclass

from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPoint, QRect, QStringListModel
from PyQt6.QtGui import (
    QFont, QSyntaxHighlighter, QTextCharFormat, QTextDocument, QKeySequence,
    QTextCursor, QPalette, QColor, QTextBlockFormat, QPainter, QFontMetrics
)
from PyQt6.QtWidgets import (
    QPlainTextEdit, QWidget, QVBoxLayout, QPushButton, QHBoxLayout,
    QCompleter, QAbstractItemView, QTextEdit,
    QFrame, QListWidget, QListWidgetItem, QLabel, QSplitter
)

from ..models import UserPreferences
from ..cte_support import CTEParser, CTETemplateGenerator, CTEOptimizer
from .styling import setup_text_selection_colors

logger = logging.getLogger(__name__)


@dataclass
class BracketPair:
    """Represents a pair of matching brackets."""
    open_char: str
    close_char: str
    position: int
    length: int = 1


@dataclass
class AutoCompleteItem:
    """Represents an auto-completion item."""
    text: str
    type: str  # 'keyword', 'table', 'column', 'function'
    description: str = ""
    insert_text: str = ""  # What to actually insert (may differ from display text)


class EnhancedSQLSyntaxHighlighter(QSyntaxHighlighter):
    """Enhanced SQL syntax highlighter with CTE support and better highlighting."""
    
    def __init__(self, document: QTextDocument, theme: str = "light"):
        super().__init__(document)
        self.theme = theme
        self.setup_formats()
        
        # Enhanced SQL keywords including CTE support
        self.sql_keywords = {
            'SELECT', 'FROM', 'WHERE', 'JOIN', 'INNER', 'LEFT', 'RIGHT', 'FULL', 'OUTER',
            'ON', 'AS', 'GROUP', 'BY', 'ORDER', 'HAVING', 'DISTINCT', 'UNION', 'ALL',
            'INSERT', 'INTO', 'VALUES', 'UPDATE', 'SET', 'DELETE', 'CREATE', 'TABLE',
            'ALTER', 'DROP', 'INDEX', 'VIEW', 'DATABASE', 'SCHEMA', 'PRIMARY', 'KEY',
            'FOREIGN', 'REFERENCES', 'CONSTRAINT', 'NOT', 'NULL', 'DEFAULT', 'UNIQUE',
            'CHECK', 'AND', 'OR', 'IN', 'BETWEEN', 'LIKE', 'IS', 'EXISTS', 'CASE',
            'WHEN', 'THEN', 'ELSE', 'END', 'IF', 'CAST', 'CONVERT', 'COUNT', 'SUM',
            'AVG', 'MIN', 'MAX', 'LIMIT', 'OFFSET', 'ASC', 'DESC', 'NULLS', 'FIRST',
            'LAST', 'PARTITION', 'OVER', 'ROW_NUMBER', 'RANK', 'DENSE_RANK'
        }
        
        # CTE and advanced SQL keywords
        self.cte_keywords = {
            'WITH', 'RECURSIVE', 'MATERIALIZED', 'NOT MATERIALIZED'
        }
        
        # SQL functions
        self.sql_functions = {
            'COALESCE', 'ISNULL', 'NULLIF', 'SUBSTRING', 'LEN', 'LENGTH', 'TRIM',
            'LTRIM', 'RTRIM', 'UPPER', 'LOWER', 'REPLACE', 'CONCAT', 'LEFT', 'RIGHT',
            'DATEPART', 'DATEDIFF', 'GETDATE', 'NOW', 'CURRENT_TIMESTAMP', 'EXTRACT',
            'TO_DATE', 'TO_CHAR', 'PARSE_DATE', 'FORMAT', 'ROUND', 'FLOOR', 'CEIL',
            'ABS', 'POWER', 'SQRT', 'EXP', 'LOG', 'SIN', 'COS', 'TAN'
        }
        
        # All keywords combined
        self.all_keywords = self.sql_keywords | self.cte_keywords
    
    def setup_formats(self):
        """Set up text formatting styles based on theme."""
        if self.theme == "dark":
            # Dark theme colors
            keyword_color = QColor("#569CD6")  # Light blue
            cte_color = QColor("#C586C0")      # Purple
            function_color = QColor("#DCDCAA") # Yellow
            string_color = QColor("#CE9178")   # Orange
            comment_color = QColor("#6A9955")  # Green
            number_color = QColor("#B5CEA8")   # Light green
        else:
            # Light theme colors
            keyword_color = QColor("#0000FF")  # Blue
            cte_color = QColor("#800080")      # Purple
            function_color = QColor("#795E26") # Brown
            string_color = QColor("#008000")   # Green
            comment_color = QColor("#808080")  # Gray
            number_color = QColor("#098658")   # Dark green
        
        # Keyword format
        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(keyword_color)
        self.keyword_format.setFontWeight(QFont.Weight.Bold)
        
        # CTE keyword format (special highlighting)
        self.cte_format = QTextCharFormat()
        self.cte_format.setForeground(cte_color)
        self.cte_format.setFontWeight(QFont.Weight.Bold)
        
        # Function format
        self.function_format = QTextCharFormat()
        self.function_format.setForeground(function_color)
        
        # String format
        self.string_format = QTextCharFormat()
        self.string_format.setForeground(string_color)
        
        # Comment format
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(comment_color)
        self.comment_format.setFontItalic(True)
        
        # Number format
        self.number_format = QTextCharFormat()
        self.number_format.setForeground(number_color)
        
        # Bracket highlighting
        self.bracket_format = QTextCharFormat()
        self.bracket_format.setBackground(QColor("#FFFF00") if self.theme == "light" else QColor("#404040"))
    
    def highlightBlock(self, text: str):
        """Highlight a block of text."""
        # Highlight keywords
        for keyword in self.sql_keywords:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            for match in re.finditer(pattern, text, re.IGNORECASE):
                self.setFormat(match.start(), match.end() - match.start(), self.keyword_format)
        
        # Highlight CTE keywords with special formatting
        for keyword in self.cte_keywords:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            for match in re.finditer(pattern, text, re.IGNORECASE):
                self.setFormat(match.start(), match.end() - match.start(), self.cte_format)
        
        # Highlight functions
        for function in self.sql_functions:
            pattern = r'\b' + re.escape(function) + r'\s*\('
            for match in re.finditer(pattern, text, re.IGNORECASE):
                self.setFormat(match.start(), len(function), self.function_format)
        
        # Highlight strings
        string_patterns = [
            r"'([^'\\]|\\.)*'",  # Single quotes
            r'"([^"\\]|\\.)*"',  # Double quotes
        ]
        for pattern in string_patterns:
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), self.string_format)
        
        # Highlight comments
        comment_patterns = [
            r'--.*$',  # Single line comments
            r'/\*.*?\*/',  # Multi-line comments (single line)
        ]
        for pattern in comment_patterns:
            for match in re.finditer(pattern, text, re.MULTILINE):
                self.setFormat(match.start(), match.end() - match.start(), self.comment_format)
        
        # Highlight numbers
        number_pattern = r'\b\d+\.?\d*\b'
        for match in re.finditer(number_pattern, text):
            self.setFormat(match.start(), match.end() - match.start(), self.number_format)


class SQLAutoCompleter:
    """Auto-completion engine for SQL editor."""
    
    def __init__(self):
        self.sql_keywords = [
            'SELECT', 'FROM', 'WHERE', 'JOIN', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN',
            'FULL OUTER JOIN', 'ON', 'AS', 'GROUP BY', 'ORDER BY', 'HAVING', 'DISTINCT',
            'UNION', 'UNION ALL', 'INSERT INTO', 'VALUES', 'UPDATE', 'SET', 'DELETE FROM',
            'CREATE TABLE', 'ALTER TABLE', 'DROP TABLE', 'WITH', 'RECURSIVE',
            'CASE WHEN', 'THEN', 'ELSE', 'END', 'COUNT(*)', 'COUNT(DISTINCT',
            'SUM(', 'AVG(', 'MIN(', 'MAX(', 'LIMIT', 'OFFSET'
        ]
        
        # CTE-specific keywords and patterns
        self.cte_keywords = [
            'WITH', 'WITH RECURSIVE', 'MATERIALIZED', 'NOT MATERIALIZED',
            'AS (', 'UNION ALL', 'UNION', 'RECURSIVE'
        ]
        
        # CTE templates for auto-completion
        self.cte_templates = [
            'WITH cte_name AS (\n    SELECT column1, column2\n    FROM table_name\n)\nSELECT * FROM cte_name',
            'WITH RECURSIVE cte_name AS (\n    -- Base case\n    SELECT ...\n    UNION ALL\n    -- Recursive case\n    SELECT ...\n)\nSELECT * FROM cte_name',
            'WITH MATERIALIZED cte_name AS (\n    SELECT ...\n)\nSELECT * FROM cte_name'
        ]
        
        self.sql_functions = [
            'COALESCE(', 'ISNULL(', 'NULLIF(', 'SUBSTRING(', 'LENGTH(', 'TRIM(',
            'UPPER(', 'LOWER(', 'REPLACE(', 'CONCAT(', 'CURRENT_TIMESTAMP',
            'EXTRACT(', 'DATE(', 'ROUND(', 'FLOOR(', 'CEIL(', 'ABS('
        ]
        
        self.table_names: Set[str] = set()
        self.column_names: Dict[str, Set[str]] = {}  # table -> columns
        self.cte_names: Set[str] = set()  # Currently defined CTEs
    
    def update_schema_info(self, tables: Dict[str, List[str]]):
        """Update table and column information for auto-completion."""
        self.table_names = set(tables.keys())
        self.column_names = {table: set(columns) for table, columns in tables.items()}
    
    def get_completions(self, text: str, cursor_position: int) -> List[AutoCompleteItem]:
        """Get auto-completion suggestions for the given text and cursor position."""
        completions = []
        
        # Update CTE names from current text
        self._update_cte_names(text)
        
        # Get word at cursor
        word_start = cursor_position
        while word_start > 0 and text[word_start - 1].isalnum() or text[word_start - 1] == '_':
            word_start -= 1
        
        current_word = text[word_start:cursor_position].upper()
        
        if not current_word:
            return completions
        
        # Check if we're in a CTE context
        in_cte_context = self._is_in_cte_context(text, cursor_position)
        
        # Add CTE-specific completions
        if in_cte_context:
            for keyword in self.cte_keywords:
                if keyword.upper().startswith(current_word):
                    completions.append(AutoCompleteItem(
                        text=keyword,
                        type='cte_keyword',
                        description='CTE keyword',
                        insert_text=keyword
                    ))
            
            # Add CTE templates if typing "WITH"
            if current_word.startswith('WITH'):
                for i, template in enumerate(self.cte_templates):
                    completions.append(AutoCompleteItem(
                        text=f"CTE Template {i+1}",
                        type='cte_template',
                        description='CTE template',
                        insert_text=template
                    ))
        
        # Add matching keywords
        for keyword in self.sql_keywords:
            if keyword.startswith(current_word):
                completions.append(AutoCompleteItem(
                    text=keyword,
                    type='keyword',
                    description='SQL keyword',
                    insert_text=keyword
                ))
        
        # Add matching functions
        for function in self.sql_functions:
            if function.upper().startswith(current_word):
                completions.append(AutoCompleteItem(
                    text=function,
                    type='function',
                    description='SQL function',
                    insert_text=function
                ))
        
        # Add matching table names
        for table in self.table_names:
            if table.upper().startswith(current_word):
                completions.append(AutoCompleteItem(
                    text=table,
                    type='table',
                    description='Table name',
                    insert_text=table
                ))
        
        # Add matching CTE names
        for cte_name in self.cte_names:
            if cte_name.upper().startswith(current_word):
                completions.append(AutoCompleteItem(
                    text=cte_name,
                    type='cte',
                    description='CTE name',
                    insert_text=cte_name
                ))
        
        # Add matching column names
        for table, columns in self.column_names.items():
            for column in columns:
                if column.upper().startswith(current_word):
                    completions.append(AutoCompleteItem(
                        text=column,
                        type='column',
                        description=f'Column from {table}',
                        insert_text=column
                    ))
        
        return sorted(completions, key=lambda x: (x.type, x.text))
    
    def _update_cte_names(self, text: str):
        """Update CTE names from the current SQL text."""
        try:
            # Simple CTE name extraction - look for WITH ... AS pattern
            cte_pattern = re.compile(r'WITH\s+(?:RECURSIVE\s+)?(?:MATERIALIZED\s+|NOT\s+MATERIALIZED\s+)?(\w+)\s+(?:\([^)]+\))?\s+AS\s*\(', re.IGNORECASE)
            matches = cte_pattern.findall(text)
            self.cte_names = set(matches)
        except Exception:
            # If parsing fails, clear CTE names
            self.cte_names = set()
    
    def _is_in_cte_context(self, text: str, cursor_position: int) -> bool:
        """Check if the cursor is within a CTE context."""
        # Look backwards from cursor to see if we're after a WITH keyword
        text_before_cursor = text[:cursor_position].upper()
        
        # Simple check - if there's a WITH before the cursor and no SELECT after the last WITH
        last_with = text_before_cursor.rfind('WITH')
        if last_with == -1:
            return False
        
        text_after_with = text_before_cursor[last_with:]
        # If there's no main SELECT after WITH, we're likely in CTE context
        return 'SELECT' not in text_after_with or text_after_with.count('(') > text_after_with.count(')')


class IntelligentSQLEditor(QPlainTextEdit):
    """
    Enhanced SQL editor with intelligent features.
    
    Features:
    - Auto-closing brackets and quotes
    - Smart indentation
    - Bracket highlighting
    - Auto-completion
    - Multi-cursor support
    - Find and replace
    """
    
    query_requested = pyqtSignal()
    
    # Auto-closing pairs
    AUTO_CLOSE_PAIRS = {
        '(': ')',
        '[': ']',
        '{': '}',
        "'": "'",
        '"': '"'
    }
    
    def __init__(self, preferences: Optional[UserPreferences] = None, parent=None):
        super().__init__(parent)
        
        self.preferences = preferences or UserPreferences()
        self.highlighter: Optional[EnhancedSQLSyntaxHighlighter] = None
        self.auto_completer = SQLAutoCompleter()
        self.completion_popup: Optional[QListWidget] = None
        
        # CTE support
        self.cte_parser = CTEParser()
        self.cte_optimizer = CTEOptimizer()
        self.cte_templates = CTETemplateGenerator()
        
        # Bracket matching
        self.bracket_positions: List[BracketPair] = []
        self.highlight_timer = QTimer()
        self.highlight_timer.setSingleShot(True)
        self.highlight_timer.timeout.connect(self.highlight_matching_brackets)
        
        self.setup_editor()
        self.setup_signals()
    
    def setup_editor(self):
        """Set up the editor with enhanced features."""
        # Basic settings
        self.setPlaceholderText("Enter SQL query here...\nPress Ctrl+Space for auto-completion\nPress F5 to run query")
        
        # Font settings
        font = QFont(self.preferences.font_family, self.preferences.font_size)
        font.setFamily("Consolas")  # Use monospace font
        self.setFont(font)
        
        # Tab settings
        tab_width = 4
        metrics = QFontMetrics(font)
        self.setTabStopDistance(tab_width * metrics.horizontalAdvance(' '))
        
        # Line numbers and other visual enhancements
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        
        # Configure selection colors to ensure visibility
        self.setup_selection_colors()
        
        # Syntax highlighting
        if self.preferences.syntax_highlight:
            theme = "dark" if getattr(self.preferences, 'dark_theme', False) else "light"
            self.highlighter = EnhancedSQLSyntaxHighlighter(self.document(), theme)
    
    def setup_signals(self):
        """Set up signal connections."""
        self.cursorPositionChanged.connect(self.on_cursor_position_changed)
        self.textChanged.connect(self.on_text_changed)
    
    def setup_selection_colors(self):
        """Configure proper selection colors to ensure text visibility."""
        is_dark_theme = getattr(self.preferences, 'dark_theme', False)
        setup_text_selection_colors(self, is_dark_theme)
    
    def keyPressEvent(self, event):
        """Handle key press events for intelligent features."""
        key = event.key()
        text = event.text()
        modifiers = event.modifiers()
        
        # Handle F5 for query execution
        if key == Qt.Key.Key_F5:
            self.query_requested.emit()
            return
        
        # Handle Ctrl+/ for toggle comment
        if key == Qt.Key.Key_Slash and modifiers == Qt.KeyboardModifier.ControlModifier:
            self.toggle_comment()
            return
        
        # Handle Ctrl+Space for auto-completion
        if key == Qt.Key.Key_Space and modifiers == Qt.KeyboardModifier.ControlModifier:
            self.show_auto_completion()
            return
        
        # Handle auto-closing brackets and quotes
        if text in self.AUTO_CLOSE_PAIRS:
            self.handle_auto_closing(text)
            return
        
        # Handle closing bracket - check if we should skip it
        if text in self.AUTO_CLOSE_PAIRS.values():
            if self.should_skip_closing_char(text):
                cursor = self.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.NextCharacter)
                self.setTextCursor(cursor)
                return
        
        # Handle Enter for smart indentation
        if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            self.handle_smart_indent()
            return
        
        # Handle Tab for indentation
        if key == Qt.Key.Key_Tab:
            if self.textCursor().hasSelection():
                self.indent_selection()
            else:
                self.insert_tab()
            return
        
        # Handle Shift+Tab for unindent
        if key == Qt.Key.Key_Backtab:
            self.unindent_selection()
            return
        
        # Handle backspace for smart deletion
        if key == Qt.Key.Key_Backspace:
            if self.handle_smart_backspace():
                return
        
        # Default handling
        super().keyPressEvent(event)
        
        # Hide completion popup on certain keys
        if self.completion_popup and self.completion_popup.isVisible():
            if key in [Qt.Key.Key_Escape, Qt.Key.Key_Return, Qt.Key.Key_Tab]:
                self.completion_popup.hide()
    
    def handle_auto_closing(self, opening_char: str):
        """Handle auto-closing of brackets and quotes."""
        cursor = self.textCursor()
        closing_char = self.AUTO_CLOSE_PAIRS[opening_char]
        
        # Check if we're inside a string or comment
        if self.is_inside_string_or_comment(cursor.position()):
            self.insertPlainText(opening_char)
            return
        
        # Insert both opening and closing characters
        cursor.insertText(opening_char + closing_char)
        
        # Move cursor back to between the characters
        cursor.movePosition(QTextCursor.MoveOperation.PreviousCharacter)
        self.setTextCursor(cursor)
    
    def should_skip_closing_char(self, closing_char: str) -> bool:
        """Check if we should skip inserting a closing character."""
        cursor = self.textCursor()
        position = cursor.position()
        text = self.toPlainText()
        
        # Check if the next character is the same closing character
        if position < len(text) and text[position] == closing_char:
            return True
        
        return False
    
    def handle_smart_indent(self):
        """Handle smart indentation on Enter."""
        cursor = self.textCursor()
        
        # Get current line and its indentation
        current_block = cursor.block()
        current_text = current_block.text()
        indent = self.get_line_indentation(current_text)
        
        # Check if we need extra indentation
        extra_indent = ""
        stripped_text = current_text.strip().upper()
        
        # Add extra indentation after certain keywords
        if any(stripped_text.endswith(keyword) for keyword in [
            'SELECT', 'FROM', 'WHERE', 'JOIN', 'ON', 'GROUP BY', 'ORDER BY',
            'HAVING', 'WITH', 'CASE', 'WHEN', '(', 'BEGIN'
        ]):
            extra_indent = "    "  # 4 spaces
        
        # Insert newline and indentation
        cursor.insertText("\n" + indent + extra_indent)
        self.setTextCursor(cursor)
    
    def get_line_indentation(self, line: str) -> str:
        """Get the indentation (whitespace) at the beginning of a line."""
        indent = ""
        for char in line:
            if char in [' ', '\t']:
                indent += char
            else:
                break
        return indent
    
    def indent_selection(self):
        """Indent the selected lines."""
        cursor = self.textCursor()
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        
        # Select full lines
        cursor.setPosition(start)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        start_pos = cursor.position()
        
        cursor.setPosition(end)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
        end_pos = cursor.position()
        
        cursor.setPosition(start_pos)
        cursor.setPosition(end_pos, QTextCursor.MoveMode.KeepAnchor)
        
        # Get selected text and indent each line
        selected_text = cursor.selectedText()
        lines = selected_text.split('\u2029')  # Qt uses this for line breaks
        indented_lines = ['    ' + line for line in lines]
        
        cursor.insertText('\n'.join(indented_lines))
    
    def unindent_selection(self):
        """Unindent the selected lines."""
        cursor = self.textCursor()
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        
        # Select full lines
        cursor.setPosition(start)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        start_pos = cursor.position()
        
        cursor.setPosition(end)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
        end_pos = cursor.position()
        
        cursor.setPosition(start_pos)
        cursor.setPosition(end_pos, QTextCursor.MoveMode.KeepAnchor)
        
        # Get selected text and unindent each line
        selected_text = cursor.selectedText()
        lines = selected_text.split('\u2029')
        unindented_lines = []
        
        for line in lines:
            if line.startswith('    '):
                unindented_lines.append(line[4:])
            elif line.startswith('\t'):
                unindented_lines.append(line[1:])
            else:
                unindented_lines.append(line)
        
        cursor.insertText('\n'.join(unindented_lines))
    
    def insert_tab(self):
        """Insert a tab (4 spaces)."""
        self.insertPlainText("    ")
    
    def handle_smart_backspace(self) -> bool:
        """Handle smart backspace for auto-closing pairs."""
        cursor = self.textCursor()
        position = cursor.position()
        text = self.toPlainText()
        
        if position == 0:
            return False
        
        # Check if we're deleting an opening character with its closing pair
        prev_char = text[position - 1]
        if prev_char in self.AUTO_CLOSE_PAIRS:
            closing_char = self.AUTO_CLOSE_PAIRS[prev_char]
            if position < len(text) and text[position] == closing_char:
                # Delete both characters
                cursor.deletePreviousChar()
                cursor.deleteChar()
                return True
        
        return False
    
    def is_inside_string_or_comment(self, position: int) -> bool:
        """Check if the position is inside a string or comment."""
        # This is a simplified implementation
        # In a full implementation, you'd parse the syntax more carefully
        text = self.toPlainText()[:position]
        
        # Count quotes to see if we're inside a string
        single_quotes = text.count("'") - text.count("\\'")
        double_quotes = text.count('"') - text.count('\\"')
        
        # Check if inside comment
        last_line = text.split('\n')[-1]
        if '--' in last_line:
            return True
        
        return (single_quotes % 2 == 1) or (double_quotes % 2 == 1)
    
    def show_auto_completion(self):
        """Show auto-completion popup."""
        cursor = self.textCursor()
        position = cursor.position()
        text = self.toPlainText()
        
        completions = self.auto_completer.get_completions(text, position)
        
        if not completions:
            return
        
        # Create or update completion popup
        if not self.completion_popup:
            self.completion_popup = QListWidget()
            self.completion_popup.setWindowFlags(Qt.WindowType.Popup)
            self.completion_popup.itemClicked.connect(self.insert_completion)
        
        # Clear and populate
        self.completion_popup.clear()
        for completion in completions[:20]:  # Limit to 20 items
            item = QListWidgetItem()
            item.setText(f"{completion.text} ({completion.type})")
            item.setData(Qt.ItemDataRole.UserRole, completion)
            self.completion_popup.addItem(item)
        
        # Position popup
        rect = self.cursorRect()
        point = self.mapToGlobal(rect.bottomLeft())
        self.completion_popup.move(point)
        self.completion_popup.resize(300, min(200, len(completions) * 25))
        self.completion_popup.show()
    
    def insert_completion(self, item: QListWidgetItem):
        """Insert the selected completion."""
        completion = item.data(Qt.ItemDataRole.UserRole)
        if completion:
            cursor = self.textCursor()
            
            # Find the start of the current word
            position = cursor.position()
            text = self.toPlainText()
            word_start = position
            while word_start > 0 and (text[word_start - 1].isalnum() or text[word_start - 1] == '_'):
                word_start -= 1
            
            # Replace the partial word with the completion
            cursor.setPosition(word_start)
            cursor.setPosition(position, QTextCursor.MoveMode.KeepAnchor)
            cursor.insertText(completion.insert_text)
        
        self.completion_popup.hide()
    
    def on_cursor_position_changed(self):
        """Handle cursor position changes for bracket highlighting."""
        self.highlight_timer.start(100)  # Delay to avoid too frequent updates
    
    def on_text_changed(self):
        """Handle text changes."""
        # Update bracket positions
        self.update_bracket_positions()
    
    def update_bracket_positions(self):
        """Update the positions of all brackets in the text."""
        text = self.toPlainText()
        self.bracket_positions.clear()
        
        bracket_chars = "()[]{}"
        for i, char in enumerate(text):
            if char in bracket_chars:
                self.bracket_positions.append(BracketPair(
                    open_char=char,
                    close_char="",
                    position=i
                ))
    
    def highlight_matching_brackets(self):
        """Highlight matching brackets around the cursor."""
        cursor = self.textCursor()
        position = cursor.position()
        text = self.toPlainText()
        
        # Find bracket at or near cursor
        bracket_pos = None
        bracket_char = None
        
        # Check character at cursor
        if position < len(text) and text[position] in "()[]{}'\"":
            bracket_pos = position
            bracket_char = text[position]
        # Check character before cursor
        elif position > 0 and text[position - 1] in "()[]{}'\"":
            bracket_pos = position - 1
            bracket_char = text[position - 1]
        
        if bracket_pos is not None and bracket_char in "()[]{}":
            matching_pos = self.find_matching_bracket(text, bracket_pos, bracket_char)
            if matching_pos is not None:
                self.highlight_bracket_pair(bracket_pos, matching_pos)
    
    def find_matching_bracket(self, text: str, pos: int, bracket: str) -> Optional[int]:
        """Find the matching bracket for the given position."""
        pairs = {'(': ')', '[': ']', '{': '}', ')': '(', ']': '[', '}': '{'}
        
        if bracket not in pairs:
            return None
        
        target = pairs[bracket]
        direction = 1 if bracket in "([{" else -1
        start = pos + direction
        count = 1
        
        for i in range(start, len(text) if direction > 0 else -1, direction):
            if i < 0:
                break
            char = text[i]
            if char == bracket:
                count += 1
            elif char == target:
                count -= 1
                if count == 0:
                    return i
        
        return None
    
    def highlight_bracket_pair(self, pos1: int, pos2: int):
        """Highlight a pair of matching brackets."""
        # This would typically use extra selections to highlight the brackets
        # For now, we'll just log the positions
        logger.debug(f"Highlighting brackets at positions {pos1} and {pos2}")
    
    def update_schema_info(self, tables: Dict[str, List[str]]):
        """Update table and column information for auto-completion."""
        self.auto_completer.update_schema_info(tables)
    
    def get_sql(self) -> str:
        """Get the SQL text from the editor."""
        return self.toPlainText()
    
    def set_sql(self, sql: str):
        """Set SQL text in the editor."""
        self.setPlainText(sql)
    
    def clear(self):
        """Clear the editor."""
        self.setPlainText("")
    
    def format_sql(self):
        """Format the SQL text (basic formatting)."""
        sql = self.get_sql()
        formatted = self.basic_sql_format(sql)
        self.set_sql(formatted)
    
    def toggle_comment(self):
        """
        Toggle SQL line comments (--) for the current line or selected lines.
        
        If lines are commented, uncomment them.
        If lines are not commented, comment them.
        Works with Ctrl+/ shortcut like VS Code.
        """
        cursor = self.textCursor()
        
        # Get selection boundaries
        start_pos = cursor.selectionStart()
        end_pos = cursor.selectionEnd()
        has_selection = start_pos != end_pos
        
        # Get the document
        doc = self.document()
        
        # Find start and end blocks
        start_block = doc.findBlock(start_pos)
        end_block = doc.findBlock(end_pos)
        
        # If no selection or end is at start of block, don't include that block
        if end_pos == end_block.position() and end_block.blockNumber() > start_block.blockNumber():
            end_block = end_block.previous()
        
        # Collect all blocks to process
        blocks = []
        current_block = start_block
        while current_block.isValid() and current_block.blockNumber() <= end_block.blockNumber():
            blocks.append(current_block)
            current_block = current_block.next()
        
        if not blocks:
            return
        
        # Determine if we should comment or uncomment
        # Check if all non-empty lines are already commented
        non_empty_blocks = [b for b in blocks if b.text().strip()]
        if not non_empty_blocks:
            return  # Nothing to do
        
        all_commented = all(b.text().lstrip().startswith('--') for b in non_empty_blocks)
        
        # Begin edit block for undo/redo
        cursor.beginEditBlock()
        
        # Process each block
        for block in blocks:
            line_text = block.text()
            
            # Create a cursor for this block - select only the text, not the newline
            block_cursor = QTextCursor(block)
            block_cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            block_cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
            
            if all_commented:
                # Uncomment: remove "-- " or "--" from start
                stripped = line_text.lstrip()
                if stripped.startswith('-- '):
                    # Remove "-- " (with space)
                    leading_spaces = len(line_text) - len(stripped)
                    new_line = line_text[:leading_spaces] + stripped[3:]
                    block_cursor.insertText(new_line)
                elif stripped.startswith('--'):
                    # Remove "--" (without space)
                    leading_spaces = len(line_text) - len(stripped)
                    new_line = line_text[:leading_spaces] + stripped[2:]
                    block_cursor.insertText(new_line)
            else:
                # Comment: add "-- " at the start (preserving indentation)
                if line_text.strip():  # Only comment non-empty lines
                    stripped = line_text.lstrip()
                    leading_spaces = len(line_text) - len(stripped)
                    new_line = line_text[:leading_spaces] + '-- ' + stripped
                    block_cursor.insertText(new_line)
        
        cursor.endEditBlock()
        
        # Restore selection
        # Recalculate positions since text length changed
        new_start_block = doc.findBlockByNumber(start_block.blockNumber())
        new_end_block = doc.findBlockByNumber(end_block.blockNumber())
        
        new_cursor = QTextCursor(doc)
        new_cursor.setPosition(new_start_block.position())
        
        if has_selection:
            # Select from start of first block to end of last block
            new_cursor.setPosition(new_end_block.position() + new_end_block.length() - 1, QTextCursor.MoveMode.KeepAnchor)
        
        self.setTextCursor(new_cursor)
    
    def basic_sql_format(self, sql: str) -> str:
        """Basic SQL formatting."""
        # This is a simple formatter - in production you might use sqlparse or similar
        lines = sql.split('\n')
        formatted_lines = []
        indent_level = 0
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                formatted_lines.append('')
                continue
            
            # Decrease indent for certain keywords
            if any(stripped.upper().startswith(kw) for kw in ['END', ')', 'ELSE']):
                indent_level = max(0, indent_level - 1)
            
            # Add indented line
            formatted_lines.append('    ' * indent_level + stripped)
            
            # Increase indent for certain keywords
            if any(stripped.upper().endswith(kw) for kw in ['SELECT', 'FROM', 'WHERE', 'WITH', 'CASE', '(']):
                indent_level += 1
        
        return '\n'.join(formatted_lines)
    
    def insert_cte_template(self, template_type: str = "simple"):
        """Insert a CTE template at the cursor position."""
        cursor = self.textCursor()
        
        if template_type == "simple":
            template = self.cte_templates.get_simple_cte_template()
        elif template_type == "recursive":
            template = self.cte_templates.get_recursive_cte_template()
        elif template_type == "materialized":
            template = self.cte_templates.get_materialized_cte_template()
        elif template_type == "multiple":
            template = self.cte_templates.get_multiple_cte_template()
        elif template_type == "time_series":
            template = self.cte_templates.get_time_series_cte_template()
        else:
            template = self.cte_templates.get_simple_cte_template()
        
        cursor.insertText(template)
        
        # Position cursor at the first CTE name for easy editing
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        # Look for the first CTE name pattern
        text = template
        first_cte_match = re.search(r'WITH\s+(?:RECURSIVE\s+)?(?:MATERIALIZED\s+|NOT\s+MATERIALIZED\s+)?(\w+)', text, re.IGNORECASE)
        if first_cte_match:
            # Move to and select the CTE name
            start_pos = cursor.position()
            text_before = text[:first_cte_match.start(1)]
            cursor.setPosition(start_pos + len(text_before))
            cursor.setPosition(start_pos + len(text_before) + len(first_cte_match.group(1)), 
                             QTextCursor.MoveMode.KeepAnchor)
            self.setTextCursor(cursor)
    
    def analyze_cte_structure(self) -> str:
        """Analyze the current SQL for CTE structure and return suggestions."""
        sql = self.get_sql()
        if not sql.strip():
            return "No SQL to analyze"
        
        try:
            analysis = self.cte_optimizer.analyze_query(sql)
            
            if not analysis.ctes:
                return "No CTEs found in the current query"
            
            suggestions = []
            suggestions.append(f"Found {len(analysis.ctes)} CTE(s)")
            
            if analysis.has_recursive:
                suggestions.append("Contains recursive CTE(s)")
            
            suggestions.append(f"Complexity score: {analysis.complexity_score}")
            
            if analysis.optimization_suggestions:
                suggestions.append("Optimization suggestions:")
                suggestions.extend(f"  • {suggestion}" for suggestion in analysis.optimization_suggestions)
            
            # Add materialization suggestions
            materialization_suggestions = self.cte_optimizer.suggest_materialization(analysis)
            if materialization_suggestions:
                suggestions.append("Materialization suggestions:")
                suggestions.extend(f"  • {suggestion}" for suggestion in materialization_suggestions)
            
            return "\n".join(suggestions)
            
        except Exception as e:
            return f"Error analyzing CTE structure: {str(e)}"
    
    def show_cte_help(self) -> str:
        """Return CTE help information."""
        help_text = """
CTE (Common Table Expression) Help:

Basic CTE Syntax:
  WITH cte_name AS (
      SELECT columns FROM table
  )
  SELECT * FROM cte_name

Recursive CTE:
  WITH RECURSIVE cte_name AS (
      -- Base case (anchor)
      SELECT ... 
      UNION ALL
      -- Recursive case
      SELECT ... FROM cte_name
  )
  SELECT * FROM cte_name

Materialized CTE:
  WITH MATERIALIZED cte_name AS (
      SELECT expensive_calculation()
  )
  SELECT * FROM cte_name

Multiple CTEs:
  WITH cte1 AS (...),
       cte2 AS (...)
  SELECT * FROM cte1 JOIN cte2

Keyboard Shortcuts:
  • Ctrl+Shift+C: Insert CTE template
  • Ctrl+Shift+R: Insert recursive CTE template
  • Ctrl+Space: Auto-completion with CTE support

Tips:
  • Use CTEs for complex queries to improve readability
  • Materialize CTEs that are referenced multiple times
  • Be careful with recursive CTEs to avoid infinite loops
  • Use column lists in CTE definitions for clarity
        """
        return help_text.strip()