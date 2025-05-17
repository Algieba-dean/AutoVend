import time
import json
from main import AutoVend

def format_time(seconds):
    """Format time in seconds to a readable string"""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    return f"{seconds:.2f}s"

def performance_test():
    """Test the performance of different optimization configurations"""
    print("=== AutoVend Performance Test ===\n")
    
    # Test messages with varying complexity
    test_messages = [
        "Hi there, I'm looking for a new car.",
        "I'm John, 35 years old. I work in finance and I have 2 kids. I need a family SUV with good safety features.",
        "Can you tell me about cars with at least 300 horsepower, AWD, and under $60,000?",
        "I'd like to schedule a test drive for the BMW X5 this Saturday at noon."
    ]
    
    # Test different configurations
    configurations = [
        {"name": "Baseline (No optimizations)", "streaming": False, "batch": False},
        {"name": "With streaming only", "streaming": True, "batch": False},
        {"name": "With batch processing only", "streaming": False, "batch": True},
        {"name": "Full optimization", "streaming": True, "batch": True}
    ]
    
    results = {}
    
    for config in configurations:
        print(f"\nTesting configuration: {config['name']}")
        print("-" * 40)
        
        # Create assistant with specific configuration
        assistant = AutoVend(use_streaming=config['streaming'])
        assistant.use_batch_processing = config['batch']
        
        # Store timing results for this configuration
        config_results = []
        
        for i, message in enumerate(test_messages):
            print(f"\nTest {i+1}: {message}")
            
            # Reset for clean test
            assistant.reset()
            
            # Process message and measure time
            start_time = time.time()
            result = assistant.process_message(message)
            end_time = time.time()
            
            # Record results
            processing_time = result["processing_time"]
            total_time = end_time - start_time
            activated_modules = sum(1 for v in result["activated_modules"].values() if v)
            
            # Store detailed results
            test_result = {
                "message": message,
                "processing_time": processing_time,
                "total_time": total_time,
                "activated_modules": activated_modules,
                "stage": result["current_stage"]
            }
            config_results.append(test_result)
            
            # Print results for this test
            print(f"  Processing time: {format_time(processing_time)}")
            print(f"  Total time: {format_time(total_time)}")
            print(f"  Modules activated: {activated_modules}")
            print(f"  Stage: {result['current_stage']}")
            
        # Store results for this configuration
        results[config["name"]] = config_results
    
    # Print comparative summary
    print("\n=== Performance Summary ===\n")
    print("{:<25} | {:<15} | {:<15} | {:<15} | {:<15}".format(
        "Configuration", "Simple Msg", "Profile Msg", "Needs Msg", "Test Drive Msg"
    ))
    print("-" * 90)
    
    for config_name, config_results in results.items():
        times = [result["total_time"] for result in config_results]
        print("{:<25} | {:<15} | {:<15} | {:<15} | {:<15}".format(
            config_name,
            format_time(times[0]),
            format_time(times[1]),
            format_time(times[2]),
            format_time(times[3])
        ))
    
    # Print performance improvement percentages
    baseline_times = [r["total_time"] for r in results["Baseline (No optimizations)"]]
    optimized_times = [r["total_time"] for r in results["Full optimization"]]
    improvement_pct = [(baseline - optimized) / baseline * 100 for baseline, optimized in zip(baseline_times, optimized_times)]
    
    print("\n=== Performance Improvement ===\n")
    print("Average improvement: {:.1f}%".format(sum(improvement_pct) / len(improvement_pct)))
    for i, pct in enumerate(improvement_pct):
        print(f"Message {i+1}: {pct:.1f}% faster")

if __name__ == "__main__":
    performance_test() 