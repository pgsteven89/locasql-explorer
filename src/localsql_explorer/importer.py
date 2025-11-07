"""
File importer module for reading CSV, XLSX, and Parquet files.

This module provides the FileImporter class which handles:
- Reading various file formats (CSV, Excel, Parquet)
- Data validation and type inference
- Error handling for corrupt or invalid files
- Integration with DatabaseManager for table registration
"""

import csv
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


class SheetInfo(BaseModel):
    """Information about an Excel worksheet."""
    
    model_config = {"arbitrary_types_allowed": True}
    
    name: str = Field(..., description="Sheet name")
    index: int = Field(..., description="Sheet index (0-based)")
    row_count: int = Field(..., description="Number of rows with data")
    column_count: int = Field(..., description="Number of columns with data")
    columns: List[str] = Field(default_factory=list, description="Column headers")
    sample_data: Optional[pd.DataFrame] = Field(None, description="Sample rows for preview")
    is_empty: bool = Field(False, description="Whether sheet appears to be empty")
    has_merged_cells: bool = Field(False, description="Whether sheet contains merged cells")


class BatchImportResult(BaseModel):
    """Result of importing multiple sheets from an Excel file."""
    
    model_config = {"arbitrary_types_allowed": True}
    
    success: bool = Field(..., description="Whether overall import was successful")
    file_path: str = Field(..., description="Source Excel file path")
    total_sheets: int = Field(..., description="Total number of sheets processed")
    successful_imports: List[ImportResult] = Field(default_factory=list, description="Successfully imported sheets")
    failed_imports: List[Tuple[str, str]] = Field(default_factory=list, description="Failed sheet imports (name, error)")
    warnings: List[str] = Field(default_factory=list, description="Overall import warnings")
    table_names: List[str] = Field(default_factory=list, description="Names of created tables")


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
    
    def detect_csv_delimiter(
        self,
        file_path: Union[str, Path],
        sample_size: int = 8192
    ) -> str:
        """
        Detect the delimiter used in a CSV file.
        
        Args:
            file_path: Path to CSV file
            sample_size: Number of bytes to read for detection (default: 8KB)
            
        Returns:
            str: Detected delimiter (comma, tab, pipe, semicolon, or comma as fallback)
        """
        file_path = Path(file_path)
        
        try:
            # Read a sample of the file
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                sample = f.read(sample_size)
            
            # Use csv.Sniffer to detect the delimiter
            sniffer = csv.Sniffer()
            
            # Try to detect delimiter
            try:
                dialect = sniffer.sniff(sample, delimiters=',\t|;')
                detected_delimiter = dialect.delimiter
                logger.info(f"Detected delimiter for {file_path.name}: {repr(detected_delimiter)}")
                return detected_delimiter
            except csv.Error:
                # If Sniffer fails, fall back to manual detection
                logger.warning(f"CSV Sniffer failed for {file_path.name}, using manual detection")
                
                # Count occurrences of common delimiters
                lines = sample.split('\n')[:10]  # Check first 10 lines
                if not lines:
                    return ','
                
                delimiter_counts = {
                    ',': sum(line.count(',') for line in lines),
                    '\t': sum(line.count('\t') for line in lines),
                    '|': sum(line.count('|') for line in lines),
                    ';': sum(line.count(';') for line in lines)
                }
                
                # Return delimiter with highest count
                detected = max(delimiter_counts, key=delimiter_counts.get)
                if delimiter_counts[detected] > 0:
                    logger.info(f"Manually detected delimiter for {file_path.name}: {repr(detected)}")
                    return detected
                else:
                    logger.warning(f"No delimiter detected for {file_path.name}, defaulting to comma")
                    return ','
                    
        except Exception as e:
            logger.warning(f"Error detecting delimiter for {file_path}: {str(e)}, defaulting to comma")
            return ','
    
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
        Import data from a CSV file with automatic delimiter detection.
        
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
            # Auto-detect delimiter if default comma is specified
            # This assumes comma is the default and triggers auto-detection
            detected_delimiter = None
            if options.delimiter == ",":
                detected_delimiter = self.detect_csv_delimiter(file_path)
                if detected_delimiter != ",":
                    warnings.append(f"Auto-detected delimiter: {repr(detected_delimiter)}")
                    options.delimiter = detected_delimiter
            
            # Prepare pandas read_csv arguments
            read_args = {
                'filepath_or_buffer': file_path,
                'delimiter': options.delimiter,
                'encoding': options.encoding,
                'header': options.header_row,
                'skiprows': options.skip_rows,
                'nrows': options.max_rows,
                'low_memory': False,  # Prevent dtype warnings for large files
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
                'detected_delimiter': detected_delimiter,
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
    
    def detect_excel_sheets(self, file_path: Union[str, Path]) -> List[SheetInfo]:
        """
        Analyze an Excel file and return information about all worksheets.
        
        Args:
            file_path: Path to Excel file
            
        Returns:
            List of SheetInfo objects containing metadata about each sheet
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is not a valid Excel file
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if file_path.suffix.lower() not in ['.xlsx', '.xls']:
            raise ValueError(f"Not an Excel file: {file_path}")
        
        try:
            # Read Excel file to get sheet information
            excel_file = pd.ExcelFile(file_path)
            sheet_infos = []
            
            for index, sheet_name in enumerate(excel_file.sheet_names):
                try:
                    # Read just the header and a few sample rows for analysis
                    sample_df = pd.read_excel(
                        excel_file, 
                        sheet_name=sheet_name,
                        nrows=10  # Read first 10 rows for preview
                    )
                    
                    # Get full sheet dimensions (read without nrows limit to count)
                    full_df = pd.read_excel(excel_file, sheet_name=sheet_name)
                    actual_rows = len(full_df.dropna(how='all'))  # Exclude empty rows
                    actual_cols = len(full_df.dropna(axis=1, how='all').columns)  # Exclude empty columns
                    
                    # Determine if sheet is effectively empty
                    is_empty = actual_rows <= 1 or actual_cols == 0 or full_df.empty
                    
                    # Create sample data for preview (limit to first 5 rows)
                    preview_df = sample_df.head(5) if not sample_df.empty else pd.DataFrame()
                    
                    # Get column headers
                    columns = list(full_df.columns) if not full_df.empty else []
                    
                    sheet_info = SheetInfo(
                        name=sheet_name,
                        index=index,
                        row_count=actual_rows,
                        column_count=actual_cols,
                        columns=columns,
                        sample_data=preview_df if not preview_df.empty else None,
                        is_empty=is_empty,
                        has_merged_cells=False  # We could detect this with openpyxl if needed
                    )
                    
                    sheet_infos.append(sheet_info)
                    
                except Exception as e:
                    logger.warning(f"Could not analyze sheet '{sheet_name}': {e}")
                    # Create a minimal SheetInfo for problematic sheets
                    sheet_info = SheetInfo(
                        name=sheet_name,
                        index=index,
                        row_count=0,
                        column_count=0,
                        columns=[],
                        sample_data=None,
                        is_empty=True,
                        has_merged_cells=False
                    )
                    sheet_infos.append(sheet_info)
            
            excel_file.close()
            return sheet_infos
            
        except Exception as e:
            error_msg = f"Failed to analyze Excel file {file_path}: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def import_excel_multiple_sheets(
        self,
        file_path: Union[str, Path],
        selected_sheets: List[Union[str, int]],
        base_table_name: Optional[str] = None
    ) -> BatchImportResult:
        """
        Import multiple sheets from an Excel file as separate tables.
        
        Args:
            file_path: Path to Excel file
            selected_sheets: List of sheet names or indices to import
            base_table_name: Base name for tables (defaults to filename)
            
        Returns:
            BatchImportResult containing information about all import operations
        """
        file_path = Path(file_path)
        
        if not base_table_name:
            base_table_name = file_path.stem
        
        successful_imports = []
        failed_imports = []
        warnings = []
        table_names = []
        
        total_sheets = len(selected_sheets)
        
        for sheet_identifier in selected_sheets:
            try:
                # Create import options for this specific sheet
                options = ImportOptions(sheet_name=sheet_identifier)
                
                # Import the individual sheet
                result = self.import_excel(file_path, options)
                
                if result.success:
                    # Generate table name
                    if isinstance(sheet_identifier, int):
                        # Convert index to sheet name for table naming
                        try:
                            excel_file = pd.ExcelFile(file_path)
                            sheet_name = excel_file.sheet_names[sheet_identifier]
                            excel_file.close()
                        except:
                            sheet_name = f"sheet_{sheet_identifier}"
                    else:
                        sheet_name = str(sheet_identifier)
                    
                    # Sanitize sheet name for SQL table naming
                    sanitized_sheet_name = self._sanitize_name(sheet_name)
                    table_name = f"{self._sanitize_name(base_table_name)}_{sanitized_sheet_name}"
                    
                    # Update result with final table name
                    result.metadata['table_name'] = table_name
                    result.metadata['sheet_name'] = sheet_name
                    result.metadata['base_file_name'] = base_table_name
                    
                    successful_imports.append(result)
                    table_names.append(table_name)
                    
                    logger.info(f"Successfully imported sheet '{sheet_name}' as table '{table_name}'")
                    
                else:
                    sheet_display_name = str(sheet_identifier)
                    failed_imports.append((sheet_display_name, result.error or "Unknown error"))
                    logger.error(f"Failed to import sheet '{sheet_display_name}': {result.error}")
                    
            except Exception as e:
                sheet_display_name = str(sheet_identifier)
                error_msg = str(e)
                failed_imports.append((sheet_display_name, error_msg))
                logger.error(f"Exception importing sheet '{sheet_display_name}': {error_msg}")
        
        # Determine overall success
        overall_success = len(successful_imports) > 0
        
        # Generate warnings
        if failed_imports:
            warnings.append(f"{len(failed_imports)} out of {total_sheets} sheets failed to import")
        
        if len(successful_imports) < total_sheets:
            warnings.append(f"Only {len(successful_imports)} out of {total_sheets} sheets imported successfully")
        
        # Create batch result
        batch_result = BatchImportResult(
            success=overall_success,
            file_path=str(file_path),
            total_sheets=total_sheets,
            successful_imports=successful_imports,
            failed_imports=failed_imports,
            warnings=warnings,
            table_names=table_names
        )
        
        logger.info(f"Batch import completed: {len(successful_imports)}/{total_sheets} sheets successful")
        
        return batch_result
    
    def _sanitize_name(self, name: str) -> str:
        """
        Sanitize a name for use as a SQL table name.
        
        Args:
            name: Raw name to sanitize
            
        Returns:
            Sanitized name safe for SQL usage
        """
        import re
        # Replace special characters with underscores
        sanitized = re.sub(r'[^\w]', '_', name)
        # Remove multiple consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        # Ensure it's not empty
        if not sanitized:
            sanitized = 'unnamed'
        return sanitized.lower()
    
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