import os
import json
import argparse
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split
from transformers import AutoTokenizer
from tqdm import tqdm
from sklearn.model_selection import train_test_split

# Import local modules
from model import ImplicitLabelPredictor
from dataset import VehicleQueryDataset, collate_batch
from utils import load_label_config, filter_implicit_labels, evaluate_model, save_predictions

def parse_args():
    parser = argparse.ArgumentParser(description='Train implicit label prediction model')
    parser.add_argument('--config', type=str, default='QueryLabels.json', help='Path to the label config file')
    parser.add_argument('--dataset', type=str, default='example_dataset.json', help='Path to the dataset file')
    parser.add_argument('--model_name', type=str, default='bert-base-uncased', help='Pretrained model name')
    parser.add_argument('--batch_size', type=int, default=16, help='Training batch size')
    parser.add_argument('--epochs', type=int, default=10, help='Number of training epochs')
    parser.add_argument('--lr', type=float, default=5e-5, help='Learning rate')
    parser.add_argument('--output_dir', type=str, default='outputs', help='Directory to save outputs')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    return parser.parse_args()

def set_seed(seed):
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

def train_epoch(model, dataloader, optimizer, criterion, device):
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
            label_loss = criterion(logits, labels[label_name].to(device))
            batch_loss += label_loss
        
        # Backward pass
        optimizer.zero_grad()
        batch_loss.backward()
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
    
    print(f"Found {len(implicit_labels)} implicit labels:")
    for i, (name, info) in enumerate(implicit_labels.items(), 1):
        print(f"{i}. {name}: {len(info['candidates'])} candidates + 'none'")
    
    # Load dataset
    with open(args.dataset, 'r') as f:
        dataset_json = json.load(f)
    
    # Initialize tokenizer
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    
    # Split dataset
    train_samples, test_samples = train_test_split(
        dataset_json['samples'], test_size=0.2, random_state=args.seed
    )
    train_samples, val_samples = train_test_split(
        train_samples, test_size=0.1, random_state=args.seed
    )
    
    print(f"Dataset split: {len(train_samples)} train, {len(val_samples)} val, {len(test_samples)} test")
    
    # Create datasets
    train_dataset = VehicleQueryDataset(train_samples, tokenizer, implicit_labels)
    val_dataset = VehicleQueryDataset(val_samples, tokenizer, implicit_labels)
    test_dataset = VehicleQueryDataset(test_samples, tokenizer, implicit_labels)
    
    # Create dataloaders
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
    
    # Initialize model
    model = ImplicitLabelPredictor(args.model_name, implicit_labels)
    model.to(device)
    
    # Initialize optimizer and loss function
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)
    criterion = nn.CrossEntropyLoss()
    
    # Training loop
    best_val_loss = float('inf')
    best_epoch = 0
    
    print(f"Starting training for {args.epochs} epochs...")
    
    for epoch in range(args.epochs):
        # Train
        train_loss = train_epoch(model, train_dataloader, optimizer, criterion, device)
        
        # Validate
        val_loss = validate(model, val_dataloader, criterion, device)
        
        print(f"Epoch {epoch+1}/{args.epochs}, Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}")
        
        # Save best model
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_epoch = epoch
            
            # Save model
            torch.save(model.state_dict(), os.path.join(args.output_dir, 'best_model.pt'))
            print(f"Saved best model at epoch {epoch+1}")
    
    print(f"Training completed. Best model from epoch {best_epoch+1} with validation loss: {best_val_loss:.4f}")
    
    # Load best model for evaluation
    model.load_state_dict(torch.load(os.path.join(args.output_dir, 'best_model.pt')))
    
    # Evaluate on test set
    test_metrics = evaluate_model(model, test_dataloader, device, implicit_labels)
    
    # Save metrics
    with open(os.path.join(args.output_dir, 'test_metrics.json'), 'w') as f:
        json.dump(test_metrics, f, indent=2)
    
    # Print overall results
    print(f"\nTest Results:")
    print(f"Overall Accuracy: {test_metrics['overall']['accuracy']:.4f}")
    print(f"Overall F1 Score: {test_metrics['overall']['f1']:.4f}")
    
    # Generate and save predictions for test set
    save_predictions(model, test_dataloader, device, implicit_labels, 
                     os.path.join(args.output_dir, 'test_predictions.json'))
    
    print(f"Test predictions saved to {os.path.join(args.output_dir, 'test_predictions.json')}")
    
    # Example prediction
    example_text = "I need a comfortable family car with good safety features and fuel economy"
    predictions = model.predict(example_text, device, implicit_labels)
    
    print(f"\nExample Prediction for: '{example_text}'")
    for label, value in predictions.items():
        print(f"{label}: {value}")

if __name__ == "__main__":
    main() 