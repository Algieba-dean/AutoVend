import os
import json
import concurrent.futures
from typing import Dict, Any, List

from utils import get_openai_client, get_openai_model, timer_decorator

from Conversation.mocked_information import MockedInformation
# # LLMExtractors
from Conversation.conversation_module import ConversationModule

# from LLMExtractors.profile_extractor import ProfileExtractor
# from LLMExtractors.expertise_evaluator import ExpertiseEvaluator
# from LLMExtractors.explicit_needs_extractor import ExplicitNeedsExtractor
# from LLMExtractors.implicit_needs_inferrer import ImplicitNeedsInferrer
# from LLMExtractors.test_drive_extractor import TestDriveExtractor

# TranditionalExtractors
from InformationExtractors.explicit_in_extractor import ExplicitInOneExtractor
from InformationExtractors.expertise_analyst import ExpertiseAnalyst
from InformationExtractors.stage_arbitrator import StageArbitrator
from InformationExtractors.additional_profile_extractor import (
    AdditionalProfileExtractor,
)
from InformationExtractors.basic_profile_extractor import BasicProfileExtractor
from InformationExtractors.reservation_info_extractor import ReservationInfoExtractor
from InformationExtractors.ImplicitDeductor import ImplicitDeductor

from status_component import StatusComponent
from ModelQuery.ModelQuery import CarModelQuery


