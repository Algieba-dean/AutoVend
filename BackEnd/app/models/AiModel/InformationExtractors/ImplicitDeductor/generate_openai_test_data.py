#!/usr/bin/env python3

import os
import json
import argparse
import time
from typing import List, Dict, Any
import openai
from tqdm import tqdm

def parse_args():
    parser = argparse.ArgumentParser(description='Generate vehicle query test data using OpenAI API')
    parser.add_argument('--api_key', type=str, help='OpenAI API key (or set OPENAI_API_KEY env var)')
    parser.add_argument('--model', type=str, default='deepseek-chat', help='OpenAI model to use')
    parser.add_argument('--output', type=str, default='generated_dataset.json', help='Output file path')
    parser.add_argument('--samples', type=int, default=20, help='Number of samples to generate')
    parser.add_argument('--example_file', type=str, default='example_dataset.json', help='Example dataset file')
    parser.add_argument('--label_config', type=str, default='QueryLabels.json', help='Label configuration file')
    parser.add_argument('--batch_size', type=int, default=5, help='Number of samples to generate per API call')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    parser.add_argument('--api_url', type=str, help='OpenAI API base URL (or set OPENAI_URL env var)')
    parser.add_argument('--max_concurrency', type=int, default=1, help='Maximum number of concurrent API calls')
    return parser.parse_args()

def load_example_data(file_path: str) -> Dict[str, Any]:
    """Load example dataset to use as reference"""
    print(f"Loading example data from {file_path}...")
    with open(file_path, 'r') as f:
        data = json.load(f)
    print(f"Loaded {len(data.get('samples', []))} example samples")
    return data

def load_label_config(file_path: str) -> Dict[str, Any]:
    """Load label configuration"""
    print(f"Loading label configuration from {file_path}...")
    with open(file_path, 'r') as f:
        config = json.load(f)
    
    # Count implicit labels
    implicit_count = sum(1 for label_info in config.values() 
                         if label_info.get("implicit_support", False))
    print(f"Found {implicit_count} implicit labels out of {len(config)} total labels")
    return config

