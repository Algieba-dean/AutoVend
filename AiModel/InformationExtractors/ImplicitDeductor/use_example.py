#!/usr/bin/env python3

import argparse
import json
import torch
from model import ImplicitLabelPredictor
from utils import load_label_config, filter_implicit_labels

def parse_args():
    parser = argparse.ArgumentParser(description='Use trained implicit label prediction model')
    parser.add_argument('--config', type=str, default='QueryLabels.json', help='Path to the label config file')
    parser.add_argument('--model_path', type=str, default='outputs/best_model.pt', help='Path to the saved model')
    parser.add_argument('--model_name', type=str, default='bert-base-uncased', help='Pretrained model name used during training')
    parser.add_argument('--query', type=str, help='Query text for prediction')
    parser.add_argument('--input_file', type=str, help='Input file with queries (one per line)')
    parser.add_argument('--output_file', type=str, help='Output file to save predictions')
    return parser.parse_args()

def predict_single_query(model, query, device, implicit_labels):
    """
    Make prediction for a single query and filter out 'none' values
    
    Args:
        model: Trained model
        query: Text query
        device: Device to run prediction on
        implicit_labels: Dictionary of implicit labels with configurations
        
    Returns:
        Dictionary with non-none predictions
    """
    # Get all predictions
    all_predictions = model.predict(query, device, implicit_labels)
    
    # Filter out 'none' values
    filtered_predictions = {
        label: value for label, value in all_predictions.items()
        if value != "none"
    }
    
    return filtered_predictions

def predict_from_file(model, input_file, output_file, device, implicit_labels):
    """
    Make predictions for queries in a file and save results
    
    Args:
        model: Trained model
        input_file: File with queries (one per line)
        output_file: File to save predictions
        device: Device to run prediction on
        implicit_labels: Dictionary of implicit labels with configurations
    """
    results = []
    
    with open(input_file, 'r') as f:
        queries = [line.strip() for line in f if line.strip()]
    
    for query in queries:
        filtered_predictions = predict_single_query(model, query, device, implicit_labels)
        results.append({
            "query": query,
            "predictions": filtered_predictions
        })
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Predictions saved to {output_file}")

def main():
    # Parse arguments
    args = parse_args()
    
    # Set device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    # Load label config and filter for implicit labels
    label_config = load_label_config(args.config)
    implicit_labels = filter_implicit_labels(label_config)
    
    # Initialize model
    model = ImplicitLabelPredictor(args.model_name, implicit_labels)
    
    # Load trained weights
    model.load_state_dict(torch.load(args.model_path, map_location=device))
    model.to(device)
    model.eval()
    
    print(f"Model loaded from {args.model_path}")
    
    # Make predictions
    if args.query:
        # Single query prediction
        filtered_predictions = predict_single_query(model, args.query, device, implicit_labels)
        
        print(f"\nNon-none predictions for: '{args.query}'")
        if filtered_predictions:
            for label, value in filtered_predictions.items():
                print(f"  {label}: {value}")
        else:
            print("  No non-none predictions found")
            
    elif args.input_file and args.output_file:
        # Batch prediction from file
        predict_from_file(model, args.input_file, args.output_file, device, implicit_labels)
    else:
        # Interactive mode
        print("\nEntering interactive mode. Type 'quit' to exit.")
        while True:
            query = input("\nEnter a query: ")
            if query.lower() == 'quit':
                break
                
            filtered_predictions = predict_single_query(model, query, device, implicit_labels)
            
            print(f"Non-none predictions:")
            if filtered_predictions:
                for label, value in filtered_predictions.items():
                    print(f"  {label}: {value}")
            else:
                print("  No non-none predictions found")

if __name__ == "__main__":
    main() 