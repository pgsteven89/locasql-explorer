"""
Column metadata and analysis models for LocalSQL Explorer.

This module provides detailed column information including:
- Data types and nullable status
- Statistical summaries (min, max, mean, etc.)
- Null counts and unique value counts
- Data quality metrics
- Sample values
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ColumnStatistics(BaseModel):
    """Statistical information for a column."""
    
    count: int = Field(..., description="Total number of values")
    null_count: int = Field(..., description="Number of null values")
    unique_count: int = Field(..., description="Number of unique values")
    duplicate_count: int = Field(..., description="Number of duplicate values")
    
    # Numeric statistics (when applicable)
    min_value: Optional[Union[int, float]] = Field(None, description="Minimum value")
    max_value: Optional[Union[int, float]] = Field(None, description="Maximum value")
    mean: Optional[float] = Field(None, description="Mean value")
    median: Optional[float] = Field(None, description="Median value")
    std_dev: Optional[float] = Field(None, description="Standard deviation")
    
    # String statistics (when applicable)
    min_length: Optional[int] = Field(None, description="Minimum string length")
    max_length: Optional[int] = Field(None, description="Maximum string length")
    avg_length: Optional[float] = Field(None, description="Average string length")
    
    # Date statistics (when applicable)
    min_date: Optional[str] = Field(None, description="Earliest date")
    max_date: Optional[str] = Field(None, description="Latest date")
    
    # Sample values
    sample_values: List[str] = Field(default_factory=list, description="Sample non-null values")
    null_percentage: float = Field(..., description="Percentage of null values")
    unique_percentage: float = Field(..., description="Percentage of unique values")


class ColumnMetadata(BaseModel):
    """Detailed metadata for a single column."""
    
    name: str = Field(..., description="Column name")
    data_type: str = Field(..., description="Data type (pandas/DuckDB type)")
    nullable: bool = Field(True, description="Whether column can contain nulls")
    is_primary_key: bool = Field(False, description="Whether column is a primary key")
    is_foreign_key: bool = Field(False, description="Whether column is a foreign key")
    
    # Statistics
    statistics: ColumnStatistics = Field(..., description="Column statistics")
    
    # Data quality
    quality_score: float = Field(0.0, description="Data quality score (0-100)")
    quality_issues: List[str] = Field(default_factory=list, description="Identified quality issues")
    
    # Additional metadata
    description: Optional[str] = Field(None, description="Column description")
    tags: List[str] = Field(default_factory=list, description="User-defined tags")


class TableColumnAnalysis(BaseModel):
    """Complete column analysis for a table."""
    
    table_name: str = Field(..., description="Table name")
    total_rows: int = Field(..., description="Total number of rows")
    total_columns: int = Field(..., description="Total number of columns")
    columns: List[ColumnMetadata] = Field(default_factory=list, description="Column metadata")
    analysis_timestamp: str = Field(..., description="When analysis was performed")
    
    # Table-level statistics
    overall_quality_score: float = Field(0.0, description="Overall table quality score")
    memory_usage: int = Field(0, description="Estimated memory usage in bytes")
    
    def get_column(self, column_name: str) -> Optional[ColumnMetadata]:
        """Get metadata for a specific column."""
        for col in self.columns:
            if col.name == column_name:
                return col
        return None
    
    def get_numeric_columns(self) -> List[ColumnMetadata]:
        """Get all numeric columns."""
        return [col for col in self.columns if self._is_numeric_type(col.data_type)]
    
    def get_string_columns(self) -> List[ColumnMetadata]:
        """Get all string/text columns."""
        return [col for col in self.columns if self._is_string_type(col.data_type)]
    
    def get_date_columns(self) -> List[ColumnMetadata]:
        """Get all date/datetime columns."""
        return [col for col in self.columns if self._is_date_type(col.data_type)]
    
    def get_low_quality_columns(self, threshold: float = 70.0) -> List[ColumnMetadata]:
        """Get columns with quality score below threshold."""
        return [col for col in self.columns if col.quality_score < threshold]
    
    def _is_numeric_type(self, data_type: str) -> bool:
        """Check if data type is numeric."""
        numeric_types = ['int64', 'int32', 'float64', 'float32', 'number', 'integer', 'double', 'bigint']
        return any(nt in data_type.lower() for nt in numeric_types)
    
    def _is_string_type(self, data_type: str) -> bool:
        """Check if data type is string."""
        string_types = ['object', 'string', 'varchar', 'text', 'char']
        return any(st in data_type.lower() for st in string_types)
    
    def _is_date_type(self, data_type: str) -> bool:
        """Check if data type is date/datetime."""
        date_types = ['datetime', 'date', 'timestamp', 'time']
        return any(dt in data_type.lower() for dt in date_types)


class ColumnAnalyzer:
    """
    Analyzes columns and generates detailed metadata.
    
    Features:
    - Statistical analysis for all data types
    - Data quality assessment
    - Null and unique value analysis
    - Sample value extraction
    """
    
    def __init__(self):
        """Initialize column analyzer."""
        pass
    
    def analyze_table(self, df: pd.DataFrame, table_name: str) -> TableColumnAnalysis:
        """
        Perform comprehensive analysis of a table's columns.
        
        Args:
            df: DataFrame to analyze
            table_name: Name of the table
            
        Returns:
            TableColumnAnalysis: Complete analysis results
        """
        logger.info(f"Starting column analysis for table: {table_name}")
        
        columns = []
        total_quality_score = 0.0
        
        for column_name in df.columns:
            column_meta = self.analyze_column(df, column_name)
            columns.append(column_meta)
            total_quality_score += column_meta.quality_score
        
        # Calculate overall quality score
        overall_quality = total_quality_score / len(columns) if columns else 0.0
        
        # Calculate memory usage
        memory_usage = df.memory_usage(deep=True).sum()
        
        analysis = TableColumnAnalysis(
            table_name=table_name,
            total_rows=len(df),
            total_columns=len(df.columns),
            columns=columns,
            analysis_timestamp=datetime.now().isoformat(),
            overall_quality_score=overall_quality,
            memory_usage=int(memory_usage)
        )
        
        logger.info(f"Column analysis completed for {table_name}: {len(columns)} columns analyzed")
        return analysis
    
    def analyze_column(self, df: pd.DataFrame, column_name: str) -> ColumnMetadata:
        """
        Analyze a single column in detail.
        
        Args:
            df: DataFrame containing the column
            column_name: Name of the column to analyze
            
        Returns:
            ColumnMetadata: Detailed column metadata
        """
        series = df[column_name]
        
        # Basic information
        data_type = str(series.dtype)
        nullable = series.isnull().any()
        
        # Calculate statistics
        statistics = self._calculate_statistics(series)
        
        # Assess data quality
        quality_score, quality_issues = self._assess_quality(series, statistics)
        
        return ColumnMetadata(
            name=column_name,
            data_type=data_type,
            nullable=nullable,
            statistics=statistics,
            quality_score=quality_score,
            quality_issues=quality_issues
        )
    
    def _calculate_statistics(self, series: pd.Series) -> ColumnStatistics:
        """Calculate comprehensive statistics for a column."""
        total_count = len(series)
        null_count = series.isnull().sum()
        non_null_series = series.dropna()
        unique_count = series.nunique()
        duplicate_count = total_count - unique_count
        
        # Base statistics
        stats = ColumnStatistics(
            count=total_count,
            null_count=int(null_count),
            unique_count=int(unique_count),
            duplicate_count=int(duplicate_count),
            null_percentage=float(null_count / total_count * 100) if total_count > 0 else 0.0,
            unique_percentage=float(unique_count / total_count * 100) if total_count > 0 else 0.0
        )
        
        # Sample values (up to 5 unique non-null values)
        if len(non_null_series) > 0:
            sample_values = non_null_series.unique()[:5]
            stats.sample_values = [str(val) for val in sample_values]
        
        # Numeric statistics
        if pd.api.types.is_numeric_dtype(series):
            if len(non_null_series) > 0:
                stats.min_value = float(non_null_series.min())
                stats.max_value = float(non_null_series.max())
                stats.mean = float(non_null_series.mean())
                stats.median = float(non_null_series.median())
                if len(non_null_series) > 1:
                    stats.std_dev = float(non_null_series.std())
        
        # String statistics
        elif pd.api.types.is_string_dtype(series) or series.dtype == 'object':
            string_series = non_null_series.astype(str)
            if len(string_series) > 0:
                lengths = string_series.str.len()
                stats.min_length = int(lengths.min())
                stats.max_length = int(lengths.max())
                stats.avg_length = float(lengths.mean())
        
        # Date statistics
        elif pd.api.types.is_datetime64_any_dtype(series):
            if len(non_null_series) > 0:
                stats.min_date = non_null_series.min().isoformat()
                stats.max_date = non_null_series.max().isoformat()
        
        return stats
    
    def _assess_quality(self, series: pd.Series, statistics: ColumnStatistics) -> tuple[float, List[str]]:
        """
        Assess data quality for a column.
        
        Args:
            series: The column data
            statistics: Pre-calculated statistics
            
        Returns:
            tuple: (quality_score, list_of_issues)
        """
        issues = []
        score = 100.0  # Start with perfect score and deduct for issues
        
        # High null percentage
        if statistics.null_percentage > 50:
            issues.append(f"High null percentage: {statistics.null_percentage:.1f}%")
            score -= 30
        elif statistics.null_percentage > 20:
            issues.append(f"Moderate null percentage: {statistics.null_percentage:.1f}%")
            score -= 15
        
        # Low unique values (potential data quality issue)
        if statistics.unique_percentage < 10 and statistics.count > 100:
            issues.append(f"Low uniqueness: {statistics.unique_percentage:.1f}%")
            score -= 20
        
        # All values are the same
        if statistics.unique_count == 1 and statistics.count > 1:
            issues.append("All values are identical")
            score -= 40
        
        # Numeric column issues
        if pd.api.types.is_numeric_dtype(series):
            # Check for outliers (values beyond 3 standard deviations)
            if statistics.std_dev and statistics.std_dev > 0:
                non_null = series.dropna()
                outliers = non_null[abs(non_null - statistics.mean) > 3 * statistics.std_dev]
                if len(outliers) > len(non_null) * 0.05:  # More than 5% outliers
                    issues.append(f"Potential outliers detected: {len(outliers)} values")
                    score -= 10
        
        # String column issues
        elif pd.api.types.is_string_dtype(series) or series.dtype == 'object':
            # Check for very long strings (potential data entry errors)
            if statistics.max_length and statistics.max_length > 1000:
                issues.append(f"Very long strings detected (max: {statistics.max_length} chars)")
                score -= 10
            
            # Check for very short average length when max is much larger
            if (statistics.avg_length and statistics.max_length and 
                statistics.avg_length < statistics.max_length / 10):
                issues.append("Inconsistent string lengths")
                score -= 5
        
        # Ensure score doesn't go below 0
        score = max(0.0, score)
        
        return score, issues


# Global analyzer instance
column_analyzer = ColumnAnalyzer()