def generate_expression_examples() -> Dict[str, List[Dict[str, str]]]:
    """Generate examples of indirect expressions for each label value"""
    
    # Format: label_name -> list of {value: expression} pairs
    expression_examples = {
        "prize_alias": [
            {"value": "cheap", "expressions": [
                "I'm on a tight budget",
                "I can't afford anything expensive",
                "I'm looking for something economical",
                "Money is a big concern for me",
                "I need the most affordable option available"
            ]},
            {"value": "economy", "expressions": [
                "I want a good value for my money",
                "I'm willing to spend a bit more for quality, but nothing fancy",
                "I'm budget-conscious but can afford something reliable",
                "I need something practical without breaking the bank",
                "I'm interested in a basic model with essential features"
            ]},
            {"value": "mid-range", "expressions": [
                "I can afford something decent, but not luxurious",
                "I'm looking for a balance between quality and cost",
                "I have a moderate budget for this purchase",
                "I want something nice but not extravagant",
                "I'm willing to pay for extra features, but within reason"
            ]},
            {"value": "high-end", "expressions": [
                "I want a premium vehicle with advanced features",
                "I'm willing to invest in quality and performance",
                "I prefer high-quality materials and craftsmanship",
                "I'm looking for something upscale with cutting-edge technology",
                "I expect top-tier performance and comfort"
            ]},
            {"value": "luxury", "expressions": [
                "I want the absolute best, regardless of price",
                "I'm looking for a prestigious brand with exceptional quality",
                "Money is no object for this purchase",
                "I expect the finest materials and craftsmanship available",
                "I want all the luxury amenities and exclusive features"
            ]}
        ],
        "passenger_space_volume_alias": [
            {"value": "small", "expressions": [
                "It's just me commuting most of the time",
                "I rarely have passengers in my car",
                "I prefer a cozy interior",
                "I don't need much passenger space",
                "I usually drive alone or with one other person"
            ]},
            {"value": "medium", "expressions": [
                "I sometimes have a few friends riding with me",
                "I need enough space for 3-4 people to be comfortable",
                "I'd like reasonable space for passengers",
                "I occasionally take my family on trips",
                "I need a balance between compact size and adequate seating"
            ]},
            {"value": "large", "expressions": [
                "I need to fit my whole family comfortably",
                "I often drive with multiple passengers",
                "I want everyone to have plenty of legroom",
                "I need spacious seating for adults in all rows",
                "I frequently travel with groups of people"
            ]},
            {"value": "luxury", "expressions": [
                "I want extremely generous space for all passengers",
                "I need executive-level comfort for everyone in the vehicle",
                "I expect everyone to stretch out comfortably, even on long trips",
                "I want limousine-like space in the back seats",
                "I need exceptional roominess for VIP passengers"
            ]}
        ],
        "trunk_volume_alias": [
            {"value": "small", "expressions": [
                "I just need space for a few grocery bags",
                "I rarely carry much luggage",
                "I don't need much cargo space",
                "I only need room for my gym bag and laptop",
                "I travel light and don't need much storage"
            ]},
            {"value": "medium", "expressions": [
                "I need room for luggage for weekend trips",
                "I want adequate space for shopping bags and sports equipment",
                "I occasionally need to transport medium-sized items",
                "I need space for a stroller and some shopping bags",
                "I want enough trunk space for a family grocery run"
            ]},
            {"value": "large", "expressions": [
                "I need to fit multiple suitcases for family trips",
                "I frequently transport bulky items",
                "I need space for my sports gear and equipment",
                "I want room for camping equipment for the whole family",
                "I need to carry lots of supplies for my work"
            ]},
            {"value": "luxury", "expressions": [
                "I need an exceptionally spacious cargo area",
                "I want to transport large items without folding seats",
                "I need to fit multiple golf bags plus luggage",
                "I want maximum storage capacity for long road trips",
                "I need extensive cargo space for professional equipment"
            ]}
        ],
        "chassis_height_alias": [
            {"value": "low ride height", "expressions": [
                "I enjoy a sporty driving feel",
                "I prefer cars that hug the road",
                "I want something that handles like a sports car",
                "I like vehicles that are low to the ground",
                "I want excellent cornering and stability at high speeds"
            ]},
            {"value": "medium ride height", "expressions": [
                "I want a balance between sporty driving and practical entry/exit",
                "I like being able to see the road better than in a sedan",
                "I want something that's not too low or too high",
                "I prefer a moderate height for ease of getting in and out",
                "I want decent ground clearance for occasional rough roads"
            ]},
            {"value": "high ride height", "expressions": [
                "I often drive on rough or uneven roads",
                "I want a commanding view of the road",
                "I need to navigate through occasional flooding",
                "I live in an area with deep snow in winter",
                "I want to easily see over traffic"
            ]},
            {"value": "off-road chassis", "expressions": [
                "I frequently drive on unpaved mountain trails",
                "I need to traverse extremely rough terrain",
                "I go camping in remote areas with no roads",
                "I cross streams and rocky paths in my adventures",
                "I need maximum ground clearance for serious off-roading"
            ]}
        ],
        "abs": [
            {"value": "yes", "expressions": [
                "Safety is my top priority when driving",
                "I want all modern safety features",
                "I need reliable braking in all conditions",
                "I drive in areas with frequent rain or snow",
                "I want the vehicle to have emergency braking support"
            ]}
        ],
        "voice_interaction": [
            {"value": "yes", "expressions": [
                "I want to control features without taking my hands off the wheel",
                "I'd like to use voice commands while driving",
                "I need to make calls and send texts hands-free",
                "I want to be able to ask for directions without typing",
                "I like being able to control the music with my voice"
            ]}
        ],
        "remote_parking": [
            {"value": "yes", "expressions": [
                "I'm really bad at parking in tight spaces",
                "I struggle with parallel parking",
                "I want to be able to park my car from outside the vehicle",
                "I need help fitting into small garage spaces",
                "I'd like to park my car without being inside it"
            ]}
        ],
        "auto_parking": [
            {"value": "yes", "expressions": [
                "I find parking stressful and difficult",
                "I'm not confident in my parking abilities",
                "I want the car to park itself with minimal input from me",
                "I need assistance with parallel and perpendicular parking",
                "I want technology that helps me park perfectly every time"
            ]}
        ],
        "battery_capacity_alias": [
            {"value": "small", "expressions": [
                "I only drive short distances around town",
                "I just need enough range for my daily commute",
                "I'm always near charging stations",
                "I don't need much electric range",
                "I only use my car for quick local errands"
            ]},
            {"value": "medium", "expressions": [
                "I need enough range for my weekly activities without charging daily",
                "I commute a moderate distance to work each day",
                "I want to make a few day trips without recharging",
                "I need decent range but don't go on long road trips",
                "I want to go a few days between charges"
            ]},
            {"value": "large", "expressions": [
                "I frequently take longer trips",
                "I need extensive range for my lifestyle",
                "I don't want to worry about charging on weekend getaways",
                "I need to drive several hundred miles between charges",
                "I want maximum electric range for convenience"
            ]},
            {"value": "extra-large", "expressions": [
                "I take regular long-distance road trips",
                "I need exceptional range for extended journeys",
                "I travel between cities regularly without stopping",
                "I want to minimize charging stops on interstate travel",
                "I need the maximum possible range from an electric vehicle"
            ]}
        ],
        "fuel_tank_capacity_alias": [
            {"value": "small", "expressions": [
                "I just drive around the city",
                "I prefer stopping for gas more often with a lighter car",
                "I don't mind refueling frequently",
                "I only use my car for short trips",
                "I rarely drive long distances"
            ]},
            {"value": "medium", "expressions": [
                "I like a good balance between weight and range",
                "I want to refuel about once a week",
                "I take occasional road trips but nothing extreme",
                "I commute a moderate distance daily",
                "I need decent range without excessive weight"
            ]},
            {"value": "large", "expressions": [
                "I hate stopping for gas on long trips",
                "I travel long distances regularly",
                "I want maximum driving range between fill-ups",
                "I live in a remote area far from gas stations",
                "I need to cover vast distances without refueling"
            ]}
        ],
        "fuel_consumption_alias": [
            {"value": "low", "expressions": [
                "I'm concerned about gas prices",
                "I want to minimize my fuel expenses",
                "I care about efficiency and low running costs",
                "I need excellent miles per gallon",
                "I want to spend as little as possible on fuel"
            ]},
            {"value": "medium", "expressions": [
                "I want reasonable fuel efficiency but also good performance",
                "I'm fine with average fuel consumption",
                "I need a balance between power and economy",
                "I accept moderate fuel costs for better driving experience",
                "I'm looking for decent but not exceptional fuel economy"
            ]},
            {"value": "high", "expressions": [
                "I prioritize performance over fuel efficiency",
                "I'm willing to pay more for gas to get more power",
                "I don't mind higher fuel costs for a better driving experience",
                "I want significant horsepower and acceleration",
                "Fuel economy is not my main concern"
            ]}
        ],
        "electric_consumption_alias": [
            {"value": "low", "expressions": [
                "I want to maximize my range per charge",
                "I care about electrical efficiency",
                "I want to minimize my electricity costs",
                "I need to get the most miles from each kilowatt-hour",
                "I'm looking for the most efficient electric vehicle possible"
            ]},
            {"value": "medium", "expressions": [
                "I want a good balance of performance and efficiency",
                "I'm fine with average electricity consumption",
                "I need reasonable range with decent performance",
                "I want normal energy usage for an electric vehicle",
                "I'm looking for standard consumption rates"
            ]},
            {"value": "high", "expressions": [
                "I prioritize performance over efficiency in my electric vehicle",
                "I want maximum acceleration and don't mind charging more often",
                "I'm willing to use more electricity for better performance",
                "I want a high-performance electric vehicle",
                "Range efficiency is less important than power to me"
            ]}
        ],
        "cold_resistance": [
            {"value": "low", "expressions": [
                "I live in a warm climate year-round",
                "I never drive in freezing temperatures",
                "I'm in southern California where it's always warm",
                "Winter doesn't exist where I live",
                "I only drive in temperate or hot regions"
            ]},
            {"value": "medium", "expressions": [
                "We get some cold weather in winter but nothing extreme",
                "I occasionally drive in light snow",
                "I experience mild winters in my region",
                "We get a few freezing days each year",
                "I sometimes travel to areas with colder weather"
            ]},
            {"value": "high", "expressions": [
                "I live in Norway where winters are extremely cold",
                "I drive in heavy snow and ice regularly",
                "I need a vehicle that starts reliably at -20°F",
                "I live in northern Canada with harsh winters",
                "I frequently drive in mountain areas with sub-zero temperatures"
            ]}
        ],
        "heat_resistance": [
            {"value": "low", "expressions": [
                "I live in a cool climate year-round",
                "I never experience extremely hot weather",
                "I'm in northern regions where heat isn't an issue",
                "Summer temperatures are always mild where I live",
                "I don't drive in hot climates"
            ]},
            {"value": "medium", "expressions": [
                "We get warm summers but nothing extreme",
                "I occasionally drive in hot weather",
                "I experience moderate summers in my region",
                "We get a few very hot days each year",
                "I sometimes travel to warmer areas"
            ]},
            {"value": "high", "expressions": [
                "I live in Arizona where it frequently exceeds 110°F",
                "I drive in extreme desert heat regularly",
                "I need a vehicle that performs well in scorching temperatures",
                "I live in the Middle East with intense heat year-round",
                "I frequently drive through Death Valley and similar hot regions"
            ]}
        ],
        "size": [
            {"value": "small", "expressions": [
                "I need something compact for city parking",
                "I prefer nimble cars that are easy to maneuver",
                "I want something that fits in tight spaces",
                "I navigate narrow streets and small parking spots daily",
                "I prefer a vehicle with a small footprint"
            ]},
            {"value": "medium", "expressions": [
                "I need something versatile for various situations",
                "I want a balance between space and maneuverability",
                "I'm looking for a standard-sized vehicle",
                "I need enough room without being too large",
                "I want something neither too big nor too small"
            ]},
            {"value": "large", "expressions": [
                "I need maximum interior space for people and cargo",
                "I want a substantial, imposing vehicle",
                "I'm looking for something with plenty of room",
                "I have a big family that needs lots of space",
                "I want a vehicle with significant presence on the road"
            ]}
        ],
        "vehicle_usability": [
            {"value": "low", "expressions": [
                "I want a weekend car for occasional fun drives",
                "I'm looking for something focused on performance over practicality",
                "I already have a practical car; this one is for enjoyment",
                "I don't need this vehicle for everyday tasks",
                "I want something special that isn't necessarily convenient"
            ]},
            {"value": "medium", "expressions": [
                "I need something reasonably practical for regular use",
                "I want a car that works for most of my needs",
                "I'm looking for decent utility without sacrificing style",
                "I need a vehicle that's versatile but still enjoyable",
                "I want something that balances usability with other factors"
            ]},
            {"value": "high", "expressions": [
                "I need maximum versatility for all life situations",
                "I want something that can handle anything I throw at it",
                "I'm looking for a do-everything vehicle with no compromises on utility",
                "I need a car that adapts to all my lifestyle needs",
                "I want supreme practicality and convenience"
            ]}
        ],
        "aesthetics": [
            {"value": "low", "expressions": [
                "I don't care much about how the car looks",
                "Functionality is far more important than style to me",
                "I'm not concerned with appearance, just performance",
                "I'm very practical and don't need a fancy-looking vehicle",
                "How the car functions matters much more than its style"
            ]},
            {"value": "medium", "expressions": [
                "I want something that looks decent but isn't flashy",
                "I appreciate good design but it's not my top priority",
                "I want a car with contemporary styling but nothing extreme",
                "I like vehicles that have some style without being ostentatious",
                "I want something presentable but not attention-grabbing"
            ]},
            {"value": "high", "expressions": [
                "I want a car that turns heads",
                "The vehicle's appearance is extremely important to me",
                "I'm looking for something with striking, beautiful design",
                "I want a car that expresses my personal style",
                "I appreciate exceptional automotive design and aesthetics"
            ]}
        ],
        "energy_consumption_level": [
            {"value": "low", "expressions": [
                "I'm very concerned about my carbon footprint",
                "I want to minimize my environmental impact",
                "Fuel efficiency is my absolute top priority",
                "I need to keep my energy costs as low as possible",
                "I want the most economical option available"
            ]},
            {"value": "medium", "expressions": [
                "I want reasonable efficiency but not at the expense of performance",
                "I'm looking for a good balance of economy and capability",
                "I care about fuel costs but also want adequate power",
                "I want something more efficient than average but still practical",
                "I need decent energy efficiency for daily driving"
            ]},
            {"value": "high", "expressions": [
                "I prioritize performance over efficiency",
                "I'm willing to pay more for fuel to get the driving experience I want",
                "I'm looking for powerful acceleration and high-speed capability",
                "I want a high-performance vehicle even if it uses more energy",
                "I'm interested in maximum power and don't mind the fuel costs"
            ]}
        ],
        "comfort_level": [
            {"value": "low", "expressions": [
                "I care more about performance than comfort",
                "I'm fine with a firmer ride for better handling",
                "I want a car that feels connected to the road, even if it's less comfortable",
                "I prefer driving engagement over plush comfort",
                "I don't mind a stiffer suspension for better responsiveness"
            ]},
            {"value": "medium", "expressions": [
                "I want a good balance between comfort and handling",
                "I need reasonable comfort for daily driving",
                "I prefer not to feel every bump but still want good control",
                "I want decent ride quality without excessive softness",
                "I'm looking for a comfortable ride that still feels responsive"
            ]},
            {"value": "high", "expressions": [
                "I want to feel like I'm floating on a cloud",
                "I need exceptional comfort for long drives",
                "I want luxury-level suspension and seat comfort",
                "Ride quality is extremely important to me",
                "I prefer a soft, smooth ride that isolates me from road imperfections"
            ]}
        ],
        "smartness": [
            {"value": "low", "expressions": [
                "I prefer simple cars without complicated technology",
                "I don't need fancy gadgets and screens",
                "I like basic, straightforward vehicles",
                "I want minimal electronics and simple controls",
                "I prefer traditional automotive design without high-tech features"
            ]},
            {"value": "medium", "expressions": [
                "I want modern features but nothing too complicated",
                "I appreciate useful technology that's intuitive",
                "I need standard connectivity and assistance features",
                "I want a car with current technology but not bleeding-edge",
                "I like having convenient tech features that are easy to use"
            ]},
            {"value": "high", "expressions": [
                "I want all the latest technological innovations",
                "I love cutting-edge automotive technology",
                "I need advanced driver assistance and connectivity",
                "I want a car that integrates with my digital lifestyle",
                "I'm interested in the most advanced features available in modern vehicles"
            ]}
        ],
        "family_friendliness": [
            {"value": "low", "expressions": [
                "It's just me, I don't have kids or family to drive around",
                "I rarely transport children",
                "I'm single and don't need family-oriented features",
                "I don't need child seats or family storage",
                "I'm looking for something for just myself or another adult"
            ]},
            {"value": "medium", "expressions": [
                "I occasionally need to transport friends or family",
                "I have a small family with one child",
                "I sometimes drive my nieces and nephews around",
                "I need room for a car seat occasionally",
                "I want something suitable for occasional family use"
            ]},
            {"value": "high", "expressions": [
                "I have a big family with multiple children",
                "I need to accommodate car seats and strollers easily",
                "I transport my kids and their friends regularly",
                "I want ample space and safety features for my children",
                "Family transportation is my vehicle's primary purpose"
            ]}
        ],
        "city_commuting": [
            {"value": "yes", "expressions": [
                "I drive mostly in urban areas with traffic",
                "I need something easy to park downtown",
                "I navigate through narrow city streets daily",
                "My commute involves a lot of stop-and-go traffic",
                "I primarily use my car for getting around the city"
            ]}
        ],
        "highway_long_distance": [
            {"value": "yes", "expressions": [
                "I regularly take road trips across the country",
                "I commute long distances on the interstate",
                "I frequently drive hundreds of miles at a time",
                "I spend hours on the highway each week",
                "I need something comfortable for extended highway driving"
            ]}
        ],
        "cargo_capability": [
            {"value": "yes", "expressions": [
                "I need to transport bulky items regularly",
                "I carry a lot of equipment for my hobbies",
                "I frequently haul supplies for home projects",
                "I need space for my outdoor gear and equipment",
                "I want to be able to move furniture and large items"
            ]}
        ]
    }
    
    return expression_examples

