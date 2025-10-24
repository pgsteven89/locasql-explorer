"""
Table profiling dialog with comprehensive reports and visualizations.

This module provides:
- Comprehensive profiling reports with multiple tabs
- Statistical visualizations and charts
- Data quality assessments
- Correlation matrices
- Actionable insights and recommendations
"""

import logging
from typing import Optional

import numpy as np
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QFrame, QGridLayout, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QProgressBar, QPushButton, QScrollArea,
    QSplitter, QTabWidget, QTableWidget, QTableWidgetItem, QTextEdit,
    QVBoxLayout, QWidget, QMessageBox
)

from ..table_profiling import TableProfiler, TableProfilingReport

logger = logging.getLogger(__name__)


class ProfilingWorker(QThread):
    """Worker thread for table profiling to avoid UI freezing."""
    
    finished = pyqtSignal(object)  # TableProfilingReport
    error = pyqtSignal(str)
    progress = pyqtSignal(str, int)
    
    def __init__(self, df, table_name, parent=None):
        super().__init__(parent)
        self.df = df
        self.table_name = table_name
        self.profiler = TableProfiler()
    
    def run(self):
        """Run profiling in background thread."""
        try:
            self.progress.emit("Starting table profiling...", 10)
            
            self.progress.emit("Analyzing column statistics...", 25)
            # The profiler will handle all the analysis
            
            self.progress.emit("Generating distribution analysis...", 50)
            
            self.progress.emit("Calculating correlations...", 70)
            
            self.progress.emit("Detecting patterns...", 85)
            
            self.progress.emit("Compiling report...", 95)
            
            report = self.profiler.profile_table(self.df, self.table_name)
            
            self.progress.emit("Profiling completed", 100)
            self.finished.emit(report)
            
        except Exception as e:
            logger.error(f"Profiling failed: {e}")
            self.error.emit(str(e))


