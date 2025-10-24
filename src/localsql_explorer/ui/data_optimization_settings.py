"""
Large data optimization settings dialog.

This module provides a dialog for configuring:
- Pagination thresholds
- Memory limits
- Performance settings
- Optimization preferences
"""

import logging
from typing import Dict, Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QSpinBox, QDoubleSpinBox, QCheckBox, QComboBox,
    QSlider, QFrame, QPushButton, QTabWidget, QWidget, QFormLayout,
    QMessageBox
)

from ..data_pagination import PaginationConfig

logger = logging.getLogger(__name__)


class DataOptimizationSettingsDialog(QDialog):
    """
    Dialog for configuring large data optimization settings.
    
    Features:
    - Pagination configuration
    - Memory management settings
    - Performance tuning options
    - Import/export settings
    """
    
    def __init__(self, current_config: PaginationConfig = None, parent=None):
        super().__init__(parent)
        
        self.config = current_config or PaginationConfig()
        self.original_config = PaginationConfig(
            default_page_size=self.config.default_page_size,
            max_page_size=self.config.max_page_size,
            min_page_size=self.config.min_page_size,
            memory_threshold_mb=self.config.memory_threshold_mb,
            warning_threshold_mb=self.config.warning_threshold_mb,
            chunk_size=self.config.chunk_size,
            max_memory_usage_mb=self.config.max_memory_usage_mb,
            progress_update_interval=self.config.progress_update_interval
        )
        
        self.setup_ui()
        self.load_settings()
        
    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Data Optimization Settings")
        self.setModal(True)
        self.resize(500, 600)
        
        layout = QVBoxLayout(self)
        
        # Create tabs
        tabs = QTabWidget()
        
        # Pagination tab
        pagination_tab = self.create_pagination_tab()
        tabs.addTab(pagination_tab, "Pagination")
        
        # Memory tab
        memory_tab = self.create_memory_tab()
        tabs.addTab(memory_tab, "Memory")
        
        # Performance tab
        performance_tab = self.create_performance_tab()
        tabs.addTab(performance_tab, "Performance")
        
        layout.addWidget(tabs)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.reset_btn = QPushButton("Reset to Defaults")
        self.reset_btn.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(self.reset_btn)
        
        button_layout.addStretch()
        
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Apply
        )
        self.button_box.accepted.connect(self.accept_changes)
        self.button_box.rejected.connect(self.reject)
        self.button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply_changes)
        
        button_layout.addWidget(self.button_box)
        layout.addLayout(button_layout)
    
    def create_pagination_tab(self) -> QWidget:
        """Create pagination settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Page size settings
        page_size_group = QGroupBox("Page Size Configuration")
        page_size_layout = QFormLayout(page_size_group)
        
        self.default_page_size_spin = QSpinBox()
        self.default_page_size_spin.setRange(100, 50000)
        self.default_page_size_spin.setSuffix(" rows")
        page_size_layout.addRow("Default page size:", self.default_page_size_spin)
        
        self.min_page_size_spin = QSpinBox()
        self.min_page_size_spin.setRange(10, 1000)
        self.min_page_size_spin.setSuffix(" rows")
        page_size_layout.addRow("Minimum page size:", self.min_page_size_spin)
        
        self.max_page_size_spin = QSpinBox()
        self.max_page_size_spin.setRange(1000, 100000)
        self.max_page_size_spin.setSuffix(" rows")
        page_size_layout.addRow("Maximum page size:", self.max_page_size_spin)
        
        layout.addWidget(page_size_group)
        
        # Automation settings
        auto_group = QGroupBox("Automatic Pagination")
        auto_layout = QFormLayout(auto_group)
        
        self.pagination_threshold_spin = QSpinBox()
        self.pagination_threshold_spin.setRange(1000, 1000000)
        self.pagination_threshold_spin.setSuffix(" rows")
        auto_layout.addRow("Enable pagination when result exceeds:", self.pagination_threshold_spin)
        
        self.auto_optimize_cb = QCheckBox("Automatically optimize page size based on data")
        auto_layout.addRow(self.auto_optimize_cb)
        
        layout.addWidget(auto_group)
        
        # Cache settings
        cache_group = QGroupBox("Page Caching")
        cache_layout = QFormLayout(cache_group)
        
        self.cache_size_spin = QSpinBox()
        self.cache_size_spin.setRange(1, 20)
        self.cache_size_spin.setSuffix(" pages")
        cache_layout.addRow("Cache size:", self.cache_size_spin)
        
        layout.addWidget(cache_group)
        layout.addStretch()
        
        return widget
    
    def create_memory_tab(self) -> QWidget:
        """Create memory management settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Memory thresholds
        threshold_group = QGroupBox("Memory Thresholds")
        threshold_layout = QFormLayout(threshold_group)
        
        self.memory_threshold_spin = QDoubleSpinBox()
        self.memory_threshold_spin.setRange(10.0, 2000.0)
        self.memory_threshold_spin.setDecimals(1)
        self.memory_threshold_spin.setSuffix(" MB")
        threshold_layout.addRow("Normal threshold:", self.memory_threshold_spin)
        
        self.warning_threshold_spin = QDoubleSpinBox()
        self.warning_threshold_spin.setRange(50.0, 5000.0)
        self.warning_threshold_spin.setDecimals(1)
        self.warning_threshold_spin.setSuffix(" MB")
        threshold_layout.addRow("Warning threshold:", self.warning_threshold_spin)
        
        self.max_memory_spin = QDoubleSpinBox()
        self.max_memory_spin.setRange(100.0, 10000.0)
        self.max_memory_spin.setDecimals(1)
        self.max_memory_spin.setSuffix(" MB")
        threshold_layout.addRow("Maximum memory usage:", self.max_memory_spin)
        
        layout.addWidget(threshold_group)
        
        # Memory monitoring
        monitoring_group = QGroupBox("Memory Monitoring")
        monitoring_layout = QFormLayout(monitoring_group)
        
        self.monitor_memory_cb = QCheckBox("Enable real-time memory monitoring")
        monitoring_layout.addRow(self.monitor_memory_cb)
        
        self.show_memory_warnings_cb = QCheckBox("Show memory usage warnings")
        monitoring_layout.addRow(self.show_memory_warnings_cb)
        
        self.auto_clear_cache_cb = QCheckBox("Automatically clear cache when memory is low")
        monitoring_layout.addRow(self.auto_clear_cache_cb)
        
        layout.addWidget(monitoring_group)
        layout.addStretch()
        
        return widget
    
    def create_performance_tab(self) -> QWidget:
        """Create performance settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Chunk processing
        chunk_group = QGroupBox("Chunk Processing")
        chunk_layout = QFormLayout(chunk_group)
        
        self.chunk_size_spin = QSpinBox()
        self.chunk_size_spin.setRange(1000, 100000)
        self.chunk_size_spin.setSuffix(" rows")
        chunk_layout.addRow("Chunk size for large operations:", self.chunk_size_spin)
        
        layout.addWidget(chunk_group)
        
        # Progress reporting
        progress_group = QGroupBox("Progress Reporting")
        progress_layout = QFormLayout(progress_group)
        
        self.progress_interval_spin = QSpinBox()
        self.progress_interval_spin.setRange(100, 10000)
        self.progress_interval_spin.setSuffix(" rows")
        progress_layout.addRow("Update progress every:", self.progress_interval_spin)
        
        self.show_detailed_progress_cb = QCheckBox("Show detailed progress information")
        progress_layout.addRow(self.show_detailed_progress_cb)
        
        layout.addWidget(progress_group)
        
        # Background processing
        background_group = QGroupBox("Background Processing")
        background_layout = QFormLayout(background_group)
        
        self.background_loading_cb = QCheckBox("Enable background page loading")
        background_layout.addRow(self.background_loading_cb)
        
        self.preload_adjacent_cb = QCheckBox("Preload adjacent pages")
        background_layout.addRow(self.preload_adjacent_cb)
        
        layout.addWidget(background_group)
        layout.addStretch()
        
        return widget
    
    def load_settings(self):
        """Load current settings into the UI."""
        # Pagination settings
        self.default_page_size_spin.setValue(self.config.default_page_size)
        self.min_page_size_spin.setValue(self.config.min_page_size)
        self.max_page_size_spin.setValue(self.config.max_page_size)
        
        # Memory settings
        self.memory_threshold_spin.setValue(self.config.memory_threshold_mb)
        self.warning_threshold_spin.setValue(self.config.warning_threshold_mb)
        self.max_memory_spin.setValue(self.config.max_memory_usage_mb)
        
        # Performance settings
        self.chunk_size_spin.setValue(self.config.chunk_size)
        self.progress_interval_spin.setValue(self.config.progress_update_interval)
        
        # Default checkbox states (these could be stored in config too)
        self.auto_optimize_cb.setChecked(True)
        self.monitor_memory_cb.setChecked(True)
        self.show_memory_warnings_cb.setChecked(True)
        self.auto_clear_cache_cb.setChecked(True)
        self.show_detailed_progress_cb.setChecked(True)
        self.background_loading_cb.setChecked(True)
        self.preload_adjacent_cb.setChecked(False)
        
        # Default values for new settings
        self.pagination_threshold_spin.setValue(10000)
        self.cache_size_spin.setValue(5)
    
    def save_settings(self) -> PaginationConfig:
        """Save settings and return updated config."""
        # Validate settings
        if not self.validate_settings():
            return self.config
        
        # Update config
        self.config.default_page_size = self.default_page_size_spin.value()
        self.config.min_page_size = self.min_page_size_spin.value()
        self.config.max_page_size = self.max_page_size_spin.value()
        self.config.memory_threshold_mb = self.memory_threshold_spin.value()
        self.config.warning_threshold_mb = self.warning_threshold_spin.value()
        self.config.max_memory_usage_mb = self.max_memory_spin.value()
        self.config.chunk_size = self.chunk_size_spin.value()
        self.config.progress_update_interval = self.progress_interval_spin.value()
        
        return self.config
    
    def validate_settings(self) -> bool:
        """Validate the current settings."""
        errors = []
        
        # Page size validation
        if self.min_page_size_spin.value() >= self.default_page_size_spin.value():
            errors.append("Minimum page size must be less than default page size")
        
        if self.default_page_size_spin.value() >= self.max_page_size_spin.value():
            errors.append("Default page size must be less than maximum page size")
        
        # Memory validation
        if self.memory_threshold_spin.value() >= self.warning_threshold_spin.value():
            errors.append("Memory threshold must be less than warning threshold")
        
        if self.warning_threshold_spin.value() >= self.max_memory_spin.value():
            errors.append("Warning threshold must be less than maximum memory usage")
        
        if errors:
            QMessageBox.warning(
                self,
                "Invalid Settings",
                "Please correct the following issues:\n\n" + "\n".join(f"• {error}" for error in errors)
            )
            return False
        
        return True
    
    def reset_to_defaults(self):
        """Reset all settings to defaults."""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Reset all optimization settings to default values?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            default_config = PaginationConfig()
            self.config = default_config
            self.load_settings()
    
    def apply_changes(self):
        """Apply changes without closing dialog."""
        self.save_settings()
    
    def accept_changes(self):
        """Accept and save changes."""
        if self.validate_settings():
            self.save_settings()
            self.accept()
    
    def get_config(self) -> PaginationConfig:
        """Get the current configuration."""
        return self.config
    
    def has_changes(self) -> bool:
        """Check if settings have been modified."""
        current = self.save_settings()
        return (
            current.default_page_size != self.original_config.default_page_size or
            current.min_page_size != self.original_config.min_page_size or
            current.max_page_size != self.original_config.max_page_size or
            current.memory_threshold_mb != self.original_config.memory_threshold_mb or
            current.warning_threshold_mb != self.original_config.warning_threshold_mb or
            current.max_memory_usage_mb != self.original_config.max_memory_usage_mb or
            current.chunk_size != self.original_config.chunk_size or
            current.progress_update_interval != self.original_config.progress_update_interval
        )