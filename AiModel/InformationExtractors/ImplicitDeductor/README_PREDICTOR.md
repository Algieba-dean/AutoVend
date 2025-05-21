# Implicit Label Predictor

A lightweight wrapper for using the trained implicit label prediction model in your applications.

## Installation

1. Make sure you have all dependencies installed:
```bash
pip install -r requirements.txt
```

2. Make sure you have the following files:
   - `implicit_predictor.py` - The main predictor class
   - `model.py` - Model architecture definition
   - `utils.py` - Utility functions for model usage
   - `QueryLabels.json` - Label definitions and configurations
   - Trained model weights (typically in `outputs/best_model.pt` or `outputs/final_model.pt`)

## Basic Usage

Here's how to use the ImplicitPredictor class in your code:

```python
from implicit_predictor import ImplicitPredictor

# Initialize the predictor
predictor = ImplicitPredictor(
    model_path='outputs/best_model.pt',
    config_path='QueryLabels.json'
)

# Make a prediction for a single query
query = "I want an economical car with good fuel efficiency for city commuting"
result = predictor.predict(query)  # Returns only non-none values by default

# Print the results
print(f"Query: {query}")
for label, value in result.items():
    print(f"  {label}: {value}")
```

## Advanced Usage

### Getting All Predictions (Including None Values)

```python
# Get all predictions including none values
all_predictions = predictor.predict(query, filter_none=False)
```

### Batch Processing Multiple Queries

```python
# Process multiple queries at once
queries = [
    "I need a luxury SUV with good off-road capability",
    "I want to buy an electric car with long driving range"
]
batch_results = predictor.predict_batch(queries)
```

### File-Based Processing

```python
# Process queries from a file and save results to another file
predictor.save_predictions(
    input_file="queries.txt",  # One query per line
    output_file="results.json"
)
```

### Getting Available Labels and Their Candidates

```python
# Get all available implicit labels
labels = predictor.get_available_labels()

# Get candidate values for a specific label
candidates = predictor.get_label_candidates("prize_alias")
```

## Running the Example

An example script is provided to demonstrate the usage:

```bash
python predictor_example.py
```

## Integration Tips

- For web applications: Use the predictor in your API routes to extract implicit labels from user queries
- For search systems: Use the predictor to enrich search queries with additional filters
- For recommendation systems: Use the predicted labels to refine user preferences
- For analytics: Process historical user queries to identify common implicit preferences

## Performance Considerations

- The model uses BERT or similar Transformer architecture, which can be resource-intensive
- For production environments with high traffic, consider:
  - Using a smaller model
  - Setting up batch processing
  - Implementing caching for common queries
  - Running on GPU for better performance 