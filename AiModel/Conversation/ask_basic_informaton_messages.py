import random
ASK_NAME_MESSAGES = [
    "May I have the pleasure of knowing your name? It would mean a lot to me as I strive to provide you with the most personalized experience possible",
    "Could you kindly share your name with me? It will help me ensure that our interaction is as smooth and efficient as possible.",
    "I'm super excited to help you out. What's your name? Knowing it will make our conversation even more enjoyable and tailored just for you",
    "I genuinely want to make sure I'm giving you the best service possible. Could you let me know your name? It's important to me that I address you correctly and make this a pleasant experience for you",
    "I'm thrilled to be of assistance! Could you please share your name with me? Knowing it will help me personalize our conversation and make it even more effective for you",
    "I'm excited to help you find the perfect vehicle. Could you share your name with me? Knowing it will make our conversation even more personalized and tailored just for you",
    "I'm here to make your car shopping experience as smooth as possible. Could you let me know your name? It's important to me that I address you correctly and make this a pleasant experience for you",
    "I'm thrilled to be of assistance! Could you please share your name with me? Knowing it will help me personalize our conversation and make it even more effective for you",
]
def get_ask_name_message():
    ask_name_message = random.choice(ASK_NAME_MESSAGES)
    return ask_name_message
ASK_TITLE_MESSAGES = [
    "How would you prefer to be addressed? Is it Mr., Mrs., Miss., or Ms.?"
    "Would you prefer to be addressed as Mr., Mrs., Miss., or Ms.?",
    "To ensure I'm being considerate, could you let me know if you prefer Mr., Mrs., Miss., or Ms.? I want to get this right.",
    "To be as respectful as possible, could you let me know how you'd like to be addressed? Mr., Mrs., Miss., or Ms.? Your preference really matters.",
    "To get it just right, do you go by Mr., Mrs., Miss., or Ms.? It's all about making you feel comfortable and respected."
]
def get_ask_title_message():
    ask_title_message = random.choice(ASK_TITLE_MESSAGES)
    return ask_title_message
ASK_TARGET_DRIVER_MESSAGES = [
    "Could you let us know who the primary driver of the vehicle will be? Is it you, your spouse, or perhaps someone else like a family member or friend?",
    "I hope this question doesn't feel too personal, but we need to know who'll be the main driver of the vehicle. Is it you, your wife, husband, or maybe your son or daughter?",
    "For our records and to ensure we provide the most accurate service, could you please specify who the primary driver of the vehicle will be? Is it yourself, your spouse, or another individual such as a family member or friend?",
    "We need to identify the primary driver of the vehicle for our documentation. Is it you, your spouse, or perhaps your son, daughter, or another family member? Your cooperation is greatly appreciated.",
    "To complete our process, we kindly ask you to specify the primary driver of the vehicle. Is it you, your spouse, or someone else like your father, mother, or a friend?",
    "Super excited to help you out! Just need to know who'll be the primary driver here. Is it you, your wife, husband, or perhaps your mom, dad, or a friend? Let's make sure we've got it right!",
]
def get_ask_target_driver_message():
    ask_target_driver_message = random.choice(ASK_TARGET_DRIVER_MESSAGES)
    return ask_target_driver_message