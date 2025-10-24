"""
Test theme system functionality in LocalSQL Explorer.
"""

import sys
import tempfile
from pathlib import Path

# Add src to Python path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from localsql_explorer.themes import ThemeManager, ThemeType


def test_theme_manager_basic():
    """Test basic theme manager functionality."""
    print("Testing basic theme manager functionality...")
    
    # Create theme manager
    theme_manager = ThemeManager()
    
    # Test default theme
    current_theme = theme_manager.get_current_theme()
    print(f"Default theme: {current_theme.value}")
    
    # Test theme switching
    original_theme = current_theme
    theme_manager.toggle_theme()
    new_theme = theme_manager.get_current_theme()
    print(f"After toggle: {new_theme.value}")
    
    # Verify theme changed
    assert new_theme != original_theme, "Theme should have changed after toggle"
    
    # Test setting specific theme
    theme_manager.set_theme(ThemeType.DARK)
    assert theme_manager.get_current_theme() == ThemeType.DARK, "Should be dark theme"
    
    theme_manager.set_theme(ThemeType.LIGHT)
    assert theme_manager.get_current_theme() == ThemeType.LIGHT, "Should be light theme"
    
    print("✅ Basic theme manager test passed!")


def test_theme_stylesheets():
    """Test theme stylesheet generation."""
    print("\nTesting theme stylesheet generation...")
    
    theme_manager = ThemeManager()
    
    # Test light theme stylesheet
    light_stylesheet = theme_manager.get_stylesheet(ThemeType.LIGHT)
    assert len(light_stylesheet) > 1000, "Light stylesheet should be substantial"
    assert "#ffffff" in light_stylesheet, "Light theme should contain white colors"
    assert "QMainWindow" in light_stylesheet, "Should contain main window styling"
    
    # Test dark theme stylesheet
    dark_stylesheet = theme_manager.get_stylesheet(ThemeType.DARK)
    assert len(dark_stylesheet) > 1000, "Dark stylesheet should be substantial"
    assert "#1e1e1e" in dark_stylesheet, "Dark theme should contain dark colors"
    assert "QMainWindow" in dark_stylesheet, "Should contain main window styling"
    
    # Verify stylesheets are different
    assert light_stylesheet != dark_stylesheet, "Light and dark stylesheets should be different"
    
    print("✅ Theme stylesheet test passed!")


def test_theme_persistence():
    """Test theme persistence across sessions."""
    print("\nTesting theme persistence...")
    
    # Create first theme manager instance
    theme_manager1 = ThemeManager()
    
    # Set to dark theme
    theme_manager1.set_theme(ThemeType.DARK)
    current_theme1 = theme_manager1.get_current_theme()
    print(f"Set theme to: {current_theme1.value}")
    
    # Create second instance (simulating app restart)
    theme_manager2 = ThemeManager()
    current_theme2 = theme_manager2.get_current_theme()
    print(f"Loaded theme: {current_theme2.value}")
    
    # Verify persistence
    assert current_theme1 == current_theme2, "Theme should persist across sessions"
    
    print("✅ Theme persistence test passed!")


def test_theme_components():
    """Test theme color components."""
    print("\nTesting theme color components...")
    
    theme_manager = ThemeManager()
    
    # Test light theme colors
    light_theme = theme_manager.themes[ThemeType.LIGHT]
    light_colors = light_theme["colors"]
    
    required_colors = [
        "background", "surface", "primary", "text", "border",
        "success", "warning", "error", "info", "selection"
    ]
    
    for color in required_colors:
        assert color in light_colors, f"Light theme should have {color} color"
        assert light_colors[color].startswith("#"), f"{color} should be a hex color"
    
    # Test dark theme colors
    dark_theme = theme_manager.themes[ThemeType.DARK]
    dark_colors = dark_theme["colors"]
    
    for color in required_colors:
        assert color in dark_colors, f"Dark theme should have {color} color"
        assert dark_colors[color].startswith("#"), f"{color} should be a hex color"
    
    # Verify themes have different color values
    assert light_colors["background"] != dark_colors["background"], "Themes should have different backgrounds"
    assert light_colors["text"] != dark_colors["text"], "Themes should have different text colors"
    
    print("✅ Theme components test passed!")


if __name__ == "__main__":
    test_theme_manager_basic()
    test_theme_stylesheets()
    test_theme_persistence()
    test_theme_components()
    print("\n🎉 All theme tests passed!")