class AutoVend:
    """
    Main AutoVend AI car sales assistant class.
    Integrates all modules to process user messages and generate responses.
    """

    def __init__(self, api_key=None, model=None):
        """
        Initialize the AutoVend assistant.

        Args:
            api_key (str, optional): OpenAI API key. Defaults to environment variable.
            model (str, optional): OpenAI model to use. Defaults to environment variable.
        """
        # Get OpenAI model name
        self.model = model or get_openai_model()

        # # Initialize all modules
        # self.profile_extractor = ProfileExtractor(api_key=api_key, model=self.model)
        # self.expertise_evaluator = ExpertiseEvaluator(api_key=api_key, model=self.model)
        # self.explicit_needs_extractor = ExplicitNeedsExtractor(api_key=api_key, model=self.model)
        # self.implicit_needs_inferrer = ImplicitNeedsInferrer(api_key=api_key, model=self.model)
        # self.test_drive_extractor = TestDriveExtractor(api_key=api_key, model=self.model)
        self.conversation_module = ConversationModule(api_key=api_key, model=self.model)

        # Initialize tranditional extractors
        self.explicit_in_extractor = ExplicitInOneExtractor()
        self.expertise_analyst = ExpertiseAnalyst()
        self.stage_arbitrator = StageArbitrator()
        self.additional_profile_extractor = AdditionalProfileExtractor()
        self.basic_profile_extractor = BasicProfileExtractor()
        self.reservation_info_extractor = ReservationInfoExtractor()
        self.implicit_deductor = ImplicitDeductor()

        # tools
        self.car_model_query = CarModelQuery()
        self.status_component = StatusComponent()
        self.mocked_information = MockedInformation()
        # Create a thread pool executor
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=6)

    @timer_decorator
    def generate_response(
        self,
        message: str,
        stage: Dict[str, Any],
        profile: Dict[str, Any],
        needs: Dict[str, Any],
        matched_car_models: List[str],
        reservation_info: Dict[str, Any],
    ):
        """
        Process a user message through all modules in parallel and generate a response.

        Args:
            user_message (str): The user's message

        Returns:
            dict: Dictionary containing the assistant's response and all extracted data
        """
        # first user_message will be empty string and just return initial response
        if message == "":
            new_stage = "initial"
            self.status_component.update_stage(new_stage)
            self.status_component.update_profile(profile)
            return self.conversation_module.generate_initial_message(), self.status_component.stage, self.status_component.user_profile, self.status_component.needs, self.status_component.matched_car_models, self.status_component.test_drive_info
        if message.lower() == "Hi AutoVend".lower():
            new_stage = "initial"
        if message.lower() == "Hi AutoVend".lower():
            new_stage = "welcome"
            self.status_component.update_profile(profile)
            self.status_component.update_stage(new_stage)
            return self.conversation_module.generate_welcome_message(self.status_component.user_profile), self.status_component.stage, self.status_component.user_profile, self.status_component.needs, self.status_component.matched_car_models, self.status_component.test_drive_info
        if self.status_component.stage["previous_stage"] == "welcome":
            new_stage = "profile_analysis"
            self.status_component.update_stage(new_stage)

        # Use thread pool to run all extractors in parallel
        future_basic_profile = self.executor.submit(self.basic_profile_extractor.extract_basic_profile, message)
        future_additional_profile = self.executor.submit(self.additional_profile_extractor.extract_additional_profile, message)
        future_expertise = self.executor.submit(self.expertise_analyst.analyze_expertise, message)
        future_explicit_needs = self.executor.submit(self.explicit_in_extractor.extract_explicit_needs, message)
        future_implicit_needs = self.executor.submit(self.implicit_deductor.extract_implicit_values, message)
        future_test_drive = self.executor.submit(self.reservation_info_extractor.extract_all_info, message)
        
        basic_profile_info = future_basic_profile.result()
        additional_profile_info = future_additional_profile.result()
        expertise_info = future_expertise.result()
        explicit_needs_info = future_explicit_needs.result()
        implicit_needs_info = future_implicit_needs.result()
        test_drive_info = future_test_drive.result()
        
        if self.status_component.stage["current_stage"] == "initial":
            ...
        elif self.status_component.stage["current_stage"] == "welcome":
            ...
        elif self.status_component.stage["current_stage"] == "farewell":
            ...
        # below stages can't directly return results
        elif self.status_component.stage["current_stage"] == "profile_analysis":
            ...
        elif self.status_component.stage["current_stage"] == "needs_analysis":
            ...
        elif (
            self.status_component.stage["current_stage"] == "car_selection_confirmation"
        ):
            ...
        elif self.status_component.stage["current_stage"] == "implicit_confirmation":
            ...
        elif self.status_component.stage["current_stage"] == "model_introduction":
            ...
        elif self.status_component.stage["current_stage"] == "reservation4s":
            ...
        elif self.status_component.stage["current_stage"] == "reservation_confirmation":
            ...

        # # llm extractors
        # future_profile = self.executor.submit(self.profile_extractor.extract_profile, user_message)
        # future_expertise = self.executor.submit(self.expertise_evaluator.evaluate_expertise, user_message)
        # future_explicit_needs = self.executor.submit(self.explicit_needs_extractor.extract_explicit_needs, user_message)
        # future_implicit_needs = self.executor.submit(self.implicit_needs_inferrer.infer_implicit_needs, user_message)
        # future_test_drive = self.executor.submit(self.test_drive_extractor.extract_test_drive_info, user_message)
        #
        # # Wait for all futures to complete and collect results
        # profile_info = future_profile.result()
        # expertise_info = future_expertise.result()
        # explicit_needs_info = future_explicit_needs.result()
        # implicit_needs_info = future_implicit_needs.result()
        # test_drive_info = future_test_drive.result()

        # Update state with results
        if basic_profile_info:
            self.status_component.update_profile(basic_profile_info)
        if additional_profile_info:
            self.status_component.update_profile(additional_profile_info)

        if expertise_info:
            self.status_component.update_profile({"expertise": expertise_info})

        if explicit_needs_info:
            self.status_component.update_explicit_needs(explicit_needs_info)

        if implicit_needs_info:
            self.status_component.update_implicit_needs(implicit_needs_info)

        if test_drive_info:
            self.status_component.update_test_drive_info(test_drive_info)

        # Once we have needs information, query matching car models
        # This depends on the results of the extractors, so it cannot be parallelized with them
        if self.status_component.needs["explicit"] or self.status_component.needs["implicit"]:
            # Combine explicit and implicit needs
            combined_needs = {**self.status_component.needs["explicit"], **self.status_component.needs["implicit"]}
            # Use existing query_car_model method
            # TODO: filter_needs is not used yet
            car_models, filter_needs = self.car_model_query.query_car_model(
                combined_needs
            )
            # Construct matched car models information
            self.status_component.update_matched_car_models(car_models)
            self.status_component.update_matched_car_model_infos(
                [
                    self.car_model_query.get_car_model_info(model) for model in car_models
                ]
            )

        # Determine next stage based on current information
        new_stage = self.stage_arbitrator.determine_stage(
            message,
            self.status_component.user_profile,
            self.status_component.needs["explicit"],
            self.status_component.needs["implicit"],
            self.status_component.test_drive_info,
        )

        # post process after extraction
        if self.status_component.stage["previous_stage"] == "welcome":
            self.status_component.update_stage("profile_analysis")
        # self.status_component.update_stage(new_stage)

        # Generate response (this still needs to be sequential after we have all the extracted info)
        response = "hard coded response"
        # response = self.conversation_module.generate_response(
        #     message,
        #     self.status_component.user_profile,
        #     self.status_component.needs["explicit"],
        #     self.status_component.needs["implicit"],
        #     self.status_component.test_drive_info,
        #     self.status_component.matched_car_models,
        #     self.status_component.matched_car_model_infos,
        #     self.status_component.stage["current_stage"],
        # )

        # Return complete result with all data
        return response, self.status_component.stage, self.status_component.user_profile, self.status_component.needs, self.status_component.matched_car_models, self.status_component.test_drive_info


    def get_car_model_details(self, model_name):
        """
        Get detailed information about a specific car model.

        Args:
            model_name (str): Name of the car model

        Returns:
            dict: Dictionary containing detailed information about the car model
        """
        return self.car_model_query.get_car_model_info(model_name)

    def reset(self):
        """Reset the assistant state."""
        self.status_component.reset()
        self.conversation_module.clear_history()

    def __del__(self):
        """Clean up resources on object deletion."""
        self.executor.shutdown(wait=False)


