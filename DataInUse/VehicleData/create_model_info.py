#!/usr/bin/env python
"""
Script to generate detailed information files for car models
using OpenAI API to generate realistic car specifications.

Usage:
    python create_model_info.py --model_name "Audi-A8"
    python create_model_info.py --brand_name "Audi"  # Generate info for all models in brand's model_list.py
"""

import os
import argparse
import openai
import re
import time
from brand_list import brand_list

# OpenAI API configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-40f9ea6f41bd4cbbae8a9d4adb07fbf8")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "deepseek-chat")
OPENAI_URL = os.getenv("OPENAI_URL", "https://api.deepseek.com/v1")

client = openai.OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_URL,
)

# Define label categories based on powertrain type
PURE_ELECTRIC_LABELS = ["battery_capacity", "electric_consumption"]
PURE_COMBUSTION_LABELS = ["engine_displacement", "fuel_consumption", "fuel_tank_capacity"]

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Generate detailed information file for a specific car model")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--model_name", type=str, help="Car model name (e.g., 'Audi-A8')")
    group.add_argument("--brand_name", type=str, help="Brand name to generate info for all models")
    parser.add_argument("--delay", type=int, default=2, help="Delay in seconds between API calls when processing multiple models (default: 2)")
    parser.add_argument("--skip_existing", action="store_true", help="Skip models that already have .toml files")
    return parser.parse_args()

def validate_model_name(model_name):
    """Validate if the model name follows the correct format and the brand exists."""
    if "-" not in model_name:
        print(f"Error: Model name '{model_name}' does not follow the format 'Brand-Model'.")
        return False
    
    brand = model_name.split("-")[0]
    if brand not in brand_list:
        print(f"Error: Brand '{brand}' is not in the list of available brands.")
        print("Available brands:")
        for b in sorted(brand_list):
            print(f"- {b}")
        return False
    
    return True

def validate_brand_name(brand_name):
    """Validate if the brand exists."""
    if brand_name not in brand_list:
        print(f"Error: Brand '{brand_name}' is not in the list of available brands.")
        print("Available brands:")
        for b in sorted(brand_list):
            print(f"- {b}")
        return False
    return True

def get_models_for_brand(brand_name):
    """Get all models for a specific brand from model_list.py."""
    model_list_path = os.path.join(os.getcwd(), brand_name, "model_list.py")
    
    if not os.path.exists(model_list_path):
        print(f"Error: Model list file '{model_list_path}' does not exist.")
        return []
    
    try:
        # Create a temporary namespace
        namespace = {}
        # Execute the file content in the namespace
        with open(model_list_path, 'r') as f:
            exec(f.read(), namespace)
        # Extract the model_list variable
        if 'model_list' in namespace:
            models = namespace['model_list']
            print(f"Found {len(models)} models for {brand_name}.")
            return models
        else:
            print(f"Error: No 'model_list' found in {model_list_path}")
            return []
    except Exception as e:
        print(f"Error reading model list file: {e}")
        return []

def check_model_exists(model_name):
    """Check if the model exists in the brand's model_list.py file."""
    brand = model_name.split("-")[0]
    model_list_path = os.path.join(os.getcwd(), brand, "model_list.py")
    
    if not os.path.exists(model_list_path):
        print(f"Warning: Model list file '{model_list_path}' does not exist.")
        return True  # Allow generating info even if model_list.py doesn't exist
    
    try:
        # Create a temporary namespace
        namespace = {}
        # Execute the file content in the namespace
        with open(model_list_path, 'r') as f:
            exec(f.read(), namespace)
        # Extract the model_list variable
        if 'model_list' in namespace and model_name in namespace['model_list']:
            return True
        else:
            print(f"Warning: Model '{model_name}' not found in {model_list_path}")
            print("Available models:")
            if 'model_list' in namespace:
                for model in namespace['model_list']:
                    print(f"- {model}")
            return False
    except Exception as e:
        print(f"Error reading model list file: {e}")
        return False

def check_info_file_exists(model_name):
    """Check if the model's info file already exists."""
    brand = model_name.split("-")[0]
    info_file = os.path.join(os.getcwd(), brand, f"{model_name}.toml")
    return os.path.exists(info_file)

