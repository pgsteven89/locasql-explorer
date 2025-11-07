"""
CSV File Diagnostic Tool

This script analyzes a CSV/pipe-delimited file to identify issues with:
- Field count inconsistencies
- Delimiter detection
- Problematic rows
- Encoding issues
"""

import csv
import sys
from pathlib import Path
from collections import Counter

def analyze_csv_file(file_path: str):
    """Analyze a CSV file for structural issues."""
    
    file_path = Path(file_path)
    
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return
    
    print(f"\n{'='*70}")
    print(f"CSV File Analysis: {file_path.name}")
    print(f"{'='*70}\n")
    
    # Detect delimiter
    print("🔍 Detecting delimiter...")
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            sample = f.read(8192)
        
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sample, delimiters=',\t|;')
        detected_delimiter = dialect.delimiter
        
        delimiter_names = {
            ',': 'comma (,)',
            '\t': 'tab (\\t)',
            '|': 'pipe (|)',
            ';': 'semicolon (;)'
        }
        
        print(f"✓ Detected delimiter: {delimiter_names.get(detected_delimiter, repr(detected_delimiter))}\n")
        
    except Exception as e:
        print(f"❌ Could not detect delimiter: {e}\n")
        detected_delimiter = input("Please enter delimiter character (or press Enter for '|'): ") or '|'
    
    # Analyze structure
    print("📊 Analyzing file structure...")
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        if not lines:
            print("❌ File is empty")
            return
        
        # Analyze header
        header = lines[0].strip()
        header_fields = header.split(detected_delimiter)
        expected_field_count = len(header_fields)
        
        print(f"✓ Header found with {expected_field_count} fields:")
        for i, field in enumerate(header_fields, 1):
            print(f"   {i:2d}. {field[:50]}")  # Show first 50 chars
        print()
        
        # Analyze data rows
        field_counts = []
        problematic_lines = []
        
        for i, line in enumerate(lines[1:], start=2):
            line = line.strip()
            if not line:
                continue
            
            fields = line.split(detected_delimiter)
            field_count = len(fields)
            field_counts.append(field_count)
            
            if field_count != expected_field_count:
                problematic_lines.append({
                    'line_num': i,
                    'field_count': field_count,
                    'content': line[:100]  # First 100 chars
                })
        
        # Statistics
        print(f"📈 File Statistics:")
        print(f"   Total lines: {len(lines)}")
        print(f"   Data rows: {len(field_counts)}")
        print(f"   Expected fields per row: {expected_field_count}")
        
        if field_counts:
            counter = Counter(field_counts)
            print(f"\n   Field count distribution:")
            for count, frequency in sorted(counter.items()):
                percentage = (frequency / len(field_counts)) * 100
                status = "✓" if count == expected_field_count else "⚠"
                print(f"   {status} {count:3d} fields: {frequency:5d} rows ({percentage:5.1f}%)")
        
        # Report problematic lines
        if problematic_lines:
            print(f"\n⚠ Found {len(problematic_lines)} rows with incorrect field counts:\n")
            
            # Show first 10 problematic lines
            for issue in problematic_lines[:10]:
                print(f"   Line {issue['line_num']}: {issue['field_count']} fields (expected {expected_field_count})")
                print(f"      Content: {issue['content']}")
                
                # Show which fields might be the issue
                fields = issue['content'].split(detected_delimiter)
                if len(fields) > expected_field_count:
                    extra = len(fields) - expected_field_count
                    print(f"      ⚠ {extra} extra field(s) detected")
                else:
                    missing = expected_field_count - len(fields)
                    print(f"      ⚠ {missing} field(s) missing")
                print()
            
            if len(problematic_lines) > 10:
                print(f"   ... and {len(problematic_lines) - 10} more problematic lines")
            
            # Suggest solutions
            print(f"\n💡 Possible Solutions:")
            print(f"   1. Check if data contains unescaped delimiter characters ('{detected_delimiter}')")
            print(f"   2. Look for missing or extra delimiters in the problematic lines")
            print(f"   3. Ensure text fields with delimiters are properly quoted")
            print(f"   4. Check for newlines within quoted fields")
            print(f"   5. Verify the file encoding (currently using UTF-8)")
            
        else:
            print(f"\n✓ All rows have consistent field counts!")
        
    except Exception as e:
        print(f"❌ Error analyzing file: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'='*70}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\nUsage: python analyze_csv.py <file_path>")
        print("\nExample: python analyze_csv.py data.csv")
        
        # Try to get input
        file_path = input("\nOr enter file path now: ").strip().strip('"')
        if file_path:
            analyze_csv_file(file_path)
    else:
        file_path = sys.argv[1]
        analyze_csv_file(file_path)
