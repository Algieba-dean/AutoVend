#!/usr/bin/env python3

import time
import os
import torch

# Import only ultra-light predictor
from ultra_light_predictor import UltraLightPredictor

def get_model_size(model):
    """Calculate model size in MB for any model type"""
    if hasattr(model, 'get_model_size'):
        # Use the model's own method if it exists
        return model.get_model_size()
    else:
        # Calculate manually if method doesn't exist
        param_size = 0
        for param in model.parameters():
            if param.requires_grad:
                param_size += param.nelement() * param.element_size()
        
        buffer_size = 0
        for buffer in model.buffers():
            buffer_size += buffer.nelement() * buffer.element_size()
        
        size_mb = (param_size + buffer_size) / 1024**2
        return round(size_mb, 2)

def measure_inference_time(predictor, query, warmup=3, repeat=5):
    """Measure inference time for a single prediction"""
    # Warmup
    for _ in range(warmup):
        predictor.predict(query)
    
    # Measure time
    start_time = time.time()
    for _ in range(repeat):
        predictor.predict(query)
    end_time = time.time()
    
    return (end_time - start_time) / repeat

def print_predictions(predictions):
    """Print prediction results in a readable format"""
    if predictions:
        for label, value in predictions.items():
            print(f"  {label}: {value}")
    else:
        print("  No non-none predictions found")

def main():
    print("=== Ultra-Lightweight Model Predictor Example ===\n")
    
    # Test query
    query = "I need an economical sedan with good fuel efficiency for city driving"
    
    # Load only ultra-lightweight model
    if not os.path.exists('outputs/best_ultra_light_model.pt'):
        print("Ultra-lightweight model not found. Please train the model first.")
        return
    
    print("Loading ultra-lightweight model...")
    start_time = time.time()
    predictor = UltraLightPredictor(
        model_path='outputs/best_ultra_light_model.pt',
        config_path='QueryLabels.json',
        max_seq_length=32,
        hidden_dim=128
    )
    load_time = time.time() - start_time
    model_size = get_model_size(predictor.model)
    
    # Measure prediction time
    inference_time = measure_inference_time(predictor, query)
    
    # Print basic information
    print(f"\nModel size: {model_size:.2f} MB")
    print(f"Load time: {load_time*1000:.1f} ms")
    print(f"Average inference time: {inference_time*1000:.2f} ms")
    
    # Make a prediction
    print(f"\nTest query: '{query}'")
    print("\nPredictions:")
    predictions = predictor.predict(query)
    print_predictions(predictions)
    
    # Feature details
    print("\n=== Ultra-Lightweight Model Features ===\n")
    features = [
        ("Model architecture", "Tiny BERT (2 layers)"),
        ("Sequence length", "32 tokens"),
        ("Embedding dimension", "128"),
        ("Quantization", "Aggressive INT8 quantization"),
        ("Memory usage", "Very low (<20 MB)"),
        ("Use case", "Resource-constrained environments")
    ]
    
    for feature, value in features:
        print(f"{feature}: {value}")
    
    # Optimizations
    print("\n=== Ultra-Lightweight Model Optimizations ===\n")
    optimizations = [
        ("Reduced layers", "Uses only 2 transformer layers instead of 6 or 12"),
        ("Reduced attention heads", "Uses only 2 attention heads"),
        ("Embedding pruning", "30% of embedding weights are pruned to zero"),
        ("Reduced sequence length", "Uses only 32 tokens for input"),
        ("Dimensional reduction", "Projects features to smaller dimensions"),
        ("Shared representations", "Uses a shared representation layer for all labels"),
        ("INT8 quantization", "Weights quantized to 8-bit integers on CPU"),
        ("ONNX export", "Can be exported to ONNX for further optimization")
    ]
    
    for opt, desc in optimizations:
        print(f"{opt}: {desc}")
    
    # Example exports
    print("\n=== Additional Features ===\n")
    print("1. Export to ONNX")
    print("   To export the model to ONNX format for deployment:")
    print("   predictor.export_to_onnx('ultra_light_model.onnx')")
    
    print("\n2. Batch Processing")
    print("   For processing multiple queries efficiently:")
    print("   results = predictor.predict_batch(['query1', 'query2', 'query3'])")
    
    print("\n3. Available Labels")
    print(f"   This model supports {len(predictor.get_available_labels())} implicit labels")

if __name__ == "__main__":
    main() 