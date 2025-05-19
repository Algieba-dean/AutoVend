import random
WELCOME_MESSAGES = [
        "This is AutoVend, your intelligent car purchasing assistant. How can I help you find your ideal vehicle today?",
        "I'm AutoVend, an AI-powered car consultant. I'm here to make your car shopping experience easier. What kind of vehicle are you looking for?",
        "Welcome to our virtual showroom! I'm AutoVend, your smart car assistant. I can help with everything from finding the right model to booking a test drive. How may I assist you?",
        "Thank you for contacting us! This is AutoVend, your personal car shopping guide. I'm here to help you find the perfect vehicle for your needs. What brings you to our service today?",
        "Good day! AutoVend at your service. I'm specialized in helping customers find their perfect car match. What type of vehicle are you interested in exploring?"
    ]
def get_welcome_message():
    welcome_message = random.choice(WELCOME_MESSAGES)
    return welcome_message