def extract_sections_from_template(template):
    """Extract section names and the last label from the template."""
    section_pattern = r'\[(.*?)\]'
    sections = re.findall(section_pattern, template)
    
    # Find the last label in the template
    lines = template.strip().split('\n')
    last_label = None
    for line in reversed(lines):
        line = line.strip()
        if line and line[0] != '#' and line[0] != '[' and '=' in line:
            last_label = line.split('=')[0].strip()
            break
    
    return sections, last_label

def extract_labels_from_template(template):
    """Extract all labels from the template file."""
    labels = []
    current_section = None
    
    for line in template.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
            
        # Check for section headers
        section_match = re.match(r'\[(.*?)\]', line)
        if section_match:
            current_section = section_match.group(1)
            continue
            
        # Extract label
        if '=' in line:
            label = line.split('=')[0].strip()
            if re.match(r'^[a-zA-Z0-9_]+$', label) and not label.endswith("_comments"):
                labels.append(label)
    
    return labels

def get_powertrain_type(content):
    """Extract the powertrain_type from the content."""
    pattern = r'powertrain_type\s*=\s*"([^"]+)"'
    match = re.search(pattern, content)
    if match:
        return match.group(1)
    return None

def set_inapplicable_values_to_none(content):
    """Set inapplicable values based on powertrain type to 'None'."""
    powertrain_type = get_powertrain_type(content)
    if not powertrain_type:
        return content  # Can't determine powertrain type
    
    lines = content.strip().split('\n')
    result_lines = []
    
    for line in lines:
        if '=' in line:
            parts = line.split('=', 1)
            label = parts[0].strip()
            value = parts[1].strip()
            
            # Don't modify comment fields
            if label.endswith("_comments"):
                result_lines.append(line)
                continue
                
            # Check if this label should be set to "None" based on powertrain type
            if ((powertrain_type in ["Gasoline Engine", "Diesel Engine"] and label in PURE_ELECTRIC_LABELS) or
                (powertrain_type == "Battery Electric Vehicle" and label in PURE_COMBUSTION_LABELS)):
                result_lines.append(f'{label} = "None"')
            else:
                result_lines.append(line)
        else:
            result_lines.append(line)
    
    return '\n'.join(result_lines)

def filter_labels_by_powertrain(labels, powertrain_type):
    """Filter labels based on the powertrain type."""
    # We no longer filter out labels - all labels are included
    # but the inapplicable ones will be set to "None"
    return labels

def read_template():
    """Read the CarLabels.toml template file."""
    try:
        with open("CarLabels.toml", "r") as f:
            return f.read()
    except Exception as e:
        print(f"Error reading template file: {e}")
        return None

def clean_toml_content(content, template):
    """Clean and format the TOML content to match the template structure."""
    # Extract sections and last label from template
    template_sections, last_label = extract_sections_from_template(template)
    
    # Determine powertrain type to handle specific labels
    powertrain_type = get_powertrain_type(content)
    
    # Split content into lines for processing
    lines = content.strip().split('\n')
    cleaned_lines = []
    current_section = None
    found_sections = set()
    processed_labels = set()
    reached_last_label = False
    
    # Process each line
    for line in lines:
        line = line.strip()
        if not line:
            cleaned_lines.append(line)
            continue
            
        if line.startswith('#'):
            cleaned_lines.append(line)
            continue
        
        # Check for section headers
        section_match = re.match(r'\[(.*?)\]', line)
        if section_match:
            section_name = section_match.group(1)
            if section_name in template_sections and section_name not in found_sections:
                current_section = section_name
                found_sections.add(section_name)
                cleaned_lines.append(f"[{current_section}]")
            continue
        
        # Process label lines
        if '=' in line:
            label = line.split('=')[0].strip()
            
            # Allow both standard labels and _comments fields
            if re.match(r'^[a-zA-Z0-9_]+$', label):
                base_label = label.replace("_comments", "")
                
                # We no longer skip labels based on powertrain type
                # Instead, we'll later set inapplicable values to "None"
                
                # If we've already reached the last label, only allow comments for it
                if reached_last_label and not label.endswith("_comments") and label != last_label:
                    continue
                    
                # Stop processing once we've reached the last label and processed its comments
                if last_label and base_label == last_label and not label.endswith("_comments"):
                    reached_last_label = True
                
                # Keep track of processed labels to avoid duplicates
                if label not in processed_labels:
                    processed_labels.add(label)
                    cleaned_lines.append(line)
        
    # Ensure all template sections are included
    for section in template_sections:
        if section not in found_sections:
            cleaned_lines.append(f"[{section}]")
    
    # Return the cleaned content
    return '\n'.join(cleaned_lines)

