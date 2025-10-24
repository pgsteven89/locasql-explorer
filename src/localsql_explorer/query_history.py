"""
Query history and favorites management for LocalSQL Explorer.

This module provides:
- Query history tracking with metadata
- Favorites management system
- Persistent storage of queries
- Query search and filtering
- Usage statistics and analytics
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class QueryEntry(BaseModel):
    """A single query entry in the history."""
    
    id: str = Field(..., description="Unique query identifier")
    sql: str = Field(..., description="SQL query text")
    timestamp: str = Field(..., description="When the query was executed")
    execution_time: float = Field(0.0, description="Query execution time in seconds")
    row_count: int = Field(0, description="Number of rows returned")
    success: bool = Field(True, description="Whether query executed successfully")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    is_favorite: bool = Field(False, description="Whether query is marked as favorite")
    tags: List[str] = Field(default_factory=list, description="User-defined tags")
    description: Optional[str] = Field(None, description="User description of the query")
    tables_used: List[str] = Field(default_factory=list, description="Tables referenced in query")
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict) -> "QueryEntry":
        """Create from dictionary."""
        return cls(**data)


class QueryHistory:
    """
    Manages query history and favorites with persistent storage.
    
    Features:
    - Automatic query tracking
    - Favorites management
    - Search and filtering
    - Persistent storage
    - Usage analytics
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize query history manager.
        
        Args:
            storage_path: Path to store history file (defaults to user data dir)
        """
        self.storage_path = storage_path or self._get_default_storage_path()
        self.queries: Dict[str, QueryEntry] = {}
        self.load_history()
        
    def _get_default_storage_path(self) -> Path:
        """Get default storage path for query history."""
        # Use user's data directory
        try:
            from pathlib import Path
            import os
            
            if os.name == 'nt':  # Windows
                data_dir = Path.home() / "AppData" / "Local" / "LocalSQL Explorer"
            else:  # Unix-like
                data_dir = Path.home() / ".localsql_explorer"
                
            data_dir.mkdir(parents=True, exist_ok=True)
            return data_dir / "query_history.json"
        except Exception:
            # Fallback to current directory
            return Path("query_history.json")
    
    def add_query(self, sql: str, execution_time: float = 0.0, row_count: int = 0, 
                  success: bool = True, error_message: Optional[str] = None,
                  tables_used: Optional[List[str]] = None) -> str:
        """
        Add a query to the history.
        
        Args:
            sql: SQL query text
            execution_time: Time taken to execute
            row_count: Number of rows returned
            success: Whether query was successful
            error_message: Error message if failed
            tables_used: List of tables used in query
            
        Returns:
            str: Query ID
        """
        # Generate unique ID
        query_id = self._generate_query_id(sql)
        
        # Extract tables from SQL if not provided
        if tables_used is None:
            tables_used = self._extract_tables_from_sql(sql)
        
        # Create query entry
        entry = QueryEntry(
            id=query_id,
            sql=sql.strip(),
            timestamp=datetime.now().isoformat(),
            execution_time=execution_time,
            row_count=row_count,
            success=success,
            error_message=error_message,
            tables_used=tables_used
        )
        
        self.queries[query_id] = entry
        self.save_history()
        
        logger.info(f"Added query to history: {query_id}")
        return query_id
    
    def mark_favorite(self, query_id: str, is_favorite: bool = True) -> bool:
        """
        Mark a query as favorite or remove from favorites.
        
        Args:
            query_id: Query identifier
            is_favorite: Whether to mark as favorite
            
        Returns:
            bool: True if successful
        """
        if query_id in self.queries:
            self.queries[query_id].is_favorite = is_favorite
            self.save_history()
            logger.info(f"Query {query_id} favorite status: {is_favorite}")
            return True
        return False
    
    def add_tag(self, query_id: str, tag: str) -> bool:
        """
        Add a tag to a query.
        
        Args:
            query_id: Query identifier
            tag: Tag to add
            
        Returns:
            bool: True if successful
        """
        if query_id in self.queries and tag not in self.queries[query_id].tags:
            self.queries[query_id].tags.append(tag)
            self.save_history()
            return True
        return False
    
    def remove_tag(self, query_id: str, tag: str) -> bool:
        """
        Remove a tag from a query.
        
        Args:
            query_id: Query identifier
            tag: Tag to remove
            
        Returns:
            bool: True if successful
        """
        if query_id in self.queries and tag in self.queries[query_id].tags:
            self.queries[query_id].tags.remove(tag)
            self.save_history()
            return True
        return False
    
    def set_description(self, query_id: str, description: str) -> bool:
        """
        Set description for a query.
        
        Args:
            query_id: Query identifier
            description: Query description
            
        Returns:
            bool: True if successful
        """
        if query_id in self.queries:
            self.queries[query_id].description = description
            self.save_history()
            return True
        return False
    
    def get_recent_queries(self, limit: int = 20) -> List[QueryEntry]:
        """
        Get recent queries ordered by timestamp.
        
        Args:
            limit: Maximum number of queries to return
            
        Returns:
            List[QueryEntry]: Recent queries
        """
        sorted_queries = sorted(
            self.queries.values(),
            key=lambda q: q.timestamp,
            reverse=True
        )
        return sorted_queries[:limit]
    
    def get_favorites(self) -> List[QueryEntry]:
        """
        Get all favorite queries.
        
        Returns:
            List[QueryEntry]: Favorite queries
        """
        return [q for q in self.queries.values() if q.is_favorite]
    
    def search_queries(self, search_term: str, include_sql: bool = True, 
                      include_description: bool = True, include_tags: bool = True) -> List[QueryEntry]:
        """
        Search queries by text.
        
        Args:
            search_term: Text to search for
            include_sql: Whether to search SQL text
            include_description: Whether to search descriptions
            include_tags: Whether to search tags
            
        Returns:
            List[QueryEntry]: Matching queries
        """
        search_term = search_term.lower()
        matches = []
        
        for query in self.queries.values():
            if include_sql and search_term in query.sql.lower():
                matches.append(query)
            elif include_description and query.description and search_term in query.description.lower():
                matches.append(query)
            elif include_tags and any(search_term in tag.lower() for tag in query.tags):
                matches.append(query)
        
        return matches
    
    def get_queries_by_table(self, table_name: str) -> List[QueryEntry]:
        """
        Get queries that use a specific table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List[QueryEntry]: Queries using the table
        """
        return [q for q in self.queries.values() if table_name in q.tables_used]
    
    def get_query_stats(self) -> Dict:
        """
        Get query usage statistics.
        
        Returns:
            Dict: Statistics about query usage
        """
        total_queries = len(self.queries)
        successful_queries = sum(1 for q in self.queries.values() if q.success)
        favorite_count = sum(1 for q in self.queries.values() if q.is_favorite)
        
        if total_queries > 0:
            avg_execution_time = sum(q.execution_time for q in self.queries.values()) / total_queries
            success_rate = successful_queries / total_queries
        else:
            avg_execution_time = 0.0
            success_rate = 0.0
        
        # Most used tables
        table_usage = {}
        for query in self.queries.values():
            for table in query.tables_used:
                table_usage[table] = table_usage.get(table, 0) + 1
        
        most_used_tables = sorted(table_usage.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "total_queries": total_queries,
            "successful_queries": successful_queries,
            "favorite_count": favorite_count,
            "success_rate": success_rate,
            "average_execution_time": avg_execution_time,
            "most_used_tables": most_used_tables
        }
    
    def delete_query(self, query_id: str) -> bool:
        """
        Delete a query from history.
        
        Args:
            query_id: Query identifier
            
        Returns:
            bool: True if successful
        """
        if query_id in self.queries:
            del self.queries[query_id]
            self.save_history()
            logger.info(f"Deleted query: {query_id}")
            return True
        return False
    
    def clear_history(self, keep_favorites: bool = True) -> int:
        """
        Clear query history.
        
        Args:
            keep_favorites: Whether to keep favorite queries
            
        Returns:
            int: Number of queries deleted
        """
        if keep_favorites:
            to_delete = [qid for qid, q in self.queries.items() if not q.is_favorite]
            for qid in to_delete:
                del self.queries[qid]
            deleted_count = len(to_delete)
        else:
            deleted_count = len(self.queries)
            self.queries.clear()
        
        self.save_history()
        logger.info(f"Cleared {deleted_count} queries from history")
        return deleted_count
    
    def save_history(self):
        """Save history to storage."""
        try:
            data = {
                "version": "1.0",
                "queries": {qid: q.to_dict() for qid, q in self.queries.items()}
            }
            
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to save query history: {e}")
    
    def load_history(self):
        """Load history from storage."""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                queries_data = data.get("queries", {})
                self.queries = {
                    qid: QueryEntry.from_dict(qdata) 
                    for qid, qdata in queries_data.items()
                }
                
                logger.info(f"Loaded {len(self.queries)} queries from history")
            else:
                logger.info("No existing query history found")
                
        except Exception as e:
            logger.error(f"Failed to load query history: {e}")
            self.queries = {}
    
    def _generate_query_id(self, sql: str) -> str:
        """Generate a unique ID for a query."""
        import hashlib
        import time
        
        # Use SQL hash + timestamp for uniqueness
        sql_hash = hashlib.md5(sql.encode()).hexdigest()[:8]
        timestamp = str(int(time.time() * 1000))[-6:]  # Last 6 digits of timestamp
        
        return f"q_{sql_hash}_{timestamp}"
    
    def _extract_tables_from_sql(self, sql: str) -> List[str]:
        """Extract table names from SQL query (basic implementation)."""
        import re
        
        # Simple regex to find table names after FROM and JOIN keywords
        # This is a basic implementation - could be enhanced with proper SQL parsing
        pattern = r'(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        matches = re.findall(pattern, sql, re.IGNORECASE)
        
        return list(set(matches))  # Remove duplicates