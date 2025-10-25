# Development Tests

This directory contains test scripts created during the development process for validating specific features and implementations.

## Test Scripts

| File | Purpose | Phase |
|------|---------|-------|
| `test_dataset_filtering.py` | Tests dataset-level filtering functionality | Phase 6 |
| `test_enhanced_metrics.py` | Tests query metrics and performance tracking | Phase 6 |
| `test_export_layout_fix.py` | Tests export button layout improvements | Phase 7 |
| `test_export_pagination.py` | Tests paginated export functionality | Phase 6 |
| `test_layout_fix.py` | Tests UI layout improvements | Phase 6 |
| `test_phase7_implementation.py` | Tests cell-level copy functionality | Phase 7 |
| `test_search_functionality.py` | Tests search and filtering features | Phase 6 |

## Usage

These tests were created for development validation and may require:
- Proper Python environment with dependencies
- Sample data files (available in `../../sample_data/`)
- Running LocalSQL Explorer application

## Note

For formal testing, use the main test suite in `../unit/` and `../integration/`.
These development tests are kept for reference and debugging purposes.