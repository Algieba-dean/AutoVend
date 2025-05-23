#!/usr/bin/env python3

import os
import json
import argparse
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
from transformers import AutoTokenizer
from tqdm import tqdm
from sklearn.model_selection import train_test_split

# Import local modules
from ultra_light_model import UltraLightImplicitLabelPredictor
from dataset import VehicleQueryDataset, collate_batch
from utils import load_label_config, filter_implicit_labels, evaluate_model, save_predictions

def parse_args():
    parser = argparse.ArgumentParser(description='Train ultra-lightweight implicit label prediction model')
    parser.add_argument('--config', type=str, default='QueryLabels.json', help='Path to the label config file')
    parser.add_argument('--dataset', type=str, default='example_dataset.json', help='Path to the dataset file')
    parser.add_argument('--model_name', type=str, default='prajjwal1/bert-tiny', help='Pretrained tiny model name')
    parser.add_argument('--batch_size', type=int, default=32, help='Training batch size')
    parser.add_argument('--epochs', type=int, default=15, help='Number of training epochs')
    parser.add_argument('--lr', type=float, default=5e-4, help='Learning rate')
    parser.add_argument('--output_dir', type=str, default='outputs', help='Directory to save outputs')
    parser.add_argument('--seed', type=int, default=213, help='Random seed')
    parser.add_argument('--max_seq_length', type=int, default=32, help='Maximum sequence length')
    parser.add_argument('--hidden_dim', type=int, default=128, help='Hidden dimension size')
    parser.add_argument('--embedding_pruning', type=float, default=0.3, help='Embedding pruning rate (0-1)')
    parser.add_argument('--quantize', action='store_true', help='Apply quantization after training')
    parser.add_argument('--export_onnx', action='store_true', help='Export to ONNX format after training')
    parser.add_argument('--distillation', action='store_true', help='Use knowledge distillation if available')
    parser.add_argument('--teacher_model', type=str, default='outputs/best_light_model.pt', help='Teacher model for distillation')
    return parser.parse_args()

def set_seed(seed):
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

def train_epoch(model, dataloader, optimizer, criterion, device, teacher_model=None, distillation_weight=0.5):
    model.train()
    epoch_loss = 0
    
    for batch in tqdm(dataloader, desc="Training"):
        # Move tensors to device
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        labels = batch["labels"]
        
        # Forward pass
        outputs = model(input_ids, attention_mask)
        
        # Calculate loss for each label
        batch_loss = 0
        for label_name, logits in outputs.items():
            # Standard cross entropy loss
            ce_loss = criterion(logits, labels[label_name].to(device))
            
            # Add knowledge distillation loss if teacher model is provided
            if teacher_model is not None:
                with torch.no_grad():
                    teacher_outputs = teacher_model(input_ids, attention_mask)
                    if label_name in teacher_outputs:
                        teacher_logits = teacher_outputs[label_name]
                        # Temperature-scaled distillation loss
                        T = 2.0  # Temperature parameter
                        distill_loss = nn.KLDivLoss(reduction='batchmean')(
                            F.log_softmax(logits / T, dim=1),
                            F.softmax(teacher_logits / T, dim=1)
                        ) * (T * T)
                        # Combine losses
                        loss = (1 - distillation_weight) * ce_loss + distillation_weight * distill_loss
                    else:
                        loss = ce_loss
            else:
                loss = ce_loss
                
            batch_loss += loss
        
        # Backward pass
        optimizer.zero_grad()
        batch_loss.backward()
        
        # Gradient clipping to prevent exploding gradients
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        
        optimizer.step()
        
        epoch_loss += batch_loss.item()
    
    return epoch_loss / len(dataloader)

def validate(model, dataloader, criterion, device):
    model.eval()
    val_loss = 0
    
    with torch.no_grad():
        for batch in tqdm(dataloader, desc="Validation"):
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"]
            
            outputs = model(input_ids, attention_mask)
            
            batch_loss = 0
            for label_name, logits in outputs.items():
                label_loss = criterion(logits, labels[label_name].to(device))
                batch_loss += label_loss
            
            val_loss += batch_loss.item()
    
    return val_loss / len(dataloader)

