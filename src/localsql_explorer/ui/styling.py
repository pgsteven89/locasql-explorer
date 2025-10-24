"""
UI styling utilities for LocalSQL Explorer.

This module provides common styling functions and utilities to ensure
consistent appearance across all UI components.
"""

from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtWidgets import QWidget


def setup_text_selection_colors(widget: QWidget, is_dark_theme: bool = False):
    """
    Configure proper text selection colors for any text widget.
    
    Args:
        widget: The text widget to configure
        is_dark_theme: Whether to use dark theme colors
    """
    palette = widget.palette()
    
    if is_dark_theme:
        # Dark theme: light selection background with white text
        selection_bg = QColor("#3399FF")  # Light blue background
        selection_fg = QColor("#FFFFFF")  # White text
        inactive_selection_bg = QColor("#555555")  # Gray background when inactive
        inactive_selection_fg = QColor("#FFFFFF")  # White text when inactive
    else:
        # Light theme: blue selection background with white text
        selection_bg = QColor("#3399FF")  # Blue background
        selection_fg = QColor("#FFFFFF")  # White text
        inactive_selection_bg = QColor("#CCCCCC")  # Light gray background when inactive
        inactive_selection_fg = QColor("#000000")  # Black text when inactive
    
    # Set active selection colors
    palette.setColor(QPalette.ColorRole.Highlight, selection_bg)
    palette.setColor(QPalette.ColorRole.HighlightedText, selection_fg)
    
    # Set inactive selection colors (when widget loses focus)
    palette.setColor(QPalette.ColorGroup.Inactive, QPalette.ColorRole.Highlight, inactive_selection_bg)
    palette.setColor(QPalette.ColorGroup.Inactive, QPalette.ColorRole.HighlightedText, inactive_selection_fg)
    
    # Apply the palette
    widget.setPalette(palette)


def get_theme_colors(is_dark_theme: bool = False):
    """
    Get standard theme colors for consistent styling.
    
    Args:
        is_dark_theme: Whether to return dark theme colors
        
    Returns:
        dict: Dictionary of theme colors
    """
    if is_dark_theme:
        return {
            'background': '#2b2b2b',
            'foreground': '#ffffff',
            'selection_bg': '#3399FF',
            'selection_fg': '#FFFFFF',
            'accent': '#0078d4',
            'border': '#555555',
            'error': '#f14c4c',
            'warning': '#ffb900',
            'success': '#107c10'
        }
    else:
        return {
            'background': '#ffffff',
            'foreground': '#000000',
            'selection_bg': '#3399FF',
            'selection_fg': '#FFFFFF',
            'accent': '#0078d4',
            'border': '#cccccc',
            'error': '#d13438',
            'warning': '#ff8c00',
            'success': '#107c10'
        }


def apply_consistent_text_styling(widget: QWidget, is_dark_theme: bool = False, read_only: bool = False):
    """
    Apply consistent text styling to a widget.
    
    Args:
        widget: The widget to style
        is_dark_theme: Whether to use dark theme
        read_only: Whether the widget is read-only
    """
    setup_text_selection_colors(widget, is_dark_theme)
    
    colors = get_theme_colors(is_dark_theme)
    
    if read_only:
        # Slightly muted background for read-only widgets
        if is_dark_theme:
            bg_color = '#1e1e1e'
        else:
            bg_color = '#f5f5f5'
    else:
        bg_color = colors['background']
    
    # Apply basic styling
    widget.setStyleSheet(f"""
        QTextEdit, QPlainTextEdit {{
            background-color: {bg_color};
            color: {colors['foreground']};
            border: 1px solid {colors['border']};
            font-family: 'Consolas', 'Courier New', monospace;
        }}
        
        QTextEdit:focus, QPlainTextEdit:focus {{
            border: 2px solid {colors['accent']};
        }}
    """)