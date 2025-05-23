import torch
import torch.nn as nn
from transformers import AutoModel, AutoTokenizer, AutoConfig
import torch.nn.functional as F

class UltraLightImplicitLabelPredictor(nn.Module):
    """
    An ultra-lightweight version of ImplicitLabelPredictor using tiny models and extreme optimizations
    """
    def __init__(self, model_name='prajjwal1/bert-tiny', label_config=None, 
                 max_seq_length=32, hidden_dim=128, quantize=True, embedding_pruning=0.3):
        super().__init__()
        
        # Store configuration
        self.max_seq_length = max_seq_length
        self.model_name = model_name
        self.hidden_dim = hidden_dim
        
        # Load pre-trained language model with extreme optimizations
        config = AutoConfig.from_pretrained(model_name)
        
        # Apply aggressive configuration optimizations
        if hasattr(config, 'num_attention_heads') and config.num_attention_heads > 2:
            config.num_attention_heads = 2  # Extreme reduction in attention heads
        
        if hasattr(config, 'intermediate_size') and config.intermediate_size > 512:
            config.intermediate_size = 512  # Reduce intermediate layer size
            
        if hasattr(config, 'num_hidden_layers') and config.num_hidden_layers > 2:
            config.num_hidden_layers = 2  # Use only 2 transformer layers
        
        # Load tokenizer and encoder with extreme optimizations
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.encoder = AutoModel.from_pretrained(model_name, config=config)
        
        # Get hidden size from the encoder
        encoder_hidden_size = self.encoder.config.hidden_size
        
        # Add a projection layer to further reduce dimensionality
        self.projection = nn.Linear(encoder_hidden_size, hidden_dim)
        
        # Create shared representation layers to reduce parameters
        self.shared_layer = nn.Linear(hidden_dim, hidden_dim)
        
        # Create classification heads for each implicit support label
        self.classifiers = nn.ModuleDict()
        self.num_classes = {}
        
        if label_config:
            for label_name, label_info in label_config.items():
                if label_info.get("implicit_support", False):
                    # Add "none" to the candidates
                    num_classes = len(label_info["candidates"]) + 1
                    self.num_classes[label_name] = num_classes
                    
                    # Create a lightweight classifier for this label
                    # Instead of a full Linear layer, use a more compact representation
                    self.classifiers[label_name] = nn.Linear(hidden_dim, num_classes)
        
        # Apply pruning to embedding layer
        if embedding_pruning > 0:
            self._prune_embeddings(embedding_pruning)
            
        # Apply quantization if requested
        if quantize and not torch.cuda.is_available():  # Only apply on CPU
            self.quantize()
    
    def _prune_embeddings(self, pruning_rate):
        """
        Prune embedding weights to reduce size
        """
        if hasattr(self.encoder, 'embeddings') and hasattr(self.encoder.embeddings, 'word_embeddings'):
            # Get embedding weights
            embedding = self.encoder.embeddings.word_embeddings
            weight = embedding.weight.data
            
            # Create a mask for pruning
            mask = torch.ones_like(weight)
            threshold = torch.quantile(torch.abs(weight), pruning_rate)
            mask[torch.abs(weight) < threshold] = 0
            
            # Apply mask (pruning)
            embedding.weight.data = weight * mask
            
            print(f"Pruned {pruning_rate:.1%} of embedding weights")
    
    def forward(self, input_ids, attention_mask):
        # Get encoder outputs with reduced computation
        with torch.no_grad():  # Freeze encoder for inference
            outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        
        # Different models have different output formats
        if hasattr(outputs, 'last_hidden_state'):
            pooled_output = outputs.last_hidden_state[:, 0, :]  # Use [CLS] token
        else:
            pooled_output = outputs[0][:, 0, :]  # Fallback for older models
        
        # Project to lower dimension
        projected = self.projection(pooled_output)
        
        # Apply shared representation with ReLU activation
        shared_features = F.relu(self.shared_layer(projected))
        
        # Apply each classifier
        results = {}
        for label_name, classifier in self.classifiers.items():
            logits = classifier(shared_features)
            results[label_name] = logits
            
        return results
    
    def quantize(self):
        """
        Apply aggressive quantization to reduce model size
        """
        # Only quantize on CPU - not supported on GPU
        if hasattr(torch, 'quantization'):
            try:
                # Apply dynamic quantization to the model
                self.encoder = torch.quantization.quantize_dynamic(
                    self.encoder, {nn.Linear}, dtype=torch.qint8
                )
                
                # Quantize projection and shared layers
                self.projection = torch.quantization.quantize_dynamic(
                    self.projection, {nn.Linear}, dtype=torch.qint8
                )
                
                self.shared_layer = torch.quantization.quantize_dynamic(
                    self.shared_layer, {nn.Linear}, dtype=torch.qint8
                )
                
                # Quantize classifiers
                for name in self.classifiers:
                    self.classifiers[name] = torch.quantization.quantize_dynamic(
                        self.classifiers[name], {nn.Linear}, dtype=torch.qint8
                    )
                
                print("Applied quantization to all model components")
                return True
                
            except Exception as e:
                print(f"Quantization failed: {e}")
                return False
        return False
    
    def export_to_onnx(self, output_path="ultra_light_model.onnx"):
        """
        Export model to ONNX format for even more efficient inference
        """
        try:
            # Create dummy inputs
            dummy_input_ids = torch.zeros((1, self.max_seq_length), dtype=torch.long)
            dummy_attention_mask = torch.ones((1, self.max_seq_length), dtype=torch.long)
            
            # Export to ONNX
            torch.onnx.export(
                self,
                (dummy_input_ids, dummy_attention_mask),
                output_path,
                input_names=["input_ids", "attention_mask"],
                output_names=["logits_" + name for name in self.classifiers.keys()],
                dynamic_axes={
                    "input_ids": {0: "batch_size"},
                    "attention_mask": {0: "batch_size"}
                },
                opset_version=12
            )
            print(f"Model exported to ONNX at {output_path}")
            return True
        except Exception as e:
            print(f"ONNX export failed: {e}")
            return False
    
    def predict(self, text, device, implicit_labels):
        """
        Make predictions for a single text input
        """
        self.eval()
        self.to(device)
        
        # Tokenize input text with truncation and padding
        encoding = self.tokenizer(
            text,
            truncation=True,
            max_length=self.max_seq_length,  # Use ultra-small sequence length
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
    
    def get_model_size(self):
        """
        Calculate the approximate size of the model in MB
        """
        param_size = 0
        for param in self.parameters():
            if param.requires_grad:
                param_size += param.nelement() * param.element_size()
        
        buffer_size = 0
        for buffer in self.buffers():
            buffer_size += buffer.nelement() * buffer.element_size()
        
        size_mb = (param_size + buffer_size) / 1024**2
        return round(size_mb, 2) 