def generate_system_prompt(label_config: Dict[str, Any]) -> str:
    """Create system prompt with label configuration information"""
    print("Generating enhanced system prompt with label configuration...")
    
    # Extract all implicit_support=true labels and their candidates
    implicit_labels = {}
    for label_name, label_info in label_config.items():
        if label_info.get("implicit_support", False):
            implicit_labels[label_name] = {
                "candidates": label_info["candidates"],
                "description": label_info.get("description", "")
            }
    
    # Get expression examples
    expression_examples = generate_expression_examples()
    
    # Create the system prompt
    prompt = "You are an AI assistant that generates realistic vehicle purchase queries and their corresponding labels.\n\n"
    prompt += "IMPORTANT GUIDELINES:\n"
    prompt += "1. All queries MUST be in English and relate to car/vehicle purchases.\n"
    prompt += "2. Queries should NEVER directly mention the label names but instead use indirect expressions.\n"
    prompt += "3. A label should ONLY be activated (non-none value) when the query STRONGLY implies that specific attribute.\n"
    prompt += "4. All label values MUST come ONLY from the provided candidates list (or 'none').\n"
    prompt += "5. Generated queries should be diverse and realistic, as if coming from actual car buyers.\n\n"
    prompt += r"6. Short dialog should be more 70% should be fine, The proportion of complex sentences can be a little lower 30% should be enough.\n\n"
    prompt += "7. Please generate more samples for only one label activation, such as highway_long_distance, family_friendliness, smartness, energy_consumption_level, cold_resistance, heat_resistance,auto_parking ,remote_parking ,voice_interaction ,chassis_height_alias, passenger_space_volume_alias \n\n"
    prompt += "8. based on point 7, every label should have an almost same number of samples \n\n"
    
    prompt += "The available implicit labels, their descriptions, and possible values are:\n\n"
    
    # Add each label with its description, values, and expression examples
    for label_name, info in implicit_labels.items():
        prompt += f"## {label_name}: {info['description']}\n"
        prompt += f"Possible values: {', '.join(info['candidates'])} or 'none'\n"
        
        # Add expression examples if available
        if label_name in expression_examples:
            prompt += "Example expressions:\n"
            for value_example in expression_examples[label_name]:
                value = value_example["value"]
                expressions = value_example["expressions"]
                prompt += f"- For value '{value}':\n"
                for expr in expressions[:3]:  # Limit to 3 examples per value
                    prompt += f"  * \"{expr}\"\n"
            
        prompt += "\n"
    
    # Add specific guidance for generating queries
    prompt += "INDIRECT EXPRESSION GUIDANCE:\n\n"
    
    prompt += "1. Location/Climate implications:\n"
    prompt += "   - \"I live in Norway\" → cold_resistance: high\n"
    prompt += "   - \"I'm in Arizona\" → heat_resistance: high\n\n"
    
    prompt += "2. Travel pattern implications:\n"
    prompt += "   - \"I always go far away\" → highway_long_distance: yes, fuel_tank_capacity_alias: large\n"
    prompt += "   - \"I drive mostly in the city\" → city_commuting: yes\n\n"
    
    prompt += "3. Economic implications:\n"
    prompt += "   - \"Gas prices are too high these days\" → energy_consumption_level: low, fuel_consumption_alias: low\n"
    prompt += "   - \"I don't mind spending extra on premium features\" → prize_alias: high-end or luxury\n\n"
    
    prompt += "4. Skill/Habit implications:\n"
    prompt += "   - \"I'm really bad at parking\" → auto_parking: yes, remote_parking: yes\n"
    prompt += "   - \"I drive on mountain roads frequently\" → chassis_height_alias: high ride height\n\n"
    
    prompt += "5. Lifestyle implications:\n"
    prompt += "   - \"I have a big family with four kids\" → family_friendliness: high, size: large, passenger_space_volume_alias: large\n"
    prompt += "   - \"I need to transport my music equipment regularly\" → cargo_capability: yes, trunk_volume_alias: large\n\n"
    
    print(f"Enhanced system prompt created with {len(implicit_labels)} implicit labels and detailed expression guidance")
    return prompt

