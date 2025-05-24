from auto_vend_ai import AutoVend, mocked_information
import json

current_stage_info = {"previous_stage": "", "current_stage": "initial"}
current_profile = {
    "phone_number": "1333333333",
    "age": "",
    "user_title": "",
    "name": "",
    "target_driver": "",
    "expertise": "",
    "additional_information": {
        "family_size": "",
        "price_sensitivity": "",
        "residence": "",
        "parking_conditions": "",
    },
    "connection_information": {
        "connection_phone_number": "",
        "connection_id_relationship": "",
        "connection_user_name": "",
    },
}
current_needs = {
    "explicit": {},
    "implicit": {},
}
current_reservation_info = {
    "test_driver": "",
    "reservation_date": "",
    "reservation_time": "",
    "reservation_location": "",
    "selected_car_model": "",
    "reservation_phone_number": "",
    "salesman": "",
}
current_matched_car_models = []

def print_response(initial_response, current_stage_info, current_profile, current_needs, current_matched_car_models, current_reservation_info):
    print(f"AutoVend: {initial_response}")
    print(f"Stage: {json.dumps(current_stage_info, ensure_ascii=False, indent=2)}")
    print(f"Profile: {json.dumps(current_profile, ensure_ascii=False, indent=2)}")
    print(f"Needs: {json.dumps(current_needs, ensure_ascii=False, indent=2)}")
    print(f"Matched Car Models: {json.dumps(current_matched_car_models, ensure_ascii=False, indent=2)}")
    print(f"Reservation Info: {json.dumps(current_reservation_info, ensure_ascii=False, indent=2)}")
    print("-" * 50)

