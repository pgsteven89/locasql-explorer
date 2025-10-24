"""
Column metadata preview dialog for LocalSQL Explorer.

This module provides:
- Column metadata popup/dialog
- Statistical summaries
- Data quality indicators
- Sample values display
"""

import logging
from typing import Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QFrame, QGridLayout, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QProgressBar, QPushButton, QScrollArea,
    QSplitter, QTabWidget, QTableWidget, QTableWidgetItem, QTextEdit,
    QVBoxLayout, QWidget
)

from ..column_analysis import ColumnMetadata, TableColumnAnalysis

logger = logging.getLogger(__name__)


class ColumnMetadataDialog(QDialog):
    """
    Dialog displaying detailed column metadata and statistics.
    
    Features:
    - Column overview with data types
    - Statistical summaries
    - Data quality indicators
    - Sample values
    """
    
    def __init__(self, analysis: TableColumnAnalysis, parent=None):
        super().__init__(parent)
        self.analysis = analysis
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle(f"Column Metadata - {self.analysis.table_name}")
        self.setModal(True)
        self.resize(900, 700)
        
        layout = QVBoxLayout(self)
        
        # Header with table summary
        header_frame = self.create_header_section()
        layout.addWidget(header_frame)
        
        # Main content area with tabs
        self.tab_widget = QTabWidget()
        
        # Overview tab
        overview_tab = self.create_overview_tab()
        self.tab_widget.addTab(overview_tab, "Overview")
        
        # Detailed analysis tab
        details_tab = self.create_details_tab()
        self.tab_widget.addTab(details_tab, "Detailed Analysis")
        
        # Data quality tab
        quality_tab = self.create_quality_tab()
        self.tab_widget.addTab(quality_tab, "Data Quality")
        
        layout.addWidget(self.tab_widget)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def create_header_section(self) -> QWidget:
        """Create header section with table summary."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QGridLayout(frame)
        
        # Table name
        name_label = QLabel(f"<h2>{self.analysis.table_name}</h2>")
        layout.addWidget(name_label, 0, 0, 1, 2)
        
        # Basic stats
        layout.addWidget(QLabel("<b>Total Rows:</b>"), 1, 0)
        layout.addWidget(QLabel(f"{self.analysis.total_rows:,}"), 1, 1)
        
        layout.addWidget(QLabel("<b>Total Columns:</b>"), 2, 0)
        layout.addWidget(QLabel(f"{self.analysis.total_columns}"), 2, 1)
        
        layout.addWidget(QLabel("<b>Memory Usage:</b>"), 3, 0)
        memory_mb = self.analysis.memory_usage / (1024 * 1024)
        layout.addWidget(QLabel(f"{memory_mb:.2f} MB"), 3, 1)
        
        # Quality score with visual indicator
        layout.addWidget(QLabel("<b>Overall Quality:</b>"), 4, 0)
        quality_widget = self.create_quality_indicator(self.analysis.overall_quality_score)
        layout.addWidget(quality_widget, 4, 1)
        
        # Analysis timestamp
        layout.addWidget(QLabel("<b>Analyzed:</b>"), 5, 0)
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(self.analysis.analysis_timestamp)
            time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            time_str = self.analysis.analysis_timestamp
        layout.addWidget(QLabel(time_str), 5, 1)
        
        return frame
    
    def create_quality_indicator(self, score: float) -> QWidget:
        """Create a visual quality score indicator."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Progress bar as quality indicator
        progress = QProgressBar()
        progress.setMinimum(0)
        progress.setMaximum(100)
        progress.setValue(int(score))
        progress.setTextVisible(True)
        progress.setFormat(f"{score:.1f}%")
        
        # Color based on score
        if score >= 80:
            color = "#28a745"  # Green
        elif score >= 60:
            color = "#ffc107"  # Yellow
        else:
            color = "#dc3545"  # Red
        
        progress.setStyleSheet(f"""
            QProgressBar::chunk {{
                background-color: {color};
            }}
        """)
        
        layout.addWidget(progress)
        return widget
    
    def create_overview_tab(self) -> QWidget:
        """Create overview tab with column summary."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Column summary table
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels([
            "Column", "Type", "Nulls", "Unique", "Quality", "Sample Values"
        ])
        
        # Populate table
        table.setRowCount(len(self.analysis.columns))
        
        for row, column in enumerate(self.analysis.columns):
            # Column name
            name_item = QTableWidgetItem(column.name)
            if column.statistics.null_percentage > 50:
                name_item.setBackground(Qt.GlobalColor.lightGray)
            table.setItem(row, 0, name_item)
            
            # Data type
            table.setItem(row, 1, QTableWidgetItem(column.data_type))
            
            # Null percentage
            null_text = f"{column.statistics.null_count} ({column.statistics.null_percentage:.1f}%)"
            null_item = QTableWidgetItem(null_text)
            if column.statistics.null_percentage > 20:
                null_item.setForeground(Qt.GlobalColor.red)
            table.setItem(row, 2, null_item)
            
            # Unique count
            unique_text = f"{column.statistics.unique_count} ({column.statistics.unique_percentage:.1f}%)"
            table.setItem(row, 3, QTableWidgetItem(unique_text))
            
            # Quality score
            quality_item = QTableWidgetItem(f"{column.quality_score:.1f}%")
            if column.quality_score < 70:
                quality_item.setForeground(Qt.GlobalColor.red)
            elif column.quality_score < 85:
                quality_item.setForeground(Qt.GlobalColor.darkYellow)
            else:
                quality_item.setForeground(Qt.GlobalColor.darkGreen)
            table.setItem(row, 4, quality_item)
            
            # Sample values
            sample_text = ", ".join(column.statistics.sample_values[:3])
            if len(sample_text) > 50:
                sample_text = sample_text[:47] + "..."
            table.setItem(row, 5, QTableWidgetItem(sample_text))
        
        # Configure table
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Column
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Type
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Nulls
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Unique
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Quality
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)           # Samples
        
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSortingEnabled(True)
        
        layout.addWidget(table)
        
        return tab
    
    def create_details_tab(self) -> QWidget:
        """Create detailed analysis tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Create splitter for column list and details
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Column list
        self.column_list = QTableWidget()
        self.column_list.setColumnCount(2)
        self.column_list.setHorizontalHeaderLabels(["Column", "Type"])
        self.column_list.setRowCount(len(self.analysis.columns))
        
        for row, column in enumerate(self.analysis.columns):
            self.column_list.setItem(row, 0, QTableWidgetItem(column.name))
            self.column_list.setItem(row, 1, QTableWidgetItem(column.data_type))
        
        self.column_list.resizeColumnsToContents()
        self.column_list.setMaximumWidth(300)
        self.column_list.currentRowChanged.connect(self.on_column_selected)
        
        # Details area
        self.details_area = QScrollArea()
        self.details_widget = QWidget()
        self.details_layout = QVBoxLayout(self.details_widget)
        self.details_area.setWidget(self.details_widget)
        self.details_area.setWidgetResizable(True)
        
        splitter.addWidget(self.column_list)
        splitter.addWidget(self.details_area)
        splitter.setSizes([300, 600])
        
        layout.addWidget(splitter)
        
        # Select first column by default
        if self.analysis.columns:
            self.column_list.setCurrentRow(0)
            self.show_column_details(self.analysis.columns[0])
        
        return tab
    
    def create_quality_tab(self) -> QWidget:
        """Create data quality tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Quality summary
        summary_group = QGroupBox("Quality Summary")
        summary_layout = QGridLayout(summary_group)
        
        # Overall score
        summary_layout.addWidget(QLabel("<b>Overall Quality Score:</b>"), 0, 0)
        score_widget = self.create_quality_indicator(self.analysis.overall_quality_score)
        summary_layout.addWidget(score_widget, 0, 1)
        
        # Column quality distribution
        high_quality = len([c for c in self.analysis.columns if c.quality_score >= 80])
        medium_quality = len([c for c in self.analysis.columns if 60 <= c.quality_score < 80])
        low_quality = len([c for c in self.analysis.columns if c.quality_score < 60])
        
        summary_layout.addWidget(QLabel("<b>High Quality Columns:</b>"), 1, 0)
        summary_layout.addWidget(QLabel(f"{high_quality} ({high_quality/len(self.analysis.columns)*100:.1f}%)"), 1, 1)
        
        summary_layout.addWidget(QLabel("<b>Medium Quality Columns:</b>"), 2, 0)
        summary_layout.addWidget(QLabel(f"{medium_quality} ({medium_quality/len(self.analysis.columns)*100:.1f}%)"), 2, 1)
        
        summary_layout.addWidget(QLabel("<b>Low Quality Columns:</b>"), 3, 0)
        summary_layout.addWidget(QLabel(f"{low_quality} ({low_quality/len(self.analysis.columns)*100:.1f}%)"), 3, 1)
        
        layout.addWidget(summary_group)
        
        # Issues table
        issues_group = QGroupBox("Quality Issues")
        issues_layout = QVBoxLayout(issues_group)
        
        issues_table = QTableWidget()
        issues_table.setColumnCount(3)
        issues_table.setHorizontalHeaderLabels(["Column", "Quality Score", "Issues"])
        
        # Collect all columns with issues
        columns_with_issues = [c for c in self.analysis.columns if c.quality_issues]
        issues_table.setRowCount(len(columns_with_issues))
        
        for row, column in enumerate(columns_with_issues):
            issues_table.setItem(row, 0, QTableWidgetItem(column.name))
            
            score_item = QTableWidgetItem(f"{column.quality_score:.1f}%")
            if column.quality_score < 70:
                score_item.setForeground(Qt.GlobalColor.red)
            issues_table.setItem(row, 1, score_item)
            
            issues_text = "; ".join(column.quality_issues)
            issues_table.setItem(row, 2, QTableWidgetItem(issues_text))
        
        issues_table.resizeColumnsToContents()
        issues_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        
        issues_layout.addWidget(issues_table)
        layout.addWidget(issues_group)
        
        return tab
    
    def on_column_selected(self, row: int):
        """Handle column selection in details tab."""
        if 0 <= row < len(self.analysis.columns):
            column = self.analysis.columns[row]
            self.show_column_details(column)
    
    def show_column_details(self, column: ColumnMetadata):
        """Show detailed information for a specific column."""
        # Clear existing details
        for i in reversed(range(self.details_layout.count())):
            child = self.details_layout.itemAt(i).widget()
            if child:
                child.deleteLater()
        
        # Column header
        header_label = QLabel(f"<h3>{column.name}</h3>")
        self.details_layout.addWidget(header_label)
        
        # Basic information
        basic_group = QGroupBox("Basic Information")
        basic_layout = QGridLayout(basic_group)
        
        basic_layout.addWidget(QLabel("<b>Data Type:</b>"), 0, 0)
        basic_layout.addWidget(QLabel(column.data_type), 0, 1)
        
        basic_layout.addWidget(QLabel("<b>Nullable:</b>"), 1, 0)
        basic_layout.addWidget(QLabel("Yes" if column.nullable else "No"), 1, 1)
        
        basic_layout.addWidget(QLabel("<b>Quality Score:</b>"), 2, 0)
        quality_widget = self.create_quality_indicator(column.quality_score)
        basic_layout.addWidget(quality_widget, 2, 1)
        
        self.details_layout.addWidget(basic_group)
        
        # Statistics
        stats_group = QGroupBox("Statistics")
        stats_layout = QGridLayout(stats_group)
        
        stats = column.statistics
        
        # Common statistics
        stats_layout.addWidget(QLabel("<b>Total Count:</b>"), 0, 0)
        stats_layout.addWidget(QLabel(f"{stats.count:,}"), 0, 1)
        
        stats_layout.addWidget(QLabel("<b>Null Count:</b>"), 1, 0)
        stats_layout.addWidget(QLabel(f"{stats.null_count:,} ({stats.null_percentage:.1f}%)"), 1, 1)
        
        stats_layout.addWidget(QLabel("<b>Unique Count:</b>"), 2, 0)
        stats_layout.addWidget(QLabel(f"{stats.unique_count:,} ({stats.unique_percentage:.1f}%)"), 2, 1)
        
        row = 3
        
        # Numeric statistics
        if stats.min_value is not None:
            stats_layout.addWidget(QLabel("<b>Min Value:</b>"), row, 0)
            stats_layout.addWidget(QLabel(f"{stats.min_value}"), row, 1)
            row += 1
            
            stats_layout.addWidget(QLabel("<b>Max Value:</b>"), row, 0)
            stats_layout.addWidget(QLabel(f"{stats.max_value}"), row, 1)
            row += 1
            
            if stats.mean is not None:
                stats_layout.addWidget(QLabel("<b>Mean:</b>"), row, 0)
                stats_layout.addWidget(QLabel(f"{stats.mean:.3f}"), row, 1)
                row += 1
                
                stats_layout.addWidget(QLabel("<b>Median:</b>"), row, 0)
                stats_layout.addWidget(QLabel(f"{stats.median:.3f}"), row, 1)
                row += 1
            
            if stats.std_dev is not None:
                stats_layout.addWidget(QLabel("<b>Std Dev:</b>"), row, 0)
                stats_layout.addWidget(QLabel(f"{stats.std_dev:.3f}"), row, 1)
                row += 1
        
        # String statistics
        if stats.min_length is not None:
            stats_layout.addWidget(QLabel("<b>Min Length:</b>"), row, 0)
            stats_layout.addWidget(QLabel(f"{stats.min_length}"), row, 1)
            row += 1
            
            stats_layout.addWidget(QLabel("<b>Max Length:</b>"), row, 0)
            stats_layout.addWidget(QLabel(f"{stats.max_length}"), row, 1)
            row += 1
            
            stats_layout.addWidget(QLabel("<b>Avg Length:</b>"), row, 0)
            stats_layout.addWidget(QLabel(f"{stats.avg_length:.1f}"), row, 1)
            row += 1
        
        # Date statistics
        if stats.min_date:
            stats_layout.addWidget(QLabel("<b>Earliest Date:</b>"), row, 0)
            stats_layout.addWidget(QLabel(stats.min_date), row, 1)
            row += 1
            
            stats_layout.addWidget(QLabel("<b>Latest Date:</b>"), row, 0)
            stats_layout.addWidget(QLabel(stats.max_date), row, 1)
            row += 1
        
        self.details_layout.addWidget(stats_group)
        
        # Sample values
        if stats.sample_values:
            samples_group = QGroupBox("Sample Values")
            samples_layout = QVBoxLayout(samples_group)
            
            samples_text = QTextEdit()
            samples_text.setPlainText("\n".join(stats.sample_values))
            samples_text.setMaximumHeight(100)
            samples_text.setReadOnly(True)
            
            samples_layout.addWidget(samples_text)
            self.details_layout.addWidget(samples_group)
        
        # Quality issues
        if column.quality_issues:
            issues_group = QGroupBox("Quality Issues")
            issues_layout = QVBoxLayout(issues_group)
            
            for issue in column.quality_issues:
                issue_label = QLabel(f"• {issue}")
                issue_label.setStyleSheet("color: #dc3545;")  # Red color
                issues_layout.addWidget(issue_label)
            
            self.details_layout.addWidget(issues_group)
        
        # Add stretch to push everything to top
        self.details_layout.addStretch()


class ColumnMetadataTooltip(QWidget):
    """
    Lightweight tooltip widget for showing column metadata.
    
    Can be used as a popup or embedded widget for quick column information.
    """
    
    def __init__(self, column: ColumnMetadata, parent=None):
        super().__init__(parent)
        self.column = column
        self.setup_ui()
        
        # Configure as tooltip
        self.setWindowFlags(Qt.WindowType.ToolTip)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
    def setup_ui(self):
        """Set up the tooltip UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Column name and type
        header = QLabel(f"<b>{self.column.name}</b> ({self.column.data_type})")
        layout.addWidget(header)
        
        # Quick stats
        stats = self.column.statistics
        
        stats_text = []
        stats_text.append(f"Rows: {stats.count:,}")
        stats_text.append(f"Nulls: {stats.null_count} ({stats.null_percentage:.1f}%)")
        stats_text.append(f"Unique: {stats.unique_count} ({stats.unique_percentage:.1f}%)")
        
        if stats.min_value is not None:
            stats_text.append(f"Range: {stats.min_value} - {stats.max_value}")
        
        if stats.min_length is not None:
            stats_text.append(f"Length: {stats.min_length} - {stats.max_length}")
        
        stats_label = QLabel(" | ".join(stats_text))
        stats_label.setStyleSheet("color: #666; font-size: 9pt;")
        layout.addWidget(stats_label)
        
        # Quality indicator
        quality_widget = QWidget()
        quality_layout = QHBoxLayout(quality_widget)
        quality_layout.setContentsMargins(0, 0, 0, 0)
        
        quality_layout.addWidget(QLabel("Quality:"))
        
        quality_bar = QProgressBar()
        quality_bar.setMinimum(0)
        quality_bar.setMaximum(100)
        quality_bar.setValue(int(self.column.quality_score))
        quality_bar.setMaximumHeight(12)
        quality_bar.setTextVisible(False)
        
        quality_layout.addWidget(quality_bar)
        quality_layout.addWidget(QLabel(f"{self.column.quality_score:.0f}%"))
        
        layout.addWidget(quality_widget)
        
        # Sample values
        if stats.sample_values:
            samples = ", ".join(stats.sample_values[:3])
            if len(samples) > 50:
                samples = samples[:47] + "..."
            samples_label = QLabel(f"Samples: {samples}")
            samples_label.setStyleSheet("color: #666; font-size: 9pt;")
            layout.addWidget(samples_label)
        
        self.setMaximumWidth(300)