def generate_user_prompt(example_data: Dict[str, Any], num_samples: int) -> str:
    """Create user prompt with examples and instructions"""
    print("Generating enhanced user prompt with examples and instructions...")
    # Get a few examples from the example data
    examples = example_data["samples"][:3]
    
    prompt = f"Please generate {num_samples} new vehicle purchase queries with their corresponding implicit labels.\n\n"
    prompt += "CRITICAL REQUIREMENTS:\n"
    prompt += "1. Queries must be in English and related to vehicle purchases\n"
    prompt += "2. Never directly mention label names in the queries\n"
    prompt += "3. Only set a label value when the query strongly implies that attribute\n"
    prompt += "4. Use only the allowed values for each label or 'none'\n"
    prompt += "5. Make queries natural and realistic\n\n"
    
    prompt += "Use these examples as reference format:\n\n"
    
    for example in examples:
        prompt += f"Query: \"{example['query']}\"\n"
        prompt += "Labels:\n"
        for label, value in example['labels'].items():
            prompt += f"  - {label}: {value}\n"
        prompt += "\n"
    
    prompt += "Here are some good examples of indirect expressions:\n\n"
    
    prompt += "Query: \"I live in northern Alaska and need something reliable in extreme temperatures.\"\n"
    prompt += "This implies: cold_resistance: high (but doesn't directly mention the label)\n\n"
    
    prompt += "Query: \"I'm looking for a car that can handle my weekly trips between cities without frequent refueling.\"\n"
    prompt += "This implies: highway_long_distance: yes, fuel_tank_capacity_alias: large\n\n"
    
    prompt += "Query: \"I'm terrible at parallel parking and need something that can help me squeeze into tight spots.\"\n"
    prompt += "This implies: auto_parking: yes, remote_parking: yes\n\n"
    
    prompt += f"Now, generate {num_samples} unique vehicle purchase queries with appropriate labels. Each query should imply several label values but in a natural, conversational way that a real car buyer might use.\n\n"
    prompt += "Return the result as a JSON array of objects, where each object has 'query' and 'labels' fields. The 'labels' field should be an object containing all the relevant labels with their values (use 'none' when not applicable)."
    
    return prompt

