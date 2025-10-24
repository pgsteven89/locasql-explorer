"""
Enhanced export dialog for LocalSQL Explorer.

Provides advanced export options including:
- Format-specific settings (CSV delimiters, Excel sheet names, etc.)
- Export options (headers, index, encoding)
- Preview of export settings
- File format recommendations
"""

import logging
from pathlib import Path
from typing import Dict, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QComboBox, QCheckBox, QSpinBox, QPushButton,
    QFileDialog, QMessageBox, QTabWidget, QWidget, QTextEdit,
    QDialogButtonBox
)

from ..exporter import ExportOptions, ResultExporter

logger = logging.getLogger(__name__)


class ExportOptionsDialog(QDialog):
    """Enhanced export dialog with advanced options."""
    
    def __init__(self, parent=None, suggested_filename: str = "results"):
        super().__init__(parent)
        self.suggested_filename = suggested_filename
        self.export_options = ExportOptions()
        self.selected_file_path = ""
        self.selected_format = "csv"
        
        self.init_ui()
        self.connect_signals()
        
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Export Results")
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # File selection section
        file_group = self.create_file_selection_group()
        layout.addWidget(file_group)
        
        # Export options tabs
        self.options_tabs = QTabWidget()
        self.create_options_tabs()
        layout.addWidget(self.options_tabs)
        
        # Preview section
        preview_group = self.create_preview_group()
        layout.addWidget(preview_group)
        
        # Dialog buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        
        # Update initial state
        self.update_file_format("csv")
        
    def create_file_selection_group(self) -> QGroupBox:
        """Create file selection group."""
        group = QGroupBox("Output File")
        layout = QVBoxLayout(group)
        
        # File path selection
        file_layout = QHBoxLayout()
        
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Select output file...")
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.browse_file)
        
        file_layout.addWidget(self.file_path_edit)
        file_layout.addWidget(self.browse_button)
        layout.addLayout(file_layout)
        
        # Format selection
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Format:"))
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["CSV", "Excel (XLSX)", "Parquet"])
        self.format_combo.setCurrentText("CSV")
        self.format_combo.currentTextChanged.connect(self.on_format_changed)
        
        format_layout.addWidget(self.format_combo)
        format_layout.addStretch()
        layout.addLayout(format_layout)
        
        return group
        
    def create_options_tabs(self):
        """Create tabbed options interface."""
        # General options tab
        self.general_tab = QWidget()
        self.create_general_options_tab()
        self.options_tabs.addTab(self.general_tab, "General")
        
        # CSV options tab
        self.csv_tab = QWidget()
        self.create_csv_options_tab()
        self.options_tabs.addTab(self.csv_tab, "CSV Options")
        
        # Excel options tab
        self.excel_tab = QWidget()
        self.create_excel_options_tab()
        self.options_tabs.addTab(self.excel_tab, "Excel Options")
        
    def create_general_options_tab(self):
        """Create general export options."""
        layout = QFormLayout(self.general_tab)
        
        # Include headers
        self.include_header_cb = QCheckBox("Include column headers")
        self.include_header_cb.setChecked(True)
        layout.addRow("Headers:", self.include_header_cb)
        
        # Include index
        self.include_index_cb = QCheckBox("Include row index")
        self.include_index_cb.setChecked(False)
        layout.addRow("Index:", self.include_index_cb)
        
        # Encoding
        self.encoding_combo = QComboBox()
        self.encoding_combo.addItems(["utf-8", "utf-16", "latin-1", "cp1252"])
        self.encoding_combo.setCurrentText("utf-8")
        layout.addRow("Encoding:", self.encoding_combo)
        
        # Overwrite existing
        self.overwrite_cb = QCheckBox("Overwrite existing file")
        self.overwrite_cb.setChecked(True)
        layout.addRow("File handling:", self.overwrite_cb)
        
    def create_csv_options_tab(self):
        """Create CSV-specific options."""
        layout = QFormLayout(self.csv_tab)
        
        # Delimiter
        self.delimiter_combo = QComboBox()
        self.delimiter_combo.setEditable(True)
        self.delimiter_combo.addItems([",", ";", "\t", "|"])
        self.delimiter_combo.setCurrentText(",")
        layout.addRow("Delimiter:", self.delimiter_combo)
        
        # Line terminator
        self.line_terminator_combo = QComboBox()
        self.line_terminator_combo.addItems(["\\n (Unix)", "\\r\\n (Windows)", "\\r (Mac)"])
        self.line_terminator_combo.setCurrentText("\\n (Unix)")
        layout.addRow("Line endings:", self.line_terminator_combo)
        
        # Quote character
        self.quote_char_combo = QComboBox()
        self.quote_char_combo.setEditable(True)
        self.quote_char_combo.addItems(['\"', "'", "None"])
        self.quote_char_combo.setCurrentText('\"')
        layout.addRow("Quote character:", self.quote_char_combo)
        
    def create_excel_options_tab(self):
        """Create Excel-specific options."""
        layout = QFormLayout(self.excel_tab)
        
        # Sheet name
        self.sheet_name_edit = QLineEdit("Results")
        layout.addRow("Sheet name:", self.sheet_name_edit)
        
        # Start row/column
        self.start_row_spin = QSpinBox()
        self.start_row_spin.setRange(1, 1000)
        self.start_row_spin.setValue(1)
        layout.addRow("Start row:", self.start_row_spin)
        
        self.start_col_spin = QSpinBox()
        self.start_col_spin.setRange(1, 100)
        self.start_col_spin.setValue(1)
        layout.addRow("Start column:", self.start_col_spin)
        
        # Engine
        self.excel_engine_combo = QComboBox()
        self.excel_engine_combo.addItems(["openpyxl", "xlsxwriter"])
        self.excel_engine_combo.setCurrentText("openpyxl")
        layout.addRow("Engine:", self.excel_engine_combo)
        
    def create_preview_group(self) -> QGroupBox:
        """Create export preview section."""
        group = QGroupBox("Export Summary")
        layout = QVBoxLayout(group)
        
        self.preview_text = QTextEdit()
        self.preview_text.setMaximumHeight(100)
        self.preview_text.setReadOnly(True)
        layout.addWidget(self.preview_text)
        
        return group
        
    def connect_signals(self):
        """Connect UI signals."""
        # Update preview when options change
        self.include_header_cb.toggled.connect(self.update_preview)
        self.include_index_cb.toggled.connect(self.update_preview)
        self.encoding_combo.currentTextChanged.connect(self.update_preview)
        self.delimiter_combo.currentTextChanged.connect(self.update_preview)
        self.sheet_name_edit.textChanged.connect(self.update_preview)
        
        # Update file path when format changes
        self.file_path_edit.textChanged.connect(self.update_preview)
        
    def browse_file(self):
        """Open file browser for output selection."""
        format_filters = {
            "csv": "CSV Files (*.csv)",
            "xlsx": "Excel Files (*.xlsx)",
            "parquet": "Parquet Files (*.parquet)"
        }
        
        file_filter = format_filters.get(self.selected_format, "All Files (*)")
        all_filters = ";;".join(format_filters.values()) + ";;All Files (*)"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Export File",
            f"{self.suggested_filename}.{self.selected_format}",
            all_filters
        )
        
        if file_path:
            self.file_path_edit.setText(file_path)
            self.selected_file_path = file_path
            
            # Update format based on extension
            path = Path(file_path)
            if path.suffix.lower() in ['.csv']:
                self.format_combo.setCurrentText("CSV")
            elif path.suffix.lower() in ['.xlsx', '.xls']:
                self.format_combo.setCurrentText("Excel (XLSX)")
            elif path.suffix.lower() in ['.parquet', '.pq']:
                self.format_combo.setCurrentText("Parquet")
                
    def on_format_changed(self, format_text: str):
        """Handle format selection change."""
        format_map = {
            "CSV": "csv",
            "Excel (XLSX)": "xlsx", 
            "Parquet": "parquet"
        }
        
        self.selected_format = format_map.get(format_text, "csv")
        self.update_file_format(self.selected_format)
        self.update_preview()
        
    def update_file_format(self, format_type: str):
        """Update UI based on selected format."""
        # Enable/disable relevant tabs
        self.options_tabs.setTabEnabled(1, format_type == "csv")      # CSV tab
        self.options_tabs.setTabEnabled(2, format_type == "xlsx")     # Excel tab
        
        # Update file extension if path is set
        if self.file_path_edit.text():
            path = Path(self.file_path_edit.text())
            new_path = path.with_suffix(f".{format_type}")
            self.file_path_edit.setText(str(new_path))
            
    def update_preview(self):
        """Update the export preview."""
        options = self.get_export_options()
        file_path = self.file_path_edit.text() or f"{self.suggested_filename}.{self.selected_format}"
        
        preview_lines = [
            f"Output file: {file_path}",
            f"Format: {self.selected_format.upper()}",
            f"Include headers: {'Yes' if options.include_header else 'No'}",
            f"Include index: {'Yes' if options.include_index else 'No'}",
            f"Encoding: {options.encoding}"
        ]
        
        if self.selected_format == "csv":
            preview_lines.append(f"Delimiter: '{options.delimiter}'")
        elif self.selected_format == "xlsx":
            preview_lines.append(f"Sheet name: {options.sheet_name}")
            
        self.preview_text.setPlainText("\n".join(preview_lines))
        
    def get_export_options(self) -> ExportOptions:
        """Get current export options from UI."""
        options = ExportOptions()
        
        # General options
        options.include_header = self.include_header_cb.isChecked()
        options.include_index = self.include_index_cb.isChecked()
        options.encoding = self.encoding_combo.currentText()
        options.overwrite = self.overwrite_cb.isChecked()
        
        # CSV options
        if self.selected_format == "csv":
            delimiter_text = self.delimiter_combo.currentText()
            if delimiter_text == "\\t":
                options.delimiter = "\t"
            else:
                options.delimiter = delimiter_text
                
        # Excel options
        if self.selected_format == "xlsx":
            options.sheet_name = self.sheet_name_edit.text() or "Results"
            
        return options
        
    def get_file_path(self) -> str:
        """Get the selected file path."""
        return self.file_path_edit.text()
        
    def get_file_format(self) -> str:
        """Get the selected file format."""
        return self.selected_format
        
    def accept(self):
        """Validate and accept the dialog."""
        if not self.file_path_edit.text():
            QMessageBox.warning(self, "Missing File", "Please select an output file.")
            return
            
        # Check if file exists and overwrite is disabled
        file_path = Path(self.file_path_edit.text())
        if file_path.exists() and not self.overwrite_cb.isChecked():
            reply = QMessageBox.question(
                self,
                "File Exists",
                f"The file '{file_path.name}' already exists. Do you want to overwrite it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
                
        super().accept()