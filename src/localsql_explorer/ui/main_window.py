"""
Main window for LocalSQL Explorer application.

This module provides the MainWindow class which serves as the primary application window
and coordinates all UI components including the table list, SQL editor, and results view.
"""

import logging
import sys
from pathlib import Path
from typing import Optional, List

import pandas as pd

from PyQt6.QtCore import QSettings, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
    QDialog,
    QProgressBar,
    QLabel,
)

from ..database import DatabaseManager
from ..exporter import ResultExporter
from ..importer import FileImporter
from ..models import AppConfig, UserPreferences
from .results_view import ResultsTableView
from .paginated_results import PaginatedTableWidget
from .enhanced_sql_editor import EnhancedSQLEditor
from .tabbed_sql_editor import TabbedSQLEditor
from .table_list import TableListWidget
from .excel_sheet_dialog import ExcelSheetSelectionDialog
from .export_dialog import ExportOptionsDialog
from .progress_dialog import DatabaseSaveDialog, DatabaseLoadDialog
from .query_dialogs import QueryErrorDialog, QueryMetricsDialog
from .query_history_panel import QueryHistoryPanel
from .query_worker import QueryWorker, PaginatedQueryWorker, MultiQueryWorker
from ..query_history import QueryHistory
from ..themes import theme_manager, ThemeType

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    Main application window for LocalSQL Explorer.
    
    Provides the primary user interface with:
    - Menu bar with file operations
    - Dockable table list panel
    - SQL editor pane
    - Query results viewer
    - Status bar for feedback
    """
    
    # Signals
    table_imported = pyqtSignal(str)  # Table name
    query_executed = pyqtSignal(str, bool)  # SQL, success
    database_loaded = pyqtSignal(str)  # Database path
    
    def __init__(self, config: Optional[AppConfig] = None):
        """
        Initialize the main window.
        
        Args:
            config: Application configuration
        """
        super().__init__()
        
        self.config = config or AppConfig(
            config_dir=Path.home() / ".localsql_explorer",
            data_dir=Path.home() / ".localsql_explorer" / "data",
            log_dir=Path.home() / ".localsql_explorer" / "logs"
        )
        
        # Core components
        self.db_manager: Optional[DatabaseManager] = None
        self.file_importer = FileImporter()
        self.result_exporter = ResultExporter()
        
        # Query history
        self.query_history = QueryHistory()
        
        # UI components
        self.sql_editor: Optional[TabbedSQLEditor] = None
        self.table_list: Optional[TableListWidget] = None
        self.results_view: Optional[ResultsTableView] = None
        self.paginated_results: Optional[PaginatedTableWidget] = None
        self.query_history_panel: Optional[QueryHistoryPanel] = None
        self.splitter: Optional[QSplitter] = None
        
        # Large data settings
        self.pagination_threshold = 10000  # Use pagination for results > 10k rows
        self.current_results_mode = "standard"  # "standard" or "paginated"
        
        # Settings
        self.settings = QSettings("LocalSQL Explorer", "MainWindow")
        
        # Query tracking for metrics
        self.last_query_sql = ""
        self.last_query_result = None
        self.last_query_time = 0.0
        
        # Background query execution
        self.query_worker: Optional[QueryWorker] = None
        self.paginated_worker: Optional[PaginatedQueryWorker] = None
        self.multi_query_worker: Optional[MultiQueryWorker] = None
        
        self.init_ui()
        self.init_database()
        self.restore_window_state()
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("LocalSQL Explorer")
        self.setMinimumSize(800, 600)
        
        # Set window icon if available
        icon_path = Path(__file__).parent.parent.parent.parent / "assets" / "icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        self.create_menu_bar()
        self.create_toolbar()
        self.create_central_widget()
        self.create_dock_widgets()
        self.create_status_bar()
        
        # Initialize theme from preferences
        self.init_theme()
        
        # Apply theme
        self.apply_theme()
    
    def create_menu_bar(self):
        """Create the menu bar."""
        menubar = self.menuBar()
        
        # File Menu
        file_menu = menubar.addMenu("&File")
        
        # Import action
        import_action = QAction("&Import File...", self)
        import_action.setShortcut(QKeySequence("Ctrl+I"))
        import_action.setStatusTip("Import CSV, Excel, or Parquet file")
        import_action.triggered.connect(self.import_file)
        file_menu.addAction(import_action)
        
        file_menu.addSeparator()
        
        # Database actions
        save_db_action = QAction("&Save Database...", self)
        save_db_action.setShortcut(QKeySequence("Ctrl+S"))
        save_db_action.setStatusTip("Save current database to file")
        save_db_action.triggered.connect(self.save_database)
        file_menu.addAction(save_db_action)
        
        load_db_action = QAction("&Load Database...", self)
        load_db_action.setShortcut(QKeySequence("Ctrl+O"))
        load_db_action.setStatusTip("Load database from file")
        load_db_action.triggered.connect(self.load_database)
        file_menu.addAction(load_db_action)
        
        file_menu.addSeparator()
        
        # Export action
        export_action = QAction("&Export Results...", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.setStatusTip("Export query results to file")
        export_action.triggered.connect(self.export_results)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.setStatusTip("Exit application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit Menu
        edit_menu = menubar.addMenu("&Edit")
        
        # SQL editor actions (will be connected when editor is created)
        self.undo_action = QAction("&Undo", self)
        self.undo_action.setShortcut(QKeySequence("Ctrl+Z"))
        edit_menu.addAction(self.undo_action)
        
        self.redo_action = QAction("&Redo", self)
        self.redo_action.setShortcut(QKeySequence("Ctrl+Y"))
        edit_menu.addAction(self.redo_action)
        
        edit_menu.addSeparator()
        
        self.cut_action = QAction("Cu&t", self)
        self.cut_action.setShortcut(QKeySequence("Ctrl+X"))
        edit_menu.addAction(self.cut_action)
        
        self.copy_action = QAction("&Copy", self)
        self.copy_action.setShortcut(QKeySequence("Ctrl+C"))
        edit_menu.addAction(self.copy_action)
        
        self.paste_action = QAction("&Paste", self)
        self.paste_action.setShortcut(QKeySequence("Ctrl+V"))
        edit_menu.addAction(self.paste_action)
        
        # Query Menu
        query_menu = menubar.addMenu("&Query")
        
        self.run_query_action = QAction("&Run Query", self)
        self.run_query_action.setShortcut(QKeySequence("F5"))
        self.run_query_action.setStatusTip("Execute SQL query")
        self.run_query_action.triggered.connect(self.run_query)
        query_menu.addAction(self.run_query_action)
        
        query_menu.addSeparator()
        
        clear_editor_action = QAction("&Clear Editor", self)
        clear_editor_action.setShortcut(QKeySequence("Ctrl+L"))
        clear_editor_action.setStatusTip("Clear SQL editor")
        clear_editor_action.triggered.connect(self.clear_editor)
        query_menu.addAction(clear_editor_action)
        
        # CTE Templates submenu
        cte_menu = query_menu.addMenu("&CTE Templates")
        
        insert_cte_action = QAction("Insert &CTE Template", self)
        insert_cte_action.setShortcut(QKeySequence("Ctrl+Shift+C"))
        insert_cte_action.setStatusTip("Insert Common Table Expression template")
        insert_cte_action.triggered.connect(self.insert_cte_template)
        cte_menu.addAction(insert_cte_action)
        
        insert_recursive_cte_action = QAction("Insert &Recursive CTE Template", self)
        insert_recursive_cte_action.setShortcut(QKeySequence("Ctrl+Shift+R"))
        insert_recursive_cte_action.setStatusTip("Insert Recursive Common Table Expression template")
        insert_recursive_cte_action.triggered.connect(self.insert_recursive_cte_template)
        cte_menu.addAction(insert_recursive_cte_action)
        
        # Query formatting
        format_query_action = QAction("&Format Query", self)
        format_query_action.setShortcut(QKeySequence("Ctrl+Shift+F"))
        format_query_action.setStatusTip("Format SQL query")
        format_query_action.triggered.connect(self.format_query)
        query_menu.addAction(format_query_action)
        
        query_menu.addSeparator()
        
        # Query metrics action
        show_metrics_action = QAction("Show Query &Metrics", self)
        show_metrics_action.setShortcut(QKeySequence("Ctrl+M"))
        show_metrics_action.setStatusTip("Show detailed metrics for last query")
        show_metrics_action.triggered.connect(self.show_last_query_metrics)
        query_menu.addAction(show_metrics_action)
        
        # View Menu
        view_menu = menubar.addMenu("&View")
        
        # Dock visibility toggles will be added after docks are created
        
        view_menu.addSeparator()
        
        # Theme toggle
        self.toggle_theme_action = QAction("Toggle &Theme", self)
        self.toggle_theme_action.setShortcut(QKeySequence("Ctrl+T"))
        self.toggle_theme_action.setStatusTip("Switch between light and dark theme")
        self.toggle_theme_action.triggered.connect(self.toggle_theme)
        view_menu.addAction(self.toggle_theme_action)
        
        # Update theme action text
        self.update_theme_action_text()
        
        view_menu.addSeparator()
        
        # Data optimization settings
        optimization_action = QAction("Data &Optimization Settings...", self)
        optimization_action.setStatusTip("Configure pagination and memory optimization settings")
        optimization_action.triggered.connect(self.show_optimization_settings)
        view_menu.addAction(optimization_action)
        
        # Help Menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.setStatusTip("About LocalSQL Explorer")
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_toolbar(self):
        """Create the toolbar."""
        toolbar = self.addToolBar("Main")
        toolbar.setMovable(False)
        
        # Add main actions to toolbar
        toolbar.addAction(self.findChild(QAction, "") or QAction("Import", self))
        toolbar.addSeparator()
        toolbar.addAction(self.run_query_action)
    
    def create_central_widget(self):
        """Create the central widget with SQL editor and results view."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main splitter (horizontal)
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Create tabbed SQL editor
        self.sql_editor = TabbedSQLEditor(self.config.preferences)
        self.sql_editor.query_requested.connect(self.run_query)
        self.sql_editor.all_queries_requested.connect(self.run_all_queries)
        
        # Create results views (standard and paginated)
        self.results_view = ResultsTableView()
        self.results_view.export_requested.connect(self.export_results)
        self.results_view.export_filtered_requested.connect(self.export_filtered_results_from_view)
        
        self.paginated_results = PaginatedTableWidget()
        self.paginated_results.export_requested.connect(self.export_results)
        self.paginated_results.export_all_requested.connect(self.export_all_results)
        self.paginated_results.export_filtered_requested.connect(self.export_filtered_results_from_view)
        self.paginated_results.status_updated.connect(self.update_status)
        self.paginated_results.metrics_requested.connect(self.show_paginated_metrics)
        
        # Create a stacked widget to manage results views
        self.results_stack = QStackedWidget()
        self.results_stack.addWidget(self.results_view)      # Index 0
        self.results_stack.addWidget(self.paginated_results) # Index 1
        
        # Add to splitter
        self.splitter.addWidget(self.sql_editor)
        self.splitter.addWidget(self.results_stack)
        
        # Set initial sizes (60% editor, 40% results)
        self.splitter.setSizes([600, 400])
        
        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.splitter)
        layout.setContentsMargins(0, 0, 0, 0)
        central_widget.setLayout(layout)
        
        # Connect editor actions
        self.connect_editor_actions()
    
    def create_dock_widgets(self):
        """Create dockable widgets."""
        # Table list dock
        self.table_dock = QDockWidget("Tables", self)
        self.table_list = TableListWidget()
        self.table_list.table_selected.connect(self.on_table_selected)
        self.table_list.table_preview_requested.connect(self.preview_table)
        self.table_list.table_renamed.connect(self.on_table_renamed)
        self.table_list.table_dropped.connect(self.on_table_dropped)
        self.table_list.table_column_analysis_requested.connect(self.show_column_analysis)
        self.table_list.table_profiling_requested.connect(self.show_table_profiling)
        
        # Connect new drag-and-drop signals
        self.table_list.files_dropped.connect(self.import_dropped_files)
        self.table_list.import_files_requested.connect(self.import_multiple_files)
        
        self.table_dock.setWidget(self.table_list)
        self.table_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.table_dock)
        
        # Query history dock
        self.history_dock = QDockWidget("Query History", self)
        self.query_history_panel = QueryHistoryPanel(self.query_history)
        self.query_history_panel.query_selected.connect(self.load_query_from_history)
        self.query_history_panel.query_edited.connect(self.replace_query_from_history)
        
        self.history_dock.setWidget(self.query_history_panel)
        self.history_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.history_dock)
        
        # Add dock toggle actions to view menu
        self.add_dock_actions_to_menu()
    
    def add_dock_actions_to_menu(self):
        """Add dock widget toggle actions to the View menu."""
        # Find the View menu
        for action in self.menuBar().actions():
            if action.text() == "&View":
                view_menu = action.menu()
                # Add dock actions at the beginning
                first_action = view_menu.actions()[0] if view_menu.actions() else None
                if first_action:
                    view_menu.insertAction(first_action, self.table_dock.toggleViewAction())
                    view_menu.insertAction(first_action, self.history_dock.toggleViewAction())
                else:
                    view_menu.addAction(self.table_dock.toggleViewAction())
                    view_menu.addAction(self.history_dock.toggleViewAction())
                break
    
    def create_status_bar(self):
        """Create an enhanced status bar with progress indicators."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Main status message (left side)
        self.status_bar.showMessage("Ready")
        
        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        # Connection status indicator
        self.connection_label = QLabel("🟢 Connected")
        self.connection_label.setStyleSheet("color: green; font-weight: bold;")
        self.connection_label.setToolTip("Database connection status")
        self.status_bar.addPermanentWidget(self.connection_label)
        
        # Table count indicator
        self.table_count_label = QLabel("📊 0 tables")
        self.table_count_label.setToolTip("Number of loaded tables")
        self.status_bar.addPermanentWidget(self.table_count_label)
        
        # Memory usage indicator
        self.memory_label = QLabel("💾 0 MB")
        self.memory_label.setToolTip("Estimated memory usage")
        self.status_bar.addPermanentWidget(self.memory_label)
    
    def show_progress(self, message: str, progress: int = 0):
        """Show progress bar with message."""
        self.status_bar.showMessage(message)
        self.progress_bar.setValue(progress)
        self.progress_bar.setVisible(True)
        QApplication.processEvents()  # Update UI immediately
    
    def hide_progress(self):
        """Hide progress bar."""
        self.progress_bar.setVisible(False)
        QApplication.processEvents()
    
    def update_status_indicators(self):
        """Update status bar indicators."""
        # Update table count
        if self.table_list:
            table_count = len(self.table_list.get_all_tables())
            self.table_count_label.setText(f"📊 {table_count} tables")
        
        # Update memory usage (rough estimate)
        total_memory = 0
        
        # Check both standard and paginated views
        if self.current_results_mode == "standard" and self.results_view and self.results_view.has_data():
            try:
                df = self.results_view.get_dataframe()
                if df is not None:
                    memory_bytes = df.memory_usage(deep=True).sum()
                    total_memory += memory_bytes
            except:
                pass
        elif self.current_results_mode == "paginated" and self.paginated_results:
            # For paginated view, estimate based on current page
            try:
                if hasattr(self.paginated_results, 'current_data') and self.paginated_results.current_data is not None:
                    memory_bytes = self.paginated_results.current_data.memory_usage(deep=True).sum()
                    total_memory += memory_bytes
            except:
                pass
        
        memory_mb = total_memory / (1024 * 1024)
        self.memory_label.setText(f"💾 {memory_mb:.1f} MB")
        
        # Update connection status
        if self.db_manager and hasattr(self.db_manager, 'connection') and self.db_manager.connection:
            self.connection_label.setText("🟢 Connected")
            self.connection_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.connection_label.setText("🔴 Disconnected")
            self.connection_label.setStyleSheet("color: red; font-weight: bold;")
    
    def update_status(self, message: str):
        """Update the status bar with a message."""
        if hasattr(self, 'status_bar'):
            self.status_bar.showMessage(message)
    
    def show_paginated_metrics(self, sql: str, result_data: pd.DataFrame, metrics_type: str):
        """Show metrics for paginated results (original or filtered)."""
        try:
            # Create a custom title based on metrics type
            title_prefix = "Filtered Dataset" if metrics_type == "filtered" else "Original Query"
            
            # Import here to avoid circular imports
            from .query_dialogs import QueryMetricsDialog
            
            # Create and show metrics dialog with custom title
            metrics_dialog = QueryMetricsDialog(self, sql, result_data, 0.0)  # execution_time not relevant for analysis
            metrics_dialog.setWindowTitle(f"{title_prefix} - Query Execution Metrics")
            
            # Update the dialog title in the UI if possible
            if hasattr(metrics_dialog, 'summary_frame'):
                # Add a label to indicate the type of metrics
                metrics_type_label = QLabel(f"<b>Metrics Type:</b> {title_prefix}")
                metrics_type_label.setStyleSheet("color: #0066cc; font-size: 12px; margin: 5px;")
                # Try to insert at the top of the dialog
                layout = metrics_dialog.layout()
                if layout:
                    layout.insertWidget(0, metrics_type_label)
            
            metrics_dialog.exec()
            
        except Exception as e:
            logger.error(f"Error showing paginated metrics: {e}")
            QMessageBox.warning(
                self,
                "Metrics Error", 
                f"Unable to display metrics: {str(e)}"
            )
    
    def connect_editor_actions(self):
        """Connect editor actions to SQL editor."""
        if self.sql_editor:
            self.undo_action.triggered.connect(self.sql_editor.undo)
            self.redo_action.triggered.connect(self.sql_editor.redo)
            self.cut_action.triggered.connect(self.sql_editor.cut)
            self.copy_action.triggered.connect(self.sql_editor.copy)
            self.paste_action.triggered.connect(self.sql_editor.paste)
    
    def init_database(self):
        """Initialize the database manager."""
        self.db_manager = DatabaseManager()
        logger.info("Database manager initialized")
    
    def init_theme(self):
        """Initialize theme from user preferences."""
        # Sync theme manager with preferences
        try:
            if self.config.preferences.theme == "dark":
                preferred_theme = ThemeType.DARK
            else:
                preferred_theme = ThemeType.LIGHT
            
            # Set theme without applying (we'll apply it separately)
            theme_manager.current_theme = preferred_theme
            theme_manager._save_theme(preferred_theme)
            
        except Exception as e:
            logger.warning(f"Failed to initialize theme from preferences: {e}")
            # Fall back to dark theme
            theme_manager.current_theme = ThemeType.DARK
    
    def apply_theme(self):
        """Apply the current theme to the application."""
        theme_manager.apply_theme()
        self.status_bar.showMessage(f"Applied {theme_manager.get_current_theme().value} theme")
    
    def import_file(self):
        """Import a single data file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Data File",
            "",
            "Data Files (*.csv *.xlsx *.xls *.parquet *.pq);;CSV Files (*.csv);;Excel Files (*.xlsx *.xls);;Parquet Files (*.parquet *.pq);;All Files (*)"
        )
        
        if file_path:
            self.import_files([file_path])
    
    def import_multiple_files(self):
        """Import multiple data files."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Import Multiple Data Files",
            "",
            "Data Files (*.csv *.xlsx *.xls *.parquet *.pq);;CSV Files (*.csv);;Excel Files (*.xlsx *.xls);;Parquet Files (*.parquet *.pq);;All Files (*)"
        )
        
        if file_paths:
            self.import_files(file_paths)
    
    def import_dropped_files(self, file_paths: List[str]):
        """Import files that were dropped onto the table list."""
        self.import_files(file_paths)
    
    def import_excel_with_sheet_selection(self, file_path: str) -> bool:
        """
        Import Excel file with sheet selection dialog.
        
        Args:
            file_path: Path to Excel file
            
        Returns:
            True if import was successful, False if cancelled or failed
        """
        try:
            # Analyze the Excel file to get sheet information
            self.show_progress(f"Analyzing Excel file...", 10)
            sheet_infos = self.file_importer.detect_excel_sheets(file_path)
            
            # If only one non-empty sheet, import directly without dialog
            non_empty_sheets = [s for s in sheet_infos if not s.is_empty]
            if len(non_empty_sheets) <= 1:
                self.show_progress(f"Importing single sheet...", 50)
                result = self.file_importer.import_file(file_path)
                if result.success and result.dataframe is not None:
                    return self._register_imported_table(file_path, result)
                return False
            
            # Show sheet selection dialog
            self.hide_progress()  # Hide progress during dialog
            dialog = ExcelSheetSelectionDialog(file_path, sheet_infos, self)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                selected_sheet_names = dialog.get_selected_sheet_names()
                base_table_name = dialog.get_base_table_name()
                
                if not selected_sheet_names:
                    return False
                
                # Show progress for batch import
                self.show_progress(f"Importing {len(selected_sheet_names)} sheets...", 20)
                
                # Import selected sheets
                batch_result = self.file_importer.import_excel_multiple_sheets(
                    file_path, selected_sheet_names, base_table_name
                )
                
                if batch_result.success:
                    # Register each successfully imported sheet
                    for import_result in batch_result.successful_imports:
                        table_name = import_result.metadata.get('table_name')
                        if table_name and self.db_manager:
                            # Check for name conflicts
                            original_name = table_name
                            counter = 1
                            while table_name in self.db_manager.tables:
                                table_name = f"{original_name}_{counter}"
                                counter += 1
                            
                            # Register with database
                            metadata = self.db_manager.register_table(
                                table_name,
                                import_result.dataframe,
                                file_path,
                                import_result.file_type
                            )
                            
                            # Add source sheet information to metadata
                            metadata.metadata['source_sheet'] = import_result.metadata.get('sheet_name')
                            metadata.metadata['source_file'] = Path(file_path).name
                            
                            # Update table list
                            if self.table_list:
                                self.table_list.add_table(metadata)
                            
                            logger.info(f"Successfully imported sheet '{import_result.metadata.get('sheet_name')}' as table '{table_name}'")
                    
                    # Show summary message
                    total_imported = len(batch_result.successful_imports)
                    total_failed = len(batch_result.failed_imports)
                    
                    if total_failed > 0:
                        QMessageBox.information(
                            self,
                            "Import Complete",
                            f"Excel import completed:\n• {total_imported} sheets imported successfully\n• {total_failed} sheets failed to import"
                        )
                    
                    return True
                else:
                    QMessageBox.warning(
                        self,
                        "Import Failed", 
                        f"Failed to import Excel sheets:\n{batch_result.warnings}"
                    )
                    return False
            else:
                # User cancelled
                return False
                
        except Exception as e:
            logger.error(f"Failed to import Excel file {file_path}: {e}")
            QMessageBox.critical(
                self,
                "Excel Import Error",
                f"Failed to import Excel file:\n{str(e)}"
            )
            return False
    
    def _register_imported_table(self, file_path: str, result) -> bool:
        """Helper method to register a single imported table."""
        try:
            # Generate table name and check for conflicts  
            table_name = self.file_importer.get_suggested_table_name(file_path)
            original_name = table_name
            counter = 1
            
            while table_name in self.db_manager.tables:
                table_name = f"{original_name}_{counter}"
                counter += 1
            
            # Register with database
            if self.db_manager:
                metadata = self.db_manager.register_table(
                    table_name,
                    result.dataframe,
                    file_path,
                    result.file_type
                )
                
                # Update table list
                if self.table_list:
                    self.table_list.add_table(metadata)
                
                logger.info(f"Successfully imported {Path(file_path).name} as table '{table_name}'")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to register table for {file_path}: {e}")
            return False
    
    def import_files(self, file_paths: List[str]):
        """
        Import multiple files with progress tracking.
        
        Args:
            file_paths: List of file paths to import
        """
        if not file_paths:
            return
        
        total_files = len(file_paths)
        successful_imports = 0
        failed_imports = []
        
        for i, file_path in enumerate(file_paths):
            try:
                # Update progress for current file
                file_name = Path(file_path).name
                progress = int((i / total_files) * 100)
                self.show_progress(f"Importing {file_name} ({i+1}/{total_files})...", progress)
                
                # Check if this is an Excel file for multi-sheet handling
                if Path(file_path).suffix.lower() in ['.xlsx', '.xls']:
                    success = self.import_excel_with_sheet_selection(file_path)
                    if success:
                        successful_imports += 1
                    else:
                        failed_imports.append((file_name, "User cancelled or import failed"))
                else:
                    # Import non-Excel files normally
                    result = self.file_importer.import_file(file_path)
                    
                    if result.success and result.dataframe is not None:
                        success = self._register_imported_table(file_path, result)
                        if success:
                            successful_imports += 1
                        else:
                            failed_imports.append((file_name, "Database not initialized"))
                    else:
                        failed_imports.append((file_name, result.error or "Unknown error"))
                    
            except Exception as e:
                failed_imports.append((file_name, str(e)))
                logger.error(f"Failed to import {file_name}: {e}")
        
        # Complete the import process
        self.show_progress("Finalizing imports...", 95)
        
        # Update schema info for auto-completion
        if successful_imports > 0:
            self.update_schema_info()
        
        self.show_progress("Import completed", 100)
        self.hide_progress()
        
        # Show results summary
        if total_files == 1:
            # Single file import - use original behavior
            if successful_imports == 1:
                self.status_bar.showMessage(f"Imported {Path(file_paths[0]).name} successfully")
                self.table_imported.emit(list(self.db_manager.tables.keys())[-1])
            else:
                error_msg = failed_imports[0][1] if failed_imports else "Unknown error"
                self.status_bar.showMessage(f"Import failed: {error_msg}")
                QMessageBox.critical(self, "Import Error", error_msg)
        else:
            # Multiple file import - show summary
            self._show_import_summary(successful_imports, failed_imports)
        
        self.update_status_indicators()
    
    def _show_import_summary(self, successful_imports: int, failed_imports: List[tuple]):
        """Show a summary dialog for multi-file import results."""
        total_files = successful_imports + len(failed_imports)
        
        if failed_imports:
            # Some failures - show detailed summary
            message = f"Import completed with {successful_imports}/{total_files} files imported successfully.\n\n"
            
            if failed_imports:
                message += "Failed imports:\n"
                for file_name, error in failed_imports[:5]:  # Show first 5 failures
                    message += f"• {file_name}: {error}\n"
                
                if len(failed_imports) > 5:
                    message += f"... and {len(failed_imports) - 5} more failures."
            
            QMessageBox.warning(self, "Import Summary", message)
        else:
            # All successful
            message = f"Successfully imported all {successful_imports} files!"
            self.status_bar.showMessage(message)
            QMessageBox.information(self, "Import Complete", message)
    
    def save_database(self):
        """Save the current database to a file with progress tracking."""
        if not self.db_manager:
            QMessageBox.warning(self, "Warning", "No database to save")
            return
        
        if not self.table_list or len(self.table_list.get_all_tables()) == 0:
            QMessageBox.information(self, "No Data", "No tables to save. Import some data first.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Database",
            f"localsql_explorer_db_{self.get_timestamp()}.duckdb",
            "DuckDB Files (*.duckdb);;All Files (*)"
        )
        
        if file_path:
            # Show progress dialog
            progress_dialog = DatabaseSaveDialog(self)
            progress_dialog.save_database(self.db_manager, file_path)
            
            if progress_dialog.exec() == QDialog.DialogCode.Accepted:
                # Success
                self.status_bar.showMessage(f"Database saved to {Path(file_path).name}")
                self.config.add_recent_database(file_path)
                
                # Show success message
                table_count = len(self.table_list.get_all_tables())
                QMessageBox.information(
                    self,
                    "Save Successful", 
                    f"Successfully saved database with {table_count} tables to:\n{file_path}"
                )
            else:
                # Failed or cancelled
                self.status_bar.showMessage("Database save cancelled or failed")
                
    def get_timestamp(self) -> str:
        """Get current timestamp for file naming."""
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def load_database(self):
        """Load a database from a file with progress tracking."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Database",
            "",
            "DuckDB Files (*.duckdb);;All Files (*)"
        )
        
        if file_path:
            # Confirm if current data will be lost
            if self.table_list and len(self.table_list.get_all_tables()) > 0:
                reply = QMessageBox.question(
                    self,
                    "Load Database",
                    "Loading a database will replace your current tables. Continue?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return
            
            # Show progress dialog
            progress_dialog = DatabaseLoadDialog(self)
            progress_dialog.load_database(self.db_manager, file_path)
            
            if progress_dialog.exec() == QDialog.DialogCode.Accepted:
                # Success - update UI
                if self.table_list:
                    self.table_list.clear()
                    for metadata in self.db_manager.list_tables():
                        self.table_list.add_table(metadata)
                
                # Update schema info for SQL editor auto-completion
                self.update_schema_info()
                
                table_count = len(self.db_manager.list_tables())
                self.status_bar.showMessage(f"Loaded database with {table_count} tables")
                self.config.add_recent_database(file_path)
                self.database_loaded.emit(file_path)
                
                # Show success message
                QMessageBox.information(
                    self,
                    "Load Successful",
                    f"Successfully loaded database with {table_count} tables from:\n{Path(file_path).name}"
                )
            else:
                # Failed or cancelled
                self.status_bar.showMessage("Database load cancelled or failed")
    
    def export_results(self):
        """Export query results to a file with enhanced options and support for both view modes."""
        # Determine which view is active and get data
        dataframe = None
        export_context = "query_results"
        
        if self.current_results_mode == "standard":
            if not self.results_view or not self.results_view.has_data():
                QMessageBox.information(self, "Export", "No results to export")
                return
            dataframe = self.results_view.get_dataframe()
            
        elif self.current_results_mode == "paginated":
            if not self.paginated_results or not hasattr(self.paginated_results, 'current_data'):
                QMessageBox.information(self, "Export", "No results to export")
                return
            dataframe = self.paginated_results.current_data
            export_context = "paginated_results"
            
            # For paginated results, warn user about partial export
            if hasattr(self.paginated_results, 'current_page_info') and self.paginated_results.current_page_info:
                reply = QMessageBox.question(
                    self,
                    "Export Current Page",
                    f"This will export only the current page ({self.paginated_results.current_page_info.start_row + 1:,}-{self.paginated_results.current_page_info.end_row:,} of {self.paginated_results.current_page_info.total_rows:,} rows). Continue?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
        else:
            QMessageBox.information(self, "Export", "No results to export")
            return
        
        if dataframe is None or dataframe.empty:
            QMessageBox.information(self, "Export", "No results to export")
            return
        
        # Create enhanced export dialog
        dialog = ExportOptionsDialog(self, export_context)
        
        if dialog.exec() == ExportOptionsDialog.DialogCode.Accepted:
            file_path = dialog.get_file_path()
            export_options = dialog.get_export_options()
            
            self.status_bar.showMessage(f"Exporting results to {file_path}...")
            
            try:
                if dataframe is not None:
                    # Use the enhanced exporter with custom options
                    # Get the format type from the dialog
                    format_type = dialog.get_file_format()
                    result = self.result_exporter.export_result(
                        dataframe, 
                        file_path, 
                        format_type,
                        export_options
                    )
                    
                    if result.success:
                        file_size_mb = result.file_size / (1024*1024) if result.file_size else 0
                        self.status_bar.showMessage(
                            f"Exported {result.row_count} rows to {Path(file_path).name} "
                            f"({file_size_mb:.1f} MB)"
                        )
                        
                        # Show success message with details
                        QMessageBox.information(
                            self, 
                            "Export Successful",
                            f"Successfully exported {result.row_count} rows to:\n{file_path}\n\n"
                            f"File size: {file_size_mb:.1f} MB"
                        )
                    else:
                        self.status_bar.showMessage(f"Export failed: {result.error}")
                        QMessageBox.critical(self, "Export Error", result.error or "Unknown error")
                else:
                    self.status_bar.showMessage("No data to export")
                
            except Exception as e:
                error_msg = f"Export failed: {str(e)}"
                self.status_bar.showMessage(error_msg)
                QMessageBox.critical(self, "Export Error", error_msg)
    
    def export_filtered_results_from_view(self, filtered_dataframe: pd.DataFrame):
        """Export filtered results from view (called with filtered DataFrame)."""
        if filtered_dataframe is None or filtered_dataframe.empty:
            QMessageBox.information(self, "Export", "No filtered results to export")
            return
        
        # Create enhanced export dialog
        dialog = ExportOptionsDialog(self, "filtered_results")
        
        if dialog.exec() == ExportOptionsDialog.DialogCode.Accepted:
            file_path = dialog.get_file_path()
            export_options = dialog.get_export_options()
            
            self.status_bar.showMessage(f"Exporting filtered results to {file_path}...")
            
            try:
                # Use the enhanced exporter with custom options
                format_type = dialog.get_file_format()
                result = self.result_exporter.export_result(
                    filtered_dataframe, 
                    file_path, 
                    format_type,
                    export_options
                )
                
                if result.success:
                    file_size_mb = result.file_size / (1024*1024) if result.file_size else 0
                    self.status_bar.showMessage(
                        f"Exported {result.row_count} filtered rows to {Path(file_path).name} "
                        f"({file_size_mb:.1f} MB)"
                    )
                    
                    # Show success message with details
                    QMessageBox.information(
                        self, 
                        "Export Successful",
                        f"Successfully exported {result.row_count} filtered rows to:\n{file_path}\n\n"
                        f"File size: {file_size_mb:.1f} MB"
                    )
                else:
                    self.status_bar.showMessage(f"Export failed: {result.error}")
                    QMessageBox.critical(self, "Export Error", result.error or "Unknown error")
                    
            except Exception as e:
                error_msg = f"Export failed: {str(e)}"
                self.status_bar.showMessage(error_msg)
                QMessageBox.critical(self, "Export Error", error_msg)
    
    def export_all_results(self):
        """Export all query results (complete dataset, not just current page)."""
        if not self.last_query_sql:
            QMessageBox.information(self, "Export", "No query results available to export")
            return
            
        # Get file path from user
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export All Results",
            f"all_results_{int(pd.Timestamp.now().timestamp())}.csv",
            "CSV Files (*.csv);;Excel Files (*.xlsx);;Parquet Files (*.parquet)"
        )
        
        if not file_path:
            return
            
        try:
            self.status_bar.showMessage("Exporting all results...")
            
            # Execute the original query to get complete results
            complete_result = self.db_manager.execute_query(self.last_query_sql)
            
            if complete_result.success and complete_result.data is not None:
                # Use the exporter to save the complete dataset
                from localsql_explorer.exporter import ResultExporter
                exporter = ResultExporter()
                
                export_result = exporter.export_dataframe(
                    complete_result.data,
                    file_path,
                    metadata={
                        'query': self.last_query_sql,
                        'export_type': 'complete_results',
                        'total_rows': len(complete_result.data),
                        'export_timestamp': pd.Timestamp.now().isoformat()
                    }
                )
                
                if export_result.success:
                    file_size_mb = export_result.file_size / (1024*1024) if export_result.file_size else 0
                    self.status_bar.showMessage(
                        f"Exported all {export_result.row_count:,} rows to {Path(file_path).name} "
                        f"({file_size_mb:.1f} MB)"
                    )
                    
                    QMessageBox.information(
                        self,
                        "Export Complete",
                        f"Successfully exported complete dataset:\n"
                        f"• {export_result.row_count:,} total rows\n"
                        f"• File: {Path(file_path).name}\n"
                        f"• Size: {file_size_mb:.1f} MB"
                    )
                else:
                    self.status_bar.showMessage(f"Export failed: {export_result.error}")
                    QMessageBox.critical(self, "Export Error", export_result.error or "Unknown error")
            else:
                error_msg = complete_result.error or "Failed to retrieve complete results"
                self.status_bar.showMessage(f"Export failed: {error_msg}")
                QMessageBox.critical(self, "Export Error", error_msg)
                
        except Exception as e:
            error_msg = f"Export failed: {str(e)}"
            self.status_bar.showMessage(error_msg)
            QMessageBox.critical(self, "Export Error", error_msg)
    
    def run_query(self):
        """Execute the SQL query in the editor with enhanced error handling and metrics."""
        if not self.sql_editor or not self.db_manager:
            return
        
        sql = self.sql_editor.get_sql().strip()
        if not sql:
            self.status_bar.showMessage("No query to execute")
            return
        
        # Check if a query is already running
        if self.query_worker and self.query_worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Query Running",
                "A query is already running. Do you want to cancel it and run this query?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.query_worker.cancel()
                self.query_worker.wait()
            else:
                return
        
        self.show_progress("Preparing query...", 10)
        
        try:
            # Check if this is a large result set that needs pagination
            should_use_pagination = self._should_use_pagination(sql)
            
            if should_use_pagination:
                self._execute_query_with_pagination_bg(sql)
            else:
                self._execute_query_standard_bg(sql)
                
        except Exception as e:
            self.hide_progress()
            error_msg = f"Query execution failed: {str(e)}"
            self.status_bar.showMessage(error_msg)
            
            # Add failed query to history
            tables_used = self._extract_tables_from_sql(sql)
            self.query_history.add_query(
                sql=sql,
                execution_time=0.0,
                row_count=0,
                success=False,
                error_message=error_msg,
                tables_used=tables_used
            )
            
            self.query_executed.emit(sql, False)
            QMessageBox.critical(self, "Query Error", error_msg)
    
    def run_all_queries(self, queries: List[str], tab_index: int = 0):
        """
        Execute all queries in the list sequentially in background.
        
        Args:
            queries: List of SQL query strings to execute
            tab_index: Index of the tab these queries came from
        """
        if not self.db_manager or not queries:
            return
        
        # Check if already running
        if self.multi_query_worker and self.multi_query_worker.isRunning():
            QMessageBox.warning(
                self,
                "Queries Running",
                "Multiple queries are already being executed. Please wait for them to complete."
            )
            return
        
        total_queries = len(queries)
        logger.info(f"Starting background execution of {total_queries} queries from tab {tab_index}")
        
        # Create progress dialog
        from PyQt6.QtWidgets import QProgressDialog
        self.multi_query_progress = QProgressDialog(
            f"Executing queries...",
            "Cancel",
            0,
            total_queries,
            self
        )
        self.multi_query_progress.setWindowTitle("Running All Queries")
        self.multi_query_progress.setWindowModality(Qt.WindowModality.WindowModal)
        self.multi_query_progress.setMinimumDuration(0)
        
        # Connect cancel button
        self.multi_query_progress.canceled.connect(self._cancel_multi_query)
        
        # Create worker
        self.multi_query_worker = MultiQueryWorker(self.db_manager, queries, self)
        
        # Connect signals
        self.multi_query_worker.progress_update.connect(self._on_multi_query_progress)
        self.multi_query_worker.query_completed.connect(self._on_single_query_completed)
        self.multi_query_worker.all_queries_finished.connect(self._on_all_queries_finished)
        self.multi_query_worker.query_error.connect(self._on_single_query_error)
        
        # Start the worker
        self.multi_query_worker.start()
        self.multi_query_progress.show()
    
    def _cancel_multi_query(self):
        """Cancel multi-query execution."""
        if self.multi_query_worker:
            self.multi_query_worker.cancel()
    
    def _on_multi_query_progress(self, message: str, current: int, total: int):
        """Handle progress updates from multi-query worker."""
        if hasattr(self, 'multi_query_progress') and self.multi_query_progress:
            self.multi_query_progress.setLabelText(message)
            self.multi_query_progress.setValue(current)
    
    def _on_single_query_completed(self, result: dict):
        """Handle completion of a single query in multi-query execution."""
        # Add to history
        tables_used = self._extract_tables_from_sql(result['full_query'])
        self.query_history.add_query(
            sql=result['full_query'],
            execution_time=result['time'],
            row_count=result['rows'],
            success=True,
            tables_used=tables_used
        )
    
    def _on_single_query_error(self, query_num: int, sql: str, error_msg: str):
        """Handle error from a single query in multi-query execution."""
        # Add to history
        tables_used = self._extract_tables_from_sql(sql)
        self.query_history.add_query(
            sql=sql,
            execution_time=0.0,
            row_count=0,
            success=False,
            error_message=error_msg,
            tables_used=tables_used
        )
    
    def _on_all_queries_finished(self, summary: dict):
        """Handle completion of all queries."""
        try:
            # Close progress dialog
            if hasattr(self, 'multi_query_progress') and self.multi_query_progress:
                self.multi_query_progress.close()
                self.multi_query_progress = None
            
            successful = summary['successful']
            failed = summary['failed']
            total_rows = summary['total_rows']
            total_time = summary['total_time']
            results = summary['results']
            
            # Display the last successful query's results
            last_success = None
            for result in reversed(results):
                if result['success'] and result.get('data') is not None:
                    last_success = result
                    break
            
            if last_success and self.results_view:
                self._switch_to_standard_view()
                self.results_view.set_dataframe(last_success['data'])
            
            # Show summary dialog
            self._show_all_queries_summary_bg(results, successful, failed, total_rows, total_time)
            
            # Update status bar
            status_msg = f"Executed {successful + failed} queries: {successful} successful, {failed} failed in {total_time:.3f}s"
            self.status_bar.showMessage(status_msg)
            self.update_status_indicators()
            
        except Exception as e:
            logger.error(f"Error handling multi-query completion: {e}", exc_info=True)
        finally:
            # Clean up worker
            if self.multi_query_worker:
                self.multi_query_worker.deleteLater()
                self.multi_query_worker = None
    
    def _show_all_queries_summary_bg(self, results: List[dict], successful: int, failed: int, total_rows: int, total_time: float):
        """Show summary dialog for all queries execution (background version)."""
        from PyQt6.QtWidgets import QDialog, QTextEdit, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("All Queries Execution Summary")
        dialog.resize(700, 500)
        
        layout = QVBoxLayout()
        
        # Summary label
        summary_text = (
            f"<h3>Execution Summary</h3>"
            f"<p><b>Total Queries:</b> {successful + failed}<br>"
            f"<b>Successful:</b> {successful}<br>"
            f"<b>Failed:</b> {failed}<br>"
            f"<b>Total Rows:</b> {total_rows:,}<br>"
            f"<b>Total Time:</b> {total_time:.3f}s</p>"
        )
        
        summary_label = QLabel(summary_text)
        layout.addWidget(summary_label)
        
        # Results details
        details_text = QTextEdit()
        details_text.setReadOnly(True)
        
        details_html = "<h4>Query Details:</h4>"
        for result in results:
            status_color = "green" if result['status'] == 'Success' else "red"
            details_html += f"<p><b style='color:{status_color}'>Query {result['query_num']}: {result['status']}</b><br>"
            
            if result['status'] == 'Success':
                details_html += f"Rows: {result['rows']:,} | Time: {result['time']:.3f}s<br>"
            else:
                details_html += f"Error: {result.get('error', 'Unknown error')}<br>"
            
            details_html += f"<code>{result['query']}</code></p>"
        
        details_text.setHtml(details_html)
        layout.addWidget(details_text)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(dialog.accept)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        dialog.exec()
    
    def _show_all_queries_summary(self, results: List[dict], successful: int, failed: int, total_rows: int, total_time: float):
        """Show summary dialog for all queries execution."""
        from PyQt6.QtWidgets import QDialog, QTextEdit, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("All Queries Execution Summary")
        dialog.resize(700, 500)
        
        layout = QVBoxLayout()
        
        # Summary label
        summary_text = (
            f"<h3>Execution Summary</h3>"
            f"<p><b>Total Queries:</b> {successful + failed}<br>"
            f"<b>Successful:</b> {successful}<br>"
            f"<b>Failed:</b> {failed}<br>"
            f"<b>Total Rows:</b> {total_rows:,}<br>"
            f"<b>Total Time:</b> {total_time:.3f}s</p>"
        )
        
        summary_label = QLabel(summary_text)
        layout.addWidget(summary_label)
        
        # Results details
        details_text = QTextEdit()
        details_text.setReadOnly(True)
        
        details_content = "Query Execution Details:\n" + "=" * 80 + "\n\n"
        
        for result in results:
            query_num = result['query_num']
            status = result['status']
            query = result['query']
            
            details_content += f"Query {query_num}: {status}\n"
            details_content += f"SQL: {query}\n"
            
            if status == 'Success':
                details_content += f"Rows: {result['rows']:,}, Time: {result['time']:.3f}s\n"
            else:
                error = result.get('error', 'Unknown error')
                details_content += f"Error: {error}\n"
            
            details_content += "-" * 80 + "\n\n"
        
        details_text.setPlainText(details_content)
        layout.addWidget(details_text)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        dialog.exec()

    
    def _should_use_pagination(self, sql: str) -> bool:
        """Determine if query should use pagination based on estimated result size."""
        try:
            # Get estimated row count
            count_sql = f"SELECT COUNT(*) as estimated_count FROM ({sql}) AS count_query"
            count_result = self.db_manager.execute_query(count_sql)
            
            if count_result.success and count_result.data is not None:
                estimated_rows = count_result.data.iloc[0, 0]
                return estimated_rows > self.pagination_threshold
            
        except Exception as e:
            logger.debug(f"Could not estimate result size: {e}")
            
        # Default to standard view for unknown sizes
        return False
    
    def _execute_query_standard(self, sql: str):
        """Execute query with standard results view (DEPRECATED - use _execute_query_standard_bg)."""
        result = self.db_manager.execute_query(sql)
        
        if result.success and result.data is not None:
            self.show_progress("Processing results...", 60)
            
            # Switch to standard view
            self._switch_to_standard_view()
            
            # Display results
            if self.results_view:
                self.results_view.set_dataframe(result.data)
            
            self._finalize_query_execution(sql, result)
            
        else:
            self._handle_query_error(sql, result.error or "Query failed")
    
    def _execute_query_standard_bg(self, sql: str):
        """Execute query with standard results view in background thread."""
        # Create and configure worker
        self.query_worker = QueryWorker(self.db_manager, sql, self)
        
        # Connect signals
        self.query_worker.progress_update.connect(self._on_query_progress)
        self.query_worker.query_finished.connect(self._on_query_finished)
        self.query_worker.query_error.connect(self._on_query_error)
        
        # Start the worker
        self.query_worker.start()
        logger.info(f"Started background query execution: {sql[:100]}...")
    
    def _on_query_progress(self, message: str, percentage: int):
        """Handle progress updates from query worker."""
        self.show_progress(message, percentage)
    
    def _on_query_finished(self, result):
        """Handle successful query completion."""
        try:
            sql = self.query_worker.sql if self.query_worker else ""
            
            self.show_progress("Processing results...", 80)
            
            if result.success and result.data is not None:
                # Switch to standard view
                self._switch_to_standard_view()
                
                # Display results
                if self.results_view:
                    self.results_view.set_dataframe(result.data)
                
                self._finalize_query_execution(sql, result)
            else:
                self._handle_query_error(sql, result.error or "Query failed")
                
        except Exception as e:
            logger.error(f"Error processing query results: {e}", exc_info=True)
            self.hide_progress()
            QMessageBox.critical(self, "Error", f"Failed to process results: {str(e)}")
        finally:
            # Clean up worker
            if self.query_worker:
                self.query_worker.deleteLater()
                self.query_worker = None
    
    def _on_query_error(self, sql: str, error_message: str):
        """Handle query execution error."""
        self._handle_query_error(sql, error_message)
        
        # Clean up worker
        if self.query_worker:
            self.query_worker.deleteLater()
            self.query_worker = None
    
    def _execute_query_with_pagination(self, sql: str):
        """Execute query with paginated results view (DEPRECATED - use _execute_query_with_pagination_bg)."""
        try:
            self.show_progress("Setting up pagination...", 40)
            
            # Create paginator
            paginator = self.db_manager.create_query_paginator(sql)
            
            self.show_progress("Loading first page...", 60)
            
            # Switch to paginated view
            self._switch_to_paginated_view()
            
            # Set up paginated results
            if self.paginated_results:
                self.paginated_results.set_paginator(paginator)
            
            # Create a lightweight result for history tracking
            total_rows = paginator.get_total_rows()
            sample_data = paginator.get_sample_data()
            
            # Create fake result for tracking
            import time
            execution_time = time.time() - time.time()  # Will be updated properly
            
            fake_result = type('Result', (), {
                'success': True,
                'data': sample_data,
                'execution_time': execution_time,
                'row_count': total_rows
            })()
            
            self._finalize_query_execution(sql, fake_result, is_paginated=True)
            
        except Exception as e:
            self._handle_query_error(sql, str(e))
    
    def _execute_query_with_pagination_bg(self, sql: str):
        """Execute query with paginated results view in background thread."""
        # Create and configure worker
        self.paginated_worker = PaginatedQueryWorker(self.db_manager, sql, self)
        
        # Connect signals
        self.paginated_worker.progress_update.connect(self._on_query_progress)
        self.paginated_worker.paginator_ready.connect(self._on_paginator_ready)
        self.paginated_worker.query_error.connect(self._on_query_error)
        
        # Start the worker
        self.paginated_worker.start()
        logger.info(f"Started background paginated query setup: {sql[:100]}...")
    
    def _on_paginator_ready(self, paginator):
        """Handle paginator setup completion."""
        try:
            sql = self.paginated_worker.sql if self.paginated_worker else ""
            
            self.show_progress("Setting up paginated view...", 85)
            
            # Switch to paginated view
            self._switch_to_paginated_view()
            
            # Set up paginated results
            if self.paginated_results:
                self.paginated_results.set_paginator(paginator)
            
            # Create a lightweight result for history tracking
            total_rows = paginator.get_total_rows()
            sample_data = paginator.get_sample_data()
            
            # Create fake result for tracking
            import time
            execution_time = time.time() - time.time()  # Will be updated properly
            
            fake_result = type('Result', (), {
                'success': True,
                'data': sample_data,
                'execution_time': execution_time,
                'row_count': total_rows
            })()
            
            self._finalize_query_execution(sql, fake_result, is_paginated=True)
            
        except Exception as e:
            logger.error(f"Error setting up paginated view: {e}", exc_info=True)
            self.hide_progress()
            QMessageBox.critical(self, "Error", f"Failed to set up paginated view: {str(e)}")
        finally:
            # Clean up worker
            if self.paginated_worker:
                self.paginated_worker.deleteLater()
                self.paginated_worker = None
    
    def _switch_to_standard_view(self):
        """Switch to standard results view."""
        if self.current_results_mode != "standard":
            self.results_stack.setCurrentIndex(0)  # Standard view is index 0
            self.current_results_mode = "standard"
    
    def _switch_to_paginated_view(self):
        """Switch to paginated results view."""
        if self.current_results_mode != "paginated":
            self.results_stack.setCurrentIndex(1)  # Paginated view is index 1
            self.current_results_mode = "paginated"
    
    def _finalize_query_execution(self, sql: str, result, is_paginated: bool = False):
        """Finalize query execution with common tasks."""
        self.show_progress("Updating display...", 80)
        
        # Enhanced status message with more details
        row_count = result.row_count
        col_count = len(result.data.columns) if hasattr(result.data, 'columns') else 0
        memory_mb = result.data.memory_usage(deep=True).sum() / (1024 * 1024) if hasattr(result.data, 'memory_usage') else 0
        
        # Track last query for metrics
        self.last_query_sql = sql
        self.last_query_result = result.data
        self.last_query_time = result.execution_time
        
        # Add to query history
        tables_used = self._extract_tables_from_sql(sql)
        self.query_history.add_query(
            sql=sql,
            execution_time=result.execution_time,
            row_count=row_count,
            success=True,
            tables_used=tables_used
        )
        
        self.show_progress("Query completed", 100)
        self.hide_progress()
        
        # Enhanced status message
        pagination_info = " (paginated)" if is_paginated else ""
        status_msg = (
            f"Query executed successfully in {result.execution_time:.3f}s - "
            f"{row_count:,} rows, {col_count} columns ({memory_mb:.1f} MB){pagination_info}"
        )
        self.status_bar.showMessage(status_msg)
        
        self.query_executed.emit(sql, True)
        self.update_status_indicators()
    
    def _handle_query_error(self, sql: str, error_msg: str):
        """Handle query execution errors."""
        self.hide_progress()
        
        # Clean up the error message for display
        clean_error = error_msg.strip()
        
        # Show detailed error in status bar
        self.status_bar.showMessage(f"Query failed: {clean_error}")
        
        # Update SQL editor status if it supports it
        if hasattr(self.sql_editor, 'set_query_result_info'):
            self.sql_editor.set_query_result_info(f"Error: {clean_error}")
        
        # Add failed query to history
        tables_used = self._extract_tables_from_sql(sql)
        self.query_history.add_query(
            sql=sql,
            execution_time=0.0,
            row_count=0,
            success=False,
            error_message=clean_error,
            tables_used=tables_used
        )
        
        # Show enhanced error dialog - make sure it's visible
        self.show_query_error(sql, clean_error)
        
        self.query_executed.emit(sql, False)
    
    def show_query_error(self, sql: str, error_message: str):
        """Show enhanced query error dialog."""
        try:
            error_dialog = QueryErrorDialog(self, sql, error_message)
            error_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
            error_dialog.raise_()
            error_dialog.activateWindow()
            error_dialog.exec()
        except Exception as e:
            # Fallback to simple message box if error dialog fails
            logger.error(f"Failed to show error dialog: {e}")
            QMessageBox.critical(
                self, 
                "Query Error", 
                f"Query failed with error:\n\n{error_message}\n\nSQL:\n{sql[:200]}{'...' if len(sql) > 200 else ''}"
            )
    
    def show_query_metrics(self, sql: str, result_data, execution_time: float):
        """Show detailed query metrics dialog."""
        metrics_dialog = QueryMetricsDialog(self, sql, result_data, execution_time)
        metrics_dialog.exec()
    
    def show_last_query_metrics(self):
        """Show metrics for the last executed query."""
        if (self.last_query_result is None or 
            (hasattr(self.last_query_result, 'empty') and self.last_query_result.empty) or 
            not self.last_query_sql):
            QMessageBox.information(
                self,
                "No Query",
                "No query has been executed yet. Run a query first to see metrics."
            )
            return
            
        self.show_query_metrics(self.last_query_sql, self.last_query_result, self.last_query_time)
    
    def clear_editor(self):
        """Clear the SQL editor."""
        if self.sql_editor:
            self.sql_editor.clear()
            self.status_bar.showMessage("Editor cleared")
    
    def toggle_theme(self):
        """Toggle between light and dark theme."""
        theme_manager.toggle_theme()
        current_theme = theme_manager.get_current_theme()
        
        # Also update config preferences to stay in sync
        self.config.preferences.theme = current_theme.value
        
        # Update action text
        self.update_theme_action_text()
        
        self.status_bar.showMessage(f"Switched to {current_theme.value} theme")
    
    def update_theme_action_text(self):
        """Update theme toggle action text to show current theme."""
        current_theme = theme_manager.get_current_theme()
        if current_theme == ThemeType.LIGHT:
            self.toggle_theme_action.setText("Switch to &Dark Theme")
            self.toggle_theme_action.setStatusTip("Switch to dark theme")
        else:
            self.toggle_theme_action.setText("Switch to &Light Theme")
            self.toggle_theme_action.setStatusTip("Switch to light theme")
    
    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About LocalSQL Explorer",
            f"""
            <h3>LocalSQL Explorer {self.config.version}</h3>
            <p>A local desktop application for exploring and querying CSV, XLSX, and Parquet files using SQL.</p>
            <p>Built with PyQt6 and DuckDB.</p>
            <p><b>Author:</b> {self.config.app_name}</p>
            """
        )
    
    def on_table_selected(self, table_name: str):
        """Handle table selection in the table list."""
        if self.sql_editor:
            # Insert table name into editor at cursor
            self.sql_editor.insert_text(table_name)
        
        self.status_bar.showMessage(f"Selected table: {table_name}")
    
    def preview_table(self, table_name: str):
        """Preview a table by running a SELECT query."""
        if self.sql_editor and self.db_manager:
            preview_sql = f"SELECT * FROM {table_name} LIMIT 100"
            self.sql_editor.set_sql(preview_sql)
            self.run_query()
    
    def on_table_renamed(self, old_name: str, new_name: str):
        """Handle table rename operation."""
        if not self.db_manager:
            return
        
        self.status_bar.showMessage(f"Renaming table '{old_name}' to '{new_name}'...")
        
        try:
            success = self.db_manager.rename_table(old_name, new_name)
            
            if success:
                # Update table list
                if self.table_list:
                    metadata = self.db_manager.get_table_metadata(new_name)
                    if metadata:
                        self.table_list.remove_table(old_name)
                        self.table_list.add_table(metadata)
                
                self.status_bar.showMessage(f"Table renamed to '{new_name}'")
                self.update_status_indicators()
                
                # Show success message
                QMessageBox.information(
                    self,
                    "Rename Successful",
                    f"Table '{old_name}' has been renamed to '{new_name}'"
                )
            else:
                self.status_bar.showMessage(f"Failed to rename table '{old_name}'")
                QMessageBox.critical(
                    self,
                    "Rename Error", 
                    f"Failed to rename table '{old_name}' to '{new_name}'"
                )
                
        except Exception as e:
            error_msg = f"Rename failed: {str(e)}"
            self.status_bar.showMessage(error_msg)
            QMessageBox.critical(self, "Rename Error", error_msg)
    
    def on_table_dropped(self, table_name: str):
        """Handle table drop operation."""
        if not self.db_manager:
            return
        
        self.status_bar.showMessage(f"Dropping table '{table_name}'...")
        
        try:
            success = self.db_manager.drop_table(table_name)
            
            if success:
                # Update table list
                if self.table_list:
                    self.table_list.remove_table(table_name)
                
                # Clear results if showing this table
                if self.results_view:
                    current_sql = self.sql_editor.get_sql() if self.sql_editor else ""
                    if table_name in current_sql:
                        self.results_view.clear()
                
                self.status_bar.showMessage(f"Table '{table_name}' dropped")
                self.update_status_indicators()
                
                # Show success message
                QMessageBox.information(
                    self,
                    "Drop Successful",
                    f"Table '{table_name}' has been dropped"
                )
            else:
                self.status_bar.showMessage(f"Failed to drop table '{table_name}'")
                QMessageBox.critical(
                    self,
                    "Drop Error",
                    f"Failed to drop table '{table_name}'"
                )
                
        except Exception as e:
            error_msg = f"Drop failed: {str(e)}"
            self.status_bar.showMessage(error_msg)
            QMessageBox.critical(self, "Drop Error", error_msg)
    
    def show_column_analysis(self, table_name: str):
        """Show detailed column analysis for a table."""
        if not self.db_manager:
            return
        
        self.status_bar.showMessage(f"Analyzing columns for table '{table_name}'...")
        self.show_progress("Analyzing table columns...", 20)
        
        try:
            # Perform column analysis
            analysis = self.db_manager.analyze_table_columns(table_name)
            
            if analysis:
                self.show_progress("Preparing analysis dialog...", 80)
                
                # Import dialog class
                from .column_metadata_dialog import ColumnMetadataDialog
                
                # Show analysis dialog
                dialog = ColumnMetadataDialog(analysis, self)
                
                self.hide_progress()
                self.status_bar.showMessage(f"Column analysis completed for '{table_name}'")
                
                dialog.exec()
            else:
                self.hide_progress()
                self.status_bar.showMessage(f"Failed to analyze table '{table_name}'")
                QMessageBox.critical(
                    self,
                    "Analysis Error",
                    f"Failed to analyze columns for table '{table_name}'"
                )
                
        except Exception as e:
            self.hide_progress()
            error_msg = f"Column analysis failed: {str(e)}"
            self.status_bar.showMessage(error_msg)
            QMessageBox.critical(self, "Analysis Error", error_msg)
    
    def show_table_profiling(self, table_name: str):
        """Show comprehensive table profiling for a table."""
        if not self.db_manager:
            return
        
        self.status_bar.showMessage(f"Loading data for table profiling '{table_name}'...")
        self.show_progress("Loading table data...", 10)
        
        try:
            # Get table data for profiling
            df = self.db_manager.get_table_dataframe(table_name)
            
            if df is not None and not df.empty:
                self.show_progress("Preparing profiling dialog...", 50)
                
                # Import dialog class
                from .table_profiling_dialog import TableProfilingDialog
                
                self.hide_progress()
                self.status_bar.showMessage(f"Starting table profiling for '{table_name}'...")
                
                # Show profiling dialog
                dialog = TableProfilingDialog(df, table_name, self)
                dialog.exec()
                
                self.status_bar.showMessage(f"Table profiling completed for '{table_name}'")
            else:
                self.hide_progress()
                self.status_bar.showMessage(f"No data found in table '{table_name}'")
                QMessageBox.information(
                    self,
                    "Profiling Info",
                    f"Table '{table_name}' appears to be empty or could not be loaded."
                )
                
        except Exception as e:
            self.hide_progress()
            error_msg = f"Table profiling failed: {str(e)}"
            self.status_bar.showMessage(error_msg)
            QMessageBox.critical(self, "Profiling Error", error_msg)
    
    def load_query_from_history(self, sql: str):
        """Load a query from history into the SQL editor."""
        if self.sql_editor:
            self.sql_editor.set_sql(sql)
            self.status_bar.showMessage("Query loaded from history")
    
    def replace_query_from_history(self, old_sql: str, new_sql: str):
        """Replace current query with edited version from history."""
        if self.sql_editor:
            current_sql = self.sql_editor.get_sql()
            if current_sql == old_sql:
                self.sql_editor.set_sql(new_sql)
                self.status_bar.showMessage("Query updated from history")
    
    def restore_window_state(self):
        """Restore window state from settings."""
        # Window geometry
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            # Default size from config
            size = self.config.preferences.window_size
            self.resize(QSize(size[0], size[1]))
        
        # Window state (docks, etc.)
        window_state = self.settings.value("windowState")
        if window_state:
            self.restoreState(window_state)
        
        # Splitter state
        if self.splitter:
            splitter_state = self.settings.value("splitterState")
            if splitter_state:
                self.splitter.restoreState(splitter_state)
        
        # Restore tab state
        if self.sql_editor:
            self.sql_editor.restore_state()
    
    def save_window_state(self):
        """Save window state to settings."""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        
        if self.splitter:
            self.settings.setValue("splitterState", self.splitter.saveState())
    
    def show_optimization_settings(self):
        """Show data optimization settings dialog."""
        from .data_optimization_settings import DataOptimizationSettingsDialog
        from ..data_pagination import PaginationConfig
        
        # Create current config from main window settings
        current_config = PaginationConfig(
            default_page_size=getattr(self, 'default_page_size', 1000),
            memory_threshold_mb=getattr(self, 'memory_threshold_mb', 100.0),
            max_memory_usage_mb=getattr(self, 'max_memory_usage_mb', 1000.0)
        )
        
        dialog = DataOptimizationSettingsDialog(current_config, self)
        
        if dialog.exec() == DataOptimizationSettingsDialog.DialogCode.Accepted:
            # Apply new settings
            new_config = dialog.get_config()
            
            # Update main window settings
            self.pagination_threshold = getattr(new_config, 'pagination_threshold', 10000)
            self.default_page_size = new_config.default_page_size
            self.memory_threshold_mb = new_config.memory_threshold_mb
            self.max_memory_usage_mb = new_config.max_memory_usage_mb
            
            # Update paginated results widget if it exists
            if self.paginated_results:
                self.paginated_results.config = new_config
            
            self.status_bar.showMessage("Data optimization settings updated")
            
            # Save settings
            self.settings.setValue("pagination/threshold", self.pagination_threshold)
            self.settings.setValue("pagination/page_size", self.default_page_size)
            self.settings.setValue("memory/threshold_mb", self.memory_threshold_mb)
            self.settings.setValue("memory/max_usage_mb", self.max_memory_usage_mb)
    
    def update_schema_info(self):
        """Update schema information for auto-completion."""
        if not self.sql_editor or not self.db_manager:
            return
        
        try:
            # Get tables and their columns
            tables = {}
            for table_metadata in self.db_manager.list_tables():
                table_name = table_metadata.name
                try:
                    # Get column information
                    columns = self.db_manager.get_table_columns(table_name)
                    tables[table_name] = [col['name'] for col in columns]
                except Exception as e:
                    logger.warning(f"Could not get columns for table {table_name}: {e}")
                    tables[table_name] = []
            
            # Update SQL editor auto-completion
            self.sql_editor.update_schema_info(tables)
            logger.info(f"Updated schema info for {len(tables)} tables")
            
        except Exception as e:
            logger.error(f"Failed to update schema info: {e}")
    
    def insert_cte_template(self):
        """Insert a CTE template into the SQL editor."""
        if self.sql_editor:
            self.sql_editor.insert_cte_template()
    
    def insert_recursive_cte_template(self):
        """Insert a recursive CTE template into the SQL editor."""
        if self.sql_editor:
            self.sql_editor.insert_recursive_cte_template()
    
    def format_query(self):
        """Format the SQL query in the editor."""
        if self.sql_editor:
            self.sql_editor.format_sql()
    
    def closeEvent(self, event):
        """Handle application close event."""
        # Save window state
        self.save_window_state()
        
        # Save tab state
        if self.sql_editor:
            self.sql_editor.save_state()
        
        # Close database connection
        if self.db_manager:
            self.db_manager.close()
        
        event.accept()
    
    def _extract_tables_from_sql(self, sql: str) -> list[str]:
        """Extract table names from SQL query for history tracking."""
        import re
        
        # Simple regex to find table names after FROM and JOIN keywords
        # This is a basic implementation - could be enhanced with proper SQL parsing
        pattern = r'(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        matches = re.findall(pattern, sql, re.IGNORECASE)
        
        return list(set(matches))  # Remove duplicates


def main():
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    app.setApplicationName("LocalSQL Explorer")
    app.setApplicationVersion("0.1.0")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run application
    sys.exit(app.exec())