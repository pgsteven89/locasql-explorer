"""
Excel Sheet Selection Dialog - UI component for selecting multiple Excel worksheets.

This module provides the ExcelSheetSelectionDialog class which allows users to:
- View all available worksheets in an Excel file
- Select one, multiple, or all worksheets for import
- Preview worksheet data and metadata
- Configure table naming for imported sheets
"""

import logging
from pathlib import Path
from typing import List, Optional, Tuple, Union

import pandas as pd
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QCheckBox, QTextEdit,
    QTableWidget, QTableWidgetItem, QSplitter, QGroupBox,
    QFormLayout, QLineEdit, QProgressBar, QMessageBox,
    QHeaderView
)

from ..importer import SheetInfo

logger = logging.getLogger(__name__)


class SheetListItem(QListWidgetItem):
    """Custom list item that holds sheet information."""
    
    def __init__(self, sheet_info: SheetInfo):
        self.sheet_info = sheet_info
        
        # Create display text with metadata
        if sheet_info.is_empty:
            display_text = f"📄 {sheet_info.name} (Empty)"
        else:
            display_text = f"📊 {sheet_info.name} ({sheet_info.row_count} rows × {sheet_info.column_count} cols)"
        
        super().__init__(display_text)
        
        # Make item checkable
        self.setFlags(self.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        self.setCheckState(Qt.CheckState.Unchecked)
        
        # Disable empty sheets by default
        if sheet_info.is_empty:
            self.setFlags(self.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            font = self.font()
            font.setItalic(True)
            self.setFont(font)


class ExcelSheetSelectionDialog(QDialog):
    """
    Dialog for selecting which Excel worksheets to import.
    
    Features:
    - List of all worksheets with metadata
    - Checkboxes for multiple selection
    - Data preview for selected sheets
    - Table naming configuration
    - Select All/None buttons
    """
    
    def __init__(self, file_path: str, sheet_infos: List[SheetInfo], parent=None):
        super().__init__(parent)
        
        self.file_path = Path(file_path)
        self.sheet_infos = sheet_infos
        self.selected_sheets = []
        
        self.setWindowTitle(f"Import Excel Worksheets - {self.file_path.name}")
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)
        
        self.init_ui()
        self.populate_sheet_list()
        
        # Auto-select first non-empty sheet
        self.auto_select_default_sheet()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Title and file info
        title_label = QLabel(f"Select worksheets to import from:")
        title_label.setFont(QFont("", 10, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        file_info_label = QLabel(f"📁 {self.file_path.name} ({len(self.sheet_infos)} worksheets)")
        file_info_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(file_info_label)
        
        # Main content splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Left side: Sheet list and controls
        left_panel = QGroupBox("Available Worksheets")
        left_layout = QVBoxLayout(left_panel)
        
        # Selection controls
        controls_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self.select_all_sheets)
        controls_layout.addWidget(self.select_all_btn)
        
        self.select_none_btn = QPushButton("Select None")
        self.select_none_btn.clicked.connect(self.select_no_sheets)
        controls_layout.addWidget(self.select_none_btn)
        
        self.smart_select_btn = QPushButton("Select Non-Empty")
        self.smart_select_btn.clicked.connect(self.select_non_empty_sheets)
        controls_layout.addWidget(self.smart_select_btn)
        
        controls_layout.addStretch()
        left_layout.addLayout(controls_layout)
        
        # Sheet list
        self.sheet_list = QListWidget()
        self.sheet_list.itemChanged.connect(self.on_sheet_selection_changed)
        self.sheet_list.itemSelectionChanged.connect(self.on_sheet_highlight_changed)
        left_layout.addWidget(self.sheet_list)
        
        splitter.addWidget(left_panel)
        
        # Right side: Preview and naming
        right_panel = QGroupBox("Preview & Configuration")
        right_layout = QVBoxLayout(right_panel)
        
        # Sheet info display
        self.info_label = QLabel("Select a worksheet to preview")
        self.info_label.setStyleSheet("font-weight: bold; color: #0066cc; margin: 5px;")
        right_layout.addWidget(self.info_label)
        
        # Preview table
        self.preview_table = QTableWidget()
        self.preview_table.setMaximumHeight(200)
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        right_layout.addWidget(self.preview_table)
        
        # Table naming configuration
        naming_group = QGroupBox("Table Naming")
        naming_layout = QFormLayout(naming_group)
        
        self.base_name_edit = QLineEdit(self.file_path.stem)
        naming_layout.addRow("Base name:", self.base_name_edit)
        
        self.naming_preview = QTextEdit()
        self.naming_preview.setMaximumHeight(100)
        self.naming_preview.setReadOnly(True)
        naming_layout.addRow("Tables to create:", self.naming_preview)
        
        right_layout.addWidget(naming_group)
        
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([400, 600])
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.import_btn = QPushButton("Import Selected Sheets")
        self.import_btn.clicked.connect(self.accept)
        self.import_btn.setEnabled(False)
        button_layout.addWidget(self.import_btn)
        
        layout.addLayout(button_layout)
    
    def populate_sheet_list(self):
        """Populate the sheet list with available worksheets."""
        for sheet_info in self.sheet_infos:
            item = SheetListItem(sheet_info)
            self.sheet_list.addItem(item)
    
    def auto_select_default_sheet(self):
        """Auto-select the first non-empty sheet."""
        for i in range(self.sheet_list.count()):
            item = self.sheet_list.item(i)
            if isinstance(item, SheetListItem) and not item.sheet_info.is_empty:
                item.setCheckState(Qt.CheckState.Checked)
                self.sheet_list.setCurrentItem(item)
                break
    
    def on_sheet_selection_changed(self, item):
        """Handle when a sheet's checkbox state changes."""
        if isinstance(item, SheetListItem):
            self.update_selection_ui()
        
        # Connect base name changes to naming preview
        self.base_name_edit.textChanged.connect(self.update_naming_preview)
    
    def on_sheet_highlight_changed(self):
        """Handle when the highlighted sheet changes."""
        current_item = self.sheet_list.currentItem()
        if isinstance(current_item, SheetListItem):
            self.show_sheet_preview(current_item.sheet_info)
    
    def show_sheet_preview(self, sheet_info: SheetInfo):
        """Display preview of the selected sheet."""
        # Update info label
        if sheet_info.is_empty:
            self.info_label.setText(f"📄 {sheet_info.name} - No data to preview")
        else:
            self.info_label.setText(f"📊 {sheet_info.name} - {sheet_info.row_count} rows × {sheet_info.column_count} columns")
        
        # Clear previous preview
        self.preview_table.clear()
        self.preview_table.setRowCount(0)
        self.preview_table.setColumnCount(0)
        
        # Show sample data if available
        if sheet_info.sample_data is not None and not sheet_info.sample_data.empty:
            df = sheet_info.sample_data
            
            # Set up table dimensions
            self.preview_table.setRowCount(len(df))
            self.preview_table.setColumnCount(len(df.columns))
            
            # Set headers
            self.preview_table.setHorizontalHeaderLabels([str(col) for col in df.columns])
            
            # Populate data
            for row in range(len(df)):
                for col in range(len(df.columns)):
                    value = df.iloc[row, col]
                    # Handle various data types
                    if pd.isna(value):
                        display_value = ""
                    else:
                        display_value = str(value)
                    
                    item = QTableWidgetItem(display_value)
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.preview_table.setItem(row, col, item)
        
        # Update table naming preview
        self.update_naming_preview()
    
    def update_selection_ui(self):
        """Update UI elements based on current selection."""
        selected_count = 0
        self.selected_sheets = []
        
        for i in range(self.sheet_list.count()):
            item = self.sheet_list.item(i)
            if isinstance(item, SheetListItem) and item.checkState() == Qt.CheckState.Checked:
                selected_count += 1
                self.selected_sheets.append(item.sheet_info)
        
        # Update import button
        self.import_btn.setEnabled(selected_count > 0)
        if selected_count == 0:
            self.import_btn.setText("Import Selected Sheets")
        elif selected_count == 1:
            self.import_btn.setText("Import 1 Sheet")
        else:
            self.import_btn.setText(f"Import {selected_count} Sheets")
        
        # Update naming preview
        self.update_naming_preview()
    
    def update_naming_preview(self):
        """Update the table naming preview."""
        base_name = self.base_name_edit.text().strip() or "unnamed"
        
        if not self.selected_sheets:
            self.naming_preview.setText("No sheets selected")
            return
        
        preview_text = []
        for sheet_info in self.selected_sheets:
            sanitized_base = self._sanitize_name(base_name)
            sanitized_sheet = self._sanitize_name(sheet_info.name)
            table_name = f"{sanitized_base}_{sanitized_sheet}"
            preview_text.append(f"• {table_name} (from '{sheet_info.name}')")
        
        self.naming_preview.setText("\n".join(preview_text))
    
    def select_all_sheets(self):
        """Select all available (non-empty) sheets."""
        for i in range(self.sheet_list.count()):
            item = self.sheet_list.item(i)
            if isinstance(item, SheetListItem) and not item.sheet_info.is_empty:
                item.setCheckState(Qt.CheckState.Checked)
    
    def select_no_sheets(self):
        """Deselect all sheets."""
        for i in range(self.sheet_list.count()):
            item = self.sheet_list.item(i)
            if isinstance(item, SheetListItem):
                item.setCheckState(Qt.CheckState.Unchecked)
    
    def select_non_empty_sheets(self):
        """Select only non-empty sheets."""
        for i in range(self.sheet_list.count()):
            item = self.sheet_list.item(i)
            if isinstance(item, SheetListItem):
                if not item.sheet_info.is_empty:
                    item.setCheckState(Qt.CheckState.Checked)
                else:
                    item.setCheckState(Qt.CheckState.Unchecked)
    
    def get_selected_sheet_names(self) -> List[str]:
        """Get the names of selected sheets."""
        return [sheet_info.name for sheet_info in self.selected_sheets]
    
    def get_base_table_name(self) -> str:
        """Get the base table name from user input."""
        return self.base_name_edit.text().strip() or self.file_path.stem
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize a name for SQL table usage."""
        import re
        sanitized = re.sub(r'[^\w]', '_', name)
        sanitized = re.sub(r'_+', '_', sanitized)
        sanitized = sanitized.strip('_')
        if not sanitized:
            sanitized = 'unnamed'
        return sanitized.lower()
    
    def accept(self):
        """Override accept to validate selection."""
        if not self.selected_sheets:
            QMessageBox.warning(
                self, 
                "No Sheets Selected", 
                "Please select at least one worksheet to import."
            )
            return
        
        base_name = self.get_base_table_name()
        if not base_name:
            QMessageBox.warning(
                self,
                "Invalid Base Name",
                "Please provide a valid base name for the tables."
            )
            return
        
        super().accept()