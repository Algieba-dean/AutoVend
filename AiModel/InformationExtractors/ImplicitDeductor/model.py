import torch
import torch.nn as nn
from transformers import AutoModel, AutoTokenizer

class ImplicitLabelPredictor(nn.Module):
    def __init__(self, model_name, label_config):
        super().__init__()
        
        # Load pre-trained language model
        self.encoder = AutoModel.from_pretrained(model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        # Get hidden size from the encoder
        hidden_size = self.encoder.config.hidden_size
        
        # Create classification heads for each implicit support label
        self.classifiers = nn.ModuleDict()
        
        # Store the number of classes for each label
        self.num_classes = {}
        
        for label_name, label_info in label_config.items():
            if label_info.get("implicit_support", False):
                # Add "none" to the candidates
                num_classes = len(label_info["candidates"]) + 1
                self.num_classes[label_name] = num_classes
                
                # Create a classifier for this label
                self.classifiers[label_name] = nn.Linear(hidden_size, num_classes)
    
    def forward(self, input_ids, attention_mask):
        # Get encoder outputs
        outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        pooled_output = outputs.last_hidden_state[:, 0, :]  # Use [CLS] token
        
        # Apply each classifier
        results = {}
        for label_name, classifier in self.classifiers.items():
            logits = classifier(pooled_output)
            results[label_name] = logits
            
        return results

    def predict(self, text, device, implicit_labels):
        """
        Make predictions for a single text input
        """
        self.eval()
        self.to(device)
        
        # Tokenize input text
        encoding = self.tokenizer(
            text,
            truncation=True,
            max_length=128,
            padding="max_length",
            return_tensors="pt"
        )
        
        input_ids = encoding["input_ids"].to(device)
        attention_mask = encoding["attention_mask"].to(device)
        
        # Make prediction
        with torch.no_grad():
            outputs = self(input_ids, attention_mask)
        
        # Process results
        predictions = {}
        for label_name, logits in outputs.items():
            probabilities = torch.softmax(logits, dim=1)[0]
            predicted_idx = torch.argmax(probabilities, dim=0).item()
            
            # Map back to label value
            candidates = implicit_labels[label_name]["candidates"]
            if predicted_idx < len(candidates):
                predictions[label_name] = candidates[predicted_idx]
            else:
                predictions[label_name] = "none"
        
        return predictions 