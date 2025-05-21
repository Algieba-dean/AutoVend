import torch
import json
import os
from model import ImplicitLabelPredictor
from utils import load_label_config, filter_implicit_labels

class ImplicitPredictor:
    """
    A wrapper class for the implicit label prediction model
    that makes it easy to use in other applications
    """
    
    def __init__(self, model_path='outputs/best_model.pt', config_path='QueryLabels.json', 
                 model_name='bert-base-uncased', device=None):
        """
        Initialize the predictor with a trained model
        
        Args:
            model_path: Path to the saved model weights
            config_path: Path to the label config file (QueryLabels.json)
            model_name: Name of the pretrained model used during training
            device: Device to run the model on ('cuda' or 'cpu'). If None, will use CUDA if available.
        """
        # Set device
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)
            
        # Load model config if available
        model_config_path = os.path.join(os.path.dirname(model_path), 'model_config.json')
        if os.path.exists(model_config_path):
            with open(model_config_path, 'r') as f:
                model_config = json.load(f)
                model_name = model_config.get('model_name', model_name)
                config_path = model_config.get('config_file', config_path)
        
        # Load label config
        self.label_config = load_label_config(config_path)
        self.implicit_labels = filter_implicit_labels(self.label_config)
        
        # Initialize model
        self.model = ImplicitLabelPredictor(model_name, self.implicit_labels)
        
        # Load trained weights
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.to(self.device)
        self.model.eval()
        
    def predict(self, query, filter_none=True):
        """
        Make prediction for a query
        
        Args:
            query: Text query to predict labels for
            filter_none: If True, only returns non-none predictions
            
        Returns:
            Dictionary with predicted labels
        """
        # Get all predictions
        all_predictions = self.model.predict(query, self.device, self.implicit_labels)
        
        # Filter out 'none' values if requested
        if filter_none:
            return {
                label: value for label, value in all_predictions.items()
                if value != "none"
            }
        else:
            return all_predictions
    
    def predict_batch(self, queries, filter_none=True):
        """
        Make predictions for a batch of queries
        
        Args:
            queries: List of text queries
            filter_none: If True, only returns non-none predictions
            
        Returns:
            List of dictionaries with predicted labels for each query
        """
        results = []
        
        for query in queries:
            predictions = self.predict(query, filter_none)
            results.append({
                "query": query,
                "predictions": predictions
            })
            
        return results
    
    def save_predictions(self, input_file, output_file, filter_none=True):
        """
        Process queries from a file and save predictions to another file
        
        Args:
            input_file: Path to input file with queries (one per line)
            output_file: Path to output file to save predictions
            filter_none: If True, only saves non-none predictions
        """
        with open(input_file, 'r') as f:
            queries = [line.strip() for line in f if line.strip()]
        
        results = self.predict_batch(queries, filter_none)
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
    
    def get_available_labels(self):
        """
        Get the list of all available implicit labels
        
        Returns:
            List of label names
        """
        return list(self.implicit_labels.keys())
    
    def get_label_candidates(self, label_name):
        """
        Get the candidate values for a specific label
        
        Args:
            label_name: Name of the label
            
        Returns:
            List of candidate values for the label
        """
        if label_name in self.implicit_labels:
            return self.implicit_labels[label_name]['candidates']
        return [] 