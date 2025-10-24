"""
Unit tests for the importer module.

Tests for FileImporter class including:
- File type detection
- CSV import functionality
- Excel import functionality
- Parquet import functionality
- Error handling and validation
"""

import pytest
import pandas as pd
from pathlib import Path

from localsql_explorer.importer import FileImporter, ImportOptions, ImportResult


class TestFileImporter:
    """Test suite for FileImporter class."""
    
    def test_init(self, file_importer: FileImporter):
        """Test FileImporter initialization."""
        assert file_importer.import_history == []
    
    def test_detect_file_type_csv(self, file_importer: FileImporter):
        """Test detecting CSV file type."""
        assert file_importer.detect_file_type("test.csv") == "csv"
        assert file_importer.detect_file_type("test.CSV") == "csv"
    
    def test_detect_file_type_excel(self, file_importer: FileImporter):
        """Test detecting Excel file types."""
        assert file_importer.detect_file_type("test.xlsx") == "excel"
        assert file_importer.detect_file_type("test.xls") == "excel"
        assert file_importer.detect_file_type("test.XLSX") == "excel"
    
    def test_detect_file_type_parquet(self, file_importer: FileImporter):
        """Test detecting Parquet file types."""
        assert file_importer.detect_file_type("test.parquet") == "parquet"
        assert file_importer.detect_file_type("test.pq") == "parquet"
        assert file_importer.detect_file_type("test.PARQUET") == "parquet"
    
    def test_detect_file_type_unsupported(self, file_importer: FileImporter):
        """Test detecting unsupported file types."""
        with pytest.raises(ValueError, match="Unsupported file type"):
            file_importer.detect_file_type("test.txt")
        
        with pytest.raises(ValueError, match="Unsupported file type"):
            file_importer.detect_file_type("test.json")
    
    def test_import_csv_success(self, file_importer: FileImporter, sample_csv_file: Path):
        """Test successful CSV import."""
        result = file_importer.import_csv(sample_csv_file)
        
        assert result.success is True
        assert result.dataframe is not None
        assert result.file_type == "csv"
        assert result.file_path == str(sample_csv_file)
        assert result.error is None
        assert len(result.dataframe) == 5  # Based on sample data
        assert "id" in result.dataframe.columns
        assert "name" in result.dataframe.columns
    
    def test_import_csv_with_options(self, file_importer: FileImporter, temp_dir: Path):
        """Test CSV import with custom options."""
        # Create CSV with custom delimiter
        csv_path = temp_dir / "custom.csv"
        csv_path.write_text("id;name;value\n1;Alice;100\n2;Bob;200")
        
        options = ImportOptions(delimiter=";")
        result = file_importer.import_csv(csv_path, options)
        
        assert result.success is True
        assert len(result.dataframe) == 2
        assert list(result.dataframe.columns) == ["id", "name", "value"]
    
    def test_import_csv_nonexistent_file(self, file_importer: FileImporter, temp_dir: Path):
        """Test CSV import with non-existent file."""
        nonexistent_file = temp_dir / "nonexistent.csv"
        result = file_importer.import_csv(nonexistent_file)
        
        assert result.success is False
        assert result.error is not None
        assert result.dataframe is None
    
    def test_import_excel_success(self, file_importer: FileImporter, sample_excel_file: Path):
        """Test successful Excel import."""
        result = file_importer.import_excel(sample_excel_file)
        
        assert result.success is True
        assert result.dataframe is not None
        assert result.file_type == "excel"
        assert result.file_path == str(sample_excel_file)
        assert result.error is None
        assert len(result.dataframe) == 3  # Based on sample data
        assert "product" in result.dataframe.columns
    
    def test_import_excel_with_sheet_name(self, file_importer: FileImporter, temp_dir: Path):
        """Test Excel import with specific sheet name."""
        excel_path = temp_dir / "multi_sheet.xlsx"
        
        # Create multi-sheet Excel file
        with pd.ExcelWriter(excel_path) as writer:
            pd.DataFrame({"col1": [1, 2]}).to_excel(writer, sheet_name="Sheet1", index=False)
            pd.DataFrame({"col2": [3, 4]}).to_excel(writer, sheet_name="Sheet2", index=False)
        
        options = ImportOptions(sheet_name="Sheet2")
        result = file_importer.import_excel(excel_path, options)
        
        assert result.success is True
        assert "col2" in result.dataframe.columns
        assert "col1" not in result.dataframe.columns
    
    def test_import_parquet_success(self, file_importer: FileImporter, sample_parquet_file: Path):
        """Test successful Parquet import."""
        result = file_importer.import_parquet(sample_parquet_file)
        
        assert result.success is True
        assert result.dataframe is not None
        assert result.file_type == "parquet"
        assert result.file_path == str(sample_parquet_file)
        assert result.error is None
        assert len(result.dataframe) == 5  # Based on sample data
        assert "timestamp" in result.dataframe.columns
    
    def test_import_parquet_with_row_limit(self, file_importer: FileImporter, sample_parquet_file: Path):
        """Test Parquet import with row limit."""
        options = ImportOptions(max_rows=2)
        result = file_importer.import_parquet(sample_parquet_file, options)
        
        assert result.success is True
        assert len(result.dataframe) == 2
        assert len(result.warnings) > 0  # Should warn about limiting rows
    
    def test_import_file_auto_detect_csv(self, file_importer: FileImporter, sample_csv_file: Path):
        """Test automatic file type detection for CSV."""
        result = file_importer.import_file(sample_csv_file)
        
        assert result.success is True
        assert result.file_type == "csv"
    
    def test_import_file_auto_detect_excel(self, file_importer: FileImporter, sample_excel_file: Path):
        """Test automatic file type detection for Excel."""
        result = file_importer.import_file(sample_excel_file)
        
        assert result.success is True
        assert result.file_type == "excel"
    
    def test_import_file_auto_detect_parquet(self, file_importer: FileImporter, sample_parquet_file: Path):
        """Test automatic file type detection for Parquet."""
        result = file_importer.import_file(sample_parquet_file)
        
        assert result.success is True
        assert result.file_type == "parquet"
    
    def test_import_file_nonexistent(self, file_importer: FileImporter, temp_dir: Path):
        """Test importing non-existent file."""
        nonexistent_file = temp_dir / "nonexistent.csv"
        result = file_importer.import_file(nonexistent_file)
        
        assert result.success is False
        assert "File not found" in result.error
    
    def test_get_suggested_table_name(self, file_importer: FileImporter):
        """Test table name generation from file paths."""
        # Basic file name
        name = file_importer.get_suggested_table_name("data.csv")
        assert name == "data"
        
        # File with path
        name = file_importer.get_suggested_table_name("/path/to/sales_data.xlsx")
        assert name == "sales_data"
        
        # File with spaces and special characters
        name = file_importer.get_suggested_table_name("Sales Data (2023).csv")
        assert name == "sales_data_2023"
        
        # File starting with number
        name = file_importer.get_suggested_table_name("2023_sales.csv")
        assert name == "table_2023_sales"
        
        # Empty or problematic names
        name = file_importer.get_suggested_table_name("_.csv")
        assert name == "imported_table"
    
    def test_import_history_tracking(self, file_importer: FileImporter, sample_csv_file: Path):
        """Test that import operations are tracked in history."""
        assert len(file_importer.import_history) == 0
        
        result1 = file_importer.import_file(sample_csv_file)
        assert len(file_importer.import_history) == 1
        assert file_importer.import_history[0] == result1
        
        # Import another file
        result2 = file_importer.import_csv(sample_csv_file)
        assert len(file_importer.import_history) == 2
    
    def test_get_import_history(self, file_importer: FileImporter, sample_csv_file: Path):
        """Test getting import history."""
        file_importer.import_file(sample_csv_file)
        
        history = file_importer.get_import_history()
        assert len(history) == 1
        assert isinstance(history[0], ImportResult)
        
        # Ensure it's a copy (modifications don't affect original)
        history.clear()
        assert len(file_importer.import_history) == 1
    
    def test_clear_history(self, file_importer: FileImporter, sample_csv_file: Path):
        """Test clearing import history."""
        file_importer.import_file(sample_csv_file)
        assert len(file_importer.import_history) == 1
        
        file_importer.clear_history()
        assert len(file_importer.import_history) == 0


