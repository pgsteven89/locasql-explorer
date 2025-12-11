# 🧩 LocalSQL Explorer

A powerful local desktop application for exploring and querying CSV, XLSX, and Parquet files using SQL.

## 📋 Overview

LocalSQL Explorer transforms your data files into a queryable SQL database, allowing you to:

- 📂 **Import Multiple Formats**: CSV, Excel (XLSX), and Parquet files
- 🗃️ **SQL Database**: Each file becomes a table in an embedded DuckDB database  
- 🔍 **Advanced Querying**: Run complex SQL queries including JOINs across multiple tables
- 📊 **Interactive Results**: View, search, filter, and export query results
- 💾 **Persistence**: Save your database for future sessions
- 📤 **Export Options**: Multiple export formats with full/filtered data support

## ✨ Key Features

### � **Performance & Scalability**
- **DuckDB Engine**: Lightning-fast vectorized query processing
- **Memory Efficient**: Paginated results for large datasets (1M+ rows)
- **Smart Import**: Automatic data type detection and optimization
- **Parallel Processing**: Multi-threaded operations for better performance

### 💻 **User Interface** 
- **Modern PyQt6 UI**: Clean, responsive interface with dark/light themes
- **Syntax Highlighting**: SQL editor with intelligent highlighting
- **Interactive Tables**: Sortable columns, cell-level selection, right-click menus
- **Real-time Search**: Column-specific filtering with case sensitivity options
- **Progress Indicators**: Visual feedback for long-running operations

### 🔧 **Data Management**
- **Drag & Drop Import**: Convenient file import with batch processing
- **Table Management**: Rename, drop, refresh tables with schema information
- **Query History**: Track and reuse previous queries
- **Error Handling**: Clear, actionable error messages and validation

### 📈 **Analysis Tools**
- **Query Metrics**: Detailed performance and data statistics
- **Filter Metrics**: Compare original vs filtered dataset characteristics
- **Export Analytics**: Multiple export modes (page, all, filtered)
- **Memory Monitoring**: Real-time memory usage tracking

### 🤖 **MCP Integration (NEW!)**
- **AI Assistant Access**: Connect Claude Desktop and other MCP clients to your data
- **Natural Language Queries**: Let AI help you explore and analyze data
- **Local-First**: No cloud uploads - data stays on your machine
- **Automated Analysis**: Use AI prompts for data quality checks and insights

## 🛠️ Installation

### Prerequisites

- **Python 3.10+** (Python 3.11+ recommended)
- **Operating System**: Windows, macOS, or Linux
- **Memory**: 4GB RAM minimum (8GB+ recommended for large datasets)

### Method 1: Quick Install (Recommended)

```bash
# Clone the repository
git clone https://github.com/pgsteven89/localsql-explorer.git
cd localsql-explorer

# Create virtual environment (recommended)
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install all dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Method 2: Manual Dependencies

If you prefer to install dependencies manually:

```bash
pip install duckdb>=0.9.0
pip install pandas>=2.0.0
pip install PyQt6>=6.5.0
pip install openpyxl>=3.1.0
pip install pyarrow>=13.0.0
pip install sqlparse>=0.4.0
```

### Method 3: Using pip (Future)

```bash
# Once published to PyPI
pip install localsql-explorer
```

## 🚀 Running the Application

### Command Line Methods

```bash
# Method 1: Using the installed command
localsql-explorer

# Method 2: Using Python module
python -m localsql_explorer

# Method 3: Direct execution
python src/localsql_explorer/main.py
```

### IDE/Development Methods

```python
# Run from your IDE or Python script
from localsql_explorer import main
main.main()
```

### Executable (Future)

Pre-built executables will be available for download on the releases page.

## 📖 Usage Guide

### Getting Started

1. **Launch Application**: Use any of the methods above
2. **Import Your Data**: 
   - Click "Import" button or drag & drop files
   - Select CSV, XLSX, or Parquet files
   - Files become tables named after the filename
3. **Explore Schema**: View tables and columns in the left sidebar
4. **Write Queries**: Use the SQL editor with syntax highlighting
5. **Execute**: Press `F5` or click "Run Query"
6. **Analyze Results**: Use search, filtering, and export features

### Example Workflow

```sql
-- After importing sales.csv and customers.xlsx
SELECT 
    c.customer_name,
    s.product,
    s.amount
