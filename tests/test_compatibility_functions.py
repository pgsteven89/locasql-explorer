
import pytest
import pandas as pd
from localsql_explorer.database import DatabaseManager

def test_compatibility_functions():
    """Test that compatibility macros (to_date, to_char, nvl) are registered and working."""

    # Initialize DatabaseManager (in-memory)
    db = DatabaseManager()

    # Create sample data
    data = {
        'id': [1, 2, 3, 4],
        'date_str': ['2023-01-01', '2023-02-15', '2023-03-30', None],
        'value': [10.0, None, 20.0, None]
    }
    df = pd.DataFrame(data)
    # Ensure object dtype for strings for pandas/duckdb compatibility
    df['date_str'] = df['date_str'].astype(object)

    db.register_table('test_table', df)

    # Test to_date
    query_to_date = """
        SELECT to_date(date_str, '%Y-%m-%d') as parsed_date
        FROM test_table
        WHERE id = 1
    """
    result = db.execute_query(query_to_date)
    assert result.success
    assert result.data is not None
    # DuckDB returns DATE which Pandas converts to datetime64[ns]
    assert pd.Timestamp(result.data.iloc[0]['parsed_date']) == pd.Timestamp('2023-01-01')

    # Test to_char
    query_to_char = """
        SELECT to_char(CAST('2023-12-25' AS DATE), '%d/%m/%Y') as formatted_date
    """
    result = db.execute_query(query_to_char)
    assert result.success
    assert result.data.iloc[0]['formatted_date'] == '25/12/2023'

    # Test nvl
    query_nvl = """
        SELECT nvl(value, 0.0) as filled_value
        FROM test_table
        WHERE id = 2
    """
    result = db.execute_query(query_nvl)
    assert result.success
    assert result.data.iloc[0]['filled_value'] == 0.0

    # isnull is reserved in DuckDB so we don't test it as a macro

if __name__ == "__main__":
    test_compatibility_functions()
