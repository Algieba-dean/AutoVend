import time
import json
from main import AutoVend

def format_time(seconds):
    """Format time in a readable way"""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    return f"{seconds:.2f}s"

def simulate_conversation(use_streaming=False, use_batch=True):
    """
    Simulate a conversation flow and measure performance.
    
    Args:
        use_streaming (bool): Whether to use streaming responses
        use_batch (bool): Whether to use batch processing
    """
    # Create assistant with specified configuration
    assistant = AutoVend(use_streaming=use_streaming)
    assistant.use_batch_processing = use_batch
    
    # Define a conversation flow
    conversation = [
        "Hi there, I'm looking for a new car.",
        "My name is David Chen, I'm 36 years old and work in finance. I'm married with two kids.",
        "I'm looking for an SUV or crossover with good fuel economy for daily commute, but also spacious enough for family trips.",
        "Safety is very important to me. I'd like advanced safety features like lane keeping and automatic braking.",
        "My budget is around $45,000 to $60,000. I prefer luxury brands if possible.",
        "I'd be interested in something with good performance too, maybe around 300 horsepower.",
        "Can I test drive the BMW X5 and Mercedes GLE this weekend?",
        "Saturday at 2pm would be perfect. My phone number is 555-123-4567."
    ]
    
    # Print test configuration
    config_desc = []
    if use_streaming:
        config_desc.append("streaming ON")
    else:
        config_desc.append("streaming OFF")
        
    if use_batch:
        config_desc.append("batch processing ON")
    else:
        config_desc.append("batch processing OFF")
        
    print(f"\n=== Testing conversation flow with {' & '.join(config_desc)} ===\n")
    
    results = []
    for i, message in enumerate(conversation):
        print(f"\n[Turn {i+1}] User: {message}")
        
        # Process message and time it
        start_time = time.time()
        result = assistant.process_message(message)
        end_time = time.time()
        elapsed = end_time - start_time
        
        # If using non-streaming mode, print the response now
        if not use_streaming:
            # In non-streaming mode, print the full response at once
            print(f"AutoVend: {result['response']}")
        
        # Save metrics
        results.append({
            "turn": i+1,
            "message": message,
            "response_time": elapsed,
            "processing_time": result["processing_time"],
            "stage": result["current_stage"],
            "activated_modules": sum(1 for v in result["activated_modules"].values() if v)
        })
        
        print(f"Stage: {result['current_stage']} | Time: {format_time(elapsed)} | "
              f"Modules: {results[-1]['activated_modules']}")
    
    # Print final summary
    print("\n=== Conversation Summary ===")
    print(f"Total turns: {len(results)}")
    avg_time = sum(r["response_time"] for r in results) / len(results)
    print(f"Average response time: {format_time(avg_time)}")
    
    # Print stage transitions
    stages = [r["stage"] for r in results]
    print("Stage progression:", " → ".join(stages))
    
    return results

def run_comparative_tests():
    """Run tests with different configurations and compare results"""
    print("=== AutoVend Conversation Flow Tests ===\n")
    
    # Test all configurations
    configs = [
        {"name": "Baseline", "streaming": False, "batch": False},
        {"name": "Streaming only", "streaming": True, "batch": False},
        {"name": "Batch only", "streaming": False, "batch": True},
        {"name": "Full optimization", "streaming": True, "batch": True}
    ]
    
    all_results = {}
    
    for config in configs:
        print(f"\nTesting configuration: {config['name']}")
        print("-" * 40)
        
        results = simulate_conversation(
            use_streaming=config["streaming"], 
            use_batch=config["batch"]
        )
        
        all_results[config["name"]] = results
    
    # Print comparative summary
    print("\n=== Performance Comparison ===\n")
    print("{:<20} | {:<15} | {:<15} | {:<15}".format(
        "Configuration", "Avg Time", "First Turn", "Last Turn"
    ))
    print("-" * 70)
    
    for config_name, results in all_results.items():
        avg_time = sum(r["response_time"] for r in results) / len(results)
        first_turn = results[0]["response_time"]
        last_turn = results[-1]["response_time"]
        
        print("{:<20} | {:<15} | {:<15} | {:<15}".format(
            config_name,
            format_time(avg_time),
            format_time(first_turn),
            format_time(last_turn)
        ))
    
    # Calculate improvement from baseline to full optimization
    baseline = all_results["Baseline"]
    optimized = all_results["Full optimization"]
    
    baseline_avg = sum(r["response_time"] for r in baseline) / len(baseline)
    optimized_avg = sum(r["response_time"] for r in optimized) / len(optimized)
    improvement = (baseline_avg - optimized_avg) / baseline_avg * 100
    
    print(f"\nOverall improvement: {improvement:.1f}%")
    
    # Print subjective assessment
    print("\nSubjective assessment:")
    print("- Streaming mode gives immediate feedback but may feel choppy")
    print("- Batch processing reduces total processing time but has longer initial delay")
    print("- Full optimization provides best balance of immediate feedback and overall speed")
    print("- For phone-call-like experience, streaming mode is essential")

if __name__ == "__main__":
    run_comparative_tests() 