#!/usr/bin/env python
"""
Cleanup script to remove old test files after reorganization
"""

import os
import sys

# Files that should be removed after the reorganization
files_to_remove = [
    'test_data.py',
    'tests_README.md',
    'test_report.json'
]

def main():
    """Remove old test files"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("Cleaning up old test files...")
    for file_name in files_to_remove:
        file_path = os.path.join(current_dir, file_name)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"Removed: {file_name}")
            except Exception as e:
                print(f"Error removing {file_name}: {e}")
        else:
            print(f"File not found: {file_name}")
    
    print("\nCleanup completed.")
    print("All test files are now organized in the 'tests' directory.")
    print("\nTo run the tests, use:")
    print("  python run_tests.py")
    print("\nTo run manual tests, use:")
    print("  python run_manual_test.py")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 