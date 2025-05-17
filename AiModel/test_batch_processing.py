import time
import json
from batch_processor import BatchProcessor
from main import AutoVend

def test_batch_processor():
    """Test the batch processor functionality directly"""
    print("=== Batch Processor Direct Test ===\n")
    
    batch_processor = BatchProcessor()
    
    # Test messages
    test_messages = [
        "I'm John, 35 years old, married with 2 kids. I need an SUV for my family.",
        "I'm looking for a car with at least 300 horsepower, AWD, and good fuel economy.",
        "I'd like to schedule a test drive for this Saturday at your downtown location."
    ]
    
    # Test module decisions
    print("Testing module decisions batch processing...")
    stages = ["profile_analysis", "needs_analysis", "car_selection_confirmation"]
    
    for i, (message, stage) in enumerate(zip(test_messages, stages)):
        print(f"\nTest {i+1}: '{message[:30]}...' (Stage: {stage})")
        
        start_time = time.time()
        decisions = batch_processor.process_module_decisions(message, stage)
        end_time = time.time()
        
        print(f"Module decisions made in {(end_time - start_time):.2f} seconds:")
        for module, active in decisions.items():
            status = "✓ ACTIVE" if active else "✗ INACTIVE"
            print(f"  {module}: {status}")
    
    # Test extraction batching
    print("\nTesting extraction batch processing...\n")
    
    for i, message in enumerate(test_messages):
        print(f"Test {i+1}: '{message[:30]}...'")
        
        # Define which modules to activate
        extractions_needed = {
            "profile_extractor": (i == 0),
            "expertise_evaluator": True,
            "explicit_needs_extractor": (i == 1),
            "implicit_needs_inferrer": (i < 2),
            "test_drive_extractor": (i == 2)
        }
        
        active_count = sum(1 for v in extractions_needed.values() if v)
        print(f"Activating {active_count} modules: " + 
              ", ".join(k for k, v in extractions_needed.items() if v))
        
        start_time = time.time()
        results = batch_processor.process_extraction_batch(message, extractions_needed)
        end_time = time.time()
        
        print(f"Extraction completed in {(end_time - start_time):.2f} seconds")
        print(f"Results received: {len(results)} module(s)")
        
        # Print a sample from each result
        for module, data in results.items():
            if isinstance(data, dict):
                sample = next(iter(data.items())) if data else None
                print(f"  {module}: {sample}")
            else:
                print(f"  {module}: {data}")

def test_autovend_batch_mode():
    """Test AutoVend with batch processing enabled/disabled"""
    print("\n=== AutoVend Batch Processing Test ===\n")
    
    # Test message that would trigger multiple modules
    test_message = "Hi, I'm Maria. I'm 32 and work as a doctor. I have two children aged 5 and 7. I'm looking for a family SUV with good safety features, at least 250hp, and would like to test drive this weekend if possible."
    
    # Test with batch processing disabled
    assistant_no_batch = AutoVend(use_streaming=False)
    assistant_no_batch.use_batch_processing = False
    
    print("Test WITHOUT batch processing:")
    start_time = time.time()
    result_no_batch = assistant_no_batch.process_message(test_message)
    end_time = time.time()
    no_batch_time = end_time - start_time
    
    print(f"Processing time: {result_no_batch['processing_time']:.2f} seconds")
    print(f"Total time: {no_batch_time:.2f} seconds")
    print(f"Modules activated: {sum(1 for v in result_no_batch['activated_modules'].values() if v)}")
    
    # Test with batch processing enabled
    assistant_batch = AutoVend(use_streaming=False)
    assistant_batch.use_batch_processing = True
    
    print("\nTest WITH batch processing:")
    start_time = time.time()
    result_batch = assistant_batch.process_message(test_message)
    end_time = time.time()
    batch_time = end_time - start_time
    
    print(f"Processing time: {result_batch['processing_time']:.2f} seconds")
    print(f"Total time: {batch_time:.2f} seconds")
    print(f"Modules activated: {sum(1 for v in result_batch['activated_modules'].values() if v)}")
    
    # Calculate improvement
    improvement = (no_batch_time - batch_time) / no_batch_time * 100
    print(f"\nPerformance improvement: {improvement:.1f}%")
    
    # Print extracted data comparison
    print("\nExtracted data comparison:")
    
    # Compare profile data
    print("Profile data:")
    print(f"  Without batch: {json.dumps(result_no_batch.get('extracted_profile', {}), ensure_ascii=False)[:100]}...")
    print(f"  With batch: {json.dumps(result_batch.get('extracted_profile', {}), ensure_ascii=False)[:100]}...")
    
    # Compare explicit needs
    print("Explicit needs:")
    print(f"  Without batch: {json.dumps(result_no_batch.get('explicit_needs', {}), ensure_ascii=False)[:100]}...")
    print(f"  With batch: {json.dumps(result_batch.get('explicit_needs', {}), ensure_ascii=False)[:100]}...")

if __name__ == "__main__":
    test_batch_processor()
    test_autovend_batch_mode() 