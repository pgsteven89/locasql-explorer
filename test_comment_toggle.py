"""
Test script for comment toggle functionality.
"""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt
from src.localsql_explorer.ui.intelligent_sql_editor import IntelligentSQLEditor
from src.localsql_explorer.models import UserPreferences
from src.localsql_explorer.query_parser import get_query_parser

def main():
    """Test the comment toggle functionality."""
    app = QApplication(sys.argv)
    
    # Create main window
    window = QMainWindow()
    window.setWindowTitle("Comment Toggle Test - Press Ctrl+/")
    window.resize(800, 600)
    
    # Create central widget
    central_widget = QWidget()
    window.setCentralWidget(central_widget)
    
    layout = QVBoxLayout()
    central_widget.setLayout(layout)
    
    # Create editor
    preferences = UserPreferences()
    editor = IntelligentSQLEditor(preferences)
    
    # Add some test SQL
    test_sql = """SELECT * FROM users WHERE status = 'active';
SELECT id, name FROM customers;
SELECT COUNT(*) as total FROM orders;
-- This line is already commented
SELECT * FROM products;"""
    
    editor.setPlainText(test_sql)
    
    layout.addWidget(editor)
    
    # Add buttons for testing
    button_layout = QHBoxLayout()
    
    def test_comment():
        """Test commenting functionality."""
        cursor = editor.textCursor()
        print(f"\nCurrent cursor position: {cursor.position()}")
        print(f"Has selection: {cursor.hasSelection()}")
        if cursor.hasSelection():
            print(f"Selection: {cursor.selectionStart()} to {cursor.selectionEnd()}")
        
        editor.toggle_comment()
        
        print("After toggle:")
        print(editor.toPlainText())
        print("-" * 80)
    
    def test_parse_queries():
        """Test query parsing with comments."""
        parser = get_query_parser()
        sql = editor.toPlainText()
        queries = parser.parse_queries(sql)
        
        print("\n" + "=" * 80)
        print("QUERY PARSING TEST")
        print("=" * 80)
        print(f"Found {len(queries)} queries:\n")
        
        for i, query in enumerate(queries, 1):
            print(f"Query {i}:")
            print(f"  Lines: {query.start_line + 1} to {query.end_line + 1}")
            print(f"  Text: {query.text[:60]}...")
            print()
        
        print("=" * 80)
    
    comment_btn = QPushButton("Toggle Comment (or press Ctrl+/)")
    comment_btn.clicked.connect(test_comment)
    button_layout.addWidget(comment_btn)
    
    parse_btn = QPushButton("Parse Queries")
    parse_btn.clicked.connect(test_parse_queries)
    button_layout.addWidget(parse_btn)
    
    layout.addLayout(button_layout)
    
    # Show window
    window.show()
    
    print("=" * 80)
    print("Comment Toggle Test")
    print("=" * 80)
    print()
    print("How to test:")
    print("  1. Click on a line (single line)")
    print("  2. Press Ctrl+/ to comment it")
    print("  3. Press Ctrl+/ again to uncomment it")
    print()
    print("  4. Select multiple lines")
    print("  5. Press Ctrl+/ to comment all selected lines")
    print("  6. Press Ctrl+/ again to uncomment all")
    print()
    print("  7. Mix commented and uncommented lines")
    print("  8. Select them and press Ctrl+/")
    print()
    print("  9. Click 'Parse Queries' to see what gets parsed")
    print("     (commented queries should be skipped)")
    print()
    print("=" * 80)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