def validate_generated_content(content, template):
    """Validate that the generated content contains all required labels based on powertrain type."""
    # We want to validate all labels now, regardless of powertrain type
    template_labels = extract_labels_from_template(template)
    content_labels = extract_labels_from_template(content)
    
    # Check if all template labels are in the content
    missing_labels = [label for label in template_labels if label not in content_labels]
    
    if missing_labels:
        print("Warning: The following labels are missing in the generated content:")
        for label in missing_labels:
            print(f"- {label}")
        return False, missing_labels
    
    return True, []

def check_for_missing_comments(content):
    """Check if any labels are missing their corresponding _comments."""
    lines = content.strip().split('\n')
    labels = set()
    comments = set()
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#') or line.startswith('['):
            continue
            
        if '=' in line:
            label = line.split('=')[0].strip()
            if re.match(r'^[a-zA-Z0-9_]+$', label):
                if label.endswith("_comments"):
                    comments.add(label.replace("_comments", ""))
                else:
                    # Include all labels, even those that might be set to "None"
                    labels.add(label)
    
    # Find labels without comments, excluding title and car_model
    labels_without_comments = [label for label in labels if label not in comments 
                              and label != "title" and label != "car_model"]
    
    return labels_without_comments

def fix_missing_labels(content, template, missing_labels):
    """Add any missing labels to the content."""
    sections = {}
    current_section = None
    
    # Parse the template to find which section each label belongs to
    for line in template.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
            
        # Check for section headers
        section_match = re.match(r'\[(.*?)\]', line)
        if section_match:
            current_section = section_match.group(1)
            if current_section not in sections:
                sections[current_section] = []
            continue
            
        # Extract label
        if '=' in line and current_section:
            label = line.split('=')[0].strip()
            if re.match(r'^[a-zA-Z0-9_]+$', label):
                # Include all labels from the template 
                # (inapplicable ones will be set to "None" later)
                sections[current_section].append((label, line))
    
    # Parse the content to find existing sections
    content_lines = content.strip().split('\n')
    updated_content = []
    current_section = None
    
    for line in content_lines:
        # Add the current line
        updated_content.append(line)
        
        # Keep track of current section
        section_match = re.match(r'\[(.*?)\]', line.strip())
        if section_match:
            current_section = section_match.group(1)
            
            # If this is the end of a section, add any missing labels
            if current_section in sections:
                for label, template_line in sections[current_section]:
                    if label in missing_labels:
                        # Add the missing label
                        updated_content.append(template_line)
                        print(f"Added missing label: {label}")
    
    return '\n'.join(updated_content)

