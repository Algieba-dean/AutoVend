import random
CONGRATULATION_MESSAGES = [
]
ASK_TEST_DRIVER_MESSAGES = [
]
ASK_RESERVATION_DATE_MESSAGES = [
]
ASK_RESERVATION_TIME_MESSAGES = [
]
ASK_RESERVATION_LOCATION_MESSAGES = [
]

def get_congratulation_message():
    congratulation_message = random.choice(CONGRATULATION_MESSAGES)
    return congratulation_message
def get_ask_test_driver_message():
    ask_test_driver_message = random.choice(ASK_TEST_DRIVER_MESSAGES)
    return ask_test_driver_message
def get_ask_reservation_date_message():
    ask_reservation_date_message = random.choice(ASK_RESERVATION_DATE_MESSAGES)
    return ask_reservation_date_message
def get_ask_reservation_time_message():
    ask_reservation_time_message = random.choice(ASK_RESERVATION_TIME_MESSAGES)
    return ask_reservation_time_message
def get_ask_reservation_location_message():
    ask_reservation_location_message = random.choice(ASK_RESERVATION_LOCATION_MESSAGES)
    return ask_reservation_location_message