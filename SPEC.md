# 🧩 LocalSQL Explorer

*A local desktop application for exploring and querying CSV, XLSX, and Parquet files using SQL.*

---

## 1. Overview

**LocalSQL Explorer** is a Python desktop app that allows users to:

* Import datasets from CSV, Excel (XLSX), or Parquet files.
* Treat each file as a table within an embedded DuckDB database.
* Run SQL queries (including joins across multiple tables).
* View results in an interactive table view.
* Export query results to various formats.
* Save or load a persistent DuckDB database for future use.

This project emphasizes **spec-driven development**, ensuring all features are clearly defined before implementation.

---

## 2. Core Features

| Feature              | Description                                                                                           |
| -------------------- | ----------------------------------------------------------------------------------------------------- |
| **File Import**      | Import CSV, XLSX, or Parquet files using a file picker.                                               |
| **Table Management** | Each imported file becomes a DuckDB table (named after the file). Supports rename, drop, and refresh. |
| **Table List View**  | Sidebar showing all tables and basic metadata (columns, row count).                                   |
| **SQL Editor Pane**  | Syntax-highlighted editor for writing SQL queries.                                                    |
| **Query Execution**  | Execute SQL queries across any combination of tables.                                                 |
| **Results Viewer**   | Display query results in a scrollable, sortable table view.                                           |
| **Export Results**   | Export results to CSV, Excel, or Parquet.                                                             |
| **Persistence**      | Save and load the database (`.duckdb` file).                                                          |
| **Error Handling**   | Display clear, user-friendly messages for SQL or file errors.                                         |
| **Theme Support**    | Optional dark/light theme toggle.                                                                     |

---

## 3. Technical Specifications

### Backend