def call_openai_api(api_key: str, model: str, system_prompt: str, user_prompt: str, api_url: str = None, verbose: bool = False) -> List[Dict[str, Any]]:
    """Call OpenAI API to generate the test data"""
    # Use specified API key, URL and model, or get from environment with defaults
    OPENAI_API_KEY = api_key or os.getenv("OPENAI_API_KEY", "sk-40f9ea6f41bd4cbbae8a9d4adb07fbf8")
    OPENAI_MODEL = model or os.getenv("OPENAI_MODEL", "deepseek-chat")
    OPENAI_URL = api_url or os.getenv("OPENAI_URL", "https://api.deepseek.com/v1")
    
    # Initialize client with base_url
    client = openai.OpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_URL,
    )
    
    print(f"Calling API using model: {OPENAI_MODEL}")
    start_time = time.time()
    
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.8,
            max_tokens=4000,
            response_format={"type": "json_object"}
        )
        
        elapsed = time.time() - start_time
        print(f"API call completed in {elapsed:.2f} seconds")
        
        # Extract and parse the JSON response
        content = response.choices[0].message.content
        
        if verbose:
            print("Raw API response:")
            print(content[:500] + "..." if len(content) > 500 else content)
        
        try:
            generated_data = json.loads(content)
            
            # Validate the response format
            if "samples" in generated_data:
                print(f"Received {len(generated_data['samples'])} samples in expected format")
                return generated_data["samples"]
            elif isinstance(generated_data, list):
                print(f"Received {len(generated_data)} samples in list format")
                return generated_data
            elif "query" in generated_data and "labels" in generated_data:
                # Single sample
                print("Received a single sample")
                return [generated_data]
            else:
                # Try to extract samples from other possible formats
                possible_samples = []
                for key, value in generated_data.items():
                    if isinstance(value, dict) and "query" in value and "labels" in value:
                        possible_samples.append(value)
                
                if possible_samples:
                    print(f"Extracted {len(possible_samples)} samples from alternative format")
                    return possible_samples
                else:
                    print("Warning: Unexpected response format. Using as is.")
                    return [generated_data]
        
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            print("Response was not valid JSON. First 100 characters:")
            print(content[:100])
            return []
            
    except Exception as e:
        print(f"API call failed: {e}")
        return []

