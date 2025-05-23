import os
import sys
import json
from .implicit_deductor import ImplicitDeductor, run_test
from .implicit_deductor import (
    test_prize_alias, test_passenger_space_volume_alias, test_trunk_volume_alias,
    test_chassis_height_alias, test_abs, test_voice_interaction, test_remote_parking,
    test_auto_parking, test_battery_capacity_alias, test_fuel_tank_capacity_alias,
    test_fuel_consumption_alias, test_electric_consumption_alias, test_cold_resistance,
    test_heat_resistance, test_size, test_vehicle_usability, test_aesthetics,
    test_energy_consumption_level, test_comfort_level, test_smartness,
    test_family_friendliness, test_city_commuting, test_highway_long_distance,
    test_cargo_capability, test_multiple_labels, test_synonyms_expressions,
    test_casual_conversation
)

def mock_config_files():
    """Create mock configuration files for testing"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create Config directory if it doesn't exist
    config_dir = os.path.join(os.path.dirname(os.path.dirname(current_dir)), "Config")
    os.makedirs(config_dir, exist_ok=True)

    # Mock QueryLabels.json for testing
    query_labels = {
        "prize_alias": {
            "candidates": ["cheap", "economy", "mid-range", "high-end", "luxury"],
            "priority": 1,
            "value_type": "fuzzy",
            "implicit_support": True,
            "deduct_from_value": False,
            "description": "the prize of a vehicle model, but in level way instead of a range"
        },
        "passenger_space_volume_alias": {
            "candidates": ["small", "medium", "large", "luxury"],
            "priority": 5,
            "value_type": "fuzzy",
            "implicit_support": True,
            "deduct_from_value": False,
            "description": "the alias value of passenger_space_volume"
        },
        "trunk_volume_alias": {
            "candidates": ["small", "medium", "large", "luxury"],
            "priority": 6,
            "value_type": "fuzzy",
            "implicit_support": True,
            "deduct_from_value": False,
            "description": "the alias value of the trunk_volume"
        },
        "chassis_height_alias": {
            "candidates": ["low ride height", "medium ride height", "high ride height", "off-road chassis"],
            "priority": 8,
            "value_type": "fuzzy",
            "implicit_support": True,
            "deduct_from_value": False,
            "description": "the alias value of chassis_height"
        },
        "abs": {
            "candidates": ["yes", "no"],
            "priority": 5,
            "value_type": "boolean",
            "implicit_support": True,
            "deduct_from_value": False,
            "description": "vehicle has abs function or not"
        },
        "voice_interaction": {
            "candidates": ["yes", "no"],
            "priority": 13,
            "value_type": "boolean",
            "implicit_support": True,
            "deduct_from_value": False,
            "description": "the vehicle have the voice interaction or not"
        },
        "remote_parking": {
            "candidates": ["yes", "no"],
            "priority": 13,
            "value_type": "boolean",
            "implicit_support": True,
            "deduct_from_value": False,
            "description": "the vehicle support remote parking or not"
        },
        "auto_parking": {
            "candidates": ["yes", "no"],
            "priority": 12,
            "value_type": "boolean",
            "implicit_support": True,
            "deduct_from_value": False,
            "description": "the vehicle support auto parking or not"
        },
        "battery_capacity_alias": {
            "candidates": ["small", "medium", "large", "extra-large"],
            "priority": 7,
            "value_type": "fuzzy",
            "implicit_support": True,
            "deduct_from_value": False,
            "description": "the alias value of battery_capacity_alias"
        },
        "fuel_tank_capacity_alias": {
            "candidates": ["small", "medium", "large"],
            "priority": 8,
            "value_type": "fuzzy",
            "implicit_support": True,
            "deduct_from_value": False,
            "description": "the alias value of fuel_tank_capacity"
        },
        "fuel_consumption_alias": {
            "candidates": ["low", "medium", "high"],
            "priority": 6,
            "value_type": "fuzzy",
            "implicit_support": True,
            "deduct_from_value": False,
            "description": "the alias value of fuel_consumption"
        },
        "electric_consumption_alias": {
            "candidates": ["low", "medium", "high"],
            "priority": 6,
            "value_type": "fuzzy",
            "implicit_support": True,
            "deduct_from_value": False,
            "description": "the alias value of electric_consumption"
        },
        "cold_resistance": {
            "candidates": ["low", "medium", "high"],
            "priority": 12,
            "value_type": "fuzzy",
            "implicit_support": True,
            "deduct_from_value": False,
            "description": "the cold resistance level of the vehicle"
        },
        "heat_resistance": {
            "candidates": ["low", "medium", "high"],
            "priority": 12,
            "value_type": "fuzzy",
            "implicit_support": True,
            "deduct_from_value": False,
            "description": "the heat resistance level of the vehicle"
        },
        "size": {
            "candidates": ["small", "medium", "large"],
            "priority": 5,
            "value_type": "fuzzy",
            "implicit_support": True,
            "deduct_from_value": False,
            "description": "the estimated size of the vehicle"
        },
        "vehicle_usability": {
            "candidates": ["low", "medium", "high"],
            "priority": 5,
            "value_type": "fuzzy",
            "implicit_support": True,
            "deduct_from_value": False,
            "description": "the usability level of the vehicle"
        },
        "aesthetics": {
            "candidates": ["low", "medium", "high"],
            "priority": 5,
            "value_type": "fuzzy",
            "implicit_support": True,
            "deduct_from_value": False,
            "description": "the aesthetic level of the vehicle"
        },
        "energy_consumption_level": {
            "candidates": ["low", "medium", "high"],
            "priority": 5,
            "value_type": "fuzzy",
            "implicit_support": True,
            "deduct_from_value": False,
            "description": "the energy consumption level of the vehicle"
        },
        "comfort_level": {
            "candidates": ["low", "medium", "high"],
            "priority": 6,
            "value_type": "fuzzy",
            "implicit_support": True,
            "deduct_from_value": False,
            "description": "the comfort level of the vehicle"
        },
        "smartness": {
            "candidates": ["low", "medium", "high"],
            "priority": 6,
            "value_type": "fuzzy",
            "implicit_support": True,
            "deduct_from_value": False,
            "description": "the smartness level of the vehicle"
        },
        "family_friendliness": {
            "candidates": ["low", "medium", "high"],
            "priority": 6,
            "value_type": "fuzzy",
            "implicit_support": True,
            "deduct_from_value": False,
            "description": "how family-friendly the vehicle is"
        },
        "city_commuting": {
            "candidates": ["yes", "no"],
            "priority": 7,
            "value_type": "boolean",
            "implicit_support": True,
            "deduct_from_value": False,
            "description": "whether the vehicle is good at city commuting"
        },
        "highway_long_distance": {
            "candidates": ["yes", "no"],
            "priority": 8,
            "value_type": "boolean",
            "implicit_support": True,
            "deduct_from_value": False,
            "description": "whether the vehicle is suitable for highway long-distance travel"
        },
        "cargo_capability": {
            "candidates": ["yes", "no"],
            "priority": 8,
            "value_type": "boolean",
            "implicit_support": True,
            "deduct_from_value": False,
            "description": "whether the vehicle has good cargo capability"
        }
    }
    
    query_labels_path = os.path.join(config_dir, "QueryLabels.json")
    with open(query_labels_path, 'w', encoding='utf-8') as f:
        json.dump(query_labels, f, indent=4)
    
    # Create ImplicitExpression.json for testing
    with open(os.path.join(config_dir, "ImplicitExpression.json"), 'r', encoding='utf-8') as f:
        implicit_expressions = json.load(f)
        
    print(f"Mock config files created in {config_dir}")
    return query_labels_path, os.path.join(config_dir, "ImplicitExpression.json")

def run_all_tests():
    """Run all tests for ImplicitDeductor"""
    # Create mock config files for testing
    query_labels_path, implicit_expressions_path = mock_config_files()
    
    # Run tests
    run_test("Prize Alias Test", test_prize_alias)
    run_test("Passenger Space Volume Alias Test", test_passenger_space_volume_alias)
    run_test("Trunk Volume Alias Test", test_trunk_volume_alias)
    run_test("Chassis Height Alias Test", test_chassis_height_alias)
    run_test("ABS Test", test_abs)
    run_test("Voice Interaction Test", test_voice_interaction)
    run_test("Remote Parking Test", test_remote_parking)
    run_test("Auto Parking Test", test_auto_parking)
    run_test("Battery Capacity Alias Test", test_battery_capacity_alias)
    run_test("Fuel Tank Capacity Alias Test", test_fuel_tank_capacity_alias)
    run_test("Fuel Consumption Alias Test", test_fuel_consumption_alias)
    run_test("Electric Consumption Alias Test", test_electric_consumption_alias)
    run_test("Cold Resistance Test", test_cold_resistance)
    run_test("Heat Resistance Test", test_heat_resistance)
    run_test("Size Test", test_size)
    run_test("Vehicle Usability Test", test_vehicle_usability)
    run_test("Aesthetics Test", test_aesthetics)
    run_test("Energy Consumption Level Test", test_energy_consumption_level)
    run_test("Comfort Level Test", test_comfort_level)
    run_test("Smartness Test", test_smartness)
    run_test("Family Friendliness Test", test_family_friendliness)
    run_test("City Commuting Test", test_city_commuting)
    run_test("Highway Long Distance Test", test_highway_long_distance)
    run_test("Cargo Capability Test", test_cargo_capability)
    run_test("Multiple Labels Test", test_multiple_labels)
    run_test("Synonyms Expressions Test", test_synonyms_expressions)
    run_test("Casual Conversation Test", test_casual_conversation)

if __name__ == "__main__":
    run_all_tests() 