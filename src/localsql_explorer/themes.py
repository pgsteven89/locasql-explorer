"""
Theme management system for LocalSQL Explorer.

This module provides:
- Light and dark theme definitions
- Theme switching functionality
- CSS stylesheet generation
- Theme persistence across sessions
"""

import logging
from enum import Enum
from pathlib import Path
from typing import Dict, Optional

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication

logger = logging.getLogger(__name__)


class ThemeType(Enum):
    """Available theme types."""
    LIGHT = "light"
    DARK = "dark"


class ThemeManager:
    """
    Manages application themes with persistent storage.
    
    Features:
    - Light and dark theme support
    - CSS stylesheet generation
    - Theme persistence
    - Dynamic theme switching
    """
    
    def __init__(self):
        """Initialize theme manager."""
        self.settings = QSettings("LocalSQL Explorer", "Themes")
        self.current_theme = self._load_saved_theme()
        
        # Theme definitions
        self.themes = {
            ThemeType.LIGHT: self._create_light_theme(),
            ThemeType.DARK: self._create_dark_theme()
        }
    
    def _load_saved_theme(self) -> ThemeType:
        """Load saved theme from settings."""
        saved_theme = self.settings.value("current_theme", ThemeType.DARK.value)
        try:
            return ThemeType(saved_theme)
        except ValueError:
            return ThemeType.DARK
    
    def _save_theme(self, theme: ThemeType):
        """Save current theme to settings."""
        self.settings.setValue("current_theme", theme.value)
        logger.info(f"Saved theme: {theme.value}")
    
    def get_current_theme(self) -> ThemeType:
        """Get the current theme."""
        return self.current_theme
    
    def set_theme(self, theme: ThemeType):
        """
        Set and apply a theme.
        
        Args:
            theme: Theme type to apply
        """
        self.current_theme = theme
        self._save_theme(theme)
        self.apply_theme()
        logger.info(f"Applied theme: {theme.value}")
    
    def toggle_theme(self):
        """Toggle between light and dark themes."""
        new_theme = ThemeType.DARK if self.current_theme == ThemeType.LIGHT else ThemeType.LIGHT
        self.set_theme(new_theme)
    
    def apply_theme(self):
        """Apply the current theme to the application."""
        app = QApplication.instance()
        if app:
            stylesheet = self.get_stylesheet(self.current_theme)
            app.setStyleSheet(stylesheet)
    
    def get_stylesheet(self, theme: ThemeType) -> str:
        """
        Get CSS stylesheet for a theme.
        
        Args:
            theme: Theme type
            
        Returns:
            str: CSS stylesheet
        """
        theme_config = self.themes.get(theme, self.themes[ThemeType.DARK])
        return self._generate_stylesheet(theme_config)
    
    def _create_light_theme(self) -> Dict:
        """Create light theme configuration."""
        return {
            "name": "Light",
            "colors": {
                # Main colors
                "background": "#ffffff",
                "surface": "#f8f9fa",
                "surface_variant": "#e9ecef",
                "primary": "#0066cc",
                "primary_variant": "#004499",
                "secondary": "#6c757d",
                "accent": "#28a745",
                
                # Text colors
                "text": "#212529",
                "text_secondary": "#6c757d",
                "text_disabled": "#adb5bd",
                "text_on_primary": "#ffffff",
                
                # Border and outline colors
                "border": "#dee2e6",
                "border_focus": "#0066cc",
                "outline": "#ced4da",
                
                # Status colors
                "success": "#28a745",
                "warning": "#ffc107",
                "error": "#dc3545",
                "info": "#17a2b8",
                
                # Component specific
                "button_hover": "#e9ecef",
                "selection": "#0066cc33",
                "selection_inactive": "#f8f9fa",
                "tooltip": "#343a40",
                "tooltip_text": "#ffffff",
                
                # SQL Editor specific
                "editor_background": "#ffffff",
                "editor_current_line": "#f8f9fa",
                "editor_line_numbers": "#6c757d",
                "editor_selection": "#0066cc33",
                
                # Table specific
                "table_header": "#f8f9fa",
                "table_alternate": "#f8f9fa",
                "table_grid": "#dee2e6",
                
                # Dock and splitter
                "dock_title": "#e9ecef",
                "splitter": "#dee2e6",
            }
        }
    
    def _create_dark_theme(self) -> Dict:
        """Create dark theme configuration."""
        return {
            "name": "Dark",
            "colors": {
                # Main colors
                "background": "#1e1e1e",
                "surface": "#252526",
                "surface_variant": "#2d2d30",
                "primary": "#4fc3f7",
                "primary_variant": "#29b6f6",
                "secondary": "#9e9e9e",
                "accent": "#66bb6a",
                
                # Text colors
                "text": "#e0e0e0",
                "text_secondary": "#bdbdbd",
                "text_disabled": "#757575",
                "text_on_primary": "#000000",
                
                # Border and outline colors
                "border": "#3e3e42",
                "border_focus": "#4fc3f7",
                "outline": "#515151",
                
                # Status colors
                "success": "#66bb6a",
                "warning": "#ffca28",
                "error": "#f44336",
                "info": "#29b6f6",
                
                # Component specific
                "button_hover": "#2d2d30",
                "selection": "#4fc3f733",
                "selection_inactive": "#252526",
                "tooltip": "#616161",
                "tooltip_text": "#e0e0e0",
                
                # SQL Editor specific
                "editor_background": "#1e1e1e",
                "editor_current_line": "#252526",
                "editor_line_numbers": "#9e9e9e",
                "editor_selection": "#4fc3f733",
                
                # Table specific
                "table_header": "#2d2d30",
                "table_alternate": "#252526",
                "table_grid": "#3e3e42",
                
                # Dock and splitter
                "dock_title": "#2d2d30",
                "splitter": "#3e3e42",
            }
        }
    
    def _generate_stylesheet(self, theme_config: Dict) -> str:
        """
        Generate CSS stylesheet from theme configuration.
        
        Args:
            theme_config: Theme configuration dictionary
            
        Returns:
            str: Generated CSS stylesheet
        """
        colors = theme_config["colors"]
        
        stylesheet = f"""
/* Main Application Styling */
QMainWindow {{
    background-color: {colors["background"]};
    color: {colors["text"]};
}}

QWidget {{
    background-color: {colors["background"]};
    color: {colors["text"]};
    selection-background-color: {colors["selection"]};
}}

/* Menu and Menu Bar */
QMenuBar {{
    background-color: {colors["surface"]};
    border-bottom: 1px solid {colors["border"]};
    color: {colors["text"]};
    padding: 2px;
}}

QMenuBar::item {{
    background-color: transparent;
    padding: 4px 8px;
    border-radius: 4px;
}}

QMenuBar::item:selected {{
    background-color: {colors["button_hover"]};
}}

QMenu {{
    background-color: {colors["surface"]};
    border: 1px solid {colors["border"]};
    color: {colors["text"]};
    padding: 4px;
}}

QMenu::item {{
    padding: 6px 20px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {colors["primary"]};
    color: {colors["text_on_primary"]};
}}

QMenu::separator {{
    height: 1px;
    background-color: {colors["border"]};
    margin: 4px 8px;
}}

/* Toolbar */
QToolBar {{
    background-color: {colors["surface"]};
    border: none;
    spacing: 2px;
    padding: 4px;
}}

QToolButton {{
    background-color: transparent;
    border: none;
    padding: 6px;
    border-radius: 4px;
}}

QToolButton:hover {{
    background-color: {colors["button_hover"]};
}}

QToolButton:pressed {{
    background-color: {colors["primary"]};
    color: {colors["text_on_primary"]};
}}

/* Buttons */
QPushButton {{
    background-color: {colors["surface"]};
    border: 1px solid {colors["border"]};
    color: {colors["text"]};
    padding: 6px 12px;
    border-radius: 4px;
    font-weight: normal;
}}

QPushButton:hover {{
    background-color: {colors["button_hover"]};
    border-color: {colors["border_focus"]};
}}

QPushButton:pressed {{
    background-color: {colors["primary"]};
    color: {colors["text_on_primary"]};
}}

QPushButton:disabled {{
    background-color: {colors["surface_variant"]};
    color: {colors["text_disabled"]};
    border-color: {colors["outline"]};
}}

/* Text Input Fields */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {colors["editor_background"]};
    border: 1px solid {colors["border"]};
    color: {colors["text"]};
    padding: 4px;
    border-radius: 4px;
    selection-background-color: {colors["selection"]};
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {colors["border_focus"]};
    outline: none;
}}

/* ComboBox */
QComboBox {{
    background-color: {colors["surface"]};
    border: 1px solid {colors["border"]};
    color: {colors["text"]};
    padding: 4px 8px;
    border-radius: 4px;
    min-width: 100px;
}}

QComboBox:hover {{
    border-color: {colors["border_focus"]};
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 4px solid {colors["text"]};
    margin-right: 4px;
}}

QComboBox QAbstractItemView {{
    background-color: {colors["surface"]};
    border: 1px solid {colors["border"]};
    color: {colors["text"]};
    selection-background-color: {colors["primary"]};
    selection-color: {colors["text_on_primary"]};
}}

/* Tables */
QTableWidget, QTableView {{
    background-color: {colors["editor_background"]};
    alternate-background-color: {colors["table_alternate"]};
    color: {colors["text"]};
    gridline-color: {colors["table_grid"]};
    border: 1px solid {colors["border"]};
    selection-background-color: {colors["selection"]};
}}

QHeaderView::section {{
    background-color: {colors["table_header"]};
    color: {colors["text"]};
    border: none;
    border-right: 1px solid {colors["border"]};
    border-bottom: 1px solid {colors["border"]};
    padding: 6px;
    font-weight: bold;
}}

QHeaderView::section:hover {{
    background-color: {colors["button_hover"]};
}}

/* List Widgets */
QListWidget {{
    background-color: {colors["editor_background"]};
    border: 1px solid {colors["border"]};
    color: {colors["text"]};
    selection-background-color: {colors["selection"]};
    outline: none;
}}

QListWidget::item {{
    padding: 4px 8px;
    border-bottom: 1px solid {colors["table_grid"]};
}}

QListWidget::item:hover {{
    background-color: {colors["button_hover"]};
}}

QListWidget::item:selected {{
    background-color: {colors["primary"]};
    color: {colors["text_on_primary"]};
}}

/* Tree Widget */
QTreeWidget {{
    background-color: {colors["editor_background"]};
    border: 1px solid {colors["border"]};
    color: {colors["text"]};
    selection-background-color: {colors["selection"]};
    outline: none;
}}

QTreeWidget::item {{
    padding: 2px;
}}

QTreeWidget::item:hover {{
    background-color: {colors["button_hover"]};
}}

QTreeWidget::item:selected {{
    background-color: {colors["primary"]};
    color: {colors["text_on_primary"]};
}}

/* Dock Widgets */
QDockWidget {{
    background-color: {colors["surface"]};
    color: {colors["text"]};
    border: 1px solid {colors["border"]};
}}

QDockWidget::title {{
    background-color: {colors["dock_title"]};
    color: {colors["text"]};
    padding: 6px;
    border-bottom: 1px solid {colors["border"]};
    font-weight: bold;
}}

QDockWidget::close-button, QDockWidget::float-button {{
    background-color: transparent;
    border: none;
    padding: 2px;
}}

QDockWidget::close-button:hover, QDockWidget::float-button:hover {{
    background-color: {colors["button_hover"]};
}}

/* Splitter */
QSplitter::handle {{
    background-color: {colors["splitter"]};
}}

QSplitter::handle:horizontal {{
    width: 3px;
    margin: 2px 0;
}}

QSplitter::handle:vertical {{
    height: 3px;
    margin: 0 2px;
}}

QSplitter::handle:hover {{
    background-color: {colors["primary"]};
}}

/* Status Bar */
QStatusBar {{
    background-color: {colors["surface"]};
    color: {colors["text"]};
    border-top: 1px solid {colors["border"]};
    padding: 2px;
}}

QStatusBar::item {{
    border: none;
}}

/* Progress Bar */
QProgressBar {{
    background-color: {colors["surface_variant"]};
    border: 1px solid {colors["border"]};
    border-radius: 4px;
    text-align: center;
    color: {colors["text"]};
    height: 16px;
}}

QProgressBar::chunk {{
    background-color: {colors["primary"]};
    border-radius: 3px;
}}

/* Scroll Bars */
QScrollBar:vertical {{
    background-color: {colors["surface_variant"]};
    width: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:vertical {{
    background-color: {colors["secondary"]};
    border-radius: 6px;
    min-height: 20px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {colors["primary"]};
}}

QScrollBar:horizontal {{
    background-color: {colors["surface_variant"]};
    height: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:horizontal {{
    background-color: {colors["secondary"]};
    border-radius: 6px;
    min-width: 20px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {colors["primary"]};
}}

QScrollBar::add-line, QScrollBar::sub-line {{
    background: none;
    border: none;
}}

/* Tabs */
QTabWidget::pane {{
    background-color: {colors["surface"]};
    border: 1px solid {colors["border"]};
}}

QTabBar::tab {{
    background-color: {colors["surface_variant"]};
    color: {colors["text"]};
    padding: 6px 12px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}}

QTabBar::tab:selected {{
    background-color: {colors["surface"]};
    border-bottom: 2px solid {colors["primary"]};
}}

QTabBar::tab:hover:!selected {{
    background-color: {colors["button_hover"]};
}}

/* Tooltips */
QToolTip {{
    background-color: {colors["tooltip"]};
    color: {colors["tooltip_text"]};
    border: 1px solid {colors["border"]};
    padding: 4px;
    border-radius: 4px;
}}

/* Group Box */
QGroupBox {{
    background-color: {colors["surface"]};
    border: 1px solid {colors["border"]};
    border-radius: 4px;
    margin-top: 8px;
    font-weight: bold;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: {colors["text"]};
    background-color: {colors["surface"]};
}}

/* Checkboxes and Radio Buttons */
QCheckBox, QRadioButton {{
    color: {colors["text"]};
    spacing: 8px;
}}

QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    background-color: {colors["surface"]};
    border: 1px solid {colors["border"]};
    border-radius: 3px;
}}

QCheckBox::indicator:checked {{
    background-color: {colors["primary"]};
    border-color: {colors["primary"]};
}}

QRadioButton::indicator {{
    border-radius: 8px;
}}

QRadioButton::indicator:checked {{
    background-color: {colors["primary"]};
    border-color: {colors["primary"]};
}}

/* Frame styling */
QFrame[frameShape="1"] {{ /* Box frame */
    border: 1px solid {colors["border"]};
}}

QFrame[frameShape="4"] {{ /* HLine */
    color: {colors["border"]};
}}

QFrame[frameShape="5"] {{ /* VLine */
    color: {colors["border"]};
}}

/* Dialog styling */
QDialog {{
    background-color: {colors["background"]};
    color: {colors["text"]};
}}

QDialogButtonBox {{
    background-color: {colors["surface"]};
}}
"""
        
        return stylesheet


# Global theme manager instance
theme_manager = ThemeManager()