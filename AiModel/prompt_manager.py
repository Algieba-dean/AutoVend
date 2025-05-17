import json
import os

class PromptManager:
    """
    A class for managing and loading prompt templates from external files.
    Helps reduce the size of prompts by loading only what's needed.
    """
    
    def __init__(self, templates_dir="prompts"):
        """
        Initialize the PromptManager.
        
        Args:
            templates_dir (str): Directory containing prompt template files
        """
        self.templates = {}
        self.load_templates(templates_dir)
    
    def load_templates(self, templates_dir):
        """
        Load all template files from the specified directory.
        
        Args:
            templates_dir (str): Directory containing prompt template files
        """
        # Create directory if it doesn't exist
        if not os.path.exists(templates_dir):
            os.makedirs(templates_dir)
            
        # Load all JSON files in the templates directory
        if os.path.isdir(templates_dir):
            for filename in os.listdir(templates_dir):
                if filename.endswith(".json"):
                    template_type = filename[:-5]  # Remove .json extension
                    try:
                        with open(os.path.join(templates_dir, filename), "r", encoding="utf-8") as f:
                            self.templates[template_type] = json.load(f)
                    except (json.JSONDecodeError, FileNotFoundError) as e:
                        print(f"Error loading template {filename}: {e}")
    
    def get_base_prompt(self):
        """
        Get the base prompt template that contains common instructions.
        
        Returns:
            str: Base prompt template
        """
        return self.templates.get("base", {}).get("content", "")
    
    def get_expertise_prompt(self, level):
        """
        Get expertise-specific prompt based on the user's expertise level.
        
        Args:
            level (int): User's expertise level (0-10)
            
        Returns:
            str: Expertise-specific prompt
        """
        expertise_levels = self.templates.get("expertise", {})
        if 0 <= level <= 3:
            return expertise_levels.get("novice", "")
        elif 4 <= level <= 6:
            return expertise_levels.get("intermediate", "")
        elif 7 <= level <= 8:
            return expertise_levels.get("advanced", "")
        else:
            return expertise_levels.get("expert", "")
    
    def get_stage_prompt(self, stage):
        """
        Get stage-specific prompt based on the current conversation stage.
        
        Args:
            stage (str): Current conversation stage
            
        Returns:
            str: Stage-specific prompt
        """
        return self.templates.get("stages", {}).get(stage, "") 