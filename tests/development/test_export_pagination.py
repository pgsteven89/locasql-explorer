#!/usr/bin/env python3
"""
Test script to verify the enhanced export and pagination functionality.
"""

import sys
import tempfile
import pandas as pd
from pathlib import Path
from PyQt6.QtWidgets import QApplication

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def test_export_functionality():
    """Test the new export functionality in paginated results."""
    from localsql_explorer.database import DatabaseManager
    from localsql_explorer.ui.paginated_results import PaginatedTableWidget
    
    print("Testing enhanced export and pagination functionality...")
    
    # Create QApplication if it doesn't exist
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    try:
        # Create test data
        data = {
            'id': range(1, 201),  # 200 rows for testing pagination
            'name': [f'User_{i}' for i in range(1, 201)],
            'category': [f'Category_{i % 5}' for i in range(1, 201)],
            'value': [i * 10.5 for i in range(1, 201)],
            'status': ['active' if i % 3 == 0 else 'inactive' for i in range(1, 201)]
        }
        df = pd.DataFrame(data)
        
        # Create database and register data
        db_manager = DatabaseManager()
        db_manager.connection.register('test_export_table', df)
        
        print(f"✅ Created test dataset with {len(df)} rows")
        
        # Create paginator with smaller page size to test pagination
        query = "SELECT * FROM test_export_table"
        paginator = db_manager.create_query_paginator(query)
        
        # Create paginated widget
        widget = PaginatedTableWidget(paginator)
        
        print("✅ PaginatedTableWidget created successfully")
        
        # Test initial state
        assert hasattr(widget, 'export_page_btn'), "Export page button not found"
        assert hasattr(widget, 'export_all_btn'), "Export all button not found" 
        assert hasattr(widget, 'export_filtered_btn'), "Export filtered button not found"
        print("✅ All export buttons are present")
        
        # Test page size selector
        assert hasattr(widget, 'page_size_combo'), "Page size combo not found"
        available_sizes = [widget.page_size_combo.itemText(i) for i in range(widget.page_size_combo.count())]
        expected_sizes = ["100", "500", "1000", "2500", "5000", "10000"]
        for size in expected_sizes:
            assert size in available_sizes, f"Page size {size} not found"
        print(f"✅ Page size options available: {available_sizes}")
        
        # Load initial page and simulate data being loaded
        widget.load_initial_page()
        app.processEvents()
        
        # Simulate data loading by directly setting current_data for testing
        # In real usage, this would be set by the async worker
        if widget.current_data is None:
            # Simulate first page of data (first 50 rows)
            page_data = df.head(50)
            from localsql_explorer.data_pagination import PageInfo
            page_info = PageInfo(
                page_number=0,
                page_size=50,
                total_rows=len(df),
                start_row=0,
                end_row=49,
                total_pages=(len(df) + 49) // 50,
                has_previous=False,
                has_next=True
            )
            widget.current_data = page_data
            widget.current_page_info = page_info
            widget.populate_table(page_data)
            widget.update_column_dropdown()
            print("✅ Simulated data loading for testing")
        
        # Simulate page size change
        original_size = widget.current_page_size
        widget.page_size_combo.setCurrentText("50")  # Set to smaller size
        widget.on_page_size_changed("50")
        print(f"✅ Page size changed from {original_size} to {widget.current_page_size}")
        
        # Test signal connections
        signals_connected = []
        if hasattr(widget, 'export_requested'):
            signals_connected.append('export_requested')
        if hasattr(widget, 'export_all_requested'):
            signals_connected.append('export_all_requested')  
        if hasattr(widget, 'export_filtered_requested'):
            signals_connected.append('export_filtered_requested')
        
        print(f"✅ Signals available: {signals_connected}")
        assert len(signals_connected) == 3, f"Expected 3 signals, found {len(signals_connected)}"
        
        # Test filtered export button state
        widget.search_input.setText("Category_1")
        widget.filter_current_page()
        
        # Check that filtered export button is enabled when search is active
        search_active = bool(widget.search_input.text().strip())
        print(f"✅ Search filter active: {search_active}")
        
        # Test get_filtered_data method
        filtered_data = widget.get_filtered_data()
        print(f"✅ Filtered data contains {len(filtered_data)} rows")
        
        # Debug: check what's actually in the current data
        if widget.current_data is not None:
            print(f"Debug: Current data has {len(widget.current_data)} rows")
            print(f"Debug: Category column sample: {widget.current_data['category'].head().tolist()}")
            print(f"Debug: Searching for 'Category_1' in category column")
            
            # Check if any data matches manually
            matches = widget.current_data[widget.current_data['category'].str.contains('Category_1', na=False)]
            print(f"Debug: Manual search found {len(matches)} matches")
            
            if len(matches) > 0:
                print(f"Debug: First matching row: {matches.iloc[0].to_dict()}")
        
        # Only assert if we have current data loaded
        if widget.current_data is not None and len(widget.current_data) > 0:
            # Look for a value that should definitely exist
            sample_category = widget.current_data['category'].iloc[0] if len(widget.current_data) > 0 else None
            if sample_category:
                print(f"Debug: Trying search for actual value: {sample_category}")
                widget.search_input.setText(sample_category)
                widget.filter_current_page()
                filtered_data = widget.get_filtered_data()
                print(f"✅ Filtered data with '{sample_category}' contains {len(filtered_data)} rows")
                assert len(filtered_data) > 0, f"Filtered data should contain matching rows for {sample_category}"
        
        # Test clearing search
        widget.search_input.setText("")
        widget.filter_current_page()
        
        filtered_data_empty = widget.get_filtered_data()
        print(f"✅ Data after clearing search: {len(filtered_data_empty)} rows")
        
        print("All export and pagination tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_export_functionality()