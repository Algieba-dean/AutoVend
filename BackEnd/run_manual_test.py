#!/usr/bin/env python
"""
Manual test launcher script for AutoVend API
Run this from the project root to execute the manual test suite
"""

import os
import sys
import importlib.util
from pathlib import Path

def import_module_from_path(path):
    """Import a module from a file path"""
    module_name = Path(path).stem
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def main():
    """Execute manual tests from the test directory"""
    # Get the path to the manual test script
    manual_test_path = os.path.join("tests", "utils", "manual_test.py")
    
    if not os.path.exists(manual_test_path):
        print(f"Error: Could not find manual test script at {manual_test_path}")
        return 1
    
    # Import and run the test module
    try:
        manual_test = import_module_from_path(manual_test_path)
        manual_test.main()
        return 0
    except Exception as e:
        print(f"Error running manual tests: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 