def validate_sample(sample: Dict[str, Any], label_config: Dict[str, Any]) -> bool:
    """Validate that a sample has the correct format and values"""
    # Check required fields
    if "query" not in sample or "labels" not in sample:
        print(f"Missing required fields in sample: {sample}")
        return False
    
    # Check that query is not empty and is in English
    query = sample["query"].strip()
    if not query:
        print("Empty query found")
        return False
    
    # Simple check for English language (could be improved)
    english_words = ["i", "the", "a", "an", "and", "or", "in", "with", "need", "want"]
    if not any(word in query.lower() for word in english_words):
        print(f"Query may not be in English: {query}")
        return False
    
    # Check that labels is a dictionary
    labels = sample["labels"]
    if not isinstance(labels, dict):
        print(f"Labels is not a dictionary: {labels}")
        return False
    
    # Check that each label has a valid value
    invalid_values = False
    for label_name, label_value in labels.items():
        if label_name not in label_config:
            print(f"Unknown label: {label_name}")
            invalid_values = True
            continue
            
        # Check if value is valid
        if label_value != "none" and label_value not in label_config[label_name]["candidates"]:
            print(f"Invalid value '{label_value}' for label '{label_name}', expected one of: {label_config[label_name]['candidates']} or 'none'")
            invalid_values = True
    
    return not invalid_values

