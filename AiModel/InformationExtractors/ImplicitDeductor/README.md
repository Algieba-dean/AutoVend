# Implicit Label Prediction Model

This project trains a machine learning model to predict implicit labels from vehicle queries. It uses Transformer models to extract semantic information from text and predict multiple labels simultaneously.

## Features

- Multi-label classification for vehicle-related queries
- Supports all implicit_support=true labels from QueryLabels.json
- Based on Transformer architecture (default: BERT)
- Evaluates performance with accuracy, precision, recall, and F1 score

## Directory Structure

```
.
├── README.md
├── QueryLabels.json          # Label definitions 
├── model.py                  # Model implementation
├── dataset.py                # Dataset class
├── utils.py                  # Utility functions
├── train_implicit_model.py   # Training script
├── example_dataset.json      # Example dataset for training
└── requirements.txt          # Dependencies
```

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Make sure you have the QueryLabels.json file in your project directory.

## Usage

### Training

To train the model with default parameters:

```bash
python train_implicit_model.py
```

With custom parameters:

```bash
python train_implicit_model.py --config QueryLabels.json --dataset example_dataset.json --model_name bert-base-uncased --batch_size 16 --epochs 10 --lr 5e-5 --output_dir outputs
```

### Arguments

- `--config`: Path to the label config file (default: 'QueryLabels.json')
- `--dataset`: Path to the dataset file (default: 'example_dataset.json')
- `--model_name`: Pretrained model name (default: 'bert-base-uncased')
- `--batch_size`: Training batch size (default: 16)
- `--epochs`: Number of training epochs (default: 10)
- `--lr`: Learning rate (default: 5e-5)
- `--output_dir`: Directory to save outputs (default: 'outputs')
- `--seed`: Random seed (default: 42)

### Dataset Format

The dataset should be a JSON file with the following structure:

```json
{
    "samples": [
        {
            "query": "I want a cheap car with good city driving capability",
            "labels": {
                "prize_alias": "cheap",
                "city_commuting": "yes",
                "passenger_space_volume_alias": "none",
                ...
            }
        },
        ...
    ]
}
```

Each label must be one of the candidates defined in QueryLabels.json, or "none" to indicate the label is not activated for this query.

## Outputs

The training script generates the following outputs in the specified output directory:

- `best_model.pt`: The best model weights based on validation loss
- `test_metrics.json`: Evaluation metrics on the test set
- `test_predictions.json`: Model predictions on the test set

## Example Prediction

After training, you can use the model to predict implicit labels for new queries:

```python
from model import ImplicitLabelPredictor
from utils import load_label_config, filter_implicit_labels
import torch

# Load model and config
label_config = load_label_config('QueryLabels.json')
implicit_labels = filter_implicit_labels(label_config)
model = ImplicitLabelPredictor('bert-base-uncased', implicit_labels)
model.load_state_dict(torch.load('outputs/best_model.pt'))

# Make prediction
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
text = "I need a spacious family car with good safety features"
predictions = model.predict(text, device, implicit_labels)

# Print results
for label, value in predictions.items():
    print(f"{label}: {value}")
``` 