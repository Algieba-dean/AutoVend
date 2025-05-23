import openai
import sys
import os
# Add the parent directory (AiModel) to sys.path to allow importing utils
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import get_openai_client, clean_thinking_output, get_openai_model

class LLMStageArbitrator:
    def __init__(self, model=None):
        self.client = get_openai_client()
        self.model = model or get_openai_model()

    def get_chat_stage(self, conversation_history: list, user_profile: dict) -> str:
        """
        Determines the current stage of the car purchase conversation.

        Args:
            conversation_history: A list of messages representing the conversation so far.
                                  Each message should be a dictionary with "role" and "content" keys.
            user_profile: A dictionary containing user profile information.

        Returns:
            The determined chat stage as a string.
        """
        # Check for profile_analysis stage based on user_profile
        if not user_profile.get("user_title") or \
           not user_profile.get("name") or \
           not user_profile.get("target_driver"):
            return "profile_analysis"

        # If not profile_analysis, proceed to LLM for other stages
        # The prompt will be refined later based on your specific stage details for other stages.
        prompt_template = """
You are an AI assistant responsible for determining the current stage of a car purchase conversation.
The user's basic profile information (title, name, target_driver) has already been collected.
Based on the conversation history provided, identify which of the following stages the conversation is currently in. Only output the stage name.

- needs_analysis: The user is discussing their car requirements (e.g., expressing needs, asking about key details of a car, agreeing to or inquiring about requirements, seeking to understand car information). The assistant is working to understand these needs, and may also introduce car models and their details.
- reservation4s: The user expresses a desire to book a test drive, schedule a visit to a dealership (4S store), or make a reservation related to a car.
- farewell: The conversation is concluding, with expressions of gratitude, goodbyes, or an indication that no further assistance is immediately needed.

Conversation History:
{history}

Current Stage:
        """
        prompt = prompt_template.format(history="\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history]))

        messages = [
            {"role": "system", "content": "You are an AI assistant that helps determine the current stage of a car purchase conversation, excluding the initial profile analysis."},
            {"role": "user", "content": prompt}
        ]

        # Call OpenAI API with optimized parameters
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=50
        )

        assistant_response = response.choices[0].message.content
        assistant_response = clean_thinking_output(assistant_response)

        valid_stages_after_profile = ["needs_analysis", "reservation4s", "farewell"]
        if assistant_response in valid_stages_after_profile:
            return assistant_response
        else:
            print(f"Warning: OpenAI returned an unexpected stage (after profile completion): {assistant_response}")
            # Fallback to needs_analysis if LLM output is unclear after profile completion
            return "needs_analysis" 

if __name__ == "__main__":
    arbitrator = LLMStageArbitrator()

    # Sample user profiles
    profile_incomplete = {
        "phone_number": "1234567890", "age": "30", "user_title": "Mr.", "name": "", "target_driver": "self",
        "expertise": "intermediate", "additional_information": {}, "connection_information": {}
    }
    profile_complete = {
        "phone_number": "1234567890", "age": "35", "user_title": "Ms.", "name": "Jane Doe", "target_driver": "self",
        "expertise": "expert", "additional_information": {"family_size": "4"}, "connection_information": {}
    }

    # Test case 1: Profile incomplete
    print("Testing with incomplete profile (expecting profile_analysis):")
    stage = arbitrator.get_chat_stage([], profile_incomplete) # Conversation history can be empty for this check
    print(f"Determined stage: {stage}\n")

    # Test case 2: Profile complete, initial conversation (expecting needs_analysis from LLM)
    sample_history_1 = [
        {"role": "user", "content": "Hello, I'm looking to buy a new car."},
        {"role": "assistant", "content": "Great! To help you better, could you tell me a bit about your driving habits and what you're looking for in a car?"}
    ]
    print("Testing with complete profile, sample_history_1 (expecting needs_analysis):")
    stage1 = arbitrator.get_chat_stage(sample_history_1, profile_complete)
    print(f"Determined stage for history 1: {stage1}\n")

    # Test case 3: Profile complete, conversation about needs (expecting needs_analysis from LLM)
    sample_history_2 = [
        {"role": "user", "content": "I mostly drive in the city, and I need something fuel-efficient."},
        {"role": "assistant", "content": "Okay, city driving and fuel efficiency. Any preferences on car size or type, like an SUV or a sedan?"},
        {"role": "user", "content": "I think a compact SUV would be good."}
    ]
    print("Testing with complete profile, sample_history_2 (expecting needs_analysis):")
    stage2 = arbitrator.get_chat_stage(sample_history_2, profile_complete)
    print(f"Determined stage for history 2: {stage2}\n")

    # Test case 4: Profile complete, conversation about specific model (expecting model_introduction from LLM)
    # sample_history_3 = [
    #     {"role": "user", "content": "The new Model X sounds interesting. Can you tell me more about its features and price?"},
    #     {"role": "assistant", "content": "Certainly! The Model X is a fantastic electric SUV. It starts at $79,990 and comes with features like..."}
    # ]
    # print("Testing with complete profile, sample_history_3 (expecting model_introduction):")
    # stage3 = arbitrator.get_chat_stage(sample_history_3, profile_complete)
    # print(f"Determined stage for history 3: {stage3}\n")
    
    # Test case 5: Profile complete, booking test drive (expecting reservation4s from LLM)
    print("Testing with complete profile, sample_history_4 (expecting reservation4s):")
    sample_history_4 = [
        {"role": "user", "content": "I'd like to book a test drive for the Model S this Saturday."}, 
        {"role": "assistant", "content": "Sure, I can help with that. What time works for you?"}
    ]
    stage4 = arbitrator.get_chat_stage(sample_history_4, profile_complete)
    print(f"Determined stage for history 4: {stage4}\n")

    # Test case 6: Profile complete, farewell (expecting farewell from LLM)
    print("Testing with complete profile, sample_history_5 (expecting farewell):")
    sample_history_5 = [
        {"role": "user", "content": "Thanks for all your help!"},
        {"role": "assistant", "content": "You're welcome! Have a great day!"}
    ]
    stage5 = arbitrator.get_chat_stage(sample_history_5, profile_complete)
    print(f"Determined stage for history 5: {stage5}\n") 