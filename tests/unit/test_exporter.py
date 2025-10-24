"""Unit tests for the exporter module."""

import pytest
import pandas as pd
from pathlib import Path

from localsql_explorer.exporter import ResultExporter, ExportOptions, ExportResult


class TestResultExporter:
    """Test suite for ResultExporter class."""
    
    def test_init(self, result_exporter: ResultExporter):
        """Test ResultExporter initialization."""
        assert result_exporter.export_history == []
    
    def test_export_to_csv_success(self, result_exporter: ResultExporter, sample_dataframe: pd.DataFrame, temp_dir: Path):
        """Test successful CSV export."""
        output_file = temp_dir / "test_export.csv"
        
        result = result_exporter.export_to_csv(sample_dataframe, output_file)
        
        assert result.success is True
        assert result.file_path == str(output_file)
        assert result.file_type == "csv"
        assert result.row_count == len(sample_dataframe)
        assert result.error is None
        
        # Verify file exists and contains correct data
        assert output_file.exists()
        exported_df = pd.read_csv(output_file)
        pd.testing.assert_frame_equal(sample_dataframe, exported_df)
    
    def test_export_to_excel_success(self, result_exporter: ResultExporter, sample_dataframe: pd.DataFrame, temp_dir: Path):
        """Test successful Excel export."""
        output_file = temp_dir / "test_export.xlsx"
        
        result = result_exporter.export_to_excel(sample_dataframe, output_file)
        
        assert result.success is True
        assert result.file_type == "excel"
        assert output_file.exists()
        
        # Verify file contains correct data
        exported_df = pd.read_excel(output_file)
        pd.testing.assert_frame_equal(sample_dataframe, exported_df)
    
    def test_export_to_parquet_success(self, result_exporter: ResultExporter, sample_dataframe: pd.DataFrame, temp_dir: Path):
        """Test successful Parquet export."""
        output_file = temp_dir / "test_export.parquet"
        
        result = result_exporter.export_to_parquet(sample_dataframe, output_file)
        
        assert result.success is True
        assert result.file_type == "parquet"
        assert output_file.exists()
        
        # Verify file contains correct data
        exported_df = pd.read_parquet(output_file)
        pd.testing.assert_frame_equal(sample_dataframe, exported_df)


class TestExportOptions:
    """Test suite for ExportOptions model."""
    
    def test_default_options(self):
        """Test default export options."""
        options = ExportOptions()
        
        assert options.delimiter == ","
        assert options.encoding == "utf-8"
        assert options.include_index is False
        assert options.include_header is True
        assert options.sheet_name == "Sheet1"
        assert options.overwrite is False


# Additional test files would go here for other modules...