def load_teacher_model(model_path, device, label_config):
    """Load a pre-trained teacher model for knowledge distillation"""
    from light_model import LightImplicitLabelPredictor
    
    try:
        print(f"Loading teacher model from {model_path}...")
        teacher_model = LightImplicitLabelPredictor(
            label_config=label_config,
            quantize=False
        )
        teacher_model.load_state_dict(torch.load(model_path, map_location=device))
        teacher_model.to(device)
        teacher_model.eval()  # Set to evaluation mode
        print("Teacher model loaded successfully")
        return teacher_model
    except Exception as e:
        print(f"Failed to load teacher model: {e}")
        return None

def main():
    # Parse arguments
    args = parse_args()
    set_seed(args.seed)
    
    # Create output directory if not exists
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Set device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    # Load label config and filter for implicit labels
    label_config = load_label_config(args.config)
    implicit_labels = filter_implicit_labels(label_config)
    
    print(f"Found {len(implicit_labels)} implicit labels")
    
    # Load dataset
    with open(args.dataset, 'r') as f:
        dataset_json = json.load(f)
    
    # Initialize tokenizer for the tiny model
    tokenizer = AutoTokenizer.from_pretrained(args.model_name, model_max_length=args.max_seq_length)
    
    # Split dataset
    train_samples, test_samples = train_test_split(
        dataset_json['samples'], test_size=0.2, random_state=args.seed
    )
    train_samples, val_samples = train_test_split(
        train_samples, test_size=0.1, random_state=args.seed
    )
    
    print(f"Dataset split: {len(train_samples)} train, {len(val_samples)} val, {len(test_samples)} test")
    
    # Create datasets with ultra-small sequence length
    train_dataset = VehicleQueryDataset(train_samples, tokenizer, implicit_labels, max_length=args.max_seq_length)
    val_dataset = VehicleQueryDataset(val_samples, tokenizer, implicit_labels, max_length=args.max_seq_length)
    test_dataset = VehicleQueryDataset(test_samples, tokenizer, implicit_labels, max_length=args.max_seq_length)
    
    # Create dataloaders with larger batch size for smaller models
    train_dataloader = DataLoader(
        train_dataset, 
        batch_size=args.batch_size, 
        shuffle=True,
        collate_fn=collate_batch
    )
    val_dataloader = DataLoader(
        val_dataset, 
        batch_size=args.batch_size,
        collate_fn=collate_batch
    )
    test_dataloader = DataLoader(
        test_dataset, 
        batch_size=args.batch_size,
        collate_fn=collate_batch
    )
    
    # Load teacher model if distillation is enabled
    teacher_model = None
    if args.distillation and os.path.exists(args.teacher_model):
        teacher_model = load_teacher_model(args.teacher_model, device, implicit_labels)
    
    # Initialize ultra-lightweight model
    print(f"Initializing ultra-lightweight model with {args.model_name}...")
    model = UltraLightImplicitLabelPredictor(
        model_name=args.model_name,
        label_config=implicit_labels,
        max_seq_length=args.max_seq_length,
        hidden_dim=args.hidden_dim,
        quantize=False,  # Don't quantize during training
        embedding_pruning=args.embedding_pruning
    )
    model.to(device)
    
    # Report initial model size
    model_size_before = model.get_model_size()
    print(f"Initial model size: {model_size_before} MB")
    
    # Initialize optimizer and loss function
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    criterion = nn.CrossEntropyLoss()
    
    # Learning rate scheduler
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', factor=0.5, patience=2
    )
    
    # Training loop
    best_val_loss = float('inf')
    best_epoch = 0
    
    print(f"Starting training for {args.epochs} epochs...")
    
    for epoch in range(args.epochs):
        # Train
        train_loss = train_epoch(model, train_dataloader, optimizer, criterion, device, teacher_model)
        
        # Validate
        val_loss = validate(model, val_dataloader, criterion, device)
        
        # Update learning rate based on validation loss
        scheduler.step(val_loss)
        
        print(f"Epoch {epoch+1}/{args.epochs}, Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}")
        
        # Save best model
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_epoch = epoch
            
            # Save model
            torch.save(model.state_dict(), os.path.join(args.output_dir, 'best_ultra_light_model.pt'))
            print(f"Saved best model at epoch {epoch+1}")
    
    print(f"Training completed. Best model from epoch {best_epoch+1} with validation loss: {best_val_loss:.4f}")
    
    # Save final model
    final_model_path = os.path.join(args.output_dir, 'final_ultra_light_model.pt')
    torch.save(model.state_dict(), final_model_path)
    print(f"Saved final model to {final_model_path}")
    
    # Apply quantization if requested
    if args.quantize and not torch.cuda.is_available():
        print("Applying quantization to the final model...")
        model.quantize()
        torch.save(model.state_dict(), os.path.join(args.output_dir, 'quantized_ultra_light_model.pt'))
        print(f"Saved quantized model to {os.path.join(args.output_dir, 'quantized_ultra_light_model.pt')}")
        
        # Report new model size
        model_size_after = model.get_model_size()
        print(f"Model size before quantization: {model_size_before} MB")
        print(f"Model size after quantization: {model_size_after} MB")
        print(f"Size reduction: {(1 - model_size_after / model_size_before) * 100:.1f}%")
    
    # Export to ONNX if requested
    if args.export_onnx:
        print("Exporting model to ONNX format...")
        onnx_path = os.path.join(args.output_dir, 'ultra_light_model.onnx')
        model.export_to_onnx(onnx_path)
    
    # Load best model for evaluation
    model.load_state_dict(torch.load(os.path.join(args.output_dir, 'best_ultra_light_model.pt')))
    
    # Evaluate on test set
    test_metrics = evaluate_model(model, test_dataloader, device, implicit_labels)
    
    # Save metrics
    with open(os.path.join(args.output_dir, 'test_metrics_ultra_light.json'), 'w') as f:
        json.dump(test_metrics, f, indent=2)
    
    # Print overall results
    print(f"\nTest Results:")
    print(f"Overall Accuracy: {test_metrics['overall']['accuracy']:.4f}")
    print(f"Overall F1 Score: {test_metrics['overall']['f1']:.4f}")
    
    # Generate and save predictions for test set
    save_predictions(model, test_dataloader, device, implicit_labels, 
                     os.path.join(args.output_dir, 'test_predictions_ultra_light.json'))
    
    print(f"Test predictions saved to {os.path.join(args.output_dir, 'test_predictions_ultra_light.json')}")
    
    # Save model configuration for easier loading later
    model_config = {
        "model_name": args.model_name,
        "implicit_labels": list(implicit_labels.keys()),
        "max_seq_length": args.max_seq_length,
        "hidden_dim": args.hidden_dim,
        "quantized": args.quantize,
        "config_file": args.config,
    }
    with open(os.path.join(args.output_dir, 'ultra_light_model_config.json'), 'w') as f:
        json.dump(model_config, f, indent=2)
    print(f"Model configuration saved to {os.path.join(args.output_dir, 'ultra_light_model_config.json')}")
    
    # Example prediction
    example_text = "I need a comfortable family car with good safety features and fuel economy"
    
    # Convert model to eval mode and make prediction
    model.eval()
    predictions = model.predict(example_text, device, implicit_labels)
    
    print(f"\nExample Prediction for: '{example_text}'")
    for label, value in predictions.items():
        print(f"  {label}: {value}")
    
    # Show filtered (non-none) predictions
    filtered_predictions = {label: value for label, value in predictions.items() if value != "none"}
    print(f"\nFiltered predictions (non-none only):")
    for label, value in filtered_predictions.items():
        print(f"  {label}: {value}")
    
    # Final size report
    print(f"\nFinal model size: {model.get_model_size()} MB")
    
    # Compare with original model if available
    try:
        from light_model import LightImplicitLabelPredictor
        original_model = LightImplicitLabelPredictor()
        original_size = original_model.get_model_size()
        print(f"Original LightImplicitLabelPredictor size: {original_size} MB")
        print(f"Size reduction: {(1 - model.get_model_size() / original_size) * 100:.1f}%")
    except Exception as e:
        print(f"Could not compare with original model: {e}")

if __name__ == "__main__":
    main() 