def save_dataset(samples: List[Dict[str, Any]], output_path: str):
    """Save the generated dataset to a JSON file"""
    dataset = {"samples": samples}
    
    with open(output_path, 'w') as f:
        json.dump(dataset, f, indent=4)
    
    print(f"Generated {len(samples)} samples and saved to {output_path}")
    # Print file size
    file_size = os.path.getsize(output_path) / 1024  # KB
    print(f"File size: {file_size:.2f} KB")

def load_existing_dataset(output_path: str) -> List[Dict[str, Any]]:
    """Load existing dataset if it exists"""
    if not os.path.exists(output_path):
        return []
    
    try:
        with open(output_path, 'r') as f:
            dataset = json.load(f)
            if "samples" in dataset and isinstance(dataset["samples"], list):
                samples = dataset["samples"]
                print(f"Loaded {len(samples)} existing samples from {output_path}")
                return samples
            else:
                print(f"Warning: Invalid format in {output_path}, not using existing samples")
                return []
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading existing dataset: {e}")
        return []

def append_sample(sample: Dict[str, Any], all_samples: List[Dict[str, Any]], output_path: str):
    """Append a single sample to the dataset and save immediately"""
    all_samples.append(sample)
    
    # Save entire dataset immediately
    dataset = {"samples": all_samples}
    
    # Use safe writing pattern to avoid potential corruption
    temp_path = output_path + ".tmp"
    with open(temp_path, 'w') as f:
        json.dump(dataset, f, indent=4)
    
    # Atomic rename is more reliable than overwriting
    if os.path.exists(output_path):
        os.replace(temp_path, output_path)
    else:
        os.rename(temp_path, output_path)
    
    return len(all_samples)

