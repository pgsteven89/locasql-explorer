"""
Query parser module for handling multiple SQL queries in a single editor.

This module provides utilities for:
- Parsing multiple SQL statements separated by semicolons
- Detecting the query at a specific cursor position
- Handling edge cases (strings, comments, nested statements)
- Validating query boundaries
"""

import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class QueryInfo:
    """Information about a parsed SQL query."""
    text: str  # The query text
    start_pos: int  # Starting character position in the full text
    end_pos: int  # Ending character position in the full text
    start_line: int  # Starting line number (0-based)
    end_line: int  # Ending line number (0-based)
    query_number: int  # Query number (1-based)


class QueryParser:
    """
    Parser for handling multiple SQL queries in a single text.
    
    Features:
    - Split text into individual SQL statements
    - Handle semicolons in strings and comments
    - Detect query at cursor position
    - Validate query boundaries
    """
    
    def __init__(self):
        """Initialize the query parser."""
        pass
    
    def parse_queries(self, text: str) -> List[QueryInfo]:
        """
        Parse multiple SQL queries from text.
        
        Args:
            text: The full SQL text containing one or more queries
            
        Returns:
            List of QueryInfo objects, one for each query found
        """
        if not text or not text.strip():
            return []
        
        queries = []
        query_positions = self._find_query_boundaries(text)
        
        lines = text.split('\n')
        
        for idx, (start_pos, end_pos) in enumerate(query_positions, 1):
            query_text = text[start_pos:end_pos].strip()
            
            if not query_text:
                continue
            
            # Calculate line numbers
            start_line = text[:start_pos].count('\n')
            end_line = text[:end_pos].count('\n')
            
            queries.append(QueryInfo(
                text=query_text,
                start_pos=start_pos,
                end_pos=end_pos,
                start_line=start_line,
                end_line=end_line,
                query_number=idx
            ))
        
        return queries
    
    def get_query_at_cursor(self, text: str, cursor_position: int) -> Optional[QueryInfo]:
        """
        Get the query at the specified cursor position.
        
        Args:
            text: The full SQL text
            cursor_position: The cursor position (character index)
            
        Returns:
            QueryInfo for the query at cursor position, or None if no query found
        """
        queries = self.parse_queries(text)
        
        for query in queries:
            if query.start_pos <= cursor_position <= query.end_pos:
                return query
        
        return None
    
    def _find_query_boundaries(self, text: str) -> List[Tuple[int, int]]:
        """
        Find the boundaries of all queries in the text.
        
        This method handles:
        - Semicolons as statement separators
        - Semicolons inside strings (single and double quotes)
        - Semicolons in comments (-- and /* */)
        
        Args:
            text: The full SQL text
            
        Returns:
            List of (start_pos, end_pos) tuples for each query
        """
        boundaries = []
        current_pos = 0
        query_start = 0
        
        in_single_quote = False
        in_double_quote = False
        in_line_comment = False
        in_block_comment = False
        
        i = 0
        while i < len(text):
            char = text[i]
            
            # Check for block comment start
            if not in_single_quote and not in_double_quote and not in_line_comment:
                if i < len(text) - 1 and text[i:i+2] == '/*':
                    in_block_comment = True
                    i += 2
                    continue
            
            # Check for block comment end
            if in_block_comment:
                if i < len(text) - 1 and text[i:i+2] == '*/':
                    in_block_comment = False
                    i += 2
                    continue
                i += 1
                continue
            
            # Check for line comment start
            if not in_single_quote and not in_double_quote and not in_block_comment:
                if i < len(text) - 1 and text[i:i+2] == '--':
                    in_line_comment = True
                    i += 2
                    continue
            
            # Check for line comment end
            if in_line_comment:
                if char == '\n':
                    in_line_comment = False
                i += 1
                continue
            
            # Handle quotes (not in comments)
            if not in_line_comment and not in_block_comment:
                # Single quote
                if char == "'":
                    # Check if it's escaped
                    if i > 0 and text[i-1] == '\\':
                        i += 1
                        continue
                    in_single_quote = not in_single_quote
                    i += 1
                    continue
                
                # Double quote
                if char == '"':
                    # Check if it's escaped
                    if i > 0 and text[i-1] == '\\':
                        i += 1
                        continue
                    in_double_quote = not in_double_quote
                    i += 1
                    continue
            
            # Check for semicolon (statement terminator)
            if (char == ';' and 
                not in_single_quote and 
                not in_double_quote and 
                not in_line_comment and 
                not in_block_comment):
                
                # Found a query boundary
                boundaries.append((query_start, i + 1))
                query_start = i + 1
            
            i += 1
        
        # Add the last query if there's remaining text
        if query_start < len(text):
            remaining_text = text[query_start:].strip()
            if remaining_text:
                boundaries.append((query_start, len(text)))
        
        return boundaries
    
    def format_query_text(self, query: QueryInfo) -> str:
        """
        Format a query for display.
        
        Args:
            query: The QueryInfo object
            
        Returns:
            Formatted query text
        """
        return query.text.strip()
    
    def validate_query_syntax(self, query_text: str) -> Tuple[bool, Optional[str]]:
        """
        Perform basic syntax validation on a query.
        
        Args:
            query_text: The SQL query text
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        query = query_text.strip()
        
        if not query:
            return False, "Empty query"
        
        # Check for balanced parentheses
        paren_count = 0
        in_string = False
        string_char = None
        
        for char in query:
            if char in ('"', "'") and not in_string:
                in_string = True
                string_char = char
            elif char == string_char and in_string:
                in_string = False
                string_char = None
            elif not in_string:
                if char == '(':
                    paren_count += 1
                elif char == ')':
                    paren_count -= 1
                    if paren_count < 0:
                        return False, "Unbalanced parentheses: too many closing parentheses"
        
        if paren_count != 0:
            return False, f"Unbalanced parentheses: {paren_count} unclosed opening parentheses"
        
        # Basic SQL keyword check
        sql_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER', 'WITH', 'DESCRIBE', 'SHOW', 'PRAGMA']
        query_upper = query.upper()
        
        has_keyword = any(query_upper.startswith(kw) or f' {kw} ' in query_upper or f'\n{kw} ' in query_upper 
                         for kw in sql_keywords)
        
        if not has_keyword:
            return False, "Query does not appear to contain a valid SQL statement"
        
        return True, None


# Singleton instance
_parser_instance = None


def get_query_parser() -> QueryParser:
    """Get the singleton query parser instance."""
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = QueryParser()
    return _parser_instance
