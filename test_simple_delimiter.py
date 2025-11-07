"""
Simple test for CSV delimiter detection.
"""

import csv
import tempfile
from pathlib import Path

def detect_csv_delimiter(file_path, sample_size=8192):
    """
    Detect the delimiter used in a CSV file.
    
    Args:
        file_path: Path to CSV file
        sample_size: Number of bytes to read for detection
        
    Returns:
        str: Detected delimiter
    """
    try:
        # Read a sample of the file
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            sample = f.read(sample_size)
        
        # Use csv.Sniffer to detect the delimiter
        sniffer = csv.Sniffer()
        
        # Try to detect delimiter
        try:
            dialect = sniffer.sniff(sample, delimiters=',\t|;')
            detected_delimiter = dialect.delimiter
            return detected_delimiter
        except csv.Error:
            # If Sniffer fails, fall back to manual detection
            lines = sample.split('\n')[:10]  # Check first 10 lines
            if not lines:
                return ','
            
            delimiter_counts = {
                ',': sum(line.count(',') for line in lines),
                '\t': sum(line.count('\t') for line in lines),
                '|': sum(line.count('|') for line in lines),
                ';': sum(line.count(';') for line in lines)
            }
            
            # Return delimiter with highest count
            detected = max(delimiter_counts, key=delimiter_counts.get)
            if delimiter_counts[detected] > 0:
                return detected
            else:
                return ','
                
    except Exception as e:
        print(f"Error: {e}")
        return ','

def test_delimiter_detection():
    """Test delimiter detection with various delimiters."""
    
    # Test data for different delimiters
    test_cases = [
        ("comma", "name,age,city\nJohn,30,NYC\nJane,25,LA\nBob,35,Chicago\n", ","),
        ("tab", "name\tage\tcity\nJohn\t30\tNYC\nJane\t25\tLA\nBob\t35\tChicago\n", "\t"),
        ("pipe", "name|age|city\nJohn|30|NYC\nJane|25|LA\nBob|35|Chicago\n", "|"),
        ("semicolon", "name;age;city\nJohn;30;NYC\nJane;25;LA\nBob;35;Chicago\n", ";"),
    ]
    
    print("\nTesting CSV Delimiter Detection")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for test_name, content, expected_delimiter in test_cases:
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            f.write(content)
            temp_path = Path(f.name)
        
        try:
            # Detect delimiter
            detected = detect_csv_delimiter(temp_path)
            
            # Check result
            if detected == expected_delimiter:
                status = "✓ PASS"
                passed += 1
            else:
                status = "✗ FAIL"
                failed += 1
            
            delimiter_repr = {
                ',': 'comma (,)',
                '\t': 'tab (\\t)',
                '|': 'pipe (|)',
                ';': 'semicolon (;)'
            }
            
            expected_str = delimiter_repr.get(expected_delimiter, repr(expected_delimiter))
            detected_str = delimiter_repr.get(detected, repr(detected))
            
            print(f"{status} - {test_name:12s}: Expected {expected_str}, Got {detected_str}")
            
        finally:
            # Cleanup
            temp_path.unlink()
    
    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print()

if __name__ == "__main__":
    test_delimiter_detection()