class TableProfilingDialog(QDialog):
    """
    Comprehensive table profiling dialog with multiple analysis views.
    
    Features:
    - Overview with key metrics
    - Statistical distributions
    - Correlation analysis
    - Data quality assessment
    - Pattern detection
    - Actionable insights
    """
    
    def __init__(self, df, table_name, parent=None):
        super().__init__(parent)
        self.df = df
        self.table_name = table_name
        self.report: Optional[TableProfilingReport] = None
        
        self.setup_ui()
        self.start_profiling()
        
    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle(f"Table Profiling - {self.table_name}")
        self.setModal(True)
        self.resize(1200, 800)
        
        layout = QVBoxLayout(self)
        
        # Header
        header_frame = self.create_header_section()
        layout.addWidget(header_frame)
        
        # Progress bar (shown during profiling)
        self.progress_frame = QFrame()
        progress_layout = QVBoxLayout(self.progress_frame)
        
        self.progress_label = QLabel("Initializing profiling...")
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)
        
        layout.addWidget(self.progress_frame)
        
        # Main content (hidden initially)
        self.content_widget = QTabWidget()
        self.content_widget.setVisible(False)
        layout.addWidget(self.content_widget)
        
        # Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.button_box.rejected.connect(self.reject)
        
        # Add export button
        self.export_btn = QPushButton("Export Report")
        self.export_btn.clicked.connect(self.export_report)
        self.button_box.addButton(self.export_btn, QDialogButtonBox.ButtonRole.ActionRole)
        
        layout.addWidget(self.button_box)
    
    def create_header_section(self) -> QWidget:
        """Create header section with basic table info."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QGridLayout(frame)
        
        # Table name
        name_label = QLabel(f"<h2>{self.table_name}</h2>")
        layout.addWidget(name_label, 0, 0, 1, 2)
        
        # Basic stats
        layout.addWidget(QLabel("<b>Rows:</b>"), 1, 0)
        layout.addWidget(QLabel(f"{len(self.df):,}"), 1, 1)
        
        layout.addWidget(QLabel("<b>Columns:</b>"), 1, 2)
        layout.addWidget(QLabel(f"{len(self.df.columns)}"), 1, 3)
        
        memory_mb = self.df.memory_usage(deep=True).sum() / (1024 * 1024)
        layout.addWidget(QLabel("<b>Memory:</b>"), 1, 4)
        layout.addWidget(QLabel(f"{memory_mb:.2f} MB"), 1, 5)
        
        return frame
    
    def start_profiling(self):
        """Start profiling in background thread."""
        self.worker = ProfilingWorker(self.df, self.table_name, self)
        self.worker.finished.connect(self.on_profiling_finished)
        self.worker.error.connect(self.on_profiling_error)
        self.worker.progress.connect(self.on_profiling_progress)
        self.worker.start()
    
    def on_profiling_progress(self, message: str, progress: int):
        """Handle profiling progress updates."""
        self.progress_label.setText(message)
        self.progress_bar.setValue(progress)
        QApplication.processEvents()
    
    def on_profiling_finished(self, report: TableProfilingReport):
        """Handle profiling completion."""
        self.report = report
        
        # Hide progress and show content
        self.progress_frame.setVisible(False)
        self.content_widget.setVisible(True)
        
        # Create tabs
        self.create_overview_tab()
        self.create_distributions_tab()
        self.create_correlations_tab()
        self.create_quality_tab()
        self.create_patterns_tab()
        self.create_insights_tab()
        
        self.adjustSize()
    
    def on_profiling_error(self, error_message: str):
        """Handle profiling errors."""
        self.progress_frame.setVisible(False)
        
        error_label = QLabel(f"<h3 style='color: red;'>Profiling Failed</h3><p>{error_message}</p>")
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout = self.layout()
        layout.insertWidget(1, error_label)
    
    def create_overview_tab(self):
        """Create overview tab with summary statistics."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Quality score overview
        quality_group = QGroupBox("Data Quality Overview")
        quality_layout = QGridLayout(quality_group)
        
        quality_report = self.report.quality_report
        
        # Overall quality
        quality_layout.addWidget(QLabel("<b>Overall Quality:</b>"), 0, 0)
        quality_widget = self.create_quality_indicator(quality_report.overall_score)
        quality_layout.addWidget(quality_widget, 0, 1)
        
        # Quality dimensions
        quality_layout.addWidget(QLabel("<b>Completeness:</b>"), 1, 0)
        quality_layout.addWidget(self.create_quality_indicator(quality_report.completeness_score), 1, 1)
        
        quality_layout.addWidget(QLabel("<b>Consistency:</b>"), 2, 0)
        quality_layout.addWidget(self.create_quality_indicator(quality_report.consistency_score), 2, 1)
        
        quality_layout.addWidget(QLabel("<b>Validity:</b>"), 3, 0)
        quality_layout.addWidget(self.create_quality_indicator(quality_report.validity_score), 3, 1)
        
        quality_layout.addWidget(QLabel("<b>Uniqueness:</b>"), 4, 0)
        quality_layout.addWidget(self.create_quality_indicator(quality_report.uniqueness_score), 4, 1)
        
        layout.addWidget(quality_group)
        
        # Data types summary
        types_group = QGroupBox("Data Types Summary")
        types_layout = QGridLayout(types_group)
        
        row = 0
        for dtype, count in self.report.data_types_summary.items():
            types_layout.addWidget(QLabel(f"<b>{dtype}:</b>"), row, 0)
            types_layout.addWidget(QLabel(f"{count} columns"), row, 1)
            row += 1
        
        layout.addWidget(types_group)
        
        # Key statistics
        stats_group = QGroupBox("Key Statistics")
        stats_layout = QGridLayout(stats_group)
        
        null_percentage = (self.df.isnull().sum().sum() / self.df.size) * 100
        duplicate_rows = len(self.df) - len(self.df.drop_duplicates())
        
        stats_layout.addWidget(QLabel("<b>Missing Values:</b>"), 0, 0)
        stats_layout.addWidget(QLabel(f"{null_percentage:.1f}%"), 0, 1)
        
        stats_layout.addWidget(QLabel("<b>Duplicate Rows:</b>"), 1, 0)
        stats_layout.addWidget(QLabel(f"{duplicate_rows:,}"), 1, 1)
        
        stats_layout.addWidget(QLabel("<b>Problematic Columns:</b>"), 2, 0)
        stats_layout.addWidget(QLabel(f"{len(quality_report.problematic_columns)}"), 2, 1)
        
        layout.addWidget(stats_group)
        
        layout.addStretch()
        self.content_widget.addTab(tab, "Overview")
    
    def create_distributions_tab(self):
        """Create distributions tab with statistical analysis."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        if not self.report.distributions:
            layout.addWidget(QLabel("No numeric columns found for distribution analysis."))
            self.content_widget.addTab(tab, "Distributions")
            return
        
        # Distributions table
        table = QTableWidget()
        table.setColumnCount(8)
        table.setHorizontalHeaderLabels([
            "Column", "Mean", "Std Dev", "Min", "Max", "Skewness", "Outliers", "Distribution"
        ])
        
        table.setRowCount(len(self.report.distributions))
        
        for row, dist in enumerate(self.report.distributions):
            table.setItem(row, 0, QTableWidgetItem(dist.column_name))
            table.setItem(row, 1, QTableWidgetItem(f"{dist.mean:.3f}"))
            table.setItem(row, 2, QTableWidgetItem(f"{dist.std:.3f}"))
            table.setItem(row, 3, QTableWidgetItem(f"{dist.min_val:.3f}"))
            table.setItem(row, 4, QTableWidgetItem(f"{dist.max_val:.3f}"))
            
            skew_text = f"{dist.skewness:.3f}" if dist.skewness else "N/A"
            table.setItem(row, 5, QTableWidgetItem(skew_text))
            
            outlier_text = f"{dist.outlier_count} ({dist.outlier_percentage:.1f}%)"
            table.setItem(row, 6, QTableWidgetItem(outlier_text))
            
            # Simple distribution description
            if dist.skewness:
                if abs(dist.skewness) < 0.5:
                    dist_desc = "Normal"
                elif dist.skewness > 0.5:
                    dist_desc = "Right-skewed"
                else:
                    dist_desc = "Left-skewed"
            else:
                dist_desc = "Unknown"
            
            table.setItem(row, 7, QTableWidgetItem(dist_desc))
        
        table.resizeColumnsToContents()
        table.setSortingEnabled(True)
        
        layout.addWidget(table)
        self.content_widget.addTab(tab, "Distributions")
    
    def create_correlations_tab(self):
        """Create correlations tab with correlation matrix."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        if not self.report.correlations:
            layout.addWidget(QLabel("No correlations found (need at least 2 numeric columns)."))
            self.content_widget.addTab(tab, "Correlations")
            return
        
        correlations = self.report.correlations
        
        # Strong correlations
        if correlations.strong_correlations:
            strong_group = QGroupBox("Strong Correlations (|r| ≥ 0.7)")
            strong_layout = QVBoxLayout(strong_group)
            
            strong_table = QTableWidget()
            strong_table.setColumnCount(3)
            strong_table.setHorizontalHeaderLabels(["Column 1", "Column 2", "Correlation"])
            strong_table.setRowCount(len(correlations.strong_correlations))
            
            for row, (col1, col2, corr) in enumerate(correlations.strong_correlations):
                strong_table.setItem(row, 0, QTableWidgetItem(col1))
                strong_table.setItem(row, 1, QTableWidgetItem(col2))
                
                corr_item = QTableWidgetItem(f"{corr:.3f}")
                if abs(corr) >= 0.9:
                    corr_item.setBackground(Qt.GlobalColor.red)  # Very strong
                elif abs(corr) >= 0.7:
                    corr_item.setBackground(Qt.GlobalColor.yellow)  # Strong
                
                strong_table.setItem(row, 2, corr_item)
            
            strong_table.resizeColumnsToContents()
            strong_layout.addWidget(strong_table)
            layout.addWidget(strong_group)
        
        # Correlation matrix (simplified view)
        matrix_group = QGroupBox("Correlation Matrix")
        matrix_layout = QVBoxLayout(matrix_group)
        
        # Create simplified correlation table
        corr_matrix = correlations.correlation_matrix
        columns = list(corr_matrix.keys())
        
        matrix_table = QTableWidget()
        matrix_table.setRowCount(len(columns))
        matrix_table.setColumnCount(len(columns))
        matrix_table.setHorizontalHeaderLabels(columns)
        matrix_table.setVerticalHeaderLabels(columns)
        
        for i, col1 in enumerate(columns):
            for j, col2 in enumerate(columns):
                corr_val = corr_matrix[col1][col2]
                item = QTableWidgetItem(f"{corr_val:.2f}")
                
                # Color coding
                if abs(corr_val) >= 0.9:
                    item.setBackground(Qt.GlobalColor.darkRed)
                elif abs(corr_val) >= 0.7:
                    item.setBackground(Qt.GlobalColor.red)
                elif abs(corr_val) >= 0.5:
                    item.setBackground(Qt.GlobalColor.yellow)
                elif abs(corr_val) >= 0.3:
                    item.setBackground(Qt.GlobalColor.lightGray)
                
                matrix_table.setItem(i, j, item)
        
        matrix_table.resizeColumnsToContents()
        matrix_layout.addWidget(matrix_table)
        layout.addWidget(matrix_group)
        
        self.content_widget.addTab(tab, "Correlations")
    
    def create_quality_tab(self):
        """Create data quality tab with detailed quality assessment."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        quality_report = self.report.quality_report
        
        # Quality issues
        if quality_report.quality_issues:
            issues_group = QGroupBox("Quality Issues")
            issues_layout = QVBoxLayout(issues_group)
            
            for issue in quality_report.quality_issues:
                issue_label = QLabel(f"• {issue}")
                issue_label.setStyleSheet("color: #dc3545;")
                issues_layout.addWidget(issue_label)
            
            layout.addWidget(issues_group)
        
        # Recommendations
        if quality_report.recommendations:
            rec_group = QGroupBox("Recommendations")
            rec_layout = QVBoxLayout(rec_group)
            
            for rec in quality_report.recommendations:
                rec_label = QLabel(f"• {rec}")
                rec_label.setStyleSheet("color: #28a745;")
                rec_layout.addWidget(rec_label)
            
            layout.addWidget(rec_group)
        
        # Column quality scores
        scores_group = QGroupBox("Column Quality Scores")
        scores_layout = QVBoxLayout(scores_group)
        
        scores_table = QTableWidget()
        scores_table.setColumnCount(2)
        scores_table.setHorizontalHeaderLabels(["Column", "Quality Score"])
        scores_table.setRowCount(len(quality_report.column_quality_scores))
        
        row = 0
        for col_name, score in sorted(quality_report.column_quality_scores.items(), 
                                     key=lambda x: x[1], reverse=True):
            scores_table.setItem(row, 0, QTableWidgetItem(col_name))
            
            score_item = QTableWidgetItem(f"{score:.1f}%")
            if score >= 90:
                score_item.setForeground(Qt.GlobalColor.darkGreen)
            elif score >= 70:
                score_item.setForeground(Qt.GlobalColor.darkYellow)
            else:
                score_item.setForeground(Qt.GlobalColor.red)
            
            scores_table.setItem(row, 1, score_item)
            row += 1
        
        scores_table.resizeColumnsToContents()
        scores_table.setSortingEnabled(True)
        scores_layout.addWidget(scores_table)
        layout.addWidget(scores_group)
        
        self.content_widget.addTab(tab, "Data Quality")
    
    def create_patterns_tab(self):
        """Create patterns tab with pattern analysis."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        if not self.report.patterns:
            layout.addWidget(QLabel("No string columns found for pattern analysis."))
            self.content_widget.addTab(tab, "Patterns")
            return
        
        for pattern in self.report.patterns:
            col_group = QGroupBox(f"Column: {pattern.column_name}")
            col_layout = QGridLayout(col_group)
            
            row = 0
            
            # Special patterns
            if pattern.email_like_count > 0:
                col_layout.addWidget(QLabel("<b>Email-like values:</b>"), row, 0)
                col_layout.addWidget(QLabel(f"{pattern.email_like_count}"), row, 1)
                row += 1
            
            if pattern.phone_like_count > 0:
                col_layout.addWidget(QLabel("<b>Phone-like values:</b>"), row, 0)
                col_layout.addWidget(QLabel(f"{pattern.phone_like_count}"), row, 1)
                row += 1
            
            if pattern.url_like_count > 0:
                col_layout.addWidget(QLabel("<b>URL-like values:</b>"), row, 0)
                col_layout.addWidget(QLabel(f"{pattern.url_like_count}"), row, 1)
                row += 1
            
            # Case patterns
            col_layout.addWidget(QLabel("<b>Uppercase values:</b>"), row, 0)
            col_layout.addWidget(QLabel(f"{pattern.uppercase_count}"), row, 1)
            row += 1
            
            col_layout.addWidget(QLabel("<b>Lowercase values:</b>"), row, 0)
            col_layout.addWidget(QLabel(f"{pattern.lowercase_count}"), row, 1)
            row += 1
            
            # Length analysis
            if pattern.constant_length:
                col_layout.addWidget(QLabel("<b>Constant length:</b>"), row, 0)
                col_layout.addWidget(QLabel(f"{pattern.constant_length} characters"), row, 1)
                row += 1
            else:
                col_layout.addWidget(QLabel("<b>Length variance:</b>"), row, 0)
                col_layout.addWidget(QLabel(f"{pattern.length_variance:.2f}"), row, 1)
                row += 1
            
            # Top patterns
            if pattern.top_patterns:
                col_layout.addWidget(QLabel("<b>Common patterns:</b>"), row, 0)
                patterns_text = ", ".join([f"{pat} ({count})" for pat, count in pattern.top_patterns[:3]])
                col_layout.addWidget(QLabel(patterns_text), row, 1)
            
            layout.addWidget(col_group)
        
        layout.addStretch()
        self.content_widget.addTab(tab, "Patterns")
    
    def create_insights_tab(self):
        """Create insights tab with key findings."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Key insights
        insights_group = QGroupBox("Key Insights")
        insights_layout = QVBoxLayout(insights_group)
        
        for insight in self.report.key_insights:
            insight_label = QLabel(f"• {insight}")
            insight_label.setWordWrap(True)
            insights_layout.addWidget(insight_label)
        
        layout.addWidget(insights_group)
        
        # Summary statistics
        summary_group = QGroupBox("Summary")
        summary_layout = QGridLayout(summary_group)
        
        summary_layout.addWidget(QLabel("<b>Profiling completed:</b>"), 0, 0)
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(self.report.profiling_timestamp)
            time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            time_str = self.report.profiling_timestamp
        summary_layout.addWidget(QLabel(time_str), 0, 1)
        
        summary_layout.addWidget(QLabel("<b>Numeric columns analyzed:</b>"), 1, 0)
        summary_layout.addWidget(QLabel(f"{len(self.report.distributions)}"), 1, 1)
        
        summary_layout.addWidget(QLabel("<b>String columns analyzed:</b>"), 2, 0)
        summary_layout.addWidget(QLabel(f"{len(self.report.patterns)}"), 2, 1)
        
        if self.report.correlations:
            summary_layout.addWidget(QLabel("<b>Strong correlations found:</b>"), 3, 0)
            summary_layout.addWidget(QLabel(f"{len(self.report.correlations.strong_correlations)}"), 3, 1)
        
        layout.addWidget(summary_group)
        layout.addStretch()
        
        self.content_widget.addTab(tab, "Insights")
    
    def create_quality_indicator(self, score: float) -> QWidget:
        """Create a visual quality score indicator."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
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
    
    def export_report(self):
        """Export profiling report to file."""
        if not self.report:
            return
        
        from PyQt6.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Profiling Report",
            f"{self.table_name}_profiling_report.txt",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                self.write_report_to_file(file_path)
                QMessageBox.information(self, "Export Successful", f"Report exported to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Failed to export report: {e}")
    
    def write_report_to_file(self, file_path: str):
        """Write profiling report to text file."""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"TABLE PROFILING REPORT\n")
            f.write(f"=" * 50 + "\n\n")
            
            f.write(f"Table: {self.report.table_name}\n")
            f.write(f"Profiled: {self.report.profiling_timestamp}\n")
            f.write(f"Rows: {self.report.total_rows:,}\n")
            f.write(f"Columns: {self.report.total_columns}\n")
            f.write(f"Memory: {self.report.memory_usage / (1024*1024):.2f} MB\n\n")
            
            # Quality overview
            f.write("DATA QUALITY OVERVIEW\n")
            f.write("-" * 30 + "\n")
            quality = self.report.quality_report
            f.write(f"Overall Score: {quality.overall_score:.1f}%\n")
            f.write(f"Completeness: {quality.completeness_score:.1f}%\n")
            f.write(f"Consistency: {quality.consistency_score:.1f}%\n")
            f.write(f"Validity: {quality.validity_score:.1f}%\n")
            f.write(f"Uniqueness: {quality.uniqueness_score:.1f}%\n\n")
            
            # Key insights
            f.write("KEY INSIGHTS\n")
            f.write("-" * 20 + "\n")
            for insight in self.report.key_insights:
                f.write(f"• {insight}\n")
            f.write("\n")
            
            # Quality issues
            if quality.quality_issues:
                f.write("QUALITY ISSUES\n")
                f.write("-" * 20 + "\n")
                for issue in quality.quality_issues:
                    f.write(f"• {issue}\n")
                f.write("\n")
            
            # Recommendations
            if quality.recommendations:
                f.write("RECOMMENDATIONS\n")
                f.write("-" * 20 + "\n")
                for rec in quality.recommendations:
                    f.write(f"• {rec}\n")
                f.write("\n")
            
            # Distribution analysis
            if self.report.distributions:
                f.write("DISTRIBUTION ANALYSIS\n")
                f.write("-" * 30 + "\n")
                for dist in self.report.distributions:
                    f.write(f"\nColumn: {dist.column_name}\n")
                    f.write(f"  Mean: {dist.mean:.3f}\n")
                    f.write(f"  Std Dev: {dist.std:.3f}\n")
                    f.write(f"  Range: {dist.min_val:.3f} - {dist.max_val:.3f}\n")
                    if dist.skewness:
                        f.write(f"  Skewness: {dist.skewness:.3f}\n")
                    f.write(f"  Outliers: {dist.outlier_count} ({dist.outlier_percentage:.1f}%)\n")
            
            # Correlation analysis
            if self.report.correlations and self.report.correlations.strong_correlations:
                f.write("\nSTRONG CORRELATIONS\n")
                f.write("-" * 25 + "\n")
                for col1, col2, corr in self.report.correlations.strong_correlations:
                    f.write(f"{col1} ↔ {col2}: {corr:.3f}\n")
            
            f.write(f"\nReport generated by LocalSQL Explorer")


