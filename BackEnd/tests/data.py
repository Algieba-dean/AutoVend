# Test data for AutoVend API tests

# Sample user profiles
VALID_PROFILES = [
    {
        "phone_number": "123456789",
        "age": "20-35",
        "user_title": "Mr. Zhang",
        "name": "John",
        "target_driver": "Self",
        "expertise": "5",
        "additional_information": {
            "family_size": "3",
            "price_sensitivity": "Medium",
            "residence": "China+Beijing+Haidian",
            "parking_conditions": "Allocated Parking Space"
        },
        "connection_information": {
            "connection_phone_number": "",
            "connection_id_relationship": ""
        }
    },
    {
        "phone_number": "987654321",
        "age": "35-50",
        "user_title": "Mrs. Li",
        "name": "Sarah",
        "target_driver": "Self",
        "expertise": "7",
        "additional_information": {
            "family_size": "4",
            "price_sensitivity": "Low",
            "residence": "China+Shanghai+Pudong",
            "parking_conditions": "Charging Pile Facilities Available"
        },
        "connection_information": {
            "connection_phone_number": "",
            "connection_id_relationship": ""
        }
    },
    {
        "phone_number": "555666777",
        "age": "50-65",
        "user_title": "Mr. Chen",
        "name": "David",
        "target_driver": "Wife",
        "expertise": "3",
        "additional_information": {
            "family_size": "2",
            "price_sensitivity": "High",
            "residence": "China+Guangzhou+Tianhe",
            "parking_conditions": "Temporary Parking Allowed"
        },
        "connection_information": {
            "connection_phone_number": "555666888",
            "connection_id_relationship": "Daughter"
        }
    }
]

# Invalid profiles for testing validation
INVALID_PROFILES = {
    "missing_required_fields": {
        "phone_number": "111222333",
        "name": "Invalid"
    },
    "invalid_title": {
        "phone_number": "111222333",
        "age": "20-35",
        "user_title": "Master Zhang",  # Invalid title format
        "name": "John",
        "target_driver": "Self",
        "expertise": "5"
    },
    "invalid_expertise": {
        "phone_number": "111222333",
        "age": "20-35",
        "user_title": "Mr. Zhang",
        "name": "John",
        "target_driver": "Self",
        "expertise": "15"  # Out of range
    }
}

# Sample chat messages
CHAT_MESSAGES = [
    "Hello, I'm looking for a new car.",
    "I need an electric SUV with good range.",
    "What's the price range for the Tesla Model Y?",
    "Does it have good safety features?",
    "I'd like to schedule a test drive.",
    "Is next Tuesday at 2pm available?",
    "Yes, please confirm the reservation."
]

# Car needs keywords for testing
CAR_NEEDS_KEYWORDS = {
    "powertrain_types": ["electric", "gas", "hybrid", "diesel", "EV", "battery"],
    "vehicle_types": ["SUV", "sedan", "compact", "truck", "van", "MPV", "sports car"],
    "brands": ["Tesla", "BMW", "Audi", "Toyota", "Honda", "Volkswagen", "BYD", "Porsche"],
    "features": ["safety", "autopilot", "self-driving", "leather", "sunroof", "camera", "sensors"],
    "performance": ["range", "speed", "acceleration", "horsepower", "torque"],
    "price": ["price", "cost", "expensive", "affordable", "budget", "luxury"]
} 