from datetime import datetime
from typing import Dict, Any, List
import random

class MockMessage:
    """Mock class to simulate AI-generated responses"""
    
    # Predefined responses for different stages
    STAGE_RESPONSES = {
        'welcome': [
            "Hi! I'm AutoVend, your smart assistant! How can I assist you in finding your ideal vehicle today?",
            "Welcome to AutoVend! I'm here to help you find the perfect car. What are you looking for?",
            "Hello! I'm your AutoVend assistant. Let's find your dream car together. What's on your mind?"
        ],
        'profile_analysis': [
            "Could you tell me a bit about yourself? For example, your driving experience and preferences?",
            "To better assist you, I'd like to know more about your driving background. How long have you been driving?",
            "Let's start by understanding your needs. What's your experience with cars?"
        ],
        'needs_analysis': [
            "I understand you're looking for a car. Could you tell me more about your specific requirements?",
            "What features are most important to you in a car?",
            "Could you share your preferences regarding vehicle type, size, and features?"
        ],
        'car_selection_confirmation': [
            "Based on your needs, I recommend the {car_model}. It offers {feature} and {feature2}.",
            "You might be interested in the {car_model}. It's perfect for your requirements.",
            "I think the {car_model} would be a great match for you. Would you like to know more?"
        ],
        'reservation4s': [
            "Would you like to schedule a test drive for the {car_model}?",
            "I can help you arrange a test drive. When would be convenient for you?",
            "Let's set up a test drive. What's your preferred date and time?"
        ],
        'reservation_confirmation': [
            "Great! I've scheduled your test drive for {date} at {time}.",
            "Your test drive is confirmed for {date} at {time}. See you then!",
            "Perfect! Your test drive is booked for {date} at {time}."
        ],
        'farewell': [
            "Thank you for choosing AutoVend! We look forward to seeing you at your test drive.",
            "It was a pleasure helping you. We'll see you at your scheduled test drive!",
            "Thank you for your interest in AutoVend. We're excited to show you the car in person!"
        ]
    }
    
    # Sample car models and features
    CAR_MODELS = {
        'SUV': ['Tesla Model Y', 'Ford Mustang Mach-E', 'Audi Q4 e-tron'],
        'Sedan': ['Tesla Model 3', 'BMW i4', 'Mercedes EQE'],
        'Hatchback': ['Volkswagen ID.3', 'Mini Cooper SE', 'Honda e']
    }
    
    CAR_FEATURES = [
        "excellent range", "advanced safety features", "spacious interior",
        "fast charging capability", "smart connectivity", "autonomous driving",
        "luxury interior", "sporty handling", "eco-friendly materials"
    ]
    
    @classmethod
    def generate_response(cls, stage: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a mock response based on the current stage and context"""
        # Get base response template
        response_template = random.choice(cls.STAGE_RESPONSES.get(stage, ["I understand. Please tell me more."]))
        
        # Fill in template variables
        if stage == 'needs_analysis':
            vehicle_type = context.get('needs', {}).get('explicit', {}).get('vehicle_category_bottom', 'vehicle')
            response = response_template.format(vehicle_type=vehicle_type)
        elif stage == 'car_selection_confirmation':
            vehicle_type = context.get('needs', {}).get('explicit', {}).get('vehicle_category_bottom', 'SUV')
            car_model = random.choice(cls.CAR_MODELS.get(vehicle_type, cls.CAR_MODELS['SUV']))
            features = random.sample(cls.CAR_FEATURES, 2)
            response = response_template.format(
                car_model=car_model,
                feature=features[0],
                feature2=features[1]
            )
        elif stage == 'reservation4s':
            car_model = context.get('matched_car_models', ['our vehicle'])[0]
            response = response_template.format(car_model=car_model)
        elif stage == 'reservation_confirmation':
            date = context.get('reservation_info', {}).get('reservation_date', 'the scheduled date')
            time = context.get('reservation_info', {}).get('reservation_time', 'the scheduled time')
            response = response_template.format(date=date, time=time)
        else:
            response = response_template
            
        # TODO, current reposne include all session information, but it should only have chat response message, other should be returned in session dict
        return {
            'message_id': f"msg_{datetime.now().timestamp()}",
            'sender_type': 'system',
            'sender_id': 'AutoVend',
            'content': response,
            'timestamp': datetime.now().isoformat(),
            'status': 'delivered'
        } 