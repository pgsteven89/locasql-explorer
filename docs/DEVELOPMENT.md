# Development Setup

This document provides instructions for setting up the development environment for LocalSQL Explorer.

## Prerequisites

- Python 3.10 or higher
- Git

## Quick Setup

1. Clone the repository:
```bash
git clone https://github.com/username/localsql-explorer.git
cd localsql-explorer
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install in development mode:
```bash
pip install -e .[dev]
```

4. Install pre-commit hooks:
```bash
pre-commit install
```

## Running the Application

### GUI Mode
```bash
# Run directly
python -m localsql_explorer

# Or use the installed command
localsql-explorer
```

### CLI Mode
```bash
# Query a file
localsql-explorer query data.csv "SELECT * FROM data WHERE value > 100"

# Convert between formats
localsql-explorer convert data.csv data.parquet

# Show help
localsql-explorer --help
```

## Development Tasks

### Running Tests
```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/

# With coverage
pytest --cov=localsql_explorer --cov-report=html
```

### Code Quality
```bash
# Format code
black src/ tests/
isort src/ tests/

# Type checking
mypy src/

# Linting
flake8 src/ tests/
```

### Building Documentation
```bash
cd docs/
make html
```

## Project Structure

```
localsql-explorer/
├── src/localsql_explorer/     # Source code
│   ├── __init__.py
│   ├── main.py               # Entry points
│   ├── database.py           # DuckDB management
│   ├── importer.py           # File import
│   ├── exporter.py           # Result export
│   ├── models.py             # Data models
│   └── ui/                   # PyQt6 UI
├── tests/                    # Test suite
│   ├── unit/                 # Unit tests
│   └── integration/          # Integration tests
├── docs/                     # Documentation
├── assets/                   # Icons and resources
└── requirements.txt          # Dependencies
```

## Contributing

1. Create a feature branch
2. Make your changes
3. Add tests for new functionality
4. Run the test suite
5. Submit a pull request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.