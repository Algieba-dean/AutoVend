#!/usr/bin/env python
"""
Test launcher script for AutoVend API
Run this from the project root to execute the test suite and generate reports
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
    """Execute tests from the test directory"""
    # Get the path to the test runner
    test_runner_path = os.path.join("tests", "run_tests.py")
    
    if not os.path.exists(test_runner_path):
        print(f"Error: Could not find test runner at {test_runner_path}")
        return 1
    
    # Import and run the test module
    try:
        test_runner = import_module_from_path(test_runner_path)
        success = test_runner.run_tests_with_report()
        return 0 if success else 1
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 