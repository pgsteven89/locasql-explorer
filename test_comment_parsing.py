"""
Comprehensive test for Phase 9 comment toggle feature.
"""

from src.localsql_explorer.query_parser import get_query_parser

def test_comment_parsing():
    """Test that commented queries are excluded from parsing."""
    parser = get_query_parser()
    
    print("=" * 80)
    print("TEST 1: Fully Commented Query")
    print("=" * 80)
    
    sql1 = """
-- SELECT * FROM users;
SELECT * FROM orders;
"""
    queries1 = parser.parse_queries(sql1)
    print(f"SQL:\n{sql1}")
    print(f"\nFound {len(queries1)} queries (should be 1)")
    for q in queries1:
        print(f"  Query {q.query_number}: {q.text[:50]}...")
    assert len(queries1) == 1, "Should find only 1 query (commented one excluded)"
    print("✅ PASSED\n")
    
    print("=" * 80)
    print("TEST 2: Mixed Commented and Uncommented")
    print("=" * 80)
    
    sql2 = """
SELECT * FROM users;
-- SELECT * FROM customers;
SELECT * FROM orders;
-- SELECT * FROM products;
SELECT * FROM inventory;
"""
    queries2 = parser.parse_queries(sql2)
    print(f"SQL:\n{sql2}")
    print(f"\nFound {len(queries2)} queries (should be 3)")
    for q in queries2:
        print(f"  Query {q.query_number}: {q.text[:50]}...")
    assert len(queries2) == 3, "Should find 3 queries (2 commented ones excluded)"
    print("✅ PASSED\n")
    
    print("=" * 80)
    print("TEST 3: Comment with Semicolon")
    print("=" * 80)
    
    sql3 = """
SELECT * FROM users;
-- This is a comment; with semicolon
SELECT * FROM orders;
"""
    queries3 = parser.parse_queries(sql3)
    print(f"SQL:\n{sql3}")
    print(f"\nFound {len(queries3)} queries (should be 2)")
    for q in queries3:
        print(f"  Query {q.query_number}: {q.text[:50]}...")
    assert len(queries3) == 2, "Semicolon in comment shouldn't create query boundary"
    print("✅ PASSED\n")
    
    print("=" * 80)
    print("TEST 4: Block Comment vs Line Comment")
    print("=" * 80)
    
    sql4 = """
SELECT * FROM users;
/* Block comment
   SELECT * FROM temp;
*/
-- Line comment SELECT * FROM temp2;
SELECT * FROM orders;
"""
    queries4 = parser.parse_queries(sql4)
    print(f"SQL:\n{sql4}")
    print(f"\nFound {len(queries4)} queries (should be 2)")
    for q in queries4:
        print(f"  Query {q.query_number}: {q.text[:50]}...")
    assert len(queries4) == 2, "Both block and line comments should be ignored"
    print("✅ PASSED\n")
    
    print("=" * 80)
    print("TEST 5: Commented Multi-line Query")
    print("=" * 80)
    
    sql5 = """
SELECT * FROM users WHERE status = 'active';

-- SELECT id, name, email
-- FROM customers
-- WHERE created_at > '2024-01-01';

SELECT COUNT(*) FROM orders;
"""
    queries5 = parser.parse_queries(sql5)
    print(f"SQL:\n{sql5}")
    print(f"\nFound {len(queries5)} queries (should be 2)")
    for q in queries5:
        print(f"  Query {q.query_number}: {q.text[:50]}...")
    assert len(queries5) == 2, "Multi-line commented query should be excluded"
    print("✅ PASSED\n")
    
    print("=" * 80)
    print("TEST 6: All Queries Commented Out")
    print("=" * 80)
    
    sql6 = """
-- SELECT * FROM users;
-- SELECT * FROM orders;
-- SELECT * FROM customers;
"""
    queries6 = parser.parse_queries(sql6)
    print(f"SQL:\n{sql6}")
    print(f"\nFound {len(queries6)} queries (should be 0)")
    assert len(queries6) == 0, "All commented queries should result in 0 queries"
    print("✅ PASSED\n")
    
    print("=" * 80)
    print("ALL TESTS PASSED! ✅")
    print("=" * 80)
    print("\nComment toggle feature correctly integrates with query parser:")
    print("  ✅ Commented queries are excluded from execution")
    print("  ✅ Semicolons in comments don't affect parsing")
    print("  ✅ Mixed commented/uncommented queries handled correctly")
    print("  ✅ Multi-line commented queries work properly")
    print("  ✅ Both line (--) and block (/* */) comments supported")
    print()

if __name__ == "__main__":
    test_comment_parsing()