# Example usage
if __name__ == "__main__":
    # Initialize the AutoVend assistant
    assistant = AutoVend()

    print("AutoVend AI Car Sales Assistant")
    print("Type 'exit' to quit")
    print("-" * 50)

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() == "exit":
            break

        stage_ = {"previous_stage": "", "current_stage": "initial"}
        profile_ = {
            "phone_number": "123456789",
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
        needs_ = {
            "explicit": {
            },
            "implicit": {},
        }
        reservation_info_ = {
            "test_driver": "",
            "reservation_date": "",
            "reservation_time": "",
            "reservation_location": "",
            "selected_car_model": "",
            "reservation_phone_number": "",
            "salesman": "",
        }
        matched_car_models_ = []
        # Process the message and get results
        response, stage_, profile_, needs_, matched_car_models_, reservation_info_ = (
            assistant.generate_response(
                user_input,
                stage_,
                profile_,
                needs_,
                matched_car_models_,
                reservation_info_,
            )
        )

        # Print the assistant's response
        print(f"\nAutoVend: {response}")

        # Debug information - comment out for production
        print("\n--- Debug Info ---")
        print(f"Stage: {stage_['current_stage']}")

        if profile_:
            print(f"Extracted Profile: {json.dumps(profile_, ensure_ascii=False)}")

        if needs_:
            print(f"Extracted Needs: {json.dumps(needs_, ensure_ascii=False)}")

        if needs_["explicit"]:
            print(
                f"Explicit Needs: {json.dumps(needs_['explicit'], ensure_ascii=False)}"
            )

        if needs_["implicit"]:
            print(
                f"Implicit Needs: {json.dumps(needs_['implicit'], ensure_ascii=False)}"
            )

        if reservation_info_:
            print(
                f"Test Drive Info: {json.dumps(reservation_info_, ensure_ascii=False)}"
            )

        if matched_car_models_:
            print(
                f"Matched Car Models: {json.dumps(matched_car_models_, ensure_ascii=False)[:200]}..."
            )

        print("-" * 50)
