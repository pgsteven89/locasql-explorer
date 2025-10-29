"""
Test script to verify table selection works with TabbedSQLEditor.
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from PyQt6.QtWidgets import QApplication, QMainWindow, QHBoxLayout, QWidget, QPushButton, QVBoxLayout
from localsql_explorer.ui.tabbed_sql_editor import TabbedSQLEditor


class TestWindow(QMainWindow):
    """Test window to verify table selection and insert_text."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Table Selection Test")
        self.resize(800, 600)
        
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QHBoxLayout(central)
        
        # Create editor first
        self.editor = TabbedSQLEditor()
        
        # Left side: buttons
        button_panel = QWidget()
        button_layout = QVBoxLayout(button_panel)
        
        # Test buttons
        insert_btn = QPushButton("Insert 'employees' table")
        insert_btn.clicked.connect(lambda: self.editor.insert_text("employees"))
        button_layout.addWidget(insert_btn)
        
        insert_query_btn = QPushButton("Insert SELECT query")
        insert_query_btn.clicked.connect(lambda: self.editor.insert_text("SELECT * FROM "))
        button_layout.addWidget(insert_query_btn)
        
        set_sql_btn = QPushButton("Set SQL")
        set_sql_btn.clicked.connect(lambda: self.editor.set_sql("SELECT id, name FROM test_table"))
        button_layout.addWidget(set_sql_btn)
        
        get_sql_btn = QPushButton("Get SQL (print to console)")
        get_sql_btn.clicked.connect(lambda: print(f"Current SQL: {self.editor.get_sql()}"))
        button_layout.addWidget(get_sql_btn)
        
        clear_btn = QPushButton("Clear SQL")
        clear_btn.clicked.connect(self.editor.clear)
        button_layout.addWidget(clear_btn)
        
        button_layout.addStretch()
        
        layout.addWidget(button_panel)
        
        # Right side: editor
        layout.addWidget(self.editor)
        
        # Set stretch factors
        layout.setStretch(0, 1)
        layout.setStretch(1, 3)
    

def main():
    """Run the test."""
    app = QApplication(sys.argv)
    
    window = TestWindow()
    window.show()
    
    print("✓ Test window created successfully")
    print("Click buttons to test insert_text and other methods")
    print("Type in the editor and click 'Get SQL' to verify get_sql works")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