def main():
    args = parse_args()
    
    # Get API key from args or environment variable
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    api_url = args.api_url or os.environ.get("OPENAI_URL")
    
    # Load example data and label config
    example_data = load_example_data(args.example_file)
    label_config = load_label_config(args.label_config)
    
    # Load existing dataset for incremental update
    all_samples = load_existing_dataset(args.output)
    initial_sample_count = len(all_samples)
    
    # Create prompts
    system_prompt = generate_system_prompt(label_config)
    
    # Calculate number of remaining samples to generate
    total_samples = args.samples
    remaining_samples = max(0, total_samples - initial_sample_count)
    
    if remaining_samples == 0:
        print(f"Already have {initial_sample_count} samples, which meets or exceeds the target of {total_samples}.")
        print("No new samples will be generated. Use a higher --samples value to generate more.")
        return
    
    print(f"Already have {initial_sample_count} samples. Will generate {remaining_samples} more to reach target of {total_samples}.")
    
    batch_size = min(args.batch_size, remaining_samples)  # Don't exceed remaining samples
    num_batches = (remaining_samples + batch_size - 1) // batch_size  # Ceiling division
    
    print(f"Generating {remaining_samples} samples in {num_batches} batch(es) of up to {batch_size}")
    
    # Create progress bar for overall progress
    progress_bar = tqdm(total=remaining_samples, desc="Generating samples")
    
    # Generate samples in batches
    for i in range(num_batches):
        # For the last batch, adjust batch size if needed
        current_batch_size = min(batch_size, total_samples - len(all_samples))
        
        user_prompt = generate_user_prompt(example_data, current_batch_size)
        batch_samples = call_openai_api(api_key, args.model, system_prompt, user_prompt, api_url, args.verbose)
        
        # Process each sample one by one
        valid_count = 0
        for sample in batch_samples:
            if validate_sample(sample, label_config):
                # Immediately append and save each valid sample
                current_count = append_sample(sample, all_samples, args.output)
                valid_count += 1
                progress_bar.update(1)
                
                # If we've reached our target, stop
                if current_count >= total_samples:
                    break
            else:
                print(f"Skipping invalid sample: {sample}")
        
        print(f"Batch {i+1}/{num_batches} complete. Added {valid_count} valid samples. Total samples so far: {len(all_samples)}/{total_samples}")
        
        # If we've reached our target, stop
        if len(all_samples) >= total_samples:
            break
        
        # Small delay between batches to avoid rate limits
        if i < num_batches - 1:
            time.sleep(1)
    
    progress_bar.close()
    
    # Final count
    samples_generated = len(all_samples) - initial_sample_count
    print(f"Generation complete. Added {samples_generated} new samples to reach {len(all_samples)} total samples.")
    print(f"All samples saved to {args.output}")
    
    # Print file size
    file_size = os.path.getsize(args.output) / 1024  # KB
    print(f"Final file size: {file_size:.2f} KB")
    
    print("Done!")

if __name__ == "__main__":
    main() 