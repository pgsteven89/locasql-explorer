"""
Test script for CSV delimiter detection functionality.
"""

import sys
import tempfile
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from localsql_explorer.importer import FileImporter

def test_delimiter_detection():
    """Test delimiter detection with various delimiters."""
    
    importer = FileImporter()
    
    # Test data for different delimiters
    test_cases = [
        ("comma", "name,age,city\nJohn,30,NYC\nJane,25,LA\n", ","),
        ("tab", "name\tage\tcity\nJohn\t30\tNYC\nJane\t25\tLA\n", "\t"),
        ("pipe", "name|age|city\nJohn|30|NYC\nJane|25|LA\n", "|"),
        ("semicolon", "name;age;city\nJohn;30;NYC\nJane;25;LA\n", ";"),
    ]
    
    print("Testing CSV Delimiter Detection")
    print("=" * 60)
    
    for test_name, content, expected_delimiter in test_cases:
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)
        
        try:
            # Detect delimiter
            detected = importer.detect_csv_delimiter(temp_path)
            
            # Check result
            status = "✓ PASS" if detected == expected_delimiter else "✗ FAIL"
            print(f"{status} - {test_name:12s}: Expected {repr(expected_delimiter)}, Got {repr(detected)}")
            
            # Test full import
            result = importer.import_csv(temp_path)
            if result.success:
                print(f"       Import successful: {result.dataframe.shape[0]} rows, {result.dataframe.shape[1]} columns")
                if result.warnings:
                    print(f"       Warnings: {', '.join(result.warnings)}")
            else:
                print(f"       Import failed: {result.error}")
            print()
            
        finally:
            # Cleanup
            temp_path.unlink()
    
    print("=" * 60)
    print("Testing complete!")

if __name__ == "__main__":
    test_delimiter_detection()