class TestImportOptions:
    """Test suite for ImportOptions model."""
    
    def test_default_options(self):
        """Test default import options."""
        options = ImportOptions()
        
        assert options.delimiter == ","
        assert options.encoding == "utf-8"
        assert options.header_row == 0
        assert options.skip_rows == 0
        assert options.sheet_name == 0
        assert options.max_rows is None
        assert options.infer_types is True
    
    def test_custom_options(self):
        """Test custom import options."""
        options = ImportOptions(
            delimiter=";",
            encoding="latin-1",
            header_row=1,
            skip_rows=2,
            sheet_name="Data",
            max_rows=1000,
            infer_types=False
        )
        
        assert options.delimiter == ";"
        assert options.encoding == "latin-1"
        assert options.header_row == 1
        assert options.skip_rows == 2
        assert options.sheet_name == "Data"
        assert options.max_rows == 1000
        assert options.infer_types is False


class TestImportResult:
    """Test suite for ImportResult model."""
    
    def test_successful_result(self, sample_dataframe: pd.DataFrame):
        """Test successful import result."""
        result = ImportResult(
            success=True,
            dataframe=sample_dataframe,
            file_path="/path/to/file.csv",
            file_type="csv"
        )
        
        assert result.success is True
        assert result.dataframe is not None
        assert result.file_path == "/path/to/file.csv"
        assert result.file_type == "csv"
        assert result.error is None
        assert result.warnings == []
    
    def test_failed_result(self):
        """Test failed import result."""
        result = ImportResult(
            success=False,
            file_path="/path/to/file.csv",
            file_type="csv",
            error="File not found"
        )
        
        assert result.success is False
        assert result.dataframe is None
        assert result.error == "File not found"
    
    def test_result_with_warnings(self, sample_dataframe: pd.DataFrame):
        """Test result with warnings."""
        result = ImportResult(
            success=True,
            dataframe=sample_dataframe,
            file_path="/path/to/file.csv",
            file_type="csv",
            warnings=["Warning 1", "Warning 2"]
        )
        
        assert result.success is True
        assert len(result.warnings) == 2
        assert "Warning 1" in result.warnings