* **Language:** Python 3.10+
* **Database Engine:** [DuckDB](https://duckdb.org) (embedded mode)
* **Core Libraries:**

  * `duckdb` – in-memory and persisted SQL engine
  * `pandas` – Excel reading and DataFrame integration
  * `openpyxl` – Excel import/export
  * `pyarrow` – Parquet import/export
  * `sqlparse` – SQL formatting and validation
  * `pydantic` – for config/spec validation
  * `typer` (optional) – for future CLI interface

### UI Layer

* **Primary Option:** PyQt6

  * `QMainWindow` with menu bar and dockable panels
  * `QPlainTextEdit` or `QsciScintilla` for SQL editor
  * `QTableView` backed by `QAbstractTableModel` for data display
* **Alternative Option (future):** Streamlit or NiceGUI for a local web-based interface.

### File Support

| File Type  | Import                      | Export                       |
| ---------- | --------------------------- | ---------------------------- |
| `.csv`     | ✅ `read_csv_auto(path)`     | ✅ `to_csv()`                 |
| `.xlsx`    | ✅ via `pandas.read_excel()` | ✅ via `DataFrame.to_excel()` |
| `.parquet` | ✅ `read_parquet(path)`      | ✅ `to_parquet()`             |

---

## 4. UI/UX Design

### Layout Overview

```
+-------------------------------------------------------------+
| Menu Bar: [Import] [Save DB] [Load DB] [Export] [Help]      |
+---------------------+---------------------------------------+
| Table List          |  SQL Editor (top half)                |
| (Left Pane)         |---------------------------------------|
| - table1            |  Query Results (bottom half)          |
| - table2            |                                       |
| - table3            |                                       |
+---------------------+---------------------------------------+
| Status Bar: "Ready" / "Executed in 0.05s"                   |
+-------------------------------------------------------------+
```

### UI Components

#### 🗂 Table List Panel

* Shows all loaded tables.
* Click → preview schema and sample rows.
* Right-click options:

  * Rename
  * Drop
  * Export

#### 📝 SQL Editor Pane

* Syntax highlighting for SQL.
* “Run Query” button with F5 shortcut.
* Query history stored locally.

#### 📊 Query Results

* Scrollable table grid with sorting.
* Pagination for large datasets.
* Right-click → “Export Result”.

#### 🧭 Menu Bar

* **File:** Import, Save DB, Load DB, Exit
* **Edit:** Undo, Redo, Clear Editor
* **View:** Toggle Table Pane, Toggle Theme
* **Help:** About, Shortcuts

---

## 5. Persistence Model

* **Save Database:** Writes current schema and data to a `.duckdb` file.

  ```python
  con = duckdb.connect('project.duckdb')
  ```
* **Load Database:** Reconnects to an existing file, rehydrating tables in the UI.
* Supports both in-memory and on-disk databases for flexibility.

---

## 6. Non-Functional Requirements

| Requirement           | Description                                                            |
| --------------------- | ---------------------------------------------------------------------- |
| **Performance**       | Handle datasets up to ~1 GB smoothly using DuckDB’s vectorized engine. |
| **Cross-Platform**    | Works on Windows, macOS, and Linux.                                    |
| **Offline Operation** | No internet required.                                                  |
| **Data Safety**       | Read-only file imports (no file mutation).                             |
| **Extensibility**     | Modular architecture for plugins (data profiling, visualization).      |

---

## 7. Phase Breakdown

### **Phase 1 – Core Functionality**

* [ ] Initialize project structure (PyQt6 + DuckDB + Pandas).
* [ ] Implement file import for CSV/XLSX/Parquet.
* [ ] Implement automatic table registration in DuckDB.
* [ ] Build UI skeleton (table list, SQL editor, result view).
* [ ] Execute queries and render results in the table view.

### **Phase 2 – Persistence & Export**

* [ ] Add export result functionality (CSV/XLSX/Parquet).
* [ ] Implement Save/Load database (using `.duckdb` files).
* [ ] Add table management actions (rename, drop).
* [ ] Add query error handling and result metrics.
* [ ] Add status bar updates and progress indicators.

### **Phase 3 – UX & Enhancements**

* [x] Add query history and favorites.
* [x] Add dark/light theme toggle.
* [x] Add column metadata preview.
* [x] Add table summary/profiling view.
* [x] Optimize large data rendering (lazy load/pagination).

### **Phase 4 – Advanced SQL Features & Editor Intelligence**

* [ ] **CTE (Common Table Expression) Support** - Add full support for CTEs (WITH clauses) in SQL queries, similar to Snowflake functionality.
  * Support multiple CTEs in a single query
  * Recursive CTE support where applicable
  * Syntax highlighting for CTE keywords
  * Error validation for CTE syntax
  * Query execution optimization for CTE performance

* [ ] **Intelligent SQL Editor** - Enhanced editor with smart auto-completion and bracket matching.
  * Auto-closing brackets: `()`, `[]`, `{}`
  * Auto-closing quotes: `''`, `""`
  * Smart indentation for multi-line queries
  * Bracket highlighting and matching
  * Auto-completion for SQL keywords, table names, and column names
  * Intelligent code formatting and prettification
  * Multi-cursor editing support
  * Find and replace with regex support

### **Phase 5 – Enhanced File Import & User Experience**

* [ ] **Drag-and-Drop File Import** - Allow users to drag files directly into the application for seamless importing.
  * Enable drag-and-drop into the table list panel to import files as new tables
  * Support dropping multiple files at once with automatic batch import
  * Visual feedback during drag operations (highlight drop zones, progress indicators)
  * Maintain all existing file format support (CSV, XLSX, Parquet)
  * Auto-generate appropriate table names from dragged file names
  * Handle file naming conflicts gracefully with user prompts

* [ ] **Multi-File Selection Import** - Enhance the "Import File" dialog to support selecting multiple files simultaneously.
  * Modify file dialog to allow multi-selection (Ctrl+click, Shift+click)
  * Import each selected file as its own separate table
  * Show progress dialog for batch imports with individual file status
  * Display summary of successful/failed imports
  * Allow users to preview and modify table names before import
  * Support mixed file types in a single selection (CSV + XLSX + Parquet)
  * Implement smart duplicate handling and table name generation

### **Phase 6 – Enhanced Search and Filtering**

* [x] **Column-Specific Search in Results View** - Add advanced search capabilities to query results with column targeting.
  * Add column dropdown selector next to search input in paginated results view
  * Populate dropdown with all column names from current query results
  * Include "All Columns" option for global search across all fields
  * Implement column-specific filtering that only searches within selected column
  * Support case-sensitive/insensitive search toggle for refined filtering
  * Maintain search state when navigating between pages in paginated results
  * Real-time search filtering with debounced input to prevent performance issues
  * Clear visual indicators showing which column is being searched and active filters

* [ ] **Enhanced Export and Pagination Controls** - Improve data export options and user control over pagination.
  * Add "Export All Results" button to export complete query result set (all pages)
  * Add "Export Filtered Results" button to export only rows matching current search filters
  * Implement dynamic page size selector with common options (100, 500, 1000, 2500, 5000, 10000)
  * Maintain user's preferred page size across sessions and queries
  * Show export progress for large result sets with cancellation option
  * Support all export formats (CSV, Excel, Parquet) for both export modes
  * Clear labeling to distinguish between current page, filtered results, and complete dataset exports

* [ ] **Advanced Filter Operators** - Extend search functionality with SQL-like operators.
  * Support basic comparison operators (equals, contains, starts with, ends with)
  * Add numeric range filtering for numeric columns (greater than, less than, between)
  * Date range filtering for date/datetime columns with calendar picker
  * Pattern matching with wildcards and basic regex support
  * Multiple filter conditions with AND/OR logic
  * Filter history and saved filter presets for common queries
  * Export filtered results while maintaining original query context

---

## 8. Future Enhancements

* Inline data visualizations (e.g., bar charts, histograms).
* Query autocomplete and table/column suggestions.
* Keyboard shortcuts for SQL execution and navigation.
* Plugin architecture for analytics extensions.
* Export full workspace as a reproducible project.

---

## 9. Project Goals

* **Ease of use:** Empower non-developers to explore local data easily.
* **Transparency:** Allow users to see and understand every query run.
* **Extensibility:** Provide a strong foundation for future data analysis features.
* **Portability:** Fully self-contained, no external dependencies required.

---

## 10. Testing & Validation

All functional components must be covered by automated tests where practical.
Tests verify correctness, stability, and data integrity for all core workflows.

### 10.1 Unit Tests

| Module                 | Tests                                                                                                                                      |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| **Importer**           | - Imports CSV, XLSX, and Parquet correctly.<br> - Handles invalid files gracefully (raises readable errors).                               |
| **DuckDB Integration** | - Tables are registered correctly.<br> - Query execution returns expected row/column counts.<br> - Invalid SQL raises a handled exception. |
| **Exporter**           | - Exports query results to CSV/XLSX/Parquet.<br> - Output schema matches query schema.                                                     |
| **Persistence**        | - Saving and reloading `.duckdb` retains tables and data.<br> - Round-trip validation (data in == data out).                               |

### 10.2 Integration Tests

| Workflow                                   | Expected Result                                    |
| ------------------------------------------ | -------------------------------------------------- |
| Import multiple files and run a join query | Query executes and result matches expected output. |
| Export after query                         | Exported file contains correct data and headers.   |
| Save and reload session                    | UI reloads with all tables and schema intact.      |
| Drop/Rename table                          | Table list and database schema update accordingly. |

### 10.3 UI Tests (optional)

If using PyQt6:

* Use `pytest-qt` to simulate user interactions:

  * File import dialog opens correctly.
  * Running a query updates the result table.
  * Error messages display in the status bar.

### 10.4 Performance Checks

* Import 1M-row CSV within <10 seconds on standard laptop hardware.
* Query execution under 3 seconds for simple filters or joins on moderate datasets.

---

**License:** MIT (tentative)
**Database Engine:** DuckDB
**Primary Framework:** PyQt6
**Author:** Phillip Stevens (initial concept)

---
