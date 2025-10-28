"""
Test script to verify Query Error Dialog respects theme settings.
Tests both light and dark theme appearances.
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from PyQt6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget
from localsql_explorer.ui.query_dialogs import QueryErrorDialog
from localsql_explorer.themes import theme_manager, ThemeType


class TestWindow(QWidget):
    """Test window with buttons to show error dialog in different themes."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Error Dialog Theme Test")
        self.resize(400, 200)
        
        layout = QVBoxLayout(self)
        
        # Dark theme button
        dark_btn = QPushButton("Show Error Dialog (Dark Theme)")
        dark_btn.clicked.connect(self.show_dark_error)
        layout.addWidget(dark_btn)
        
        # Light theme button
        light_btn = QPushButton("Show Error Dialog (Light Theme)")
        light_btn.clicked.connect(self.show_light_error)
        layout.addWidget(light_btn)
        
        # Sample SQL and error
        self.test_sql = """
SELECT 
    employee_name,
    department,
    COUNT(*) as total_count,
    salary
FROM employees
WHERE department = 'Sales'
GROUP BY department;
"""
        
        self.test_error = """Binder Error: column "employee_name" must appear in the GROUP BY clause or must be part of an aggregate function.
LINE 2:     employee_name,
            ^
This commonly occurs when mixing aggregate functions (COUNT, SUM, AVG) with regular columns."""
    
    def show_dark_error(self):
        """Show error dialog in dark theme."""
        theme_manager.set_theme(ThemeType.DARK)
        dialog = QueryErrorDialog(self, self.test_sql, self.test_error)
        dialog.exec()
    
    def show_light_error(self):
        """Show error dialog in light theme."""
        theme_manager.set_theme(ThemeType.LIGHT)
        dialog = QueryErrorDialog(self, self.test_sql, self.test_error)
        dialog.exec()


def main():
    """Run the test."""
    app = QApplication(sys.argv)
    
    # Apply initial theme
    theme_manager.apply_theme()
    
    window = TestWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
