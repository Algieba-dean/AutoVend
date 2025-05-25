from datetime import datetime
from .AiModel.auto_vend_ai import AutoVend
from typing import Dict, Any, List
import random

class AiModelMessage:
    """AI model message class for AutoVend application"""
    def __init__(self):
      self.ai_model = AutoVend(extractor_type="llm")
    def generate_response(self,message:str,stage:Dict[str, Any], profile:Dict[str, Any], needs:Dict[str, Any], matched_car_models:List[str], reservation_info:Dict[str, Any]):
      result = self.ai_model.generate_response(message,stage,profile,needs,matched_car_models,reservation_info)
      print(result)
      return result