from datetime import datetime
from typing import Dict, Any, List
import random

class AiModelMessage:
    """AI model message class for AutoVend application"""
    @classmethod
    def generate_response(cls, message:str,stage:Dict[str, Any], profile:Dict[str, Any], needs:Dict[str, Any], matched_car_models:List[str], reservation_info:Dict[str, Any]):
        """Generate a response based on the message, stage, profile, needs, matched_car_models, reservation_info"""
        stage_ = {
        "previous_stage": "welcome",
        "current_stage": "needs_analysis"
        }
        profile_ = {
    "phone_number": "123456789",
    "age": "20-35",
    "user_title": "Mr. Zhang",
    "name": "John",
    "target_driver": "Self",
    "expertise": "6",
    "additional_information": {
      "family_size": "3",
      "price_sensitivity": "Medium",
      "residence": "China+Beijing+Haidian",
      "parking_conditions": "Allocated Parking Space"
    },
    "connection_information": {
      "connection_phone_number": "",
      "connection_id_relationship": "",
      "connection_user_name": ""
    }
  }
        needs_ = {
    "explicit": {
      "powertrain_type": "Battery Electric Vehicle",
      "vehicle_category_bottom": "Compact SUV",
      "driving_range": "Above 800km"
    },
    "implicit": {
      "energy_consumption_level": "Low"
    }
  }
        reservation_info_ = {
    "test_driver": "",
    "reservation_date": "",
    "reservation_time": "",
    "reservation_location": "",
    "selected_car_model":"",
    "reservation_phone_number": "",
    "salesman": ""
  }
        matched_car_models_ = ["Model 3", "Model S", "Model X", "Model Y"]
        response = "test reponse"
        return response, stage_,profile_,needs_,matched_car_models_,reservation_info_
