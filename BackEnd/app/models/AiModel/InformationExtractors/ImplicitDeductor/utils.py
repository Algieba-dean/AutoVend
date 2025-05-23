import json
import torch
import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix

def load_label_config(config_path):
    """
    Load the label configuration from a JSON file
    
    Args:
        config_path: Path to the QueryLabels.json file
        
    Returns:
        Dictionary of all labels
    """
    with open(config_path, "r") as f:
        label_config = json.load(f)
    return label_config


def filter_implicit_labels(label_config):
    """
    Filter labels to get only those with implicit_support=True
    
    Args:
        label_config: Full label configuration dictionary
        
    Returns:
        Dictionary with only implicit support labels
    """
    return {
        name: info for name, info in label_config.items() 
        if info.get("implicit_support", False) == True
    }


def evaluate_model(model, dataloader, device, implicit_labels):
    """
    Evaluate model performance on a dataloader
    
    Args:
        model: Trained model
        dataloader: DataLoader with evaluation data
        device: Device to run evaluation on
        implicit_labels: Dictionary of implicit labels with configurations
        
    Returns:
        Dictionary of metrics per label
    """
    model.eval()
    all_predictions = {label: [] for label in implicit_labels}
    all_targets = {label: [] for label in implicit_labels}
    
    with torch.no_grad():
        for batch in dataloader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            
            outputs = model(input_ids, attention_mask)
            
            for label_name, logits in outputs.items():
                predictions = torch.argmax(logits, dim=1).cpu().numpy()
                targets = batch["labels"][label_name].cpu().numpy()
                
                all_predictions[label_name].extend(predictions)
                all_targets[label_name].extend(targets)
    
    # Calculate metrics for each label
    results = {}
    for label_name in implicit_labels:
        accuracy = accuracy_score(all_targets[label_name], all_predictions[label_name])
        precision, recall, f1, _ = precision_recall_fscore_support(
            all_targets[label_name], 
            all_predictions[label_name], 
            average='weighted'
        )
        
        results[label_name] = {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1": f1
        }
    
    overall_accuracy = np.mean([results[label]["accuracy"] for label in results])
    overall_f1 = np.mean([results[label]["f1"] for label in results])
    
    results["overall"] = {
        "accuracy": overall_accuracy,
        "f1": overall_f1
    }
    
    return results


def save_predictions(model, dataloader, device, implicit_labels, output_path):
    """
    Save model predictions to a file
    
    Args:
        model: Trained model
        dataloader: DataLoader with data to predict
        device: Device to run prediction on
        implicit_labels: Dictionary of implicit labels with configurations
        output_path: Path to save predictions
        
    Returns:
        None
    """
    model.eval()
    all_predictions = []
    
    with torch.no_grad():
        for batch in dataloader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            
            batch_size = input_ids.size(0)
            outputs = model(input_ids, attention_mask)
            
            for i in range(batch_size):
                sample_predictions = {}
                for label_name, logits in outputs.items():
                    probabilities = torch.softmax(logits[i], dim=0)
                    predicted_idx = torch.argmax(probabilities).item()
                    
                    # Map back to label value
                    candidates = implicit_labels[label_name]["candidates"]
                    if predicted_idx < len(candidates):
                        predicted_value = candidates[predicted_idx]
                    else:
                        predicted_value = "none"
                    
                    sample_predictions[label_name] = predicted_value
                
                all_predictions.append(sample_predictions)
    
    with open(output_path, 'w') as f:
        json.dump(all_predictions, f, indent=2)


def get_id2label_mapping(dataset):
    """
    Create id to label mappings for each implicit label
    
    Args:
        dataset: VehicleQueryDataset instance
        
    Returns:
        Dictionary of id2label mappings for each label
    """
    id2label = {}
    for label_name, label2id in dataset.label2id.items():
        id2label[label_name] = {id: label for label, id in label2id.items()}
    
    return id2label 