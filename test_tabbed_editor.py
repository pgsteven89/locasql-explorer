"""
Standalone test for TabbedSQLEditor widget.
"""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from src.localsql_explorer.ui.tabbed_sql_editor import TabbedSQLEditor
from src.localsql_explorer.models import UserPreferences

def main():
    """Test the tabbed SQL editor."""
    app = QApplication(sys.argv)
    
    # Create main window
    window = QMainWindow()
    window.setWindowTitle("Tabbed SQL Editor Test")
    window.resize(800, 600)
    
    # Create central widget
    central_widget = QWidget()
    window.setCentralWidget(central_widget)
    
    layout = QVBoxLayout()
    central_widget.setLayout(layout)
    
    # Create tabbed editor
    preferences = UserPreferences()
    editor = TabbedSQLEditor(preferences)
    
    # Connect signals for testing
    def on_query_requested(query: str, tab_index: int):
        print(f"Query requested from tab {tab_index}:")
        print(f"  {query[:100]}...")
        print()
    
    def on_all_queries_requested(queries: list, tab_index: int):
        print(f"All queries requested from tab {tab_index}:")
        for i, q in enumerate(queries, 1):
            print(f"  Query {i}: {q[:50]}...")
        print()
    
    editor.query_requested.connect(on_query_requested)
    editor.all_queries_requested.connect(on_all_queries_requested)
    
    layout.addWidget(editor)
    
    # Add some test SQL to the first tab
    test_sql = """-- Sample queries
SELECT * FROM users WHERE status = 'active';

SELECT id, name, email 
FROM customers 
WHERE created_at > '2024-01-01';

SELECT COUNT(*) FROM orders;
"""
    editor.set_sql(test_sql)
    
    # Show window
    window.show()
    
    print("=" * 80)
    print("Tabbed SQL Editor Test")
    print("=" * 80)
    print()
    print("Features to test:")
    print("  - Ctrl+T: Create new tab")
    print("  - Ctrl+W: Close current tab")
    print("  - Ctrl+Tab: Next tab")
    print("  - Ctrl+Shift+Tab: Previous tab")
    print("  - Ctrl+Enter: Run current query (at cursor)")
    print("  - Ctrl+Shift+Enter: Run all queries")
    print("  - Double-click tab to rename")
    print("  - Right-click tab for context menu")
    print("  - Click + button to create new tab")
    print()
    print("The first tab has sample queries separated by semicolons.")
    print("Place cursor in different queries and press Ctrl+Enter to test.")
    print()
    print("=" * 80)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
