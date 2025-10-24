"""
Advanced table profiling system for LocalSQL Explorer.

This module provides comprehensive data profiling including:
- Statistical distributions and histograms
- Correlation analysis between columns
- Data quality scoring and recommendations
- Pattern detection and anomaly identification
- Profiling reports with visualizations
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from .column_analysis import ColumnAnalyzer, TableColumnAnalysis

logger = logging.getLogger(__name__)


class DistributionAnalysis(BaseModel):
    """Distribution analysis for numeric columns."""
    
    column_name: str = Field(..., description="Column name")
    data_type: str = Field(..., description="Data type")
    
    # Basic statistics
    count: int = Field(..., description="Total count")
    mean: float = Field(..., description="Mean value")
    std: float = Field(..., description="Standard deviation")
    min_val: float = Field(..., description="Minimum value")
    max_val: float = Field(..., description="Maximum value")
    
    # Quantiles
    q25: float = Field(..., description="25th percentile")
    q50: float = Field(..., description="50th percentile (median)")
    q75: float = Field(..., description="75th percentile")
    
    # Distribution characteristics
    skewness: Optional[float] = Field(None, description="Skewness measure")
    kurtosis: Optional[float] = Field(None, description="Kurtosis measure")
    
    # Histogram data
    histogram_bins: List[float] = Field(default_factory=list, description="Histogram bin edges")
    histogram_counts: List[int] = Field(default_factory=list, description="Histogram counts")
    
    # Outliers
    outlier_count: int = Field(0, description="Number of outliers")
    outlier_percentage: float = Field(0.0, description="Percentage of outliers")
    outlier_method: str = Field("IQR", description="Method used for outlier detection")


class CorrelationAnalysis(BaseModel):
    """Correlation analysis between numeric columns."""
    
    # Correlation matrix
    correlation_matrix: Dict[str, Dict[str, float]] = Field(default_factory=dict, description="Correlation matrix")
    
    # Strong correlations (>0.7 or <-0.7)
    strong_correlations: List[Tuple[str, str, float]] = Field(default_factory=list, description="Strong correlations")
    
    # Weak correlations (between -0.3 and 0.3)
    weak_correlations: List[Tuple[str, str, float]] = Field(default_factory=list, description="Weak correlations")


class PatternAnalysis(BaseModel):
    """Pattern analysis for string columns."""
    
    column_name: str = Field(..., description="Column name")
    
    # Common patterns
    email_like_count: int = Field(0, description="Email-like patterns")
    phone_like_count: int = Field(0, description="Phone-like patterns")
    url_like_count: int = Field(0, description="URL-like patterns")
    numeric_only_count: int = Field(0, description="Numeric-only strings")
    
    # Character patterns
    uppercase_count: int = Field(0, description="All uppercase strings")
    lowercase_count: int = Field(0, description="All lowercase strings")
    mixed_case_count: int = Field(0, description="Mixed case strings")
    
    # Length patterns
    constant_length: Optional[int] = Field(None, description="Constant length if all strings same length")
    length_variance: float = Field(0.0, description="Variance in string lengths")
    
    # Most common patterns
    top_patterns: List[Tuple[str, int]] = Field(default_factory=list, description="Most common string patterns")


class DataQualityReport(BaseModel):
    """Comprehensive data quality report."""
    
    table_name: str = Field(..., description="Table name")
    
    # Overall scores
    completeness_score: float = Field(0.0, description="Completeness score (0-100)")
    consistency_score: float = Field(0.0, description="Consistency score (0-100)")
    validity_score: float = Field(0.0, description="Validity score (0-100)")
    uniqueness_score: float = Field(0.0, description="Uniqueness score (0-100)")
    overall_score: float = Field(0.0, description="Overall quality score (0-100)")
    
    # Detailed issues
    quality_issues: List[str] = Field(default_factory=list, description="Quality issues found")
    recommendations: List[str] = Field(default_factory=list, description="Improvement recommendations")
    
    # Column-level quality
    column_quality_scores: Dict[str, float] = Field(default_factory=dict, description="Quality score per column")
    problematic_columns: List[str] = Field(default_factory=list, description="Columns with quality issues")


class TableProfilingReport(BaseModel):
    """Comprehensive table profiling report."""
    
    table_name: str = Field(..., description="Table name")
    profiling_timestamp: str = Field(..., description="When profiling was performed")
    
    # Basic table info
    total_rows: int = Field(..., description="Total number of rows")
    total_columns: int = Field(..., description="Total number of columns")
    memory_usage: int = Field(..., description="Memory usage in bytes")
    
    # Column analysis (from existing system)
    column_analysis: TableColumnAnalysis = Field(..., description="Detailed column analysis")
    
    # Advanced profiling
    distributions: List[DistributionAnalysis] = Field(default_factory=list, description="Distribution analysis")
    correlations: Optional[CorrelationAnalysis] = Field(None, description="Correlation analysis")
    patterns: List[PatternAnalysis] = Field(default_factory=list, description="Pattern analysis")
    quality_report: DataQualityReport = Field(..., description="Data quality report")
    
    # Summary insights
    key_insights: List[str] = Field(default_factory=list, description="Key insights from profiling")
    data_types_summary: Dict[str, int] = Field(default_factory=dict, description="Count of each data type")
    
    def get_numeric_columns(self) -> List[str]:
        """Get list of numeric column names."""
        return [d.column_name for d in self.distributions]
    
    def get_categorical_columns(self) -> List[str]:
        """Get list of categorical column names."""
        return [p.column_name for p in self.patterns]
    
    def get_high_quality_columns(self, threshold: float = 80.0) -> List[str]:
        """Get columns with high quality scores."""
        return [col for col, score in self.quality_report.column_quality_scores.items() if score >= threshold]
    
    def get_problematic_columns(self) -> List[str]:
        """Get columns with quality issues."""
        return self.quality_report.problematic_columns


class TableProfiler:
    """
    Advanced table profiling engine.
    
    Features:
    - Statistical distribution analysis
    - Correlation analysis
    - Pattern detection
    - Data quality assessment
    - Insight generation
    """
    
    def __init__(self):
        """Initialize table profiler."""
        self.column_analyzer = ColumnAnalyzer()
    
    def profile_table(self, df: pd.DataFrame, table_name: str) -> TableProfilingReport:
        """
        Perform comprehensive profiling of a table.
        
        Args:
            df: DataFrame to profile
            table_name: Name of the table
            
        Returns:
            TableProfilingReport: Comprehensive profiling report
        """
        logger.info(f"Starting comprehensive profiling for table: {table_name}")
        
        # Start with column analysis
        column_analysis = self.column_analyzer.analyze_table(df, table_name)
        
        # Perform distribution analysis
        distributions = self._analyze_distributions(df)
        
        # Perform correlation analysis
        correlations = self._analyze_correlations(df)
        
        # Perform pattern analysis
        patterns = self._analyze_patterns(df)
        
        # Generate quality report
        quality_report = self._generate_quality_report(df, table_name, column_analysis)
        
        # Generate insights
        key_insights = self._generate_insights(df, distributions, correlations, patterns, quality_report)
        
        # Data types summary
        data_types_summary = self._summarize_data_types(df)
        
        report = TableProfilingReport(
            table_name=table_name,
            profiling_timestamp=datetime.now().isoformat(),
            total_rows=len(df),
            total_columns=len(df.columns),
            memory_usage=int(df.memory_usage(deep=True).sum()),
            column_analysis=column_analysis,
            distributions=distributions,
            correlations=correlations,
            patterns=patterns,
            quality_report=quality_report,
            key_insights=key_insights,
            data_types_summary=data_types_summary
        )
        
        logger.info(f"Profiling completed for {table_name}: {len(key_insights)} insights generated")
        return report
    
    def _analyze_distributions(self, df: pd.DataFrame) -> List[DistributionAnalysis]:
        """Analyze distributions of numeric columns."""
        distributions = []
        
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        
        for col in numeric_columns:
            series = df[col].dropna()
            
            if len(series) == 0:
                continue
            
            try:
                # Basic statistics
                stats = series.describe()
                
                # Calculate skewness and kurtosis
                skewness = series.skew() if len(series) > 2 else None
                kurtosis = series.kurtosis() if len(series) > 3 else None
                
                # Create histogram
                hist_counts, hist_bins = np.histogram(series, bins=min(50, len(series.unique())))
                
                # Detect outliers using IQR method
                Q1 = series.quantile(0.25)
                Q3 = series.quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                outliers = series[(series < lower_bound) | (series > upper_bound)]
                
                distribution = DistributionAnalysis(
                    column_name=col,
                    data_type=str(df[col].dtype),
                    count=int(stats['count']),
                    mean=float(stats['mean']),
                    std=float(stats['std']),
                    min_val=float(stats['min']),
                    max_val=float(stats['max']),
                    q25=float(stats['25%']),
                    q50=float(stats['50%']),
                    q75=float(stats['75%']),
                    skewness=float(skewness) if skewness is not None else None,
                    kurtosis=float(kurtosis) if kurtosis is not None else None,
                    histogram_bins=hist_bins.tolist(),
                    histogram_counts=hist_counts.tolist(),
                    outlier_count=len(outliers),
                    outlier_percentage=len(outliers) / len(series) * 100,
                    outlier_method="IQR"
                )
                
                distributions.append(distribution)
                
            except Exception as e:
                logger.warning(f"Failed to analyze distribution for column {col}: {e}")
        
        return distributions
    
    def _analyze_correlations(self, df: pd.DataFrame) -> Optional[CorrelationAnalysis]:
        """Analyze correlations between numeric columns."""
        numeric_df = df.select_dtypes(include=[np.number])
        
        if len(numeric_df.columns) < 2:
            return None
        
        try:
            # Calculate correlation matrix
            corr_matrix = numeric_df.corr()
            
            # Convert to dictionary format
            corr_dict = {}
            for col1 in corr_matrix.columns:
                corr_dict[col1] = {}
                for col2 in corr_matrix.columns:
                    corr_dict[col1][col2] = float(corr_matrix.loc[col1, col2])
            
            # Find strong and weak correlations
            strong_correlations = []
            weak_correlations = []
            
            for i, col1 in enumerate(corr_matrix.columns):
                for j, col2 in enumerate(corr_matrix.columns):
                    if i < j:  # Avoid duplicates and self-correlation
                        corr_val = corr_matrix.loc[col1, col2]
                        
                        if not np.isnan(corr_val):
                            if abs(corr_val) >= 0.7:
                                strong_correlations.append((col1, col2, float(corr_val)))
                            elif abs(corr_val) <= 0.3:
                                weak_correlations.append((col1, col2, float(corr_val)))
            
            return CorrelationAnalysis(
                correlation_matrix=corr_dict,
                strong_correlations=strong_correlations,
                weak_correlations=weak_correlations
            )
            
        except Exception as e:
            logger.warning(f"Failed to analyze correlations: {e}")
            return None
    
    def _analyze_patterns(self, df: pd.DataFrame) -> List[PatternAnalysis]:
        """Analyze patterns in string columns."""
        patterns = []
        
        string_columns = df.select_dtypes(include=['object']).columns
        
        for col in string_columns:
            series = df[col].dropna().astype(str)
            
            if len(series) == 0:
                continue
            
            try:
                # Pattern detection using regex
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                phone_pattern = r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
                url_pattern = r'https?://[^\s]+'
                numeric_pattern = r'^\d+$'
                
                email_count = series.str.contains(email_pattern, regex=True, na=False).sum()
                phone_count = series.str.contains(phone_pattern, regex=True, na=False).sum()
                url_count = series.str.contains(url_pattern, regex=True, na=False).sum()
                numeric_only_count = series.str.contains(numeric_pattern, regex=True, na=False).sum()
                
                # Case patterns
                uppercase_count = series.str.isupper().sum()
                lowercase_count = series.str.islower().sum()
                mixed_case_count = len(series) - uppercase_count - lowercase_count
                
                # Length analysis
                lengths = series.str.len()
                constant_length = lengths.iloc[0] if lengths.nunique() == 1 else None
                length_variance = float(lengths.var()) if len(lengths) > 1 else 0.0
                
                # Most common patterns (first 3 characters + length)
                pattern_counts = {}
                for value in series.head(1000):  # Limit for performance
                    if len(value) >= 3:
                        pattern = f"{value[:3]}...[{len(value)}]"
                        pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
                
                top_patterns = sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                
                pattern_analysis = PatternAnalysis(
                    column_name=col,
                    email_like_count=int(email_count),
                    phone_like_count=int(phone_count),
                    url_like_count=int(url_count),
                    numeric_only_count=int(numeric_only_count),
                    uppercase_count=int(uppercase_count),
                    lowercase_count=int(lowercase_count),
                    mixed_case_count=int(mixed_case_count),
                    constant_length=int(constant_length) if constant_length is not None else None,
                    length_variance=length_variance,
                    top_patterns=top_patterns
                )
                
                patterns.append(pattern_analysis)
                
            except Exception as e:
                logger.warning(f"Failed to analyze patterns for column {col}: {e}")
        
        return patterns
    
    def _generate_quality_report(self, df: pd.DataFrame, table_name: str, 
                                column_analysis: TableColumnAnalysis) -> DataQualityReport:
        """Generate comprehensive data quality report."""
        
        # Calculate quality dimensions
        completeness_score = self._calculate_completeness(df)
        consistency_score = self._calculate_consistency(df)
        validity_score = self._calculate_validity(df)
        uniqueness_score = self._calculate_uniqueness(df)
        
        overall_score = (completeness_score + consistency_score + validity_score + uniqueness_score) / 4
        
        # Generate issues and recommendations
        quality_issues = []
        recommendations = []
        
        # Completeness issues
        null_percentages = df.isnull().sum() / len(df) * 100
        high_null_cols = null_percentages[null_percentages > 20].index.tolist()
        if high_null_cols:
            quality_issues.append(f"High null percentages in columns: {', '.join(high_null_cols)}")
            recommendations.append("Consider data imputation or investigate data collection issues")
        
        # Consistency issues
        for col in df.select_dtypes(include=['object']).columns:
            unique_ratio = df[col].nunique() / len(df)
            if unique_ratio > 0.8 and len(df) > 100:
                quality_issues.append(f"Column '{col}' has very high cardinality ({unique_ratio:.1%})")
                recommendations.append(f"Review '{col}' for potential data entry inconsistencies")
        
        # Column quality scores
        column_quality_scores = {}
        problematic_columns = []
        
        for col_meta in column_analysis.columns:
            column_quality_scores[col_meta.name] = col_meta.quality_score
            if col_meta.quality_score < 70:
                problematic_columns.append(col_meta.name)
        
        return DataQualityReport(
            table_name=table_name,
            completeness_score=completeness_score,
            consistency_score=consistency_score,
            validity_score=validity_score,
            uniqueness_score=uniqueness_score,
            overall_score=overall_score,
            quality_issues=quality_issues,
            recommendations=recommendations,
            column_quality_scores=column_quality_scores,
            problematic_columns=problematic_columns
        )
    
    def _calculate_completeness(self, df: pd.DataFrame) -> float:
        """Calculate completeness score based on null values."""
        total_cells = df.size
        null_cells = df.isnull().sum().sum()
        return (1 - null_cells / total_cells) * 100 if total_cells > 0 else 0
    
    def _calculate_consistency(self, df: pd.DataFrame) -> float:
        """Calculate consistency score based on data patterns."""
        consistency_scores = []
        
        for col in df.columns:
            if df[col].dtype == 'object':
                # For string columns, check format consistency
                non_null = df[col].dropna().astype(str)
                if len(non_null) > 0:
                    lengths = non_null.str.len()
                    length_cv = lengths.std() / lengths.mean() if lengths.mean() > 0 else 0
                    consistency_scores.append(max(0, 100 - length_cv * 50))  # Penalize high variation
                else:
                    consistency_scores.append(100)
            else:
                # For numeric columns, assume consistent
                consistency_scores.append(100)
        
        return sum(consistency_scores) / len(consistency_scores) if consistency_scores else 100
    
    def _calculate_validity(self, df: pd.DataFrame) -> float:
        """Calculate validity score based on data type conformance."""
        validity_scores = []
        
        for col in df.columns:
            try:
                # Check if values conform to expected type
                if df[col].dtype in ['int64', 'float64']:
                    # For numeric, check for infinite values
                    inf_count = np.isinf(df[col]).sum()
                    validity_scores.append(100 - (inf_count / len(df)) * 100)
                else:
                    # For other types, assume valid
                    validity_scores.append(100)
            except:
                validity_scores.append(50)  # Partial score for problematic columns
        
        return sum(validity_scores) / len(validity_scores) if validity_scores else 100
    
    def _calculate_uniqueness(self, df: pd.DataFrame) -> float:
        """Calculate uniqueness score based on duplicate rows."""
        total_rows = len(df)
        unique_rows = len(df.drop_duplicates())
        return (unique_rows / total_rows) * 100 if total_rows > 0 else 0
    
    def _generate_insights(self, df: pd.DataFrame, distributions: List[DistributionAnalysis],
                          correlations: Optional[CorrelationAnalysis], patterns: List[PatternAnalysis],
                          quality_report: DataQualityReport) -> List[str]:
        """Generate key insights from profiling results."""
        insights = []
        
        # Data size insights
        rows, cols = df.shape
        memory_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)
        insights.append(f"Dataset contains {rows:,} rows and {cols} columns, using {memory_mb:.1f} MB of memory")
        
        # Quality insights
        if quality_report.overall_score >= 90:
            insights.append("Excellent data quality - minimal issues detected")
        elif quality_report.overall_score >= 70:
            insights.append("Good data quality with some minor issues")
        else:
            insights.append("Data quality concerns detected - review recommendations")
        
        # Distribution insights
        for dist in distributions:
            if dist.outlier_percentage > 10:
                insights.append(f"Column '{dist.column_name}' has {dist.outlier_percentage:.1f}% outliers")
            
            if abs(dist.skewness) > 2 if dist.skewness else False:
                skew_type = "highly skewed" if abs(dist.skewness) > 2 else "moderately skewed"
                insights.append(f"Column '{dist.column_name}' is {skew_type} (skewness: {dist.skewness:.2f})")
        
        # Correlation insights
        if correlations and correlations.strong_correlations:
            for col1, col2, corr in correlations.strong_correlations[:3]:  # Top 3
                insights.append(f"Strong correlation between '{col1}' and '{col2}' (r={corr:.2f})")
        
        # Pattern insights
        for pattern in patterns:
            if pattern.email_like_count > 0:
                insights.append(f"Column '{pattern.column_name}' contains {pattern.email_like_count} email-like values")
            if pattern.phone_like_count > 0:
                insights.append(f"Column '{pattern.column_name}' contains {pattern.phone_like_count} phone-like values")
        
        # Null value insights
        null_percentages = df.isnull().sum() / len(df) * 100
        high_null_cols = null_percentages[null_percentages > 50]
        if len(high_null_cols) > 0:
            insights.append(f"{len(high_null_cols)} columns have >50% missing values")
        
        return insights[:10]  # Limit to top 10 insights
    
    def _summarize_data_types(self, df: pd.DataFrame) -> Dict[str, int]:
        """Summarize data types in the table."""
        type_counts = {}
        
        for col in df.columns:
            dtype_str = str(df[col].dtype)
            
            # Normalize type names
            if 'int' in dtype_str:
                dtype_category = 'Integer'
            elif 'float' in dtype_str:
                dtype_category = 'Float'
            elif 'object' in dtype_str:
                dtype_category = 'Text'
            elif 'datetime' in dtype_str:
                dtype_category = 'DateTime'
            elif 'bool' in dtype_str:
                dtype_category = 'Boolean'
            else:
                dtype_category = 'Other'
            
            type_counts[dtype_category] = type_counts.get(dtype_category, 0) + 1
        
        return type_counts


# Global profiler instance
table_profiler = TableProfiler()