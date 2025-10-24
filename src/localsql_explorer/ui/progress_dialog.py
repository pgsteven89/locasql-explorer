"""
Progress dialog for long-running database operations.

Provides visual feedback for operations like:
- Database save/load operations
- Large file imports
- Complex query execution
"""

import logging
from typing import Optional, Callable

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QProgressBar, QTextEdit, QDialogButtonBox
)

logger = logging.getLogger(__name__)


class OperationWorker(QThread):
    """Worker thread for executing long-running operations."""
    
    # Signals
    progress_updated = pyqtSignal(int)  # Progress percentage (0-100)
    status_updated = pyqtSignal(str)    # Status message
    operation_completed = pyqtSignal(bool, str)  # Success, result/error message
    
    def __init__(self, operation_func: Callable, *args, **kwargs):
        super().__init__()
        self.operation_func = operation_func
        self.args = args
        self.kwargs = kwargs
        self.result = None
        self.error_message = ""
        
    def run(self):
        """Execute the operation in the background thread."""
        try:
            self.status_updated.emit("Starting operation...")
            self.progress_updated.emit(10)
            
            # Execute the operation
            self.result = self.operation_func(*self.args, **self.kwargs)
            
            self.progress_updated.emit(100)
            self.status_updated.emit("Operation completed successfully")
            self.operation_completed.emit(True, "Operation completed successfully")
            
        except Exception as e:
            self.error_message = str(e)
            self.progress_updated.emit(0)
            self.status_updated.emit(f"Operation failed: {self.error_message}")
            self.operation_completed.emit(False, self.error_message)


class ProgressDialog(QDialog):
    """
    Dialog for showing progress of long-running operations.
    
    Features:
    - Progress bar with percentage
    - Status text updates
    - Cancellation support
    - Detailed log output
    """
    
    def __init__(self, parent=None, title: str = "Operation in Progress"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.worker: Optional[OperationWorker] = None
        self.operation_completed = False
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface."""
        self.resize(450, 300)
        layout = QVBoxLayout(self)
        
        # Title and main progress
        self.title_label = QLabel("Preparing operation...")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.title_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Initializing...")
        self.status_label.setStyleSheet("color: #666;")
        layout.addWidget(self.status_label)
        
        # Detailed log (collapsible)
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("font-family: monospace; font-size: 11px;")
        layout.addWidget(self.log_text)
        
        # Buttons
        self.button_box = QDialogButtonBox()
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_operation)
        self.button_box.addButton(self.cancel_button, QDialogButtonBox.ButtonRole.RejectRole)
        
        layout.addWidget(self.button_box)
        
    def start_operation(self, operation_func: Callable, *args, **kwargs):
        """Start a long-running operation."""
        self.operation_completed = False
        
        # Create and start worker thread
        self.worker = OperationWorker(operation_func, *args, **kwargs)
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.status_updated.connect(self.update_status)
        self.worker.operation_completed.connect(self.on_operation_completed)
        
        self.worker.start()
        
        # Start a timer to simulate progress updates for operations that don't provide them
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self.simulate_progress)
        self.progress_timer.start(200)  # Update every 200ms
        
    def simulate_progress(self):
        """Simulate progress for operations that don't provide progress callbacks."""
        if not self.operation_completed and self.progress_bar.value() < 90:
            # Slowly increment progress while operation is running
            current = self.progress_bar.value()
            increment = max(1, (90 - current) // 20)
            self.progress_bar.setValue(min(90, current + increment))
            
    def update_progress(self, value: int):
        """Update progress bar."""
        self.progress_bar.setValue(value)
        
    def update_status(self, message: str):
        """Update status message."""
        self.status_label.setText(message)
        self.log_text.append(f"[{self.get_timestamp()}] {message}")
        
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def on_operation_completed(self, success: bool, message: str):
        """Handle operation completion."""
        self.operation_completed = True
        
        if hasattr(self, 'progress_timer'):
            self.progress_timer.stop()
        
        if success:
            self.progress_bar.setValue(100)
            self.title_label.setText("Operation Completed Successfully")
            self.title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: green;")
            
            # Change cancel button to close
            self.cancel_button.setText("Close")
            self.cancel_button.clicked.disconnect()
            self.cancel_button.clicked.connect(self.accept)
            
        else:
            self.progress_bar.setValue(0)
            self.title_label.setText("Operation Failed")
            self.title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: red;")
            
            # Change cancel button to close
            self.cancel_button.setText("Close")
            self.cancel_button.clicked.disconnect()
            self.cancel_button.clicked.connect(self.reject)
            
        self.update_status(message)
        
    def cancel_operation(self):
        """Cancel the running operation."""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
            self.update_status("Operation cancelled by user")
            
        self.reject()
        
    def get_result(self):
        """Get the result of the operation."""
        if self.worker:
            return self.worker.result
        return None
        
    def get_timestamp(self) -> str:
        """Get current timestamp for logging."""
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")
        
    def closeEvent(self, event):
        """Handle dialog close event."""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        event.accept()


class DatabaseSaveDialog(ProgressDialog):
    """Specialized progress dialog for database save operations."""
    
    def __init__(self, parent=None):
        super().__init__(parent, "Saving Database")
        
    def save_database(self, db_manager, file_path: str):
        """Save database with progress tracking."""
        self.title_label.setText(f"Saving database to {file_path}")
        
        def save_operation():
            self.update_status(f"Saving database to {file_path}...")
            self.update_progress(20)
            
            success = db_manager.save_database(file_path)
            
            if success:
                self.update_status("Database saved successfully")
                self.update_progress(100)
                return True
            else:
                raise Exception("Failed to save database")
                
        self.start_operation(save_operation)


class DatabaseLoadDialog(ProgressDialog):
    """Specialized progress dialog for database load operations."""
    
    def __init__(self, parent=None):
        super().__init__(parent, "Loading Database")
        
    def load_database(self, db_manager, file_path: str):
        """Load database with progress tracking."""
        self.title_label.setText(f"Loading database from {file_path}")
        
        def load_operation():
            self.update_status(f"Loading database from {file_path}...")
            self.update_progress(20)
            
            success = db_manager.load_database(file_path)
            
            if success:
                table_count = len(db_manager.list_tables())
                self.update_status(f"Database loaded successfully with {table_count} tables")
                self.update_progress(100)
                return True
            else:
                raise Exception("Failed to load database")
                
        self.start_operation(load_operation)