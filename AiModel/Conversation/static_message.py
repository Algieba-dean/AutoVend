import random
WELCOME_MESSAGES = [
        "This is AutoVend, your intelligent car purchasing assistant. Good to meet you!",
        "I'm AutoVend, an AI-powered car consultant. I'm here to make your car shopping experience easier. ",
        "Welcome to our virtual showroom! I'm AutoVend, your smart car assistant. ",
        "Thank you for contacting us! This is AutoVend, your personal car shopping guide. ",
        "Good day! AutoVend at your service. I'm specialized in helping customers find their perfect car match. Good to know you here! ",
    ]
def get_welcome_message():
    welcome_message = random.choice(WELCOME_MESSAGES)
    return welcome_message
INITIAL_MESSAGES = [
    "Hi! This is AutoVend speaking, our chat will be recorded for a better performance. If you don't mind, please say Hi AutoVend to continue. ",
    "AutoVend is a smart car shopping assistant. our chat will be recorded for a better performance. If you don't mind, please say Hi AutoVend to continue. ",
    "Thank you for choosing AutoVend. Our chat will be recorded for a better performance. If you don't mind, please say Hi AutoVend to continue. ",
]
def get_initial_message():
    initial_message = random.choice(INITIAL_MESSAGES)
    return initial_message