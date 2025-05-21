import torch
from torch.utils.data import Dataset

class VehicleQueryDataset(Dataset):
    def __init__(self, data, tokenizer, implicit_labels, max_length=128):
        """
        Dataset class for vehicle query data
        
        Args:
            data: List of dictionaries containing queries and labels
            tokenizer: Tokenizer for encoding the queries
            implicit_labels: Dict of implicit labels with their configurations
            max_length: Maximum sequence length for tokenization
        """
        self.tokenizer = tokenizer
        self.data = data
        self.max_length = max_length
        self.implicit_labels = implicit_labels
        
        # Create label to id mappings for each implicit label
        self.label2id = {}
        for label_name, label_info in implicit_labels.items():
            candidates = label_info["candidates"]
            # Add "none" as the last class
            self.label2id[label_name] = {
                **{candidate: i for i, candidate in enumerate(candidates)},
                "none": len(candidates)
            }
        
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        item = self.data[idx]
        query = item["query"]
        
        # Tokenize
        encoding = self.tokenizer(
            query,
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt"
        )
        
        # Extract tensors
        input_ids = encoding["input_ids"].squeeze(0)
        attention_mask = encoding["attention_mask"].squeeze(0)
        
        # Create label tensors
        labels = {}
        for label_name in self.implicit_labels:
            label_value = item["labels"].get(label_name, "none")
            label_id = self.label2id[label_name][label_value]
            labels[label_name] = torch.tensor(label_id, dtype=torch.long)
        
        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels
        }

def collate_batch(batch):
    """
    Custom collate function for batching samples
    """
    input_ids = torch.stack([item["input_ids"] for item in batch])
    attention_mask = torch.stack([item["attention_mask"] for item in batch])
    
    # Combine labels from all samples
    labels = {}
    for key in batch[0]["labels"].keys():
        labels[key] = torch.stack([item["labels"][key] for item in batch])
    
    return {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "labels": labels
    } 