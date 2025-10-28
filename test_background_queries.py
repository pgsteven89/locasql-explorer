"""
Test script to verify background query execution prevents UI freezing.
Tests both single and multi-query background execution.
"""

import sys
import time
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from PyQt6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget, QLabel, QTextEdit
from PyQt6.QtCore import QTimer
from localsql_explorer.database import DatabaseManager
from localsql_explorer.ui.query_worker import QueryWorker, MultiQueryWorker
import pandas as pd


class TestWindow(QWidget):
    """Test window to verify background query execution."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Background Query Execution Test")
        self.resize(600, 400)
        
        self.db_manager = None
        self.worker = None
        self.counter = 0
        
        layout = QVBoxLayout(self)
        
        # Instructions
        instructions = QLabel(
            "<h3>Background Query Test</h3>"
            "<p>This tests that long-running queries don't freeze the UI.</p>"
            "<p>Watch the counter below - it should keep updating even during query execution.</p>"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Counter label to show UI is responsive
        self.counter_label = QLabel("UI Counter: 0")
        self.counter_label.setStyleSheet("font-size: 24px; font-weight: bold; color: blue;")
        layout.addWidget(self.counter_label)
        
        # Setup database button
        setup_btn = QPushButton("1. Setup Test Database")
        setup_btn.clicked.connect(self.setup_database)
        layout.addWidget(setup_btn)
        
        # Single slow query button
        single_query_btn = QPushButton("2. Run Slow Query (Background)")
        single_query_btn.clicked.connect(self.run_slow_query)
        layout.addWidget(single_query_btn)
        
        # Multi-query button
        multi_query_btn = QPushButton("3. Run Multiple Queries (Background)")
        multi_query_btn.clicked.connect(self.run_multi_queries)
        layout.addWidget(multi_query_btn)
        
        # Status area
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(150)
        layout.addWidget(self.status_text)
        
        # Start counter timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_counter)
        self.timer.start(100)  # Update every 100ms
    
    def update_counter(self):
        """Update counter to show UI is responsive."""
        self.counter += 1
        self.counter_label.setText(f"UI Counter: {self.counter} (updating = UI is responsive!)")
    
    def log(self, message: str):
        """Log a message to the status area."""
        self.status_text.append(f"[{time.strftime('%H:%M:%S')}] {message}")
    
    def setup_database(self):
        """Set up test database with sample data."""
        try:
            self.log("Setting up test database...")
            self.db_manager = DatabaseManager()
            
            # Create a large test table
            data = pd.DataFrame({
                'id': range(10000),
                'name': [f'Person_{i}' for i in range(10000)],
                'value': range(10000, 20000),
                'category': [(f'Cat_{i % 10}') for i in range(10000)]
            })
            
            self.db_manager.register_table('test_data', data)
            self.log("✓ Database setup complete with 10,000 rows")
            
        except Exception as e:
            self.log(f"✗ Error: {str(e)}")
    
    def run_slow_query(self):
        """Run a slow query in background."""
        if not self.db_manager:
            self.log("✗ Please setup database first!")
            return
        
        # Create a query that takes some time
        sql = """
        WITH RECURSIVE numbers AS (
            SELECT 1 AS n
            UNION ALL
            SELECT n + 1 FROM numbers WHERE n < 1000
        )
        SELECT t.*, n.n as seq
        FROM test_data t
        CROSS JOIN numbers n
        WHERE t.id < 100
        ORDER BY t.id, n.n
        """
        
        self.log("Starting slow query in background...")
        self.log("↻ Watch the counter - it should keep updating!")
        
        # Create worker
        self.worker = QueryWorker(self.db_manager, sql, self)
        self.worker.progress_update.connect(self._on_progress)
        self.worker.query_finished.connect(self._on_finished)
        self.worker.query_error.connect(self._on_error)
        self.worker.start()
    
    def run_multi_queries(self):
        """Run multiple queries in background."""
        if not self.db_manager:
            self.log("✗ Please setup database first!")
            return
        
        queries = [
            "SELECT COUNT(*) as total FROM test_data",
            "SELECT category, COUNT(*) as count FROM test_data GROUP BY category",
            "SELECT AVG(value) as avg_value FROM test_data",
            "SELECT * FROM test_data WHERE id < 10",
            "SELECT category, MIN(value), MAX(value) FROM test_data GROUP BY category"
        ]
        
        self.log(f"Starting {len(queries)} queries in background...")
        self.log("↻ Watch the counter - it should keep updating!")
        
        # Create worker
        self.multi_worker = MultiQueryWorker(self.db_manager, queries, self)
        self.multi_worker.progress_update.connect(self._on_multi_progress)
        self.multi_worker.query_completed.connect(self._on_query_complete)
        self.multi_worker.all_queries_finished.connect(self._on_all_complete)
        self.multi_worker.start()
    
    def _on_progress(self, message: str, percentage: int):
        """Handle progress update."""
        self.log(f"  {message} ({percentage}%)")
    
    def _on_finished(self, result):
        """Handle query completion."""
        if result.success:
            self.log(f"✓ Query completed: {result.row_count} rows in {result.execution_time:.3f}s")
        else:
            self.log(f"✗ Query failed: {result.error}")
    
    def _on_error(self, sql: str, error: str):
        """Handle query error."""
        self.log(f"✗ Error: {error}")
    
    def _on_multi_progress(self, message: str, current: int, total: int):
        """Handle multi-query progress."""
        self.log(f"  [{current}/{total}] {message}")
    
    def _on_query_complete(self, result: dict):
        """Handle individual query completion."""
        self.log(f"  ✓ Query {result['query_num']}: {result['rows']} rows in {result['time']:.3f}s")
    
    def _on_all_complete(self, summary: dict):
        """Handle all queries completion."""
        self.log(f"✓ All queries complete: {summary['successful']} successful, {summary['failed']} failed")
        self.log(f"  Total: {summary['total_rows']} rows in {summary['total_time']:.3f}s")


def main():
    """Run the test."""
    app = QApplication(sys.argv)
    
    window = TestWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
