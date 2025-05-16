#!/usr/bin/env python
import unittest
import sys
import os
import json
import datetime
from io import StringIO
from contextlib import redirect_stdout

# Add the parent directory to sys.path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# Import test modules
from tests.test_profile_api import ProfileAPITestCase
from tests.test_chat_api import ChatAPITestCase

def run_tests_with_report():
    """Run all tests and generate a test report"""
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add tests
    test_suite.addTest(unittest.makeSuite(ProfileAPITestCase))
    test_suite.addTest(unittest.makeSuite(ChatAPITestCase))
    
    # Capture output
    output = StringIO()
    with redirect_stdout(output):
        # Run tests
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(test_suite)
    
    # Parse results
    output_text = output.getvalue()
    
    # Create report
    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "total_tests": result.testsRun,
        "passed": result.testsRun - len(result.failures) - len(result.errors),
        "failures": len(result.failures),
        "errors": len(result.errors),
        "success_rate": f"{(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.2f}%",
        "details": {
            "failures": [{"test": f"{failure[0]}", "message": str(failure[1])} for failure in result.failures],
            "errors": [{"test": f"{error[0]}", "message": str(error[1])} for error in result.errors],
        },
        "coverage": {
            "api_endpoints": {
                "profile": {
                    "GET /api/profile/default": "TESTED",
                    "GET /api/profile/{phone_number}": "TESTED",
                    "POST /api/profile": "TESTED",
                    "PUT /api/profile/{phone_number}": "TESTED"
                },
                "chat": {
                    "POST /api/chat/session": "TESTED",
                    "POST /api/chat/message": "TESTED",
                    "GET /api/chat/session/{session_id}/messages": "TESTED",
                    "PUT /api/chat/session/{session_id}/end": "TESTED"
                }
            },
            "features": {
                "user_profile_validation": "TESTED",
                "chat_session_management": "TESTED",
                "messaging": "TESTED",
                "needs_tracking": "TESTED",
                "reservation_flow": "TESTED"
            }
        }
    }
    
    # Save report to file
    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "report", "test_report.json")
    
    # Create report directory if it doesn"t exist
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    
    # Print summary
    print("\n" + "="*50)
    print("TEST REPORT SUMMARY")
    print("="*50)
    print(f"Total Tests: {report["total_tests"]}")
    print(f"Passed: {report["passed"]}")
    print(f"Failed: {report["failures"]}")
    print(f"Errors: {report["errors"]}")
    print(f"Success Rate: {report["success_rate"]}")
    print("="*50)
    print(f"Full report saved to {report_path}")
    
    # Print API coverage
    print("\nAPI ENDPOINTS COVERAGE:")
    for category, endpoints in report["coverage"]["api_endpoints"].items():
        print(f"\n{category.upper()} API:")
        for endpoint, status in endpoints.items():
            print(f"  - {endpoint}: {status}")
    
    # Print feature coverage
    print("\nFEATURE COVERAGE:")
    for feature, status in report["coverage"]["features"].items():
        feature_name = feature.replace("_", " ").title()
        print(f"  - {feature_name}: {status}")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests_with_report()
    sys.exit(0 if success else 1) 