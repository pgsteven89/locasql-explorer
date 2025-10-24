"""
CTE (Common Table Expression) Support Module

This module provides comprehensive CTE support for the SQL editor including:
- CTE syntax parsing and validation
- CTE-specific auto-completion
- Recursive CTE templates and examples
- CTE optimization suggestions
- CTE to subquery conversion utilities
"""

import logging
import re
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CTEType(Enum):
    """Types of CTEs."""
    SIMPLE = "simple"
    RECURSIVE = "recursive"
    MATERIALIZED = "materialized"
    NOT_MATERIALIZED = "not_materialized"


@dataclass
class CTEDefinition:
    """Represents a single CTE definition."""
    name: str
    columns: List[str]
    query: str
    cte_type: CTEType = CTEType.SIMPLE
    dependencies: Set[str] = None
    line_start: int = 0
    line_end: int = 0
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = set()


@dataclass
class CTEAnalysis:
    """Analysis result for CTE usage in SQL."""
    ctes: List[CTEDefinition]
    main_query: str
    has_recursive: bool = False
    complexity_score: int = 0
    optimization_suggestions: List[str] = None
    
    def __post_init__(self):
        if self.optimization_suggestions is None:
            self.optimization_suggestions = []


class CTEParser:
    """Parser for extracting and analyzing CTEs from SQL queries."""
    
    def __init__(self):
        # Regex patterns for CTE parsing
        self.with_pattern = re.compile(
            r'WITH\s+(?:RECURSIVE\s+)?(?:MATERIALIZED\s+|NOT\s+MATERIALIZED\s+)?',
            re.IGNORECASE
        )
        
        self.cte_pattern = re.compile(
            r'(\w+)(?:\s*\(([\w\s,]+)\))?\s+AS\s*\((.*?)\)',
            re.IGNORECASE | re.DOTALL
        )
        
        self.recursive_pattern = re.compile(
            r'WITH\s+RECURSIVE\s+',
            re.IGNORECASE
        )
        
        self.materialized_pattern = re.compile(
            r'WITH\s+(?:RECURSIVE\s+)?(?:(MATERIALIZED|NOT\s+MATERIALIZED)\s+)',
            re.IGNORECASE
        )
    
    def parse_ctes(self, sql: str) -> CTEAnalysis:
        """Parse CTEs from SQL query and return analysis."""
        sql = sql.strip()
        if not sql.upper().startswith('WITH'):
            return CTEAnalysis(ctes=[], main_query=sql)
        
        ctes = []
        has_recursive = bool(self.recursive_pattern.search(sql))
        
        # Find the main WITH clause
        with_match = self.with_pattern.search(sql)
        if not with_match:
            return CTEAnalysis(ctes=[], main_query=sql)
        
        # Extract the CTEs section
        cte_section, main_query = self._split_cte_and_main_query(sql)
        
        # Parse individual CTEs
        ctes = self._parse_individual_ctes(cte_section, has_recursive)
        
        # Analyze dependencies
        self._analyze_dependencies(ctes)
        
        # Calculate complexity and generate suggestions
        complexity_score = self._calculate_complexity(ctes, main_query)
        suggestions = self._generate_optimization_suggestions(ctes, complexity_score)
        
        return CTEAnalysis(
            ctes=ctes,
            main_query=main_query,
            has_recursive=has_recursive,
            complexity_score=complexity_score,
            optimization_suggestions=suggestions
        )
    
    def _split_cte_and_main_query(self, sql: str) -> Tuple[str, str]:
        """Split SQL into CTE section and main query."""
        # Find the end of the CTE section by looking for the main SELECT/INSERT/UPDATE/DELETE
        # This is simplified - a full parser would need to handle nested parentheses properly
        
        lines = sql.split('\n')
        cte_lines = []
        main_query_lines = []
        in_main_query = False
        
        for line in lines:
            stripped = line.strip().upper()
            
            # Look for main query keywords not in CTE AS clauses
            if not in_main_query and any(stripped.startswith(kw) for kw in ['SELECT', 'INSERT', 'UPDATE', 'DELETE']) and 'AS' not in line.upper():
                in_main_query = True
            
            if in_main_query:
                main_query_lines.append(line)
            else:
                cte_lines.append(line)
        
        return '\n'.join(cte_lines), '\n'.join(main_query_lines)
    
    def _parse_individual_ctes(self, cte_section: str, has_recursive: bool) -> List[CTEDefinition]:
        """Parse individual CTE definitions from the CTE section."""
        ctes = []
        
        # Remove the WITH keyword and optional modifiers
        cleaned_section = re.sub(r'WITH\s+(?:RECURSIVE\s+)?(?:MATERIALIZED\s+|NOT\s+MATERIALIZED\s+)?', '', cte_section, flags=re.IGNORECASE)
        
        # Find CTE definitions - this is a simplified approach
        # In practice, you'd want a proper SQL parser
        cte_parts = self._split_cte_definitions(cleaned_section)
        
        for i, cte_part in enumerate(cte_parts):
            cte = self._parse_single_cte(cte_part, has_recursive)
            if cte:
                ctes.append(cte)
        
        return ctes
    
    def _split_cte_definitions(self, cte_section: str) -> List[str]:
        """Split the CTE section into individual CTE definitions."""
        # This is a simplified splitter that looks for commas at the top level
        # A full implementation would need proper parentheses counting
        
        parts = []
        current_part = ""
        paren_count = 0
        
        for char in cte_section:
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
            elif char == ',' and paren_count == 0:
                if current_part.strip():
                    parts.append(current_part.strip())
                current_part = ""
                continue
            
            current_part += char
        
        if current_part.strip():
            parts.append(current_part.strip())
        
        return parts
    
    def _parse_single_cte(self, cte_text: str, has_recursive: bool) -> Optional[CTEDefinition]:
        """Parse a single CTE definition."""
        # Look for pattern: name (optional columns) AS (query)
        match = re.match(r'(\w+)(?:\s*\(([\w\s,]+)\))?\s+AS\s*\((.*)\)', cte_text, re.IGNORECASE | re.DOTALL)
        
        if not match:
            return None
        
        name = match.group(1).strip()
        columns_str = match.group(2)
        query = match.group(3).strip()
        
        columns = []
        if columns_str:
            columns = [col.strip() for col in columns_str.split(',')]
        
        # Determine CTE type
        cte_type = CTEType.RECURSIVE if has_recursive else CTEType.SIMPLE
        
        return CTEDefinition(
            name=name,
            columns=columns,
            query=query,
            cte_type=cte_type
        )
    
    def _analyze_dependencies(self, ctes: List[CTEDefinition]):
        """Analyze dependencies between CTEs."""
        cte_names = {cte.name for cte in ctes}
        
        for cte in ctes:
            # Find references to other CTEs in this CTE's query
            query_upper = cte.query.upper()
            for other_name in cte_names:
                if other_name != cte.name and other_name.upper() in query_upper:
                    cte.dependencies.add(other_name)
    
    def _calculate_complexity(self, ctes: List[CTEDefinition], main_query: str) -> int:
        """Calculate complexity score for the CTE structure."""
        score = 0
        
        # Base score for each CTE
        score += len(ctes) * 10
        
        # Add score for recursive CTEs
        for cte in ctes:
            if cte.cte_type == CTEType.RECURSIVE:
                score += 20
        
        # Add score for dependencies
        total_deps = sum(len(cte.dependencies) for cte in ctes)
        score += total_deps * 5
        
        # Add score for query length
        total_query_length = sum(len(cte.query) for cte in ctes) + len(main_query)
        score += total_query_length // 100
        
        return score
    
    def _generate_optimization_suggestions(self, ctes: List[CTEDefinition], complexity_score: int) -> List[str]:
        """Generate optimization suggestions based on CTE analysis."""
        suggestions = []
        
        if complexity_score > 100:
            suggestions.append("Consider breaking down complex CTEs into smaller, more focused ones")
        
        if len(ctes) > 5:
            suggestions.append("Large number of CTEs detected - consider using views for frequently used logic")
        
        # Check for unused CTEs
        all_cte_names = {cte.name for cte in ctes}
        referenced_names = set()
        
        for cte in ctes:
            referenced_names.update(cte.dependencies)
        
        unused_ctes = all_cte_names - referenced_names
        if unused_ctes:
            suggestions.append(f"Unused CTEs detected: {', '.join(unused_ctes)} - consider removing them")
        
        # Check for circular dependencies
        if self._has_circular_dependencies(ctes):
            suggestions.append("Circular dependencies detected in CTE structure - review CTE order")
        
        return suggestions
    
    def _has_circular_dependencies(self, ctes: List[CTEDefinition]) -> bool:
        """Check for circular dependencies in CTE structure."""
        # Simple cycle detection using DFS
        cte_graph = {cte.name: cte.dependencies for cte in ctes}
        
        def has_cycle(node, visited, rec_stack):
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in cte_graph.get(node, set()):
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        visited = set()
        for cte_name in cte_graph:
            if cte_name not in visited:
                if has_cycle(cte_name, visited, set()):
                    return True
        
        return False


