"""
Test query history integration in LocalSQL Explorer.
"""

import sys
import tempfile
from pathlib import Path

# Add src to Python path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from localsql_explorer.query_history import QueryHistory, QueryEntry


def test_query_history_basic():
    """Test basic query history functionality."""
    print("Testing basic query history functionality...")
    
    # Use temporary file for testing
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp_file:
        temp_path = Path(temp_file.name)
    
    try:
        # Initialize query history
        history = QueryHistory(temp_path)
        
        # Add a test query
        query_id = history.add_query(
            sql="SELECT * FROM customers WHERE age > 25",
            execution_time=0.123,
            row_count=42,
            success=True,
            tables_used=["customers"]
        )
        
        print(f"Added query with ID: {query_id}")
        
        # Mark as favorite
        history.mark_favorite(query_id, True)
        print("Marked query as favorite")
        
        # Add tags
        history.add_tag(query_id, "analytics")
        history.add_tag(query_id, "customers")
        print("Added tags to query")
        
        # Get recent queries
        recent = history.get_recent_queries(10)
        print(f"Recent queries: {len(recent)}")
        
        # Get favorites
        favorites = history.get_favorites()
        print(f"Favorite queries: {len(favorites)}")
        
        # Search queries
        search_results = history.search_queries("customers")
        print(f"Search results for 'customers': {len(search_results)}")
        
        # Get statistics
        stats = history.get_query_stats()
        print(f"Query statistics: {stats}")
        
        # Test persistence
        history.save_history()
        
        # Load from new instance
        history2 = QueryHistory(temp_path)
        recent2 = history2.get_recent_queries(10)
        print(f"Loaded queries after restart: {len(recent2)}")
        
        print("✅ Basic query history test passed!")
        
    finally:
        # Cleanup
        if temp_path.exists():
            temp_path.unlink()


def test_query_history_advanced():
    """Test advanced query history features."""
    print("\nTesting advanced query history features...")
    
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp_file:
        temp_path = Path(temp_file.name)
    
    try:
        history = QueryHistory(temp_path)
        
        # Add multiple queries
        queries = [
            ("SELECT * FROM users", 0.05, 100, True, ["users"]),
            ("SELECT COUNT(*) FROM orders", 0.02, 1, True, ["orders"]),
            ("SELECT * FROM invalid_table", 0.0, 0, False, []),
            ("SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id", 0.15, 250, True, ["users", "orders"]),
        ]
        
        query_ids = []
        for sql, time, rows, success, tables in queries:
            error_msg = "Table does not exist" if not success else None
            qid = history.add_query(sql, time, rows, success, error_msg, tables)
            query_ids.append(qid)
        
        print(f"Added {len(query_ids)} test queries")
        
        # Test filtering
        successful_queries = [q for q in history.get_recent_queries() if q.success]
        failed_queries = [q for q in history.get_recent_queries() if not q.success]
        
        print(f"Successful queries: {len(successful_queries)}")
        print(f"Failed queries: {len(failed_queries)}")
        
        # Test table-based filtering
        user_queries = history.get_queries_by_table("users")
        print(f"Queries using 'users' table: {len(user_queries)}")
        
        # Test search
        join_queries = history.search_queries("JOIN")
        print(f"Queries containing 'JOIN': {len(join_queries)}")
        
        # Test statistics
        stats = history.get_query_stats()
        print(f"Success rate: {stats['success_rate']:.1%}")
        print(f"Average execution time: {stats['average_execution_time']:.3f}s")
        print(f"Most used tables: {stats['most_used_tables']}")
        
        print("✅ Advanced query history test passed!")
        
    finally:
        if temp_path.exists():
            temp_path.unlink()


if __name__ == "__main__":
    test_query_history_basic()
    test_query_history_advanced()
    print("\n🎉 All query history tests passed!")