#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Example usage of the ImplicitDeductor class
"""

import json
import os
from .implicit_deductor import ImplicitDeductor


def example_1():
    """
    Basic example of implicit deduction from user text
    """
    print("\n=== Example 1: Basic Implicit Deduction ===")
    
    # Create an ImplicitDeductor instance
    deductor = ImplicitDeductor()
    
    # Example user input
    user_input = """
    I'm looking for a car that's good for my family. We have three kids and often take long road trips.
    I want something spacious with good fuel efficiency, as I'm quite conscious about environmental impact.
    The car should be comfortable for highway driving and have modern safety features.
    """
    
    # Extract implicit values
    result = deductor.extract_implicit_values(user_input)
    
    # Display results
    print("User input:")
    print(user_input)
    print("\nExtracted implicit values:")
    for label, value in result.items():
        print(f"  {label}: {value}")


def example_2():
    """
    Example of deduction from casual conversation
    """
    print("\n=== Example 2: Deduction from Casual Conversation ===")
    
    # Create an ImplicitDeductor instance
    deductor = ImplicitDeductor()
    
    # Example user input - casual conversation
    user_input = """
    I hate parking in tight spots downtown. My parking skills are terrible, and I always worry about scratching the car.
    I live in Minnesota, so winters are really cold and we get a lot of snow. 
    I usually drive alone, but I need trunk space for my golf clubs on weekends.
    """
    
    # Extract implicit values
    result = deductor.extract_implicit_values(user_input)
    
    # Display results
    print("User input:")
    print(user_input)
    print("\nExtracted implicit values:")
    for label, value in result.items():
        print(f"  {label}: {value}")


def example_3():
    """
    Example with luxury and high-end preferences
    """
    print("\n=== Example 3: Luxury and High-End Preferences ===")
    
    # Create an ImplicitDeductor instance
    deductor = ImplicitDeductor()
    
    # Example user input - luxury preferences
    user_input = """
    I want the absolute best car money can buy. Price is not an issue for me.
    I need all the latest technology and cutting-edge features.
    The interior should be exceptionally spacious and comfortable, with premium materials.
    Performance is more important to me than fuel efficiency.
    """
    
    # Extract implicit values
    result = deductor.extract_implicit_values(user_input)
    
    # Display results
    print("User input:")
    print(user_input)
    print("\nExtracted implicit values:")
    for label, value in result.items():
        print(f"  {label}: {value}")


def example_4():
    """
    Example with combination of diverse preferences
    """
    print("\n=== Example 4: Mixed Preferences ===")
    
    # Create an ImplicitDeductor instance
    deductor = ImplicitDeductor()
    
    # Example user input with mix of preferences
    user_input = """
    I'm looking for a practical car for city driving, but I occasionally go camping on weekends.
    I prefer something with decent ground clearance for rough roads, but it should still be economical.
    I have a moderate budget and want good value for money.
    Voice control would be nice so I can make calls hands-free while driving.
    """
    
    # Extract implicit values
    result = deductor.extract_implicit_values(user_input)
    
    # Display results
    print("User input:")
    print(user_input)
    print("\nExtracted implicit values:")
    for label, value in result.items():
        print(f"  {label}: {value}")


if __name__ == "__main__":
    example_1()
    example_2()
    example_3()
    example_4() 