class CTETemplateGenerator:
    """Generator for CTE templates and examples."""
    
    @staticmethod
    def get_simple_cte_template() -> str:
        """Get a simple CTE template."""
        return """WITH sales_summary AS (
    SELECT 
        region,
        SUM(sales_amount) as total_sales,
        COUNT(*) as transaction_count,
        AVG(sales_amount) as avg_sale
    FROM sales_data
    WHERE sale_date >= '2024-01-01'
    GROUP BY region
)
SELECT 
    region,
    total_sales,
    transaction_count,
    avg_sale,
    ROUND(total_sales / SUM(total_sales) OVER() * 100, 2) as pct_of_total
FROM sales_summary
ORDER BY total_sales DESC"""
    
    @staticmethod
    def get_recursive_cte_template() -> str:
        """Get a recursive CTE template."""
        return """WITH RECURSIVE employee_hierarchy AS (
    -- Base case: top-level managers
    SELECT 
        employee_id,
        employee_name,
        manager_id,
        department,
        1 as level,
        CAST(employee_name AS VARCHAR(500)) as hierarchy_path
    FROM employees
    WHERE manager_id IS NULL
    
    UNION ALL
    
    -- Recursive case: employees reporting to managers
    SELECT 
        e.employee_id,
        e.employee_name,
        e.manager_id,
        e.department,
        eh.level + 1,
        CAST(eh.hierarchy_path + ' -> ' + e.employee_name AS VARCHAR(500))
    FROM employees e
    INNER JOIN employee_hierarchy eh ON e.manager_id = eh.employee_id
    WHERE eh.level < 10  -- Prevent infinite recursion
)
SELECT 
    employee_id,
    employee_name,
    department,
    level,
    hierarchy_path,
    SPACE((level - 1) * 4) + employee_name as indented_name
FROM employee_hierarchy
ORDER BY hierarchy_path"""
    
    @staticmethod
    def get_materialized_cte_template() -> str:
        """Get a materialized CTE template."""
        return """WITH MATERIALIZED expensive_calculation AS (
    SELECT 
        customer_id,
        -- Expensive aggregation that we want to materialize
        SUM(order_amount) as total_spent,
        COUNT(*) as order_count,
        AVG(order_amount) as avg_order,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY order_amount) as median_order
    FROM orders
    WHERE order_date >= CURRENT_DATE - INTERVAL '2 years'
    GROUP BY customer_id
    HAVING COUNT(*) >= 5  -- Only customers with 5+ orders
),
customer_segments AS (
    SELECT 
        customer_id,
        total_spent,
        order_count,
        avg_order,
        median_order,
        CASE 
            WHEN total_spent >= 10000 THEN 'VIP'
            WHEN total_spent >= 5000 THEN 'Premium'
            WHEN total_spent >= 1000 THEN 'Standard'
            ELSE 'Basic'
        END as customer_segment
    FROM expensive_calculation
)
SELECT 
    cs.*,
    c.customer_name,
    c.email,
    c.registration_date
FROM customer_segments cs
JOIN customers c ON cs.customer_id = c.customer_id
ORDER BY cs.total_spent DESC"""
    
    @staticmethod
    def get_multiple_cte_template() -> str:
        """Get a template with multiple CTEs."""
        return """WITH product_stats AS (
    SELECT 
        product_id,
        product_name,
        category,
        COUNT(*) as units_sold,
        SUM(sale_amount) as revenue
    FROM sales
    WHERE sale_date >= CURRENT_DATE - INTERVAL '1 year'
    GROUP BY product_id, product_name, category
),
category_totals AS (
    SELECT 
        category,
        SUM(units_sold) as total_units,
        SUM(revenue) as total_revenue,
        COUNT(*) as product_count
    FROM product_stats
    GROUP BY category
),
top_products AS (
    SELECT 
        ps.*,
        RANK() OVER (PARTITION BY ps.category ORDER BY ps.revenue DESC) as rank_in_category,
        ROUND(ps.revenue / ct.total_revenue * 100, 2) as pct_of_category_revenue
    FROM product_stats ps
    JOIN category_totals ct ON ps.category = ct.category
),
category_performance AS (
    SELECT 
        category,
        total_revenue,
        total_units,
        product_count,
        ROUND(total_revenue / product_count, 2) as avg_revenue_per_product,
        RANK() OVER (ORDER BY total_revenue DESC) as category_rank
    FROM category_totals
)
SELECT 
    tp.product_name,
    tp.category,
    tp.units_sold,
    tp.revenue,
    tp.rank_in_category,
    tp.pct_of_category_revenue,
    cp.category_rank,
    cp.avg_revenue_per_product
FROM top_products tp
JOIN category_performance cp ON tp.category = cp.category
WHERE tp.rank_in_category <= 3  -- Top 3 products per category
ORDER BY cp.category_rank, tp.rank_in_category"""
    
    @staticmethod
    def get_time_series_cte_template() -> str:
        """Get a time series CTE template."""
        return """WITH RECURSIVE date_range AS (
    -- Generate a range of dates
    SELECT DATE '2024-01-01' as date_value
    UNION ALL
    SELECT date_value + INTERVAL '1 day'
    FROM date_range
    WHERE date_value < DATE '2024-12-31'
),
daily_sales AS (
    SELECT 
        DATE(sale_timestamp) as sale_date,
        SUM(amount) as daily_total,
        COUNT(*) as transaction_count
    FROM sales
    WHERE DATE(sale_timestamp) BETWEEN '2024-01-01' AND '2024-12-31'
    GROUP BY DATE(sale_timestamp)
),
sales_with_gaps_filled AS (
    SELECT 
        dr.date_value as sale_date,
        COALESCE(ds.daily_total, 0) as daily_total,
        COALESCE(ds.transaction_count, 0) as transaction_count
    FROM date_range dr
    LEFT JOIN daily_sales ds ON dr.date_value = ds.sale_date
),
moving_averages AS (
    SELECT 
        sale_date,
        daily_total,
        transaction_count,
        AVG(daily_total) OVER (
            ORDER BY sale_date 
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) as weekly_avg,
        AVG(daily_total) OVER (
            ORDER BY sale_date 
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ) as monthly_avg
    FROM sales_with_gaps_filled
)
SELECT 
    sale_date,
    daily_total,
    transaction_count,
    ROUND(weekly_avg, 2) as weekly_avg,
    ROUND(monthly_avg, 2) as monthly_avg,
    ROUND(daily_total - weekly_avg, 2) as variance_from_weekly_avg,
    CASE 
        WHEN daily_total > weekly_avg * 1.2 THEN 'Above Average'
        WHEN daily_total < weekly_avg * 0.8 THEN 'Below Average'
        ELSE 'Normal'
    END as performance_category
FROM moving_averages
ORDER BY sale_date"""


