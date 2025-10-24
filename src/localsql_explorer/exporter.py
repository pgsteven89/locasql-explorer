"""
Result exporter module for saving query results to various file formats.

This module provides the ResultExporter class which handles:
- Exporting DataFrame results to CSV, Excel, and Parquet formats
- Flexible export options and formatting
- Error handling and validation
- Integration with query results from DatabaseManager
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas as pd
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ExportOptions(BaseModel):
    """Options for export operations."""
    
    # CSV options
    delimiter: str = Field(",", description="CSV delimiter")
    encoding: str = Field("utf-8", description="File encoding")
    include_index: bool = Field(False, description="Whether to include row index")
    include_header: bool = Field(True, description="Whether to include column headers")
    
    # Excel options
    sheet_name: str = Field("Sheet1", description="Excel sheet name")
    
    # General options
    overwrite: bool = Field(False, description="Whether to overwrite existing files")


class ExportResult(BaseModel):
    """Result of an export operation."""
    
    success: bool = Field(..., description="Whether export was successful")
    file_path: str = Field(..., description="Output file path")
    file_type: str = Field(..., description="Export file type")
    row_count: int = Field(0, description="Number of rows exported")
    file_size: Optional[int] = Field(None, description="Output file size in bytes")
    error: Optional[str] = Field(None, description="Error message if failed")
    warnings: List[str] = Field(default_factory=list, description="Export warnings")


class ResultExporter:
    """
    Handles exporting DataFrame results to various file formats.
    
    Supported formats:
    - CSV (.csv)
    - Excel (.xlsx)
    - Parquet (.parquet)
    """
    
    SUPPORTED_FORMATS = ['csv', 'excel', 'parquet']
    
    def __init__(self):
        """Initialize the result exporter."""
        self.export_history: List[ExportResult] = []
    
    def export_to_csv(
        self,
        dataframe: pd.DataFrame,
        file_path: Union[str, Path],
        options: Optional[ExportOptions] = None
    ) -> ExportResult:
        """
        Export DataFrame to CSV format.
        
        Args:
            dataframe: DataFrame to export
            file_path: Output file path
            options: Export options
            
        Returns:
            ExportResult: Result of the export operation
        """
        file_path = Path(file_path)
        options = options or ExportOptions()
        warnings = []
        
        try:
            # Check if file exists and handle overwrite
            if file_path.exists() and not options.overwrite:
                error_msg = f"File already exists and overwrite is disabled: {file_path}"
                logger.error(error_msg)
                return ExportResult(
                    success=False,
                    file_path=str(file_path),
                    file_type='csv',
                    error=error_msg
                )
            
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare export arguments
            export_args = {
                'path_or_buf': file_path,
                'sep': options.delimiter,
                'encoding': options.encoding,
                'index': options.include_index,
                'header': options.include_header,
            }
            
            # Export to CSV
            dataframe.to_csv(**export_args)
            
            # Get file size
            file_size = file_path.stat().st_size if file_path.exists() else None
            
            logger.info(f"Successfully exported {len(dataframe)} rows to CSV: {file_path}")
            
            result = ExportResult(
                success=True,
                file_path=str(file_path),
                file_type='csv',
                row_count=len(dataframe),
                file_size=file_size,
                warnings=warnings
            )
            
        except Exception as e:
            error_msg = f"Failed to export to CSV {file_path}: {str(e)}"
            logger.error(error_msg)
            
            result = ExportResult(
                success=False,
                file_path=str(file_path),
                file_type='csv',
                error=error_msg
            )
        
        self.export_history.append(result)
        return result
    
    def export_to_excel(
        self,
        dataframe: pd.DataFrame,
        file_path: Union[str, Path],
        options: Optional[ExportOptions] = None
    ) -> ExportResult:
        """
        Export DataFrame to Excel format.
        
        Args:
            dataframe: DataFrame to export
            file_path: Output file path
            options: Export options
            
        Returns:
            ExportResult: Result of the export operation
        """
        file_path = Path(file_path)
        options = options or ExportOptions()
        warnings = []
        
        try:
            # Check if file exists and handle overwrite
            if file_path.exists() and not options.overwrite:
                error_msg = f"File already exists and overwrite is disabled: {file_path}"
                logger.error(error_msg)
                return ExportResult(
                    success=False,
                    file_path=str(file_path),
                    file_type='excel',
                    error=error_msg
                )
            
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare export arguments
            export_args = {
                'excel_writer': file_path,
                'sheet_name': options.sheet_name,
                'index': options.include_index,
                'header': options.include_header,
            }
            
            # Export to Excel
            dataframe.to_excel(**export_args)
            
            # Get file size
            file_size = file_path.stat().st_size if file_path.exists() else None
            
            logger.info(f"Successfully exported {len(dataframe)} rows to Excel: {file_path}")
            
            result = ExportResult(
                success=True,
                file_path=str(file_path),
                file_type='excel',
                row_count=len(dataframe),
                file_size=file_size,
                warnings=warnings
            )
            
        except Exception as e:
            error_msg = f"Failed to export to Excel {file_path}: {str(e)}"
            logger.error(error_msg)
            
            result = ExportResult(
                success=False,
                file_path=str(file_path),
                file_type='excel',
                error=error_msg
            )
        
        self.export_history.append(result)
        return result
    
    def export_to_parquet(
        self,
        dataframe: pd.DataFrame,
        file_path: Union[str, Path],
        options: Optional[ExportOptions] = None
    ) -> ExportResult:
        """
        Export DataFrame to Parquet format.
        
        Args:
            dataframe: DataFrame to export
            file_path: Output file path
            options: Export options
            
        Returns:
            ExportResult: Result of the export operation
        """
        file_path = Path(file_path)
        options = options or ExportOptions()
        warnings = []
        
        try:
            # Check if file exists and handle overwrite
            if file_path.exists() and not options.overwrite:
                error_msg = f"File already exists and overwrite is disabled: {file_path}"
                logger.error(error_msg)
                return ExportResult(
                    success=False,
                    file_path=str(file_path),
                    file_type='parquet',
                    error=error_msg
                )
            
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare export arguments
            export_args = {
                'path': file_path,
                'index': options.include_index,
            }
            
            # Export to Parquet
            dataframe.to_parquet(**export_args)
            
            # Get file size
            file_size = file_path.stat().st_size if file_path.exists() else None
            
            logger.info(f"Successfully exported {len(dataframe)} rows to Parquet: {file_path}")
            
            result = ExportResult(
                success=True,
                file_path=str(file_path),
                file_type='parquet',
                row_count=len(dataframe),
                file_size=file_size,
                warnings=warnings
            )
            
        except Exception as e:
            error_msg = f"Failed to export to Parquet {file_path}: {str(e)}"
            logger.error(error_msg)
            
            result = ExportResult(
                success=False,
                file_path=str(file_path),
                file_type='parquet',
                error=error_msg
            )
        
        self.export_history.append(result)
        return result
    
    def export_result(
        self,
        dataframe: pd.DataFrame,
        file_path: Union[str, Path],
        format_type: Optional[str] = None,
        options: Optional[ExportOptions] = None
    ) -> ExportResult:
        """
        Export DataFrame to the specified format, auto-detecting from file extension.
        
        Args:
            dataframe: DataFrame to export
            file_path: Output file path
            format_type: Optional format override ('csv', 'excel', 'parquet')
            options: Export options
            
        Returns:
            ExportResult: Result of the export operation
        """
        file_path = Path(file_path)
        
        # Detect format from extension if not specified
        if not format_type:
            extension = file_path.suffix.lower()
            format_map = {
                '.csv': 'csv',
                '.xlsx': 'excel',
                '.xls': 'excel',
                '.parquet': 'parquet',
                '.pq': 'parquet'
            }
            
            format_type = format_map.get(extension)
            
            if not format_type:
                error_msg = f"Cannot determine export format from extension: {extension}"
                logger.error(error_msg)
                return ExportResult(
                    success=False,
                    file_path=str(file_path),
                    file_type='unknown',
                    error=error_msg
                )
        
        # Validate format
        if format_type not in self.SUPPORTED_FORMATS:
            error_msg = f"Unsupported export format: {format_type}"
            logger.error(error_msg)
            return ExportResult(
                success=False,
                file_path=str(file_path),
                file_type=format_type,
                error=error_msg
            )
        
        # Route to appropriate export method
        if format_type == 'csv':
            return self.export_to_csv(dataframe, file_path, options)
        elif format_type == 'excel':
            return self.export_to_excel(dataframe, file_path, options)
        elif format_type == 'parquet':
            return self.export_to_parquet(dataframe, file_path, options)
        else:
            error_msg = f"Unsupported format: {format_type}"
            logger.error(error_msg)
            return ExportResult(
                success=False,
                file_path=str(file_path),
                file_type=format_type,
                error=error_msg
            )
    
    def get_export_history(self) -> List[ExportResult]:
        """Get the history of export operations."""
        return self.export_history.copy()
    
    def clear_history(self) -> None:
        """Clear the export history."""
        self.export_history.clear()