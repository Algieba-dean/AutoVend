import os
import json
import concurrent.futures
from typing import Dict, Any, List
from copy import deepcopy
import random

from utils import get_openai_client, get_openai_model, timer_decorator

from Conversation.mocked_information import mocked_information

# # LLMExtractors
from Conversation.conversation_module import ConversationModule

from LLMExtractors.profile_extractor import ProfileExtractor
from LLMExtractors.expertise_evaluator import ExpertiseEvaluator
from LLMExtractors.explicit_needs_extractor import ExplicitNeedsExtractor
from LLMExtractors.implicit_needs_inferrer import ImplicitNeedsInferrer
from LLMExtractors.test_drive_extractor import TestDriveExtractor
from LLMExtractors.llm_stage_arbitrator import LLMStageArbitrator

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

    def __init__(self, api_key=None, model=None, extractor_type="traditional"):
        """
        Initialize the AutoVend assistant.

        Args:
            api_key (str, optional): OpenAI API key. Defaults to environment variable.
            model (str, optional): OpenAI model to use. Defaults to environment variable.
            extractor_type (str, optional): Type of extractors to use ("llm" or "traditional"). Defaults to "traditional".
        """
        random.seed(213)
        self.extractor_type = extractor_type
        self.model = model or get_openai_model()
        self.api_key = api_key  # Store api_key for LLM extractors

        if self.extractor_type == "llm":
            self.profile_extractor = ProfileExtractor(
                api_key=self.api_key, model=self.model
            )
            self.expertise_evaluator = ExpertiseEvaluator(
                api_key=self.api_key, model=self.model
            )
            self.explicit_needs_extractor = ExplicitNeedsExtractor(
                api_key=self.api_key, model=self.model
            )
            self.implicit_needs_inferrer = ImplicitNeedsInferrer(
                api_key=self.api_key, model=self.model
            )
            self.test_drive_extractor = TestDriveExtractor(
                api_key=self.api_key, model=self.model
            )
            self.stage_determining_module = LLMStageArbitrator(model=self.model)
            # Set traditional extractors to None to avoid accidental use
            self.basic_profile_extractor = None
            self.additional_profile_extractor = None
            self.expertise_analyst = None
            self.explicit_in_extractor = None
            self.implicit_deductor = None
            self.reservation_info_extractor = None
        elif self.extractor_type == "traditional":
            self.basic_profile_extractor = BasicProfileExtractor()
            self.additional_profile_extractor = AdditionalProfileExtractor()
            self.expertise_analyst = ExpertiseAnalyst()
            self.explicit_in_extractor = ExplicitInOneExtractor()
            self.implicit_deductor = ImplicitDeductor()
            self.reservation_info_extractor = ReservationInfoExtractor()
            self.stage_determining_module = StageArbitrator()
            # Set LLM extractors to None
            self.profile_extractor = None
            self.expertise_evaluator = None
            self.explicit_needs_extractor = None
            self.implicit_needs_inferrer = None
            self.test_drive_extractor = None
        else:
            raise ValueError(
                f"Invalid extractor_type: {self.extractor_type}. Must be 'llm' or 'traditional'."
            )

        self.conversation_module = ConversationModule(
            api_key=self.api_key, model=self.model
        )

        # tools
        self.car_model_query = CarModelQuery()
        self.status_component = StatusComponent()
        self.mocked_information = mocked_information
        # Create a thread pool executor
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=6)

    def query_model_related_info(self):
        """
        Query model related information from the model
        """
        # This depends on the results of the extractors, so it cannot be parallelized with them
        if (
            self.status_component.needs["explicit"]
            # or self.status_component.needs["implicit"]
        ):
            # Combine explicit and implicit needs
            # no need to combine implicit needs, as they are not decided
            # combined_needs = {
            #     **self.status_component.needs["explicit"],
            #     **self.status_component.needs["implicit"],
            # }
            # Use existing query_car_model method
            # TODO: filter_needs is not used yet
            car_models, filter_needs = self.car_model_query.query_car_model(
                self.status_component.needs["explicit"]
            )
            # TODO: remove this, when query_car_model is fixed
            # Construct matched car models information
            self.status_component.update_matched_car_models(car_models)
            self.status_component.update_matched_car_model_infos(
                [self.car_model_query.get_car_model_info(model) for model in car_models]
            )

    def check_needs_analysis_jump(self, message: str):
        """
        Check if the user message is related to needs analysis
        """
        if "needs" in message.lower():
            new_stage = "needs_analysis"
            self.status_component.update_stage(new_stage)
            # handle over to needs analysis in its stage handling

    # Dispatcher method
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
        self.status_component.clear_implicit_needs() # clear implicit needs, if user wants them they will become explicict needs
        if self.extractor_type == "llm":
            return self.generate_response_llm(
                message, stage, profile, needs, matched_car_models, reservation_info
            )
        elif self.extractor_type == "traditional":
            return self.generate_response_traditional(
                message, stage, profile, needs, matched_car_models, reservation_info
            )
        else:  # Should have been caught in __init__
            raise ValueError(f"Invalid extractor_type: {self.extractor_type}")

    # Method for LLM-based extractors
    def generate_response_llm(
        self,
        user_message: str,
        stage: Dict[str, Any],  # Unused if internal state is primary
        profile: Dict[str, Any],  # Used for initial call
        needs: Dict[str, Any],  # Used for initial call
        matched_car_models: List[str],  # Used for initial call
        reservation_info: Dict[str, Any],  # Used for initial call
    ):
        # Initial message handling (common to both, but placed here for logical flow if refactoring)
        if user_message == "":
            new_stage = "initial"
            self.status_component.update_stage(new_stage)
            self.status_component.update_profile(profile)
            self.status_component.update_explicit_needs(needs.get("explicit", {}))
            self.status_component.update_implicit_needs(needs.get("implicit", {}))
            self.status_component.update_test_drive_info(reservation_info)
            self.status_component.update_matched_car_models(matched_car_models)
            return (
                self.conversation_module.generate_initial_message(),
                self.status_component.stage,
                self.status_component.user_profile,
                self.status_component.needs,
                self.status_component.matched_car_models,
                self.status_component.test_drive_info,
            )

        # LLM-specific extraction
        future_profile = self.executor.submit(
            self.profile_extractor.extract_profile, user_message
        )
        future_expertise = self.executor.submit(
            self.expertise_evaluator.evaluate_expertise, user_message
        )
        future_explicit_needs = self.executor.submit(
            self.explicit_needs_extractor.extract_explicit_needs, user_message
        )
        future_implicit_needs = self.executor.submit(
            self.implicit_needs_inferrer.infer_implicit_needs, user_message
        )
        future_test_drive = self.executor.submit(
            self.test_drive_extractor.extract_test_drive_info, user_message
        )

        profile_info = future_profile.result()
        expertise_info = future_expertise.result()
        explicit_needs_info = future_explicit_needs.result()
        implicit_needs_info = future_implicit_needs.result()
        test_drive_info = future_test_drive.result()

        # Update state from LLM extractors
        if profile_info:
            self.status_component.update_profile(profile_info)
        if expertise_info:
            if isinstance(expertise_info, str):
                self.status_component.update_profile({"expertise": expertise_info})
            elif isinstance(expertise_info, dict) and "expertise" in expertise_info:
                self.status_component.update_profile(
                    {"expertise": expertise_info["expertise"]}
                )

        if explicit_needs_info:
            self.status_component.update_explicit_needs(explicit_needs_info)
        if implicit_needs_info:
            self.status_component.update_implicit_needs(implicit_needs_info)
        if test_drive_info:
            self.status_component.update_test_drive_info(test_drive_info, is_before_reservation=True)

        # Common "Hi AutoVend" logic (could be further refactored if needed)
        if user_message.lower().replace(" ","") == "HiAutoVend".lower():
            self.status_component.update_stage("welcome")
            normal_welcome_message = self.conversation_module.generate_welcome_message(
                self.status_component.user_profile
            )
            begin_profile_message = self.conversation_module.generate_profile_response(
                user_message,
                self.status_component.user_profile,
                {},
                {},
                {},
                [],
                [],
                "profile_analysis",
            )
            self.status_component.update_stage("profile_analysis")
            autovend_response = f"{normal_welcome_message}.{begin_profile_message}"
            return (
                autovend_response,
                self.status_component.stage,
                self.status_component.user_profile,
                self.status_component.needs,
                self.status_component.matched_car_models,
                self.status_component.test_drive_info,
            )

        # LLM Stage specific logic
        if self.status_component.stage["current_stage"] == "profile_analysis":
            if self.status_component.is_all_basic_info_done():
                self.status_component.update_stage("needs_analysis")
            else:
                profile_message = self.conversation_module.generate_profile_response(
                    user_message,
                    self.status_component.user_profile,
                    self.status_component.needs["explicit"],
                    self.status_component.needs["implicit"],
                    self.status_component.test_drive_info,
                    self.status_component.matched_car_models,
                    self.status_component.matched_car_model_infos,
                    self.status_component.stage["current_stage"],
                )
                return (
                    profile_message,
                    self.status_component.stage,
                    self.status_component.user_profile,
                    self.status_component.needs,
                    self.status_component.matched_car_models,
                    self.status_component.test_drive_info,
                )

        stage_arbitrator_history = self.conversation_module.get_history_for_llm_arbitrator(user_message)
        might_new_stage = self.stage_determining_module.get_chat_stage(
            stage_arbitrator_history, self.status_component.user_profile
        )
        if might_new_stage == "needs_analysis" or might_new_stage == "model_introduce":
            self.status_component.update_stage(might_new_stage)
            self.status_component.update_explicit_needs(needs.get("explicit", {}))
            self.status_component.update_implicit_needs(needs.get("implicit", {}))
            self.query_model_related_info()  # update already matched car models and car model infos
            autovend_response = (
                self.conversation_module.generate_response_for_big_needs_llm(
                    user_message,
                    self.status_component.user_profile,
                    self.status_component.needs["explicit"],
                    self.status_component.needs["implicit"],
                    self.status_component.test_drive_info,
                    self.status_component.matched_car_models,
                    self.status_component.matched_car_model_infos,
                    self.status_component.stage["current_stage"],
                )
            )
            return (
                autovend_response,
                self.status_component.stage,
                self.status_component.user_profile,
                self.status_component.needs,
                self.status_component.matched_car_models,
                self.status_component.test_drive_info,
            )
        if might_new_stage == "reservation4s" or self.status_component.stage["current_stage"] == "reservation4s":
            self.status_component.update_stage(might_new_stage)
            self.status_component.update_test_drive_info(reservation_info)
            self.status_component.update_matched_car_models(matched_car_models)
        if self.status_component.stage["current_stage"] == "reservation4s" and self.status_component.is_all_basic_reservation_info_done():
            self.status_component.update_stage("farewell")
        if might_new_stage == "farewell" or self.status_component.stage["current_stage"] == "farewell":
            return self.handle_farewell()

        # Common stage processing logic (shared with traditional, but called with LLM context)
        return self._handle_common_stage_logic(user_message)

    def handle_farewell(self):
        self.status_component.update_stage("farewell")
        farewell_message = "Thank you for your time. Have a nice day!"
        if self.status_component.is_all_basic_reservation_info_done():
            farewell_message = f"I already contact {self.status_component.test_drive_info.get('reservation_location', '')} for you. They will contact you shortly. Thank you for your time. Have a nice day!"
        final_user_profile = deepcopy(self.status_component.user_profile)
        final_needs = deepcopy(self.status_component.needs)
        final_matched_car_models = deepcopy(self.status_component.matched_car_models)
        final_test_drive_info = deepcopy(self.status_component.test_drive_info)
        self.reset()
        return (
            farewell_message,
            self.status_component.stage,
            final_user_profile,
            final_needs,
            final_matched_car_models,
            final_test_drive_info,
        )
        

    # Method for Traditional extractors
    def generate_response_traditional(
        self,
        user_message: str,
        stage: Dict[str, Any],  # Unused if internal state is primary
        profile: Dict[str, Any],  # Used for initial call
        needs: Dict[str, Any],  # Used for initial call
        matched_car_models: List[str],  # Used for initial call
        reservation_info: Dict[str, Any],  # Used for initial call
    ):
        if user_message == "":  # Initial message handling
            new_stage = "initial"
            self.status_component.update_stage(new_stage)
            self.status_component.update_profile(profile)
            self.status_component.update_explicit_needs(needs.get("explicit", {}))
            self.status_component.update_implicit_needs(needs.get("implicit", {}))
            self.status_component.update_test_drive_info(reservation_info)
            self.status_component.update_matched_car_models(matched_car_models)
            return (
                self.conversation_module.generate_initial_message(),
                self.status_component.stage,
                self.status_component.user_profile,
                self.status_component.needs,
                self.status_component.matched_car_models,
                self.status_component.test_drive_info,
            )

        # Traditional extraction
        future_basic_profile = self.executor.submit(
            self.basic_profile_extractor.extract_basic_profile, user_message
        )
        future_additional_profile = self.executor.submit(
            self.additional_profile_extractor.extract_additional_profile, user_message
        )
        future_expertise = self.executor.submit(
            self.expertise_analyst.analyze_expertise, user_message
        )
        future_explicit_needs = self.executor.submit(
            self.explicit_in_extractor.extract_explicit_needs, user_message
        )
        future_implicit_needs = self.executor.submit(
            self.implicit_deductor.extract_implicit_values, user_message
        )
        future_test_drive = self.executor.submit(
            self.reservation_info_extractor.extract_all_info, user_message
        )

        basic_profile_info = future_basic_profile.result()
        additional_profile_info = future_additional_profile.result()
        expertise_info = future_expertise.result()
        explicit_needs_info = future_explicit_needs.result()
        implicit_needs_info = future_implicit_needs.result()
        test_drive_info = future_test_drive.result()

        # Update state from Traditional extractors
        if basic_profile_info:
            self.status_component.update_profile(basic_profile_info)
        if additional_profile_info:
            self.status_component.update_profile(additional_profile_info)
        if expertise_info:
            self.status_component.update_profile({"expertise": str(expertise_info)})
        if explicit_needs_info:
            self.status_component.update_explicit_needs(explicit_needs_info)
        if implicit_needs_info:
            self.status_component.update_implicit_needs(implicit_needs_info)
        if test_drive_info:
            self.status_component.update_test_drive_info(test_drive_info)

        # Common "Hi AutoVend" logic
        if user_message.lower() == "Hi AutoVend".lower():
            self.status_component.update_stage("welcome")
            normal_welcome_message = self.conversation_module.generate_welcome_message(
                self.status_component.user_profile
            )
            begin_profile_message = self.conversation_module.generate_profile_response(
                user_message,
                self.status_component.user_profile,
                {},
                {},
                {},
                [],
                [],
                "profile_analysis",
            )
            self.status_component.update_stage("profile_analysis")
            autovend_response = f"{normal_welcome_message}\\n{begin_profile_message}"
            return (
                autovend_response,
                self.status_component.stage,
                self.status_component.user_profile,
                self.status_component.needs,
                self.status_component.matched_car_models,
                self.status_component.test_drive_info,
            )

        # Traditional Stage specific logic
        if self.status_component.stage["current_stage"] == "profile_analysis":
            if self.status_component.is_all_basic_info_done():
                self.status_component.update_stage("needs_analysis")
            else:
                profile_message = self.conversation_module.generate_profile_response(
                    user_message,
                    self.status_component.user_profile,
                    self.status_component.needs["explicit"],
                    self.status_component.needs["implicit"],
                    self.status_component.test_drive_info,
                    self.status_component.matched_car_models,
                    self.status_component.matched_car_model_infos,
                    self.status_component.stage["current_stage"],
                )
                return (
                    profile_message,
                    self.status_component.stage,
                    self.status_component.user_profile,
                    self.status_component.needs,
                    self.status_component.matched_car_models,
                    self.status_component.test_drive_info,
                )

        self.check_needs_analysis_jump(user_message)

        might_new_stage = self.stage_determining_module.determine_stage(
            user_message,
            self.status_component.user_profile,
            self.status_component.needs["explicit"],
            self.status_component.needs["implicit"],
            self.status_component.test_drive_info,
        )

        if might_new_stage:
            if (
                self.status_component.stage["current_stage"]
                not in [
                    "needs_analysis",
                    "car_selection_confirmation",
                    "implicit_confirmation",
                    "model_introduction",
                ]
                and might_new_stage == "needs_analysis"
            ):
                self.status_component.update_stage(might_new_stage)

            if (
                self.status_component.stage["current_stage"]
                not in ["reservation4s", "reservation_confirmation"]
                and might_new_stage == "reservation4s"
            ):
                self.status_component.update_stage(might_new_stage)
            # More general update if needed

        if self.status_component.stage["current_stage"] == "needs_analysis":
            self.query_model_related_info()
            if self.status_component.is_all_basic_needs_done():
                self.status_component.update_stage("car_selection_confirmation")

        if self.status_component.stage["current_stage"] == "reservation4s":
            if self.status_component.is_all_basic_reservation_info_done():
                self.status_component.update_stage("reservation_confirmation")
            else:
                reservation_message = (
                    self.conversation_module.generate_reservation_response(
                        user_message,
                        self.status_component.user_profile,
                        self.status_component.needs["explicit"],
                        self.status_component.needs["implicit"],
                        self.status_component.test_drive_info,
                        self.status_component.matched_car_models,
                        self.status_component.matched_car_model_infos,
                        self.status_component.stage["current_stage"],
                        self.mocked_information.mocked_stores,
                        self.mocked_information.mocked_dates,
                        self.mocked_information.salesman_names,
                    )
                )

        # Common stage processing logic
        return self._handle_common_stage_logic(user_message)

    # Helper method for common stage handling logic after arbitrator and updates
    def _handle_common_stage_logic(self, user_message: str):
        if self.status_component.stage["current_stage"] == "needs_analysis" and self.status_component.is_all_basic_needs_done():
            self.status_component.update_stage("car_selection_confirmation")

        if self.status_component.stage["current_stage"] == "reservation4s":
            if self.status_component.is_all_basic_reservation_info_done():
                self.status_component.update_stage("reservation_confirmation")
            else:
                reservation_message = (
                    self.conversation_module.generate_reservation_response(
                        user_message,
                        self.status_component.user_profile,
                        self.status_component.needs["explicit"],
                        self.status_component.needs["implicit"],
                        self.status_component.test_drive_info,
                        self.status_component.matched_car_models,
                        self.status_component.matched_car_model_infos,
                        self.status_component.stage["current_stage"],
                        self.mocked_information.mocked_stores,
                        self.mocked_information.mocked_dates,
                        self.mocked_information.salesman_names,
                    )
                )
                return (
                    reservation_message,
                    self.status_component.stage,
                    self.status_component.user_profile,
                    self.status_component.needs,
                    self.status_component.matched_car_models,
                    self.status_component.test_drive_info,
                )

        if self.status_component.stage["current_stage"] == "reservation_confirmation": # llm don't have this stage
            confirmation_message = (
                self.conversation_module.generate_reservation_response(
                    user_message,
                    self.status_component.user_profile,
                    self.status_component.needs["explicit"],
                    self.status_component.needs["implicit"],
                    self.status_component.test_drive_info,
                    self.status_component.matched_car_models,
                    self.status_component.matched_car_model_infos,
                    self.status_component.stage["current_stage"],
                    self.mocked_information.mocked_stores,
                    self.mocked_information.mocked_dates,
                    self.mocked_information.salesman_names,
                )
            )
            self.status_component.update_stage("farewell")
            return (
                confirmation_message,
                self.status_component.stage,
                self.status_component.user_profile,
                self.status_component.needs,
                self.status_component.matched_car_models,
                self.status_component.test_drive_info,
            )


        # Fallback / Generic response generation for stages not explicitly returning a message above
        # unknown stage
        autovend_response = f"Unknown stage {self.status_component.stage['current_stage']}. How can I assist you further?"
        return (
            autovend_response,
            self.status_component.stage,
            self.status_component.user_profile,
            self.status_component.needs,
            self.status_component.matched_car_models,
            self.status_component.test_drive_info,
        )


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
    # Choose extractor_type: "llm" or "traditional"
    # assistant = AutoVend(extractor_type="traditional")
    assistant = AutoVend(extractor_type="llm")  # Example: use LLM extractors

    print("AutoVend AI Car Sales Assistant")
    print(
        f"Using extractor type: {assistant.extractor_type}"
    )  # Show which type is used
    print("Type 'exit' to quit")
    print("-" * 50)

    # Initial state for the first call to generate_response
    # For subsequent calls, these are ignored as the assistant maintains state internally.
    current_stage_info = {"previous_stage": "", "current_stage": "initial"}
    current_profile = {
        "phone_number": "1888888",
        "age": "",
        "user_title": "Mr.",
        "name": "John",
        "target_driver": "Self",
        "expertise": "5",
        "additional_information": {
            "family_size": "1",
            "price_sensitivity": "5",
            "residence": "Beijing",
            "parking_conditions": "Garage",
        },
        "connection_information": {
            "connection_phone_number": "",
            "connection_id_relationship": "",
            "connection_user_name": "",
        },
    }
    current_needs = {
        "explicit": {
        },
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

    # Simulate first call with empty message to get initial greeting
    (
        initial_response,
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    ) = assistant.generate_response(
        "",
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    )
    # confirm to use autovend
    (
        initial_response,
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    ) = assistant.generate_response(
        "Hi AutoVend",
        current_stage_info,
        current_profile,
        current_needs,
        current_matched_car_models,
        current_reservation_info,
    )
    print(f"AutoVend: {initial_response}")
    print("-" * 50)

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() == "exit":
            break

        # For subsequent calls, the state variables (current_stage_info, etc.) are passed
        # but the assistant primarily uses its internal self.status_component.
        # The design could be refactored so generate_response only takes user_input
        # and relies entirely on internal state after the first call.
        # However, to match the existing signature:
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
