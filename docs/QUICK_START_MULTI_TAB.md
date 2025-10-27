# Quick Start: Multi-Tab SQL Editor

## New Features in Phase 9! 🎉

LocalSQL Explorer now supports **multiple SQL editor tabs** and **multi-query execution** to boost your productivity!

---

## 📑 Working with Multiple Tabs

### Creating Tabs
- **Click the `+` button** in the tab bar
- **Press `Ctrl+T`** for quick tab creation

### Managing Tabs
- **Switch tabs**: Click on them or use `Ctrl+Tab` (next) / `Ctrl+Shift+Tab` (previous)
- **Rename tabs**: Double-click the tab title
- **Close tabs**: Click the `X` or press `Ctrl+W`
- **Reorder tabs**: Drag and drop them
- **Modified indicator**: Unsaved tabs show a `*`

### Tab Context Menu
Right-click any tab for options:
- **Rename**: Give your tab a descriptive name
- **Close**: Close this tab
- **Close Others**: Close all except this one
- **Close Tabs to the Right**: Bulk close

---

## 🎯 Running Multiple Queries

### Write Multiple Queries
Simply separate them with semicolons:

```sql
SELECT * FROM users WHERE status = 'active';

SELECT COUNT(*) as total FROM orders;

SELECT department, AVG(salary) FROM employees GROUP BY department;
```

The **"Queries: 3"** label shows how many queries were detected.

### Run Current Query
**Place your cursor** in any query and:
- **Click** "▶ Run Current Query"
- **Press `Ctrl+Enter`** (just like VS Code!)
- **Press `F5`** (legacy shortcut)

✨ Only the query at your cursor position will execute!

### Run All Queries
To execute all queries in sequence:
- **Click** "▶▶ Run All Queries"
- **Press `Ctrl+Shift+Enter`**

You'll see:
- Progress for each query
- Summary dialog when complete
- Option to cancel mid-execution
- Choice to continue if a query fails

---

## ⌨️ Keyboard Shortcuts Reference

| Shortcut | Action |
|----------|--------|
| `Ctrl+T` | New tab |
| `Ctrl+W` | Close tab |
| `Ctrl+Tab` | Next tab |
| `Ctrl+Shift+Tab` | Previous tab |
| `Ctrl+Enter` | Run current query |
| `Ctrl+Shift+Enter` | Run all queries |
| `F5` | Run current query (legacy) |

---

## 💡 Pro Tips

### Organize Your Work
Create tabs for different purposes:
- **"Exploration"**: Quick data browsing queries
- **"Analysis"**: Complex analytical queries
- **"Reports"**: Queries for regular reports
- **"Testing"**: Experimental queries

### Quick Query Testing
1. Write multiple variations of a query
2. Use semicolons to separate them
3. Press `Ctrl+Enter` to test each one quickly
4. No need to comment out or delete queries!

### Smart Query Detection
The parser is smart about semicolons:
- ✅ `SELECT * FROM users WHERE email = 'test;user@example.com';` → 1 query
- ✅ `-- comment with semicolon; SELECT * FROM users;` → 1 query
- ✅ `/* block comment; */ SELECT * FROM orders;` → 1 query

### Tab Persistence
Your tabs are automatically saved:
- All tab names preserved
- SQL content in each tab saved
- Active tab remembered
- Restored when you reopen the app

---

## 📋 Common Workflows

### Workflow 1: Data Exploration
```sql
-- Tab 1: "Users"
SELECT * FROM users LIMIT 10;

-- Tab 2: "Orders"
SELECT * FROM orders WHERE order_date > '2024-01-01';

-- Tab 3: "Summary"
SELECT 
    u.name, 
    COUNT(o.id) as order_count 
FROM users u 
LEFT JOIN orders o ON u.id = o.user_id 
GROUP BY u.name;
```

Switch between tabs to see different aspects of your data.

### Workflow 2: Report Generation
```sql
-- Tab: "Monthly Report"
-- Run all queries together
SELECT COUNT(*) as total_users FROM users;
SELECT COUNT(*) as total_orders FROM orders;
SELECT SUM(amount) as total_revenue FROM orders;
SELECT AVG(amount) as avg_order_value FROM orders;
```

Press `Ctrl+Shift+Enter` to generate complete report.

### Workflow 3: Query Development
```sql
-- Tab: "Development"
-- Test different approaches
SELECT * FROM orders WHERE status = 'pending';
SELECT * FROM orders WHERE status IN ('pending', 'processing');
SELECT * FROM orders WHERE status LIKE 'pend%';
```

Use `Ctrl+Enter` to test each variation quickly.

---

## 🆘 Troubleshooting

### "No query found to execute"
- Make sure your cursor is inside a query
- Check that queries are separated by semicolons
- Verify the query isn't empty

### Multiple queries detected incorrectly
- Check for semicolons in strings - use proper quotes
- Check comments aren't breaking parsing
- Report unusual cases for improvement

### Tab didn't restore after restart
- Ensure you closed the app normally (not force kill)
- Check app settings weren't cleared
- Try manually saving via File menu

---

## 🎓 Examples

### Example 1: Basic Multi-Query
```sql
-- Get user count by status
SELECT status, COUNT(*) as count 
FROM users 
GROUP BY status;

-- Get today's orders
SELECT * 
FROM orders 
WHERE DATE(created_at) = CURRENT_DATE;
```

Place cursor in first query → `Ctrl+Enter` → See user count  
Place cursor in second query → `Ctrl+Enter` → See today's orders

### Example 2: Data Analysis Pipeline
```sql
-- Create temp result
CREATE TEMP TABLE active_users AS
SELECT * FROM users WHERE status = 'active';

-- Analyze temp result
SELECT department, COUNT(*) 
FROM active_users 
GROUP BY department;

-- Clean up
DROP TABLE active_users;
```

Run all with `Ctrl+Shift+Enter` for complete pipeline.

### Example 3: Multiple Tabs for Context
**Tab: "Staging Queries"**
```sql
SELECT * FROM staging_users LIMIT 100;
```

**Tab: "Production Queries"**
```sql
SELECT * FROM prod_users LIMIT 100;
```

**Tab: "Comparison"**
```sql
SELECT COUNT(*) as staging_count FROM staging_users;
SELECT COUNT(*) as prod_count FROM prod_users;
```

---

## 🚀 Get Started!

1. **Open LocalSQL Explorer**
2. **Import some data** (CSV, Excel, or Parquet)
3. **Create a new tab** with `Ctrl+T`
4. **Write multiple queries** separated by semicolons
5. **Press `Ctrl+Enter`** to run the query at cursor
6. **Press `Ctrl+Shift+Enter`** to run all queries

Enjoy your enhanced SQL editing experience! 🎉

---

**Need Help?** Check the full testing guide in `docs/PHASE_9_TESTING_GUIDE.md`
