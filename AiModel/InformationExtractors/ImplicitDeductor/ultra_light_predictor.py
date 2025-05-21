import torch
import json
import os
from ultra_light_model import UltraLightImplicitLabelPredictor
from utils import load_label_config, filter_implicit_labels

class UltraLightPredictor:
    """
    A wrapper for ultra-lightweight implicit label prediction using extremely optimized model
    """
    
    def __init__(self, model_path='outputs/best_ultra_light_model.pt', config_path='QueryLabels.json', 
                 model_name='prajjwal1/bert-tiny', max_seq_length=32, hidden_dim=128,
                 quantize=True, device=None):
        """
        Initialize the ultra-lightweight predictor
        
        Args:
            model_path: Path to the saved model weights
            config_path: Path to the label config file (QueryLabels.json)
            model_name: Name of the tiny pretrained model to use
            max_seq_length: Maximum sequence length for processing
            hidden_dim: Hidden dimension size
            quantize: Whether to apply quantization to the model
            device: Device to run the model on ('cuda' or 'cpu')
        """
        # Set device
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)
        
        # Load config
        self.label_config = load_label_config(config_path)
        self.implicit_labels = filter_implicit_labels(self.label_config)
        
        # Try to load model configuration if available
        model_config_path = os.path.join(os.path.dirname(model_path), 'ultra_light_model_config.json')
        if os.path.exists(model_config_path):
            try:
                with open(model_config_path, 'r') as f:
                    config = json.load(f)
                    model_name = config.get('model_name', model_name)
                    max_seq_length = config.get('max_seq_length', max_seq_length)
                    hidden_dim = config.get('hidden_dim', hidden_dim)
                    print(f"Loaded model configuration from {model_config_path}")
            except Exception as e:
                print(f"Could not load model config: {e}, using defaults")
        
        # Initialize model with extreme optimizations
        self.model = UltraLightImplicitLabelPredictor(
            model_name=model_name,
            label_config=self.implicit_labels,
            max_seq_length=max_seq_length,
            hidden_dim=hidden_dim,
            quantize=False  # We'll quantize separately if needed
        )
        
        # Load trained weights if available
        if model_path and os.path.exists(model_path):
            try:
                self.load_model(model_path)
                print(f"Loaded model from {model_path}")
            except Exception as e:
                print(f"Could not load model from {model_path}: {e}")
                print("Using untrained model - you will need to train it first")
        
        # Apply quantization if requested (on CPU only)
        if quantize and not torch.cuda.is_available():
            print("Applying quantization...")
            self.model.quantize()
        
        self.model.to(self.device)
        self.model.eval()
        
        # Print model size
        model_size = self.model.get_model_size()
        print(f"Ultra-lightweight model size: {model_size} MB")
        
    def load_model(self, model_path):
        """
        Load model weights with support for partial loading
        """
        # Try to load state dict
        state_dict = torch.load(model_path, map_location=self.device)
        
        # If it's a standard model, try loading directly
        try:
            self.model.load_state_dict(state_dict)
            return True
        except Exception as e:
            # If that fails, try partial loading
            print(f"Standard loading failed: {e}, trying partial loading...")
            
            # Create a new state dict that matches the model's keys
            new_state_dict = {}
            model_state_dict = self.model.state_dict()
            
            # Filter and reshape weights if needed
            for key in model_state_dict:
                if key in state_dict and model_state_dict[key].shape == state_dict[key].shape:
                    new_state_dict[key] = state_dict[key]
                else:
                    if key in state_dict:
                        print(f"Shape mismatch for {key}: model={model_state_dict[key].shape}, checkpoint={state_dict[key].shape}")
                    else:
                        print(f"Key {key} not found in checkpoint")
                    # Keep the original initialized weights
                    new_state_dict[key] = model_state_dict[key]
            
            # Load the matched weights
            self.model.load_state_dict(new_state_dict)
            
            # Check how many parameters were successfully loaded
            total_params = len(model_state_dict)
            loaded_params = sum(1 for k in model_state_dict if k in state_dict and model_state_dict[k].shape == state_dict[k].shape)
            print(f"Loaded {loaded_params}/{total_params} parameters from checkpoint")
            
            return loaded_params > 0
    
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
    
    def predict_batch(self, queries, filter_none=True, batch_size=16):
        """
        Make predictions for multiple queries with efficient batching
        
        Args:
            queries: List of text queries
            filter_none: If True, only returns non-none predictions
            batch_size: Size of batches for processing
            
        Returns:
            List of dictionaries with predictions for each query
        """
        results = []
        
        # Process queries in batches for efficiency
        for i in range(0, len(queries), batch_size):
            batch_queries = queries[i:i+batch_size]
            batch_results = []
            
            # Process each query in the batch
            for query in batch_queries:
                predictions = self.predict(query, filter_none)
                batch_results.append({
                    "query": query,
                    "predictions": predictions
                })
            
            results.extend(batch_results)
        
        return results
    
    def save_predictions(self, input_file, output_file, filter_none=True):
        """
        Process queries from a file and save results to another file
        
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
        
        print(f"Predictions saved to {output_file}")
    
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
    
    def export_to_onnx(self, output_path="ultra_light_model.onnx"):
        """
        Export model to ONNX format for even more efficient inference
        
        Args:
            output_path: Path to save the ONNX model
            
        Returns:
            True if export was successful, False otherwise
        """
        return self.model.export_to_onnx(output_path) 