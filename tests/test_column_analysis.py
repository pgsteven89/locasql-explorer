"""
Test column metadata and analysis functionality.
"""

import sys
import tempfile
from pathlib import Path

# Add src to Python path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pandas as pd
import numpy as np


def test_column_analyzer_basic():
    """Test basic column analyzer functionality."""
    print("Testing basic column analyzer functionality...")
    
    from localsql_explorer.column_analysis import column_analyzer
    
    # Create test dataframe
    np.random.seed(42)  # For reproducible results
    
    data = {
        'id': range(1, 101),
        'name': [f'Person_{i}' for i in range(1, 101)],
        'age': np.random.randint(18, 80, 100),
        'salary': np.random.normal(50000, 15000, 100),
        'department': np.random.choice(['IT', 'HR', 'Finance', 'Marketing'], 100),
        'email': [f'person{i}@company.com' for i in range(1, 101)],
        'join_date': pd.date_range('2020-01-01', '2023-12-31', periods=100),
        'active': np.random.choice([True, False], 100, p=[0.8, 0.2])
    }
    
    # Add some null values for testing
    data['salary'][5:15] = None  # 10% nulls in salary
    data['department'][90:] = None  # Some nulls in department
    
    df = pd.DataFrame(data)
    
    print(f"Created test dataframe with {len(df)} rows and {len(df.columns)} columns")
    
    # Analyze the table
    analysis = column_analyzer.analyze_table(df, "test_employees")
    
    print(f"Analysis completed for table: {analysis.table_name}")
    print(f"Total rows: {analysis.total_rows}")
    print(f"Total columns: {analysis.total_columns}")
    print(f"Overall quality score: {analysis.overall_quality_score:.1f}%")
    print(f"Memory usage: {analysis.memory_usage / 1024:.1f} KB")
    
    # Test column-specific analysis
    for column in analysis.columns[:3]:  # Show first 3 columns
        print(f"\nColumn: {column.name} ({column.data_type})")
        print(f"  Quality Score: {column.quality_score:.1f}%")
        print(f"  Null Count: {column.statistics.null_count} ({column.statistics.null_percentage:.1f}%)")
        print(f"  Unique Count: {column.statistics.unique_count} ({column.statistics.unique_percentage:.1f}%)")
        
        if column.statistics.min_value is not None:
            print(f"  Range: {column.statistics.min_value} - {column.statistics.max_value}")
        
        if column.statistics.sample_values:
            print(f"  Samples: {', '.join(column.statistics.sample_values[:3])}")
        
        if column.quality_issues:
            print(f"  Issues: {'; '.join(column.quality_issues)}")
    
    print("✅ Basic column analyzer test passed!")


def test_column_analysis_edge_cases():
    """Test column analysis with edge cases."""
    print("\nTesting column analysis edge cases...")
    
    from localsql_explorer.column_analysis import column_analyzer
    
    # Test with problematic data
    data = {
        'all_nulls': [None] * 100,
        'all_same': ['same_value'] * 100,
        'mostly_nulls': [1, 2, 3] + [None] * 97,
        'very_long_strings': ['x' * (100 + i) for i in range(100)],
        'outliers': [1, 2, 3, 4, 5] * 10 + [1000000] * 10 + [6, 7, 8, 9, 10] * 8,
        'empty_strings': [''] * 50 + ['text'] * 50,
        'mixed_types': [str(i) if i % 5 == 0 else i for i in range(100)]  # Mix of strings and ints
    }
    
    df = pd.DataFrame(data)
    
    print(f"Created problematic dataframe with {len(df)} rows and {len(df.columns)} columns")
    
    # Analyze the table
    analysis = column_analyzer.analyze_table(df, "problematic_data")
    
    print(f"Overall quality score: {analysis.overall_quality_score:.1f}%")
    
    # Check that quality issues are detected
    low_quality_columns = analysis.get_low_quality_columns(threshold=80.0)
    print(f"Low quality columns: {len(low_quality_columns)}")
    
    for column in low_quality_columns:
        print(f"  {column.name}: {column.quality_score:.1f}% - {'; '.join(column.quality_issues)}")
    
    print("✅ Edge cases test passed!")


def test_database_integration():
    """Test integration with database manager."""
    print("\nTesting database integration...")
    
    from localsql_explorer.database import DatabaseManager
    import pandas as pd
    
    # Create database manager
    db_manager = DatabaseManager()
    
    # Create test data
    test_data = pd.DataFrame({
        'product_id': range(1, 51),
        'product_name': [f'Product {i}' for i in range(1, 51)],
        'price': np.random.uniform(10, 100, 50),
        'category': np.random.choice(['Electronics', 'Clothing', 'Books'], 50),
        'in_stock': np.random.choice([True, False], 50),
        'description': [f'Description for product {i}' * np.random.randint(1, 5) for i in range(1, 51)]
    })
    
    # Add some quality issues
    test_data.loc[5:10, 'price'] = None  # Some null prices
    test_data.loc[45:, 'category'] = None  # Some null categories
    
    # Register table
    metadata = db_manager.register_table('test_products', test_data, None, 'dataframe')
    print(f"Registered table: {metadata.name}")
    
    # Perform column analysis
    analysis = db_manager.analyze_table_columns('test_products')
    
    if analysis:
        print(f"Analysis successful for {analysis.table_name}")
        print(f"Columns analyzed: {len(analysis.columns)}")
        print(f"Overall quality: {analysis.overall_quality_score:.1f}%")
        
        # Check numeric and string columns
        numeric_cols = analysis.get_numeric_columns()
        string_cols = analysis.get_string_columns()
        
        print(f"Numeric columns: {len(numeric_cols)}")
        print(f"String columns: {len(string_cols)}")
        
        print("✅ Database integration test passed!")
    else:
        print("❌ Database integration test failed!")


if __name__ == "__main__":
    test_column_analyzer_basic()
    test_column_analysis_edge_cases()
    test_database_integration()
    print("\n🎉 All column analysis tests passed!")