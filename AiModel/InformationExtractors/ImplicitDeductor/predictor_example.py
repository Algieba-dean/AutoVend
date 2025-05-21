#!/usr/bin/env python3

from implicit_predictor import ImplicitPredictor

def main():
    # Create predictor instance
    predictor = ImplicitPredictor(
        model_path='outputs/best_model.pt',  # Path to model weights
        config_path='QueryLabels.json'       # Path to label config file
    )
    
    print(f"Using device: {predictor.device}")
    print(f"Available implicit labels: {len(predictor.get_available_labels())}")
    
    # Single query example
    query = "I want an economical car with good fuel efficiency for city commuting"
    print(f"\nQuery: '{query}'")
    
    # Get prediction results (non-none values only)
    filtered_predictions = predictor.predict(query)
    print("\nPrediction results (non-none values only):")
    if filtered_predictions:
        for label, value in filtered_predictions.items():
            print(f"  {label}: {value}")
    else:
        print("  No non-none predictions found")
    
    # Get all prediction results (including none values)
    all_predictions = predictor.predict(query, filter_none=False)
    print("\nAll prediction results (including none values):")
    for label, value in all_predictions.items():
        print(f"  {label}: {value}")
    
    # Batch processing example
    print("\nBatch processing example:")
    queries = [
        "I need a luxury SUV with good off-road capability and high-end features",
        "I want to buy an electric car with long driving range",
        "A spacious family car with good safety features"
    ]
    
    batch_results = predictor.predict_batch(queries)
    for i, result in enumerate(batch_results):
        query = result["query"]
        predictions = result["predictions"]
        print(f"\nQuery {i+1}: '{query}'")
        print("Predictions:")
        if predictions:
            for label, value in predictions.items():
                print(f"  {label}: {value}")
        else:
            print("  No non-none predictions found")

if __name__ == "__main__":
    main() 