FROM sales s
JOIN customers c ON s.customer_id = c.id
WHERE s.amount > 1000
ORDER BY s.amount DESC;
```

## 🎯 Key Features in Detail

### Cell-Level Interaction
- **Individual Cell Copy**: Right-click any cell → "Copy Cell Value"
- **Multi-Cell Selection**: Select multiple cells → "Copy X Cells" 
- **Keyboard Shortcuts**: `Ctrl+C` to copy selected cells
- **Row Copy**: Copy entire rows as tab-delimited text
- **Smart Formatting**: Handles nulls, dates, and special characters

### Advanced Search & Filtering
- **Column-Specific Search**: Target specific columns or search all
- **Real-Time Filtering**: Instant results as you type
- **Case Sensitivity**: Toggle for precise matching
- **Dataset-Level Filters**: Filter entire result sets, not just visible pages
- **Filter Metrics**: Compare original vs filtered statistics

### Export Options
- **Export Page**: Current visible page only
- **Export All Results**: Complete query dataset
- **Export Filtered**: Only rows matching current filters
- **Multiple Formats**: CSV, Excel, Parquet support
- **Large Dataset Handling**: Progress indicators and memory management

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `F5` | Execute SQL query |
| `Ctrl+N` | New database |
| `Ctrl+O` | Open database |
| `Ctrl+S` | Save database |
| `Ctrl+I` | Import files |
| `Ctrl+E` | Export results |
| `Ctrl+M` | Show query metrics |
| `Ctrl+C` | Copy selected cells |
| `Ctrl+Z` | Undo in SQL editor |
| `Ctrl+Y` | Redo in SQL editor |

## 🔧 Troubleshooting

### Common Issues

**ImportError: No module named 'duckdb'**
```bash
pip install duckdb>=0.9.0
```

**PyQt6 import errors**
```bash
pip install PyQt6>=6.5.0
```

**Large file import fails**
- Check available memory (close other applications)
- Try importing files individually
- Use CSV files for very large datasets (most efficient)

**Query execution timeout**
- Check query syntax for potential issues
- Verify table names match imported files
- Consider adding WHERE clauses to limit result size

### Performance Tips

- **Memory Management**: Close unused queries, use pagination for large results
- **Query Optimization**: Use WHERE clauses early, avoid SELECT *
- **File Formats**: Parquet files are fastest, CSV second, Excel slowest
- **Indexing**: DuckDB automatically optimizes common query patterns

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes following our coding standards
4. Add tests if applicable
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Development Setup

```bash
# Clone and setup development environment
git clone https://github.com/pgsteven89/localsql-explorer.git
cd localsql-explorer

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest

# Run with development features
python -m localsql_explorer --debug
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🎯 Project Status

**Current Version**: Phase 7 Implementation
- ✅ Core SQL querying and data import
- ✅ Interactive results with pagination  
- ✅ Advanced search and filtering
- ✅ Multiple export options
- ✅ Cell-level copy functionality
- ✅ Query and filter metrics
- 🚧 Documentation updates
- 📋 Enhanced UI/UX improvements

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/pgsteven89/localsql-explorer/issues)
- **Discussions**: [GitHub Discussions](https://github.com/pgsteven89/localsql-explorer/discussions)
- **Email**: support@localsql-explorer.com

---

**Built with ❤️ using DuckDB, PyQt6, and Python**

## 🤖 MCP Integration

LocalSQL Explorer now supports the Model Context Protocol (MCP), enabling AI assistants like Claude to interact with your local data files directly!

### Quick Start

1. **Install with MCP support**:
```bash
pip install -r requirements.txt
pip install -e .
```

2. **Configure Claude Desktop** (`%APPDATA%\Claude\claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "localsql-explorer": {
      "command": "python",
      "args": ["-m", "localsql_explorer.mcp_main", "--db-path", "C:\\path\\to\\database.duckdb"]
    }
  }
}
```

3. **Restart Claude Desktop** and start querying your data with natural language!

### What Can You Do?

- **"What tables are in the database?"** - List all available tables
- **"Show me the schema for the customers table"** - Get column information
- **"Run this query: SELECT * FROM sales WHERE amount > 1000"** - Execute SQL
- **"Import this file: C:\data\new_data.csv"** - Import files as tables
- **"Analyze the sales table"** - Get AI-powered data analysis

### Features

- 📊 **Resources**: Access table lists, schemas, and sample data
- 🛠️ **Tools**: Execute queries, import files, get table info
- 💡 **Prompts**: Pre-built templates for data analysis tasks
- 🔒 **Secure**: Data stays local, no cloud uploads
- ⚡ **Fast**: Direct DuckDB access with configurable row limits

### Learn More

See the complete [MCP Integration Guide](docs/mcp_guide.md) for:
- Detailed configuration options
- Security considerations
- Advanced workflows
- Troubleshooting tips

---

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