def generate_comments_for_labels(model_name, content, labels_without_comments):
    """Generate _comments for labels that don't have them."""
    if not labels_without_comments:
        return content
    
    try:
        print(f"Generating comments for {len(labels_without_comments)} labels...")
        
        # Get powertrain type to provide appropriate context
        powertrain_type = get_powertrain_type(content)
        powertrain_context = ""
        if powertrain_type:
            powertrain_context = f"This is a {powertrain_type} vehicle. "
            if powertrain_type in ["Gasoline Engine", "Diesel Engine"]:
                powertrain_context += "This is a conventional combustion engine vehicle without electric propulsion."
            elif powertrain_type == "Battery Electric Vehicle":
                powertrain_context += "This is a pure electric vehicle without any combustion engine."
            else:
                powertrain_context += "This is a hybrid vehicle with both combustion and electric systems."
        
        # Extract existing content to provide context
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are an automotive expert with deep knowledge about car specifications. "
                               "Your task is to provide detailed comments and explanations for car model attributes."
                },
                {
                    "role": "user",
                    "content": f"I need detailed comments for the following attributes of the {model_name} car model.\n\n"
                               f"{powertrain_context}\n\n"
                               f"Here's the current specification content:\n\n{content}\n\n"
                               f"Please generate detailed _comments for each of these attributes:\n"
                               f"{', '.join(labels_without_comments)}\n\n"
                               f"For each attribute, provide a detailed and realistic comment that explains the value.\n"
                               f"IMPORTANT: Return ONLY the new _comments entries in TOML format, nothing else.\n"
                               f"Format each comment as: attribute_comments = \"Detailed explanation...\"\n"
                               f"Example: prize_comments = \"The actual price of the {model_name} starts at $56,900 for the base trim, rising to $82,500 for the top trim with all options.\"\n"
                               f"For attributes with value \"None\" (meaning not applicable to this powertrain type), "
                               f"explain why the attribute is not applicable.\n"
                               f"Example: fuel_consumption_comments = \"Not applicable for this battery electric vehicle as it does not use liquid fuel.\"\n"
                               f"Be specific, accurate, and provide real-world context for each value."
                }
            ],
            temperature=0.3,
            max_tokens=2048
        )
        
        generated_comments = response.choices[0].message.content.strip()
        
        # Clean up the response
        if "```toml" in generated_comments:
            generated_comments = re.sub(r'```toml\n', '', generated_comments)
            generated_comments = re.sub(r'```', '', generated_comments)
        
        # Add the comments to the content
        content_lines = content.strip().split('\n')
        labels_map = {}
        
        # Parse generated comments
        for line in generated_comments.strip().split('\n'):
            line = line.strip()
            if '=' in line:
                parts = line.split('=', 1)
                if len(parts) == 2:
                    label = parts[0].strip()
                    value = parts[1].strip()
                    if label.endswith("_comments") and re.match(r'^[a-zA-Z0-9_]+$', label):
                        base_label = label.replace("_comments", "")
                        labels_map[base_label] = line
        
        # Insert comments after their corresponding attributes
        result_lines = []
        for line in content_lines:
            result_lines.append(line)
            line = line.strip()
            if '=' in line:
                parts = line.split('=', 1)
                if len(parts) == 2:
                    label = parts[0].strip()
                    if label in labels_without_comments and label in labels_map:
                        comment_line = labels_map[label]
                        result_lines.append(comment_line)
                        print(f"Added comment for: {label}")
        
        return '\n'.join(result_lines)
        
    except Exception as e:
        print(f"Error generating comments: {e}")
        return content

def generate_model_info(model_name, template):
    """Generate detailed information for the car model using OpenAI API."""
    try:
        # Extract brand and model
        brand, model = model_name.split("-", 1)
        
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are an automotive expert with deep knowledge about car specifications. "
                               "You provide accurate, realistic, and detailed information about car models. "
                               "Always use factual data for real car models. Include specific values, not just ranges, "
                               "and add detailed comments for qualitative attributes."
                },
                {
                    "role": "user",
                    "content": f"Create a detailed specification file for the {model_name} car model. "
                               f"I need accurate and realistic specifications in TOML format.\n\n"
                               f"Here's the template to follow:\n\n{template}\n\n"
                               f"IMPORTANT INSTRUCTIONS:\n"
                               f"1. Replace the empty values with ACTUAL, FACTUAL specifications for {model_name}.\n"
                               f"2. For the car_model field, use \"{model_name}\".\n"
                               f"3. For the brand field, use \"{brand}\".\n"
                               f"4. Fill in ALL fields with appropriate values from the candidate values listed in the template.\n"
                               f"5. For EVERY attribute, add a corresponding _comments field with specific details.\n"
                               f"   Example: If cold_resistance = \"High\", add cold_resistance_comments = \"The car's cold-start performance is excellent, with proven reliability at -30°C.\"\n"
                               f"6. For range values (like trunk_volume), select the appropriate range AND add a comment with the exact value.\n"
                               f"   Example: If trunk_volume = \"400~500L\", add trunk_volume_comments = \"The exact trunk capacity is 482L, expandable to 1,502L with rear seats folded.\"\n"
                               f"7. ALWAYS use ACTUAL, FACTUAL data based on the real {model_name}.\n"
                               f"8. Include detailed comments for EVERY attribute, especially vehicle features and performance metrics.\n"
                               f"9. Use proper TOML syntax with quotes around string values.\n"
                               f"10. STRICTLY follow the template structure. DO NOT add any sections, explanations, or content that is not part of the template.\n"
                               f"11. IMPORTANT: EVERY attribute must have a corresponding _comments field that explains it in detail.\n"
                               f"12. CRITICAL INSTRUCTION ABOUT POWERTRAIN TYPE:\n"
                               f"    - If powertrain_type is \"Gasoline Engine\" or \"Diesel Engine\" (combustion), include ALL fields but set electric-only fields to \"None\": {', '.join(PURE_ELECTRIC_LABELS)}\n"
                               f"    - If powertrain_type is \"Battery Electric Vehicle\" (pure electric), include ALL fields but set combustion-only fields to \"None\": {', '.join(PURE_COMBUSTION_LABELS)}\n"
                               f"    - For hybrid vehicles, include ALL fields with appropriate values since both systems are present.\n"
                               f"    - For fields set to \"None\", still provide _comments explaining why they are not applicable."
                }
            ],
            temperature=0.2,  # Lower temperature for more factual responses
            max_tokens=4096
        )
        
        info_content = response.choices[0].message.content.strip()
        
        # Clean up the response - remove any markdown formatting if present
        info_content = re.sub(r'```toml\n', '', info_content)
        info_content = re.sub(r'```', '', info_content)
        
        # Clean and format the content to match the template structure
        cleaned_content = clean_toml_content(info_content, template)
        
        # Validate the content
        is_valid, missing_labels = validate_generated_content(cleaned_content, template)
        
        if not is_valid:
            print("Fixing missing labels...")
            cleaned_content = fix_missing_labels(cleaned_content, template, missing_labels)
            
            # Validate again after fixing
            is_valid, still_missing = validate_generated_content(cleaned_content, template)
            if not is_valid:
                print("Warning: Could not add all missing labels.")
        
        # Check for labels that don't have comments
        labels_without_comments = check_for_missing_comments(cleaned_content)
        
        if labels_without_comments:
            print(f"Found {len(labels_without_comments)} labels without comments.")
            cleaned_content = generate_comments_for_labels(model_name, cleaned_content, labels_without_comments)
        
        # Set inapplicable values to "None" based on powertrain type
        cleaned_content = set_inapplicable_values_to_none(cleaned_content)
        
        return cleaned_content
    
    except Exception as e:
        print(f"Error generating model information with OpenAI API: {e}")
        return None

