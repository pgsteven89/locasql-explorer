"""
Test theme integration with main window.
"""

import sys
from pathlib import Path

# Add src to Python path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_main_window_theme_integration():
    """Test theme integration in main window."""
    print("Testing main window theme integration...")
    
    from PyQt6.QtWidgets import QApplication
    from localsql_explorer.ui.main_window import MainWindow
    from localsql_explorer.themes import theme_manager, ThemeType
    
    # Create QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    try:
        # Create main window
        window = MainWindow()
        print("✅ Main window created successfully")
        
        # Test initial theme
        current_theme = theme_manager.get_current_theme()
        print(f"Initial theme: {current_theme.value}")
        
        # Test theme toggle
        original_theme = current_theme
        window.toggle_theme()
        new_theme = theme_manager.get_current_theme()
        print(f"After toggle: {new_theme.value}")
        
        # Verify theme changed
        assert new_theme != original_theme, "Theme should change after toggle"
        
        # Test theme action text update
        if hasattr(window, 'toggle_theme_action'):
            action_text = window.toggle_theme_action.text()
            print(f"Theme action text: {action_text}")
            assert "Theme" in action_text, "Action text should mention theme"
        
        # Test applying theme
        window.apply_theme()
        print("✅ Theme applied successfully")
        
        # Test multiple toggles
        for i in range(3):
            window.toggle_theme()
            theme = theme_manager.get_current_theme()
            print(f"Toggle {i+1}: {theme.value}")
        
        print("✅ Main window theme integration test passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise
    finally:
        if app:
            app.quit()


if __name__ == "__main__":
    test_main_window_theme_integration()
    print("\n🎉 Theme integration test completed!")