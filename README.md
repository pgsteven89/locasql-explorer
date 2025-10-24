# LocalSQL Explorer

A local desktop application for exploring and querying CSV, XLSX, and Parquet files using SQL.

## Overview

LocalSQL Explorer allows you to:
- Import datasets from CSV, Excel (XLSX), or Parquet files
- Treat each file as a table within an embedded DuckDB database
- Run SQL queries (including joins across multiple tables)
- View results in an interactive table view
- Export query results to various formats
- Save or load a persistent DuckDB database for future use

## Features

- 📂 **File Import**: Support for CSV, XLSX, and Parquet files
- 🗃️ **Table Management**: Each imported file becomes a DuckDB table
- 📝 **SQL Editor**: Syntax-highlighted SQL editor with F5 execution
- 📊 **Results Viewer**: Interactive table view with sorting and export
- 💾 **Persistence**: Save and load databases (.duckdb files)
- 🎨 **Modern UI**: PyQt6-based interface with dark/light themes
- ⚡ **Performance**: DuckDB's vectorized engine for fast queries

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/username/localsql-explorer.git
cd localsql-explorer

# Install dependencies
pip install -e .

# Run the application
localsql-explorer
```

### Basic Usage

1. **Import Data**: Click "Import" to load CSV, Excel, or Parquet files
2. **Write SQL**: Use the SQL editor to write queries against your tables
3. **Execute**: Press F5 or click "Run Query" to execute
4. **View Results**: Results appear in the bottom panel
5. **Export**: Right-click results to export to various formats

### Example

```sql
-- Import sales.csv and customers.xlsx first
SELECT 
    c.customer_name,
    SUM(s.amount) as total_sales
FROM sales s
JOIN customers c ON s.customer_id = c.id
GROUP BY c.customer_name
ORDER BY total_sales DESC
LIMIT 10;
```

## Project Structure

```
localsql-explorer/
├── src/localsql_explorer/
│   ├── __init__.py
│   ├── database.py          # DuckDB management
│   ├── importer.py          # File import logic
│   ├── exporter.py          # Result export logic
│   ├── models.py            # Data models and config
│   ├── main.py             # Application entry point
│   └── ui/                 # PyQt6 UI components
│       ├── main_window.py  # Main application window
│       ├── sql_editor.py   # SQL editor with highlighting
│       ├── table_list.py   # Table management panel
│       └── results_view.py # Query results display
├── tests/                  # Test suite
├── docs/                   # Documentation
├── assets/                 # Icons and resources
├── SPEC.md                # Project specification
├── pyproject.toml         # Project configuration
└── requirements.txt       # Dependencies
```

## Development

### Setup Development Environment

```bash
# Install development dependencies
pip install -e .[dev]

# Install pre-commit hooks
pre-commit install

# Run tests
pytest

# Run with coverage
pytest --cov=localsql_explorer

# Format code
black src/ tests/
isort src/ tests/

# Type checking
mypy src/
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m "not slow"           # Skip slow tests
pytest tests/unit/             # Unit tests only
pytest tests/integration/      # Integration tests only

# Run with coverage
pytest --cov=localsql_explorer --cov-report=html
```

## Dependencies

### Core
- **DuckDB**: Embedded SQL database engine
- **Pandas**: Data manipulation and analysis
- **PyArrow**: Parquet file support
- **PyQt6**: Cross-platform GUI framework
- **Pydantic**: Data validation and settings

### File Format Support
- **openpyxl**: Excel (.xlsx) file support
- **pyarrow**: Parquet file support
- Built-in CSV support via pandas

## Technical Specifications

- **Python**: 3.10+
- **Database**: DuckDB (embedded)
- **UI Framework**: PyQt6
- **Supported Files**: CSV, XLSX, Parquet
- **Performance**: Handles datasets up to ~1GB smoothly
- **Platforms**: Windows, macOS, Linux

## Roadmap

### Phase 1 (Current)
- [x] Core functionality (import, query, results)
- [x] Basic UI with PyQt6
- [x] File import for CSV/XLSX/Parquet
- [x] SQL editor with syntax highlighting
- [ ] Query execution and results display

### Phase 2
- [ ] Export functionality
- [ ] Database persistence (save/load)
- [ ] Table management (rename, drop)
- [ ] Error handling and validation
- [ ] Status updates and progress indicators

### Phase 3
- [ ] Query history and favorites
- [ ] Dark/light theme toggle
- [ ] Column metadata and profiling
- [ ] Performance optimizations
- [ ] Plugin architecture

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Run the test suite (`pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Code Style

This project uses:
- **Black** for code formatting
- **isort** for import sorting
- **mypy** for type checking
- **flake8** for linting

Run `pre-commit install` to automatically format code on commit.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **DuckDB** team for the amazing embedded database
- **PyQt** for the robust GUI framework
- **Pandas** team for data manipulation tools
- The open-source community for inspiration and tools

## Support

- 📖 [Documentation](https://localsql-explorer.readthedocs.io/)
- 🐛 [Bug Reports](https://github.com/username/localsql-explorer/issues)
- 💡 [Feature Requests](https://github.com/username/localsql-explorer/discussions)
- 💬 [Community Discussions](https://github.com/username/localsql-explorer/discussions)