def write_model_info(model_name, info_content):
    """Write the generated information to a TOML file."""
    brand = model_name.split("-")[0]
    brand_dir = os.path.join(os.getcwd(), brand)
    info_file = os.path.join(brand_dir, f"{model_name}.toml")
    
    try:
        with open(info_file, 'w') as f:
            f.write(info_content)
        print(f"Successfully created {info_file}")
        return True
    except Exception as e:
        print(f"Error writing information file: {e}")
        return False

def process_single_model(model_name, template, args):
    """Process a single model - generate and save info."""
    if args.skip_existing and check_info_file_exists(model_name):
        print(f"Skipping {model_name} - info file already exists.")
        return True
        
    print(f"Generating detailed information for {model_name}...")
    info_content = generate_model_info(model_name, template)
    
    if info_content:
        success = write_model_info(model_name, info_content)
        if success:
            print(f"Done! Information file for {model_name} created successfully.")
            return True
        else:
            print(f"Failed to write information file for {model_name}.")
            return False
    else:
        print(f"Failed to generate model information for {model_name}.")
        return False

def main():
    """Main function to run the script."""
    args = parse_arguments()
    
    template = read_template()
    if not template:
        return
    
    if args.model_name:
        # Process a single model
        if not validate_model_name(args.model_name):
            return
        
        if not check_model_exists(args.model_name):
            user_input = input(f"Model '{args.model_name}' not found in model list. Continue anyway? (y/n): ")
            if user_input.lower() != 'y':
                return
        
        process_single_model(args.model_name, template, args)
    
    elif args.brand_name:
        # Process all models for a brand
        if not validate_brand_name(args.brand_name):
            return
        
        models = get_models_for_brand(args.brand_name)
        if not models:
            return
        
        print(f"Will generate info files for {len(models)} models of {args.brand_name}.")
        
        success_count = 0
        fail_count = 0
        skip_count = 0
        
        for i, model in enumerate(models):
            print(f"\nProcessing model {i+1} of {len(models)}: {model}")
            
            if args.skip_existing and check_info_file_exists(model):
                print(f"Skipping {model} - info file already exists.")
                skip_count += 1
                continue
            
            if process_single_model(model, template, args):
                success_count += 1
            else:
                fail_count += 1
            
            # Add delay between API calls to avoid rate limiting
            if i < len(models) - 1:  # Don't delay after the last model
                print(f"Waiting {args.delay} seconds before processing next model...")
                time.sleep(args.delay)
        
        print(f"\nSummary for {args.brand_name}:")
        print(f"Total models: {len(models)}")
        print(f"Successfully processed: {success_count}")
        print(f"Failed: {fail_count}")
        print(f"Skipped (already exist): {skip_count}")

if __name__ == "__main__":
    main() 