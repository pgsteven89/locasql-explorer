"""
Test script for query parser functionality.
"""

from src.localsql_explorer.query_parser import get_query_parser

def test_basic_queries():
    """Test basic query parsing."""
    parser = get_query_parser()
    
    # Test single query
    sql = "SELECT * FROM users;"
    queries = parser.parse_queries(sql)
    print(f"Test 1 - Single query:")
    print(f"  Found {len(queries)} query(ies)")
    for q in queries:
        print(f"  Query {q.query_number}: {q.text}")
    print()
    
    # Test multiple queries
    sql = """
    SELECT * FROM users;
    SELECT * FROM orders WHERE status = 'active';
    INSERT INTO logs (message) VALUES ('test');
    """
    queries = parser.parse_queries(sql)
    print(f"Test 2 - Multiple queries:")
    print(f"  Found {len(queries)} query(ies)")
    for q in queries:
        print(f"  Query {q.query_number}: {q.text[:50]}...")
    print()
    
    # Test semicolon in string
    sql = """
    SELECT * FROM users WHERE email = 'test;test@example.com';
    SELECT * FROM orders;
    """
    queries = parser.parse_queries(sql)
    print(f"Test 3 - Semicolon in string:")
    print(f"  Found {len(queries)} query(ies)")
    for q in queries:
        print(f"  Query {q.query_number}: {q.text[:60]}...")
    print()
    
    # Test comments
    sql = """
    -- This is a comment; with semicolon
    SELECT * FROM users;
    /* Block comment; with semicolon */
    SELECT * FROM orders;
    """
    queries = parser.parse_queries(sql)
    print(f"Test 4 - Comments with semicolons:")
    print(f"  Found {len(queries)} query(ies)")
    for q in queries:
        print(f"  Query {q.query_number}: {q.text[:60]}...")
    print()
    
    # Test cursor position detection
    sql = "SELECT * FROM users; SELECT * FROM orders;"
    cursor_pos = 5  # Inside first query
    query = parser.get_query_at_cursor(sql, cursor_pos)
    print(f"Test 5 - Query at cursor position {cursor_pos}:")
    if query:
        print(f"  Found query {query.query_number}: {query.text}")
    else:
        print(f"  No query found")
    print()
    
    cursor_pos = 25  # Inside second query
    query = parser.get_query_at_cursor(sql, cursor_pos)
    print(f"Test 6 - Query at cursor position {cursor_pos}:")
    if query:
        print(f"  Found query {query.query_number}: {query.text}")
    else:
        print(f"  No query found")
    print()

if __name__ == "__main__":
    print("=" * 80)
    print("Query Parser Tests")
    print("=" * 80)
    print()
    
    test_basic_queries()
    
    print("=" * 80)
    print("All tests completed!")
    print("=" * 80)
