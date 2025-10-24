"""
Test configuration and shared fixtures for LocalSQL Explorer tests.

This module provides:
- Common test fixtures
- Test configuration
- Shared utilities for testing
"""

import tempfile
from pathlib import Path
from typing import Generator

import pandas as pd
import pytest

from localsql_explorer.database import DatabaseManager
from localsql_explorer.importer import FileImporter
from localsql_explorer.exporter import ResultExporter
from localsql_explorer.models import AppConfig, UserPreferences


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Provide a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_csv_file(temp_dir: Path) -> Path:
    """Create a sample CSV file for testing."""
    csv_path = temp_dir / "sample.csv"
    
    # Create sample data
    data = {
        'id': [1, 2, 3, 4, 5],
        'name': ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve'],
        'age': [25, 30, 35, 28, 32],
        'salary': [50000.0, 60000.0, 70000.0, 55000.0, 65000.0],
        'active': [True, True, False, True, True]
    }
    
    df = pd.DataFrame(data)
    df.to_csv(csv_path, index=False)
    
    return csv_path


@pytest.fixture
def sample_excel_file(temp_dir: Path) -> Path:
    """Create a sample Excel file for testing."""
    excel_path = temp_dir / "sample.xlsx"
    
    # Create sample data
    data = {
        'product': ['Widget A', 'Widget B', 'Widget C'],
        'price': [10.99, 15.50, 8.25],
        'quantity': [100, 50, 200],
        'category': ['Electronics', 'Home', 'Electronics']
    }
    
    df = pd.DataFrame(data)
    df.to_excel(excel_path, index=False)
    
    return excel_path


@pytest.fixture
def sample_parquet_file(temp_dir: Path) -> Path:
    """Create a sample Parquet file for testing."""
    parquet_path = temp_dir / "sample.parquet"
    
    # Create sample data with different types
    data = {
        'timestamp': pd.date_range('2023-01-01', periods=5, freq='D'),
        'metric': [1.1, 2.2, 3.3, 4.4, 5.5],
        'category': ['A', 'B', 'A', 'C', 'B'],
        'count': [10, 20, 15, 25, 12]
    }
    
    df = pd.DataFrame(data)
    df.to_parquet(parquet_path, index=False)
    
    return parquet_path


@pytest.fixture
def sample_dataframe() -> pd.DataFrame:
    """Provide a sample DataFrame for testing."""
    return pd.DataFrame({
        'id': [1, 2, 3],
        'name': ['Test1', 'Test2', 'Test3'],
        'value': [10.5, 20.3, 30.1]
    })


@pytest.fixture
def db_manager(temp_dir: Path) -> Generator[DatabaseManager, None, None]:
    """Provide a DatabaseManager instance for testing."""
    db = DatabaseManager()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def persistent_db_manager(temp_dir: Path) -> Generator[DatabaseManager, None, None]:
    """Provide a persistent DatabaseManager instance for testing."""
    db_path = temp_dir / "test.duckdb"
    db = DatabaseManager(str(db_path))
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def file_importer() -> FileImporter:
    """Provide a FileImporter instance for testing."""
    return FileImporter()


@pytest.fixture
def result_exporter() -> ResultExporter:
    """Provide a ResultExporter instance for testing."""
    return ResultExporter()


@pytest.fixture
def app_config(temp_dir: Path) -> AppConfig:
    """Provide an AppConfig instance for testing."""
    return AppConfig(
        config_dir=temp_dir / "config",
        data_dir=temp_dir / "data",
        log_dir=temp_dir / "logs"
    )


@pytest.fixture
def user_preferences() -> UserPreferences:
    """Provide UserPreferences for testing."""
    return UserPreferences()


# Test data generators
def create_test_dataframe(rows: int = 100, cols: int = 5) -> pd.DataFrame:
    """Create a test DataFrame with specified dimensions."""
    import random
    import string
    
    data = {}
    
    for i in range(cols):
        if i == 0:
            # ID column
            data[f'id'] = list(range(1, rows + 1))
        elif i == 1:
            # String column
            data[f'name'] = [
                ''.join(random.choices(string.ascii_letters, k=10))
                for _ in range(rows)
            ]
        elif i == 2:
            # Integer column
            data[f'count'] = [random.randint(1, 1000) for _ in range(rows)]
        elif i == 3:
            # Float column
            data[f'value'] = [random.uniform(0, 100) for _ in range(rows)]
        else:
            # Boolean column
            data[f'flag_{i}'] = [random.choice([True, False]) for _ in range(rows)]
    
    return pd.DataFrame(data)


# Test utilities
def assert_dataframes_equal(df1: pd.DataFrame, df2: pd.DataFrame, check_dtype: bool = True):
    """Assert that two DataFrames are equal with better error messages."""
    try:
        pd.testing.assert_frame_equal(df1, df2, check_dtype=check_dtype)
    except AssertionError as e:
        pytest.fail(f"DataFrames are not equal:\n{str(e)}")


def assert_file_exists(file_path: Path):
    """Assert that a file exists."""
    assert file_path.exists(), f"File does not exist: {file_path}"


def assert_file_not_empty(file_path: Path):
    """Assert that a file exists and is not empty."""
    assert_file_exists(file_path)
    assert file_path.stat().st_size > 0, f"File is empty: {file_path}"