class QuickProfilingWidget(QWidget):
    """
    Lightweight profiling widget for quick table insights.
    
    Can be embedded in other dialogs or used as a standalone widget.
    """
    
    def __init__(self, df, table_name, parent=None):
        super().__init__(parent)
        self.df = df
        self.table_name = table_name
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the widget UI."""
        layout = QVBoxLayout(self)
        
        # Quick stats
        stats_group = QGroupBox("Quick Profile")
        stats_layout = QGridLayout(stats_group)
        
        # Basic info
        rows, cols = self.df.shape
        memory_mb = self.df.memory_usage(deep=True).sum() / (1024 * 1024)
        
        stats_layout.addWidget(QLabel("<b>Dimensions:</b>"), 0, 0)
        stats_layout.addWidget(QLabel(f"{rows:,} × {cols}"), 0, 1)
        
        stats_layout.addWidget(QLabel("<b>Memory:</b>"), 1, 0)
        stats_layout.addWidget(QLabel(f"{memory_mb:.1f} MB"), 1, 1)
        
        # Missing values
        missing_pct = (self.df.isnull().sum().sum() / self.df.size) * 100
        stats_layout.addWidget(QLabel("<b>Missing:</b>"), 2, 0)
        stats_layout.addWidget(QLabel(f"{missing_pct:.1f}%"), 2, 1)
        
        # Duplicates
        duplicates = len(self.df) - len(self.df.drop_duplicates())
        stats_layout.addWidget(QLabel("<b>Duplicates:</b>"), 3, 0)
        stats_layout.addWidget(QLabel(f"{duplicates:,}"), 3, 1)
        
        # Data types
        numeric_cols = len(self.df.select_dtypes(include=[np.number]).columns)
        text_cols = len(self.df.select_dtypes(include=['object']).columns)
        
        stats_layout.addWidget(QLabel("<b>Numeric cols:</b>"), 4, 0)
        stats_layout.addWidget(QLabel(f"{numeric_cols}"), 4, 1)
        
        stats_layout.addWidget(QLabel("<b>Text cols:</b>"), 5, 0)
        stats_layout.addWidget(QLabel(f"{text_cols}"), 5, 1)
        
        layout.addWidget(stats_group)
        
        # Full profiling button
        full_btn = QPushButton("Full Profiling Report")
        full_btn.clicked.connect(self.show_full_profiling)
        layout.addWidget(full_btn)
    
    def show_full_profiling(self):
        """Show full profiling dialog."""
        dialog = TableProfilingDialog(self.df, self.table_name, self)
        dialog.exec()