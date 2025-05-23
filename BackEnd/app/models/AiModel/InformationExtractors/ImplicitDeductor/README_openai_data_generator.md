# OpenAI Vehicle Query Data Generator

This tool uses the OpenAI API to generate vehicle query test data with a format similar to `example_dataset.json`. It automatically analyzes implicit label configurations in `QueryLabels.json` to create samples that match the required criteria.

## Key Features

- Generates additional test data based on existing samples
- Automatically extracts and uses implicit labels (implicit_support=true) from `QueryLabels.json`
- Each generated sample contains a query and corresponding set of labels
- Supports customizable sample count and output file path
- **Strict label generation rules** to ensure data quality

## Data Generation Rules

To ensure high-quality test data, the script follows these rules:

1. **Label Value Restrictions**: All label values must come strictly from the candidates list defined in `QueryLabels.json` or "none"
2. **English Vehicle Purchase Conversations**: All query text must be in English and related to vehicle purchases
3. **Implicit Association Rules**: Label values are only activated (non-none) when the query text strongly implies that attribute
4. **Indirect Expression**: Query text cannot directly mention label names, but must express them indirectly
5. **Contextual Inference**: Labels are inferred through indirect descriptions, for example:
   - Location/climate implications: "I live in Norway" → cold_resistance: high
   - Travel patterns: "I always go far away" → highway_long_distance: yes
   - Economic factors: "Gas prices are too high" → fuel_consumption_alias: low
   - Skills/habits: "I'm really bad at parking" → auto_parking: yes
   - Lifestyle: "I have a big family" → family_friendliness: high

## Installation Requirements

Install the required Python dependencies:

```bash
pip install openai argparse tqdm
```

## Usage

### Basic Usage

```bash
python generate_openai_test_data.py --api_key YOUR_OPENAI_API_KEY
```

### Configuration Options

```bash
python generate_openai_test_data.py \
  --api_key YOUR_OPENAI_API_KEY \
  --model deepseek-chat \
  --samples 20 \
  --output custom_dataset.json \
  --example_file example_dataset.json \
  --label_config QueryLabels.json \
  --batch_size 5 \
  --verbose \
  --api_url https://api.deepseek.com/v1
```

### Parameter Descriptions

- `--api_key`: OpenAI API key (can also be set via OPENAI_API_KEY environment variable)
- `--model`: AI model to use, default is deepseek-chat
- `--samples`: Number of samples to generate, default is 10
- `--output`: Output file path, default is generated_dataset.json
- `--example_file`: Example dataset file path, default is example_dataset.json
- `--label_config`: Label configuration file path, default is QueryLabels.json
- `--batch_size`: Number of samples to generate per API call, default is 5
- `--verbose`: Enable detailed output, including API response content
- `--api_url`: Base URL for the API, default is https://api.deepseek.com/v1

## Using Environment Variables

You can set the API key and other parameters using environment variables:

```bash
export OPENAI_API_KEY=your_api_key_here
export OPENAI_MODEL=deepseek-chat
export OPENAI_URL=https://api.deepseek.com/v1
python generate_openai_test_data.py
```

## Examples

### Generate 10 New Samples

```bash
python generate_openai_test_data.py
```

### Use GPT-3.5 Turbo to Generate 5 Samples

```bash
python generate_openai_test_data.py --model gpt-3.5-turbo --samples 5
```

### Specify Custom Output File

```bash
python generate_openai_test_data.py --output training_data.json
```

### Generate Large Dataset in Batches

```bash
python generate_openai_test_data.py --samples 50 --batch_size 10
```

## Generated Data Format

The generated data will be saved in the same format as `example_dataset.json`:

```json
{
  "samples": [
    {
      "query": "I need a fuel-efficient hybrid SUV for city driving",
      "labels": {
        "prize_alias": "mid-range high-end",
        "city_commuting": "yes",
        "passenger_space_volume_alias": "medium",
        "trunk_volume_alias": "medium",
        "chassis_height_alias": "medium ride height",
        ...
      }
    },
    ...
  ]
}
```

## Indirect Expression Examples

The script supports various indirect expressions, here are some examples:

| Indirect Expression | Corresponding Label |
|---------|---------|
| "I'm on a tight budget" | prize_alias: cheap |
| "I need to fit my whole family comfortably" | passenger_space_volume_alias: large |
| "I frequently drive on unpaved mountain trails" | chassis_height_alias: off-road chassis |
| "I'm really bad at parking in tight spaces" | auto_parking: yes, remote_parking: yes |
| "I drive in heavy snow and ice regularly" | cold_resistance: high |
| "I need something compact for city parking" | size: small |
| "I want a car that turns heads" | aesthetics: high |
| "Fuel efficiency is my absolute top priority" | energy_consumption_level: low |

## Important Notes

- Ensure you have a valid API key
- Generating many samples may consume API credits, consider using the batch_size parameter
- Data quality may vary depending on the model used
- The validation module automatically checks for valid label values and skips invalid samples 