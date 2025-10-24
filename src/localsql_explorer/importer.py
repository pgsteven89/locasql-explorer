"""
File importer module for reading CSV, XLSX, and Parquet files.

This module provides the FileImporter class which handles:
- Reading various file formats (CSV, Excel, Parquet)
- Data validation and type inference
- Error handling for corrupt or invalid files
- Integration with DatabaseManager for table registration
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd
import pyarrow.parquet as pq
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ImportOptions(BaseModel):
    """Options for file import operations."""
    
    # CSV options
    delimiter: str = Field(",", description="CSV delimiter")
    encoding: str = Field("utf-8", description="File encoding")
    header_row: Optional[int] = Field(0, description="Header row index (0-based)")
    skip_rows: int = Field(0, description="Number of rows to skip")
    
    # Excel options
    sheet_name: Union[str, int] = Field(0, description="Excel sheet name or index")
    
    # General options
    max_rows: Optional[int] = Field(None, description="Maximum rows to read")
    infer_types: bool = Field(True, description="Whether to infer data types")


class ImportResult(BaseModel):
    """Result of a file import operation."""
    
    model_config = {"arbitrary_types_allowed": True}
    
    success: bool = Field(..., description="Whether import was successful")
    dataframe: Optional[pd.DataFrame] = Field(None, description="Imported data")
    file_path: str = Field(..., description="Source file path")
    file_type: str = Field(..., description="Detected file type")
    error: Optional[str] = Field(None, description="Error message if failed")
    warnings: List[str] = Field(default_factory=list, description="Import warnings")
    metadata: Dict = Field(default_factory=dict, description="Additional metadata")


class FileImporter:
    """
    Handles importing data from various file formats.
    
    Supported formats:
    - CSV (.csv)
    - Excel (.xlsx, .xls)
    - Parquet (.parquet, .pq)
    """
    
    SUPPORTED_EXTENSIONS = {
        '.csv': 'csv',
        '.xlsx': 'excel',
        '.xls': 'excel',
        '.parquet': 'parquet',
        '.pq': 'parquet'
    }
    
    def __init__(self):
        """Initialize the file importer."""
        self.import_history: List[ImportResult] = []
    
    def detect_file_type(self, file_path: Union[str, Path]) -> str:
        """
        Detect file type based on file extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            str: Detected file type
            
        Raises:
            ValueError: If file type is not supported
        """
        file_path = Path(file_path)
        extension = file_path.suffix.lower()
        
        if extension not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {extension}")
        
        return self.SUPPORTED_EXTENSIONS[extension]
    
    def import_csv(
        self,
        file_path: Union[str, Path],
        options: Optional[ImportOptions] = None
    ) -> ImportResult:
        """
        Import data from a CSV file.
        
        Args:
            file_path: Path to CSV file
            options: Import options
            
        Returns:
            ImportResult: Result of the import operation
        """
        file_path = Path(file_path)
        options = options or ImportOptions()
        warnings = []
        
        try:
            # Prepare pandas read_csv arguments
            read_args = {
                'filepath_or_buffer': file_path,
                'delimiter': options.delimiter,
                'encoding': options.encoding,
                'header': options.header_row,
                'skiprows': options.skip_rows,
                'nrows': options.max_rows,
            }
            
            # Handle type inference
            if options.infer_types:
                read_args['dtype'] = None  # Let pandas infer types
            else:
                read_args['dtype'] = str  # Read everything as strings
            
            # Read the CSV file
            df = pd.read_csv(**read_args)
            
            # Validate the result
            if df.empty:
                warnings.append("File contains no data")
            
            # Check for missing column names
            unnamed_cols = [col for col in df.columns if col.startswith('Unnamed:')]
            if unnamed_cols:
                warnings.append(f"Found {len(unnamed_cols)} unnamed columns")
            
            metadata = {
                'delimiter': options.delimiter,
                'encoding': options.encoding,
                'original_shape': df.shape,
                'memory_usage': df.memory_usage(deep=True).sum()
            }
            
            logger.info(f"Successfully imported CSV: {file_path} ({df.shape[0]} rows, {df.shape[1]} columns)")
            
            result = ImportResult(
                success=True,
                dataframe=df,
                file_path=str(file_path),
                file_type='csv',
                warnings=warnings,
                metadata=metadata
            )
            
        except Exception as e:
            error_msg = f"Failed to import CSV file {file_path}: {str(e)}"
            logger.error(error_msg)
            
            result = ImportResult(
                success=False,
                file_path=str(file_path),
                file_type='csv',
                error=error_msg
            )
        
        self.import_history.append(result)
        return result
    
    def import_excel(
        self,
        file_path: Union[str, Path],
        options: Optional[ImportOptions] = None
    ) -> ImportResult:
        """
        Import data from an Excel file.
        
        Args:
            file_path: Path to Excel file
            options: Import options
            
        Returns:
            ImportResult: Result of the import operation
        """
        file_path = Path(file_path)
        options = options or ImportOptions()
        warnings = []
        
        try:
            # Prepare pandas read_excel arguments
            read_args = {
                'io': file_path,
                'sheet_name': options.sheet_name,
                'header': options.header_row,
                'skiprows': options.skip_rows,
                'nrows': options.max_rows,
            }
            
            # Handle type inference
            if not options.infer_types:
                read_args['dtype'] = str
            
            # Read the Excel file
            df = pd.read_excel(**read_args)
            
            # Validate the result
            if df.empty:
                warnings.append("Sheet contains no data")
            
            # Check for missing column names
            unnamed_cols = [col for col in df.columns if str(col).startswith('Unnamed:')]
            if unnamed_cols:
                warnings.append(f"Found {len(unnamed_cols)} unnamed columns")
            
            metadata = {
                'sheet_name': options.sheet_name,
                'original_shape': df.shape,
                'memory_usage': df.memory_usage(deep=True).sum()
            }
            
            logger.info(f"Successfully imported Excel: {file_path} ({df.shape[0]} rows, {df.shape[1]} columns)")
            
            result = ImportResult(
                success=True,
                dataframe=df,
                file_path=str(file_path),
                file_type='excel',
                warnings=warnings,
                metadata=metadata
            )
            
        except Exception as e:
            error_msg = f"Failed to import Excel file {file_path}: {str(e)}"
            logger.error(error_msg)
            
            result = ImportResult(
                success=False,
                file_path=str(file_path),
                file_type='excel',
                error=error_msg
            )
        
        self.import_history.append(result)
        return result
    
    def import_parquet(
        self,
        file_path: Union[str, Path],
        options: Optional[ImportOptions] = None
    ) -> ImportResult:
        """
        Import data from a Parquet file.
        
        Args:
            file_path: Path to Parquet file
            options: Import options
            
        Returns:
            ImportResult: Result of the import operation
        """
        file_path = Path(file_path)
        options = options or ImportOptions()
        warnings = []
        
        try:
            # Read the Parquet file
            if options.max_rows:
                # Use pyarrow for row limiting
                table = pq.read_table(file_path)
                if len(table) > options.max_rows:
                    table = table.slice(0, options.max_rows)
                    warnings.append(f"Limited to first {options.max_rows} rows")
                df = table.to_pandas()
            else:
                # Use pandas for simplicity
                df = pd.read_parquet(file_path)
            
            # Handle type conversion if needed
            if not options.infer_types:
                df = df.astype(str)
                warnings.append("Converted all columns to string type")
            
            # Validate the result
            if df.empty:
                warnings.append("File contains no data")
            
            metadata = {
                'original_shape': df.shape,
                'memory_usage': df.memory_usage(deep=True).sum(),
                'parquet_metadata': str(pq.read_metadata(file_path))
            }
            
            logger.info(f"Successfully imported Parquet: {file_path} ({df.shape[0]} rows, {df.shape[1]} columns)")
            
            result = ImportResult(
                success=True,
                dataframe=df,
                file_path=str(file_path),
                file_type='parquet',
                warnings=warnings,
                metadata=metadata
            )
            
        except Exception as e:
            error_msg = f"Failed to import Parquet file {file_path}: {str(e)}"
            logger.error(error_msg)
            
            result = ImportResult(
                success=False,
                file_path=str(file_path),
                file_type='parquet',
                error=error_msg
            )
        
        self.import_history.append(result)
        return result
    
    def import_file(
        self,
        file_path: Union[str, Path],
        options: Optional[ImportOptions] = None,
        table_name: Optional[str] = None
    ) -> ImportResult:
        """
        Import a file automatically detecting its type.
        
        Args:
            file_path: Path to the file
            options: Import options
            table_name: Optional table name (defaults to filename without extension)
            
        Returns:
            ImportResult: Result of the import operation
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            error_msg = f"File not found: {file_path}"
            logger.error(error_msg)
            return ImportResult(
                success=False,
                file_path=str(file_path),
                file_type='unknown',
                error=error_msg
            )
        
        try:
            file_type = self.detect_file_type(file_path)
            
            # Route to appropriate import method
            if file_type == 'csv':
                result = self.import_csv(file_path, options)
            elif file_type == 'excel':
                result = self.import_excel(file_path, options)
            elif file_type == 'parquet':
                result = self.import_parquet(file_path, options)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
            
            return result
            
        except Exception as e:
            error_msg = f"Failed to import file {file_path}: {str(e)}"
            logger.error(error_msg)
            
            return ImportResult(
                success=False,
                file_path=str(file_path),
                file_type='unknown',
                error=error_msg
            )
    
    def get_suggested_table_name(self, file_path: Union[str, Path]) -> str:
        """
        Generate a suggested table name from the file path.
        
        Args:
            file_path: Path to the file
            
        Returns:
            str: Suggested table name
        """
        file_path = Path(file_path)
        
        # Use filename without extension
        name = file_path.stem
        
        # Clean the name to be SQL-friendly
        # Replace spaces and special characters with underscores
        import re
        name = re.sub(r'[^\w]', '_', name)
        
        # Remove multiple consecutive underscores
        name = re.sub(r'_+', '_', name)
        
        # Remove leading/trailing underscores
        name = name.strip('_')
        
        # Ensure it starts with a letter
        if name and not name[0].isalpha():
            name = 'table_' + name
        
        # Fallback if name is empty
        if not name:
            name = 'imported_table'
        
        return name.lower()
    
    def get_import_history(self) -> List[ImportResult]:
        """Get the history of import operations."""
        return self.import_history.copy()
    
    def clear_history(self) -> None:
        """Clear the import history."""
        self.import_history.clear()