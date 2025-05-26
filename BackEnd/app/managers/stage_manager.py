from typing import Dict, Any, Optional
from enum import Enum
from datetime import datetime

class Stage(Enum):
    """Enumeration of possible conversation stages"""
    WELCOME = "welcome"
    PROFILE_ANALYSIS = "profile_analysis"
    NEEDS_ANALYSIS = "needs_analysis"
    CAR_SELECTION = "car_selection_confirmation"
    RESERVATION_4S = "reservation4s"
    RESERVATION_CONFIRMATION = "reservation_confirmation"
    FAREWELL = "farewell"

class StageTransition:
    """Represents a stage transition with validation rules"""
    def __init__(self, from_stage: Stage, to_stage: Stage, conditions: Dict[str, Any] = None):
        self.from_stage = from_stage
        self.to_stage = to_stage
        self.conditions = conditions or {}

class StageManager:
    """Manages conversation stage transitions and state"""
    
    def __init__(self):
        """Initialize the stage manager"""
        self.current_stage = Stage.WELCOME
        self.previous_stage = None
        self.stage_history = []
        self.stage_data = {}
        
        # Define valid stage transitions
        self.valid_transitions = {
            Stage.WELCOME: [Stage.PROFILE_ANALYSIS, Stage.NEEDS_ANALYSIS],
            Stage.PROFILE_ANALYSIS: [Stage.NEEDS_ANALYSIS],
            Stage.NEEDS_ANALYSIS: [Stage.CAR_SELECTION],
            Stage.CAR_SELECTION: [Stage.RESERVATION_4S],
            Stage.RESERVATION_4S: [Stage.RESERVATION_CONFIRMATION],
            Stage.RESERVATION_CONFIRMATION: [Stage.FAREWELL],
            Stage.FAREWELL: []  # End state
        }
    
    def can_transition_to(self, new_stage: Stage) -> bool:
        """Check if transition to new stage is valid"""
        return new_stage in self.valid_transitions.get(self.current_stage, [])
    
    def transition_to(self, new_stage: Stage, data: Dict[str, Any] = None) -> bool:
        """Transition to a new stage if valid"""
        if not self.can_transition_to(new_stage):
            return False
        
        # Store current stage in history
        self.stage_history.append({
            "from_stage": self.current_stage.value,
            "to_stage": new_stage.value,
            "timestamp": datetime.now().isoformat(),
            "data": data
        })
        
        # Update stages
        self.previous_stage = self.current_stage
        self.current_stage = new_stage
        
        # Store stage-specific data
        if data:
            self.stage_data[new_stage.value] = data
        
        return True
    
    def get_current_stage(self) -> Dict[str, Any]:
        """Get current stage information"""
        return {
            "previous_stage": self.previous_stage.value if self.previous_stage else "",
            "current_stage": self.current_stage.value,
            "stage_data": self.stage_data.get(self.current_stage.value, {})
        }
    
    def get_stage_history(self) -> list:
        """Get complete stage transition history"""
        return self.stage_history
    
    def reset(self):
        """Reset stage manager to initial state"""
        self.current_stage = Stage.WELCOME
        self.previous_stage = None
        self.stage_history = []
        self.stage_data = {}
    
    def validate_stage_data(self, stage: Stage, data: Dict[str, Any]) -> bool:
        """Validate data for a specific stage"""
        # Example validation rules for different stages
        validation_rules = {
            Stage.RESERVATION_CONFIRMATION: {
                "required_fields": ["test_driver", "reservation_date", "reservation_time", "reservation_location"]
            },
            Stage.CAR_SELECTION: {
                "required_fields": ["matched_car_models"]
            }
        }
        
        if stage not in validation_rules:
            return True
        
        rules = validation_rules[stage]
        required_fields = rules.get("required_fields", [])
        
        return all(field in data and data[field] for field in required_fields) 