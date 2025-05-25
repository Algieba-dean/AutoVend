#!/usr/bin/env python
"""
Script to generate model_list.py files for different car brands
using OpenAI API to generate model names.

Usage:
    python create_model_list.py --brand_name BMW --model_num 5
"""

import os
import argparse
import json
import openai
import random
from brand_list import brand_list

# Set your OpenAI API key
# openai.api_key = "your_openai_api_key"  # Replace with your API key or set environment variable
# Alternatively, set it as an environment variable:
# export OPENAI_API_KEY="your_openai_api_key"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY","sk-1a2v23fdad34513d51234")
OPENAI_MODEL = os.getenv("OPENAI_MODEL","deepseek-chat")
OPENAI_URL = os.getenv("OPENAI_URL","https://api.deepseek.com/v1")

client = openai.OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_URL,
)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Generate car model list for a specific brand")
    parser.add_argument("--brand_name", type=str, required=True, help="Brand name to generate models for")
    parser.add_argument("--model_num", type=int, default=5, help="Number of models to generate (default: 5)")
    return parser.parse_args()

def validate_brand(brand_name):
    """Validate if the provided brand name exists in our brand list."""
    if brand_name not in brand_list:
        print(f"Error: '{brand_name}' is not in the list of available brands.")
        print("Available brands:")
        for brand in sorted(brand_list):
            print(f"- {brand}")
        return False
    return True

def get_existing_models(brand_name):
    """Get existing model list if it exists."""
    brand_dir = os.path.join(os.getcwd(), brand_name)
    model_file = os.path.join(brand_dir, "model_list.py")
    existing_models = []
    
    if os.path.exists(model_file):
        try:
            # Create a temporary namespace
            namespace = {}
            # Execute the file content in the namespace
            with open(model_file, 'r') as f:
                exec(f.read(), namespace)
            # Extract the model_list variable
            if 'model_list' in namespace:
                existing_models = namespace['model_list']
                print(f"Found {len(existing_models)} existing models.")
        except Exception as e:
            print(f"Error reading existing model file: {e}")
    
    return existing_models

def generate_models(brand_name, model_num, existing_models=None):
    """Generate car model names using OpenAI API."""
    if existing_models is None:
        existing_models = []
    
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are an automotive expert that generates precise car model names. "
                               "You must provide ONLY REAL models that actually exist in the market. "
                               "Include models across different price ranges (economy, mid-range, premium, luxury) "
                               "and different vehicle types (sedans, SUVs, coupes, etc.) when applicable. "
                               "CRITICAL: Generate SPECIFIC, PRECISE model names with exact trim/variant information, "
                               "NOT just general model series. This is essential because different trims/variants "
                               "of the same model series can have significantly different specifications."
                },
                {
                    "role": "user",
                    "content": f"Generate {model_num} precise car model names for {brand_name}. "
                               f"Return only a Python list of strings with the model names in the format: "
                               f"[\"{brand_name}-ModelName1\", \"{brand_name}-ModelName2\", ...]. "
                               f"Be realistic and match the naming conventions of this brand.\n\n"
                               f"IMPORTANT INSTRUCTIONS:\n"
                               f"1. These models MUST BE REAL, SPECIFIC models that actually exist or have existed in the market.\n"
                               f"2. Include models across different price ranges from economy to luxury if possible.\n"
                               f"3. CRITICAL: Generate SPECIFIC model variants with precise trim/engine/year information, NOT just model series names.\n"
                               f"   ✓ GOOD examples: \"{brand_name}-320i xDrive\", \"{brand_name}-A8L 55 TFSI\", \"{brand_name}-Camry XSE V6\"\n"
                               f"   ✗ BAD examples: \"{brand_name}-3 Series\", \"{brand_name}-A8\", \"{brand_name}-Camry\"\n"
                               f"4. This precision is essential because we need exact parameters for each model - different trims have different specs.\n"
                               f"5. Include specific engine variant, trim level, or other distinguishing features in the model name.\n"
                               f"6. The following models already exist and should NOT be included: {existing_models}"
                }
            ],
            temperature=0.6,  # Lower temperature for more precise output
            max_tokens=1024
        )
        
        # Extract the model list from the response
        model_text = response.choices[0].message.content.strip()
        print(model_text)
        # Clean up the response to ensure it's a valid Python list
        if not model_text.startswith("[") or not model_text.endswith("]"):
            # Extract the list if it's embedded in other text
            start = model_text.find("[")
            end = model_text.rfind("]") + 1
            if start != -1 and end != 0:
                model_text = model_text[start:end]
            else:
                raise ValueError("API did not return a properly formatted list")
        
        # Convert the string representation of the list to an actual Python list
        model_list = eval(model_text)
        
        # Verify no duplicates with existing models
        new_models = []
        for model in model_list:
            if model not in existing_models:
                new_models.append(model)
        
        if len(new_models) < len(model_list):
            print(f"Removed {len(model_list) - len(new_models)} duplicate models.")
        
        return new_models
    
    except Exception as e:
        print(f"Error generating models with OpenAI API: {e}")
        # Fallback: generate some generic model names
        print("Falling back to generic model generation...")
        return []

def write_model_list(brand_name, models, existing_models=None):
    """Write the generated models to a model_list.py file in the brand directory."""
    if existing_models is None:
        existing_models = []
    
    # Combine existing and new models
    combined_models = existing_models + models
    
    brand_dir = os.path.join(os.getcwd(), brand_name)
    model_file = os.path.join(brand_dir, "model_list.py")
    
    with open(model_file, 'w') as f:
        f.write('"""\n')
        f.write(f'List of {brand_name} car models\n')
        f.write('Generated by create_model_list.py script\n')
        f.write('These are real car models across different price ranges\n')
        f.write('IMPORTANT: These are specific model variants (not just series names) to ensure accurate specifications\n')
        f.write('"""\n\n')
        f.write(f'model_list = {json.dumps(combined_models, indent=4)}\n')
    
    print(f"Successfully created {model_file} with {len(combined_models)} models "
          f"({len(models)} new, {len(existing_models)} existing)")

def main():
    """Main function to run the script."""
    args = parse_arguments()
    brand_name = args.brand_name
    model_num = args.model_num
    
    if not validate_brand(brand_name):
        return
    # for brand_name in brand_list:
    #     if brand_name == "XiaoMi":
    #         continue
    #     # Check for existing models
    #     existing_models = get_existing_models(brand_name)
    
    #     print(f"Generating {model_num} new models for {brand_name}...")
    #     new_models = generate_models(brand_name, model_num, existing_models)
    #     print(new_models)
    
    #     if new_models:
    #         write_model_list(brand_name, new_models, existing_models)
    #         print(f"Done! Added {len(new_models)} new models.")
    #     else:
    #         print("No new models were generated.")

    # Check for existing models
    existing_models = get_existing_models(brand_name)
    
    print(f"Generating {model_num} new precise model variants for {brand_name}...")
    new_models = generate_models(brand_name, model_num, existing_models)
    print(new_models)
    
    if new_models:
        write_model_list(brand_name, new_models, existing_models)
        print(f"Done! Added {len(new_models)} new specific model variants.")
    else:
        print("No new models were generated.")

if __name__ == "__main__":
    main() 