def predefined_commmand(assistant: AutoVend):
    global current_stage_info, current_profile, current_needs, current_matched_car_models, current_reservation_info
    user_input = ""
    # Simulate first call with empty message to get initial greeting
    (
        initial_response,
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    ) = assistant.generate_response(
        user_input,
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    )
    # confirm to use autovend
    user_input = "Hi AutoVend"
    (
        initial_response,
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    ) = assistant.generate_response(
        user_input,
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    )
    # AutoVend:Hi! I'm AutoVend, an AI-powered car consultant. I'm here to make your car shopping experience easier. \nMay I have your name and title (Mr., Mrs., Miss., Ms.)? Also, who will be the primary driver of the vehicle?
    # User: I'm wang, you can call me MR.wang
    # user name and title
    user_input = "I'm wang, you can call me Mr.wang"
    (
        initial_response,
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    ) = assistant.generate_response(
        user_input,
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    )
    print("user input: ", user_input)
    print_response(initial_response, current_stage_info, current_profile, current_needs, current_matched_car_models, current_reservation_info)
    # AutoVend: Mr. Wang, who will be the primary driver of the vehicle you're considering?
    # User: myself
    ...
    user_input = "my wife"
    (
        initial_response,
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    ) = assistant.generate_response(
        "my wife",
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    )
    print("user input: ", user_input)
    print_response(initial_response, current_stage_info, current_profile, current_needs, current_matched_car_models, current_reservation_info)
    # AutoVend: Got it. How can I assist you with your car purchase today? (not ok) (should ask for budget)
    user_input = "I wanna buy a suv or sedan"
    (
        initial_response,
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    ) = assistant.generate_response(
        user_input,
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    )
    print("user input: ", user_input)
    print_response(initial_response, current_stage_info, current_profile, current_needs, current_matched_car_models, current_reservation_info)
    # AutoVend: 'What’s your budget for the SUV?'
    user_input = "at most 30000 dollars"
    (
        initial_response,
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    ) = assistant.generate_response(
        user_input,
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    )
    print("user input: ", user_input)
    print_response(initial_response, current_stage_info, current_profile, current_needs, current_matched_car_models, current_reservation_info)
    # AutoVend: Based on your budget and SUV preference, I’ve picked three models for you: the Changan-UNI-Z, Nissan Kicks, and Volkswagen T-Roc Life. All fit your $20,000–$30,000 range. 
    user_input = "and she is not good at parking, any suggestion?"
    (
        initial_response,
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    ) = assistant.generate_response(
        user_input,
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    )
    print("user input: ", user_input)
    print_response(initial_response, current_stage_info, current_profile, current_needs, current_matched_car_models, current_reservation_info)
    # AutoVend: Based on your budget and SUV preference, I’ve picked three models for you: the Changan-UNI-Z, Nissan Kicks, and Volkswagen T-Roc Life. All fit your $20,000–$30,000 range. 
    user_input = "Yes, remote parking and auto parking are good"
    (
        initial_response,
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    ) = assistant.generate_response(
        user_input,
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    )
    print("user input: ", user_input)
    print_response(initial_response, current_stage_info, current_profile, current_needs, current_matched_car_models, current_reservation_info)
    # AutoVend: 'Based on your budget and SUV preference, I’ve picked three models for you: the Changan-UNI-Z, Nissan Kicks, and Volkswagen T-Roc Life. All fit your $20,000–$30,000 range. 
    # From what you’ve shared, I’m assuming you’d like a larger SUV with good fuel efficiency and higher ride height. Does that sound right, or would you like to adjust any of these preferences?'
    user_input = f"Can I know more about the {current_matched_car_models[-1]}? can you give me some details?"
    (
        initial_response,
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    ) = assistant.generate_response(
        user_input,
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    )
    print("user input: ", user_input)
    print_response(initial_response, current_stage_info, current_profile, current_needs, current_matched_car_models, current_reservation_info)
    # AutoVend: 'Sure, the Changan-UNI-Z is a compact SUV that offers a spacious interior and good fuel efficiency. It has a 1.5L turbocharged engine and a 6-speed automatic transmission. The interior is designed with a modern, minimalist aesthetic, featuring a large touchscreen display and comfortable seating. The exterior is sleek and stylish, with a bold grille and LED headlights. The Changan-UNI-Z is a great choice for someone who wants a compact SUV with good fuel efficiency and a modern, stylish design.'
    user_input = f"I'd like to pick {current_matched_car_models[-1]}, and I wanna booking a test drive for it"
    (
        initial_response,
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    ) = assistant.generate_response(
        user_input,
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    )
    print("user input: ", user_input)
    print_response(initial_response, current_stage_info, current_profile, current_needs, current_matched_car_models, current_reservation_info)


    user_input = "The test driver is my wife"
    (
        initial_response,
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    ) = assistant.generate_response(
        user_input,
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    )
    print("user input: ", user_input)
    print_response(initial_response, current_stage_info, current_profile, current_needs, current_matched_car_models, current_reservation_info)

    user_input = "Her name is kongkongkaka, and her number is 19999999"
    (
        initial_response,
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    ) = assistant.generate_response(
        user_input,
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    )
    print("user input: ", user_input)
    print_response(initial_response, current_stage_info, current_profile, current_needs, current_matched_car_models, current_reservation_info)
    user_input = f"{mocked_information.mocked_stores[0]} should be better"
    (
        initial_response,
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    ) = assistant.generate_response(
        user_input,
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    )
    print("user input: ", user_input)
    print_response(initial_response, current_stage_info, current_profile, current_needs, current_matched_car_models, current_reservation_info)
    user_input = f"{mocked_information.mocked_dates[0]} is nice day for test drive, can you book it for me?"
    (
        initial_response,
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    ) = assistant.generate_response(
        user_input,
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    )
    print("user input: ", user_input)
    print_response(initial_response, current_stage_info, current_profile, current_needs, current_matched_car_models, current_reservation_info)
    user_input = f"14:30 please"
    (
        initial_response,
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    ) = assistant.generate_response(
        user_input,
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    )
    print("user input: ", user_input)
    print_response(initial_response, current_stage_info, current_profile, current_needs, current_matched_car_models, current_reservation_info)
    user_input = f"{mocked_information.salesman_names[0]} sounds a nice pesrson, let's book it with him"
    (
        initial_response,
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    ) = assistant.generate_response(
        user_input,
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    )
    print("user input: ", user_input)
    print_response(initial_response, current_stage_info, current_profile, current_needs, current_matched_car_models, current_reservation_info)

    user_input = f"Thank you bye bye"
    (
        initial_response,
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    ) = assistant.generate_response(
        user_input,
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    )
    print("user input: ", user_input)
    print_response(initial_response, current_stage_info, current_profile, current_needs, current_matched_car_models, current_reservation_info)
    ...
    #  # confirm the prize range
    #  (
    #      initial_response,
    #      current_stage_info,
    #      current_profile,
    #      current_needs,
    #      current_matched_car_models,
    #      current_reservation_info,
    #  ) = assistant.generate_response(
    #      "prize should from 20000 to 30000",
    #      current_stage_info,
    #      current_profile,
    #      current_needs,
    #      current_matched_car_models,
    #      current_reservation_info,
    #  )
    #  (
    #      initial_response,
    #      current_stage_info,
    #      current_profile,
    #      current_needs,
    #      current_matched_car_models,
    #      current_reservation_info,
    #  ) = assistant.generate_response(
    #      "maybe a suv should be better",
    #      current_stage_info,
    #      current_profile,
    #      current_needs,
    #      current_matched_car_models,
    #      current_reservation_info,
    #  )
    print_response(initial_response, current_stage_info, current_profile, current_needs, current_matched_car_models, current_reservation_info)