class CTEOptimizer:
    """Optimizer for CTE performance and structure."""
    
    def __init__(self):
        self.parser = CTEParser()
    
    def analyze_query(self, sql: str) -> CTEAnalysis:
        """Analyze a SQL query for CTE usage and optimization opportunities."""
        return self.parser.parse_ctes(sql)
    
    def suggest_materialization(self, analysis: CTEAnalysis) -> List[str]:
        """Suggest which CTEs should be materialized."""
        suggestions = []
        
        for cte in analysis.ctes:
            # Suggest materialization for CTEs that are referenced multiple times
            ref_count = sum(1 for other_cte in analysis.ctes if cte.name in other_cte.dependencies)
            
            if ref_count > 1:
                suggestions.append(f"Consider materializing CTE '{cte.name}' as it's referenced {ref_count} times")
            
            # Suggest materialization for complex CTEs
            if len(cte.query) > 500:  # Arbitrary threshold
                suggestions.append(f"Consider materializing CTE '{cte.name}' due to query complexity")
        
        return suggestions
    
    def convert_to_subqueries(self, analysis: CTEAnalysis) -> str:
        """Convert CTEs to subqueries where appropriate."""
        # This is a simplified conversion - real implementation would be more complex
        if not analysis.ctes:
            return analysis.main_query
        
        # For simple cases with one CTE, convert to subquery
        if len(analysis.ctes) == 1 and not analysis.ctes[0].dependencies:
            cte = analysis.ctes[0]
            # Replace CTE name in main query with subquery
            subquery = f"({cte.query})"
            converted_query = analysis.main_query.replace(cte.name, subquery)
            return converted_query
        
        # For complex cases, return original with suggestion
        return f"-- Complex CTE structure - manual conversion recommended\n{analysis.main_query}"