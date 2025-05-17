import os
import json
from module_decision_maker import ModuleDecisionMaker

def test_module_decisions():
    """Test the ModuleDecisionMaker with various user messages"""
    
    # Initialize the module decision maker
    decision_maker = ModuleDecisionMaker()
    
    # Different types of user messages to test
    test_cases = [
        {
            "message": "Hello, I'm looking for a new car.",
            "stage": "welcome",
            "description": "Simple welcome message"
        },
        {
            "message": "My name is John Smith and I'm 42 years old. I work as a software engineer.",
            "stage": "profile_analysis",
            "description": "Profile information message"
        },
        {
            "message": "I need an SUV with at least 500 horsepower and good fuel economy.",
            "stage": "needs_analysis",
            "description": "Explicit needs message"
        },
        {
            "message": "I love outdoor camping and need space for my family of 5. We go skiing often.",
            "stage": "needs_analysis",
            "description": "Implicit needs message"
        },
        {
            "message": "I'd like to test drive the BMW X5 this weekend if possible.",
            "stage": "car_selection_confirmation",
            "description": "Test drive request message"
        },
        {
            "message": "The torque vectoring system in the Audi RS6 uses a mechanical LSD or an electronic one?",
            "stage": "car_selection_confirmation",
            "description": "Technical question (showing expertise)"
        }
    ]
    
    # Run test cases
    print("=== MODULE DECISION MAKER TEST ===\n")
    
    for case in test_cases:
        print(f"TEST CASE: {case['description']}")
        print(f"Message: \"{case['message']}\"")
        print(f"Stage: {case['stage']}")
        
        # Get module decisions
        decisions = decision_maker.decide_modules(case['message'], current_stage=case['stage'])
        
        # Print results
        print("\nACTIVATED MODULES:")
        for module, activated in decisions.items():
            status = "✓ ACTIVATED" if activated else "✗ SKIPPED"
            print(f"  {module}: {status}")
        print("\n" + "-"*50 + "\n")

if __name__ == "__main__":
    test_module_decisions() 