def demo_cases():
    assistant = AutoVend(extractor_type="llm")  # Example: use LLM extractors
    predefined_commmand(assistant)

    print("AutoVend AI Car Sales Assistant")
    print(
        f"Using extractor type: {assistant.extractor_type}"
    )  # Show which type is used
    print("Type 'exit' to quit")
    print("-" * 50)

    # Initial state for the first call to generate_response
    # For subsequent calls, these are ignored as the assistant maintains state internally.

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() == "exit":
            break

        # For subsequent calls, the state variables (current_stage_info, etc.) are passed
        # but the assistant primarily uses its internal self.status_component.
        # The design could be refactored so generate_response only takes user_input
        # and relies entirely on internal state after the first call.
        # However, to match the existing signature:
        global current_stage_info, current_profile, current_needs, current_matched_car_models, current_reservation_info
        (
            response,
            stage_out,
            profile_out,
            needs_out,
            matched_models_out,
            reservation_out,
        ) = assistant.generate_response(
            user_input,
            current_stage_info,  # This is the stage before processing current user_input
            current_profile,  # Current profile before processing
            current_needs,  # Current needs before processing
            current_matched_car_models,  # etc.
            current_reservation_info,
        )

        # Update local state trackers from the response for the *next* iteration's input (if needed by generate_response signature)
        current_stage_info = stage_out
        current_profile = profile_out
        current_needs = needs_out
        current_matched_car_models = matched_models_out
        current_reservation_info = reservation_out

        # Print the assistant's response
        print(f"\nAutoVend: {response}")

        # Debug information - comment out for production
        print("\n--- Debug Info ---")
        print(f"Stage: {current_stage_info['current_stage']}")

        if profile_out:
            print(
                f"User Profile: {json.dumps(profile_out, ensure_ascii=False, indent=2)}"
            )

        if needs_out:
            print(f"Needs: {json.dumps(needs_out, ensure_ascii=False, indent=2)}")

        if reservation_out:
            print(
                f"Reservation Info: {json.dumps(reservation_out, ensure_ascii=False, indent=2)}"
            )

        if matched_models_out:
            print(
                f"Matched Car Models: {json.dumps(matched_models_out, ensure_ascii=False)[:200]}..."
            )

        print("-" * 50)


if __name__ == "__main__":
    demo_cases()

