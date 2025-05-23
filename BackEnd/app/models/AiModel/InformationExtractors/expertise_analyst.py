import json
import re
import os
from pathlib import Path
import math

class ExpertiseAnalyst:
    """
    A class for analyzing user expertise level in automotive domain based on their conversations.
    The expertise level is a scale from 0 to 10:
    - 0-3: Novice - Uses basic, non-technical language, asks simple questions
    - 4-6: Intermediate - Uses some industry terms correctly, shows familiarity with car categories
    - 7-8: Advanced - Uses technical terminology fluently, discusses specific car features with understanding
    - 9-10: Expert - Deep technical knowledge, discusses specialized automotive concepts, may use engineering terms
    """
    
    def __init__(self):
        """
        Initialize the ExpertiseAnalyst with default values and automotive terminology lists.
        """
        # Default expertise level
        self.default_expertise = 3
        
        # Maximum expertise level observed (starting with default)
        self.max_expertise_level = self.default_expertise
        
        # Store conversation history for context
        self.conversation_history = []
        
        # Load automotive terms from QueryLabels.json
        self._load_automotive_terms()
        
        # Define technical term categories
        self._define_technical_terms()
    
    def _load_automotive_terms(self):
        """
        Load automotive terminology from QueryLabels.json
        """
        try:
            # Try to load QueryLabels.json
            base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            query_labels_path = os.path.join(base_dir, "QueryLabels.json")
            
            with open(query_labels_path, 'r', encoding='utf-8') as f:
                self.query_labels = json.load(f)
            
            # Extract technical terms from QueryLabels
            self.automotive_terms = set()
            self.automotive_values = set()
            
            for label, data in self.query_labels.items():
                # Add the label itself (without underscores)
                self.automotive_terms.add(label.replace("_", " ").lower())
                
                # Add any candidates
                if "candidates" in data:
                    for candidate in data["candidates"]:
                        self.automotive_values.add(candidate.lower())
        
        except (FileNotFoundError, json.JSONDecodeError):
            # Use a basic fallback set of terms if file not found
            self.automotive_terms = set([
                "sedan", "suv", "mpv", "powertrain", "hybrid", "electric vehicle", 
                "torque", "horsepower", "displacement", "wheelbase", "chassis"
            ])
            self.automotive_values = set([
                "gasoline engine", "diesel engine", "hybrid electric vehicle", "battery electric vehicle",
                "automatic transmission", "manual transmission", "leather seats", "autonomous driving"
            ])
    
    def _define_technical_terms(self):
        """
        Define dictionaries of technical terminology by expertise level.
        """
        # Basic terms that even novices might know
        self.basic_terms = {
            "car", "vehicle", "suv", "sedan", "electric", "hybrid", "gas", "mileage", 
            "price", "expensive", "cheap", "leather", "seats", "automatic", "manual",
            "transmission", "airbag", "warranty", "fuel economy", "safety"
        }
        
        # Intermediate terms showing some familiarity
        self.intermediate_terms = {
            "mpg", "horsepower", "hp", "mpv", "crossover", "awd", "fwd", "rwd", "4wd",
            "suspension", "turbocharged", "navigation", "infotainment", "adaptive cruise control",
            "blind spot", "lane assist", "parking assist", "trim level", "powertrain"
        }
        
        # Advanced terms showing deeper knowledge
        self.advanced_terms = {
            "torque", "displacement", "cvt", "dct", "wheelbase", "chassis", "drag coefficient",
            "direct injection", "turbocharging", "supercharging", "regenerative braking",
            "battery capacity", "kwh", "consumption", "l/100km", "electric range", "phev", "bev", "hev",
            "autonomous driving level", "zero to sixty", "acceleration", "electronically controlled dampers"
        }
        
        # Expert terms showing specialized knowledge
        self.expert_terms = {
            "monocoque", "unibody", "body-on-frame", "mcpherson strut", "multi-link suspension", 
            "double wishbone", "torsion beam", "continuous variable valve timing", "compression ratio", 
            "bore and stroke", "dual clutch", "planetary gearset", "coefficient of drag", 
            "rolling resistance", "power-to-weight ratio", "thermal management system", 
            "inverter efficiency", "energy density", "lithium-ion chemistry", "800v architecture",
            "silicon carbide inverters", "nox emissions", "electronic stability control algorithms"
        }
    
    def analyze_expertise(self, user_message):
        """
        Analyze user message to determine expertise level in automotive domain.
        
        Args:
            user_message (str): The user's message to analyze
            
        Returns:
            int: Expertise level on a scale from 0 to 10
        """
        # Add to conversation history
        self.conversation_history.append(user_message)
        
        # Normalize message
        normalized_message = user_message.lower()
        
        # Calculate expertise scores based on terminology usage
        expertise_score = self._calculate_technical_score(normalized_message)
        
        # Calculate additional score based on sentence structure and complexity
        complexity_score = self._calculate_complexity_score(normalized_message)
        
        # Calculate score based on specific value knowledge
        value_score = self._calculate_specific_value_score(normalized_message)
        
        # Calculate question sophistication score
        question_score = self._calculate_question_score(normalized_message)
        
        # Combine scores
        combined_score = self._combine_scores(
            expertise_score, complexity_score, value_score, question_score
        )
        
        # Convert to integer scale 0-10
        expertise_level = max(0, min(10, combined_score))
        expertise_level = round(expertise_level)
        
        # Update max expertise level if this message shows greater expertise
        if expertise_level > self.max_expertise_level:
            self.max_expertise_level = expertise_level
        
        return expertise_level
    
    def get_expertise_level(self):
        """
        Get the maximum expertise level observed.
        
        Returns:
            int: Maximum expertise level on a scale from 0 to 10
        """
        return self.max_expertise_level
    
    def get_expertise_category(self):
        """
        Get the expertise category based on the maximum expertise level.
        
        Returns:
            str: Expertise category (Novice, Intermediate, Advanced, or Expert)
        """
        if self.max_expertise_level <= 3:
            return "Novice"
        elif self.max_expertise_level <= 6:
            return "Intermediate"
        elif self.max_expertise_level <= 8:
            return "Advanced"
        else:
            return "Expert"
    
    def _calculate_technical_score(self, message):
        """
        Calculate score based on technical terminology usage.
        
        Args:
            message (str): Normalized user message
            
        Returns:
            float: Technical terminology score
        """
        # Count terms of each expertise level
        basic_count = sum(1 for term in self.basic_terms if re.search(r'\b' + re.escape(term) + r'\b', message))
        intermediate_count = sum(1 for term in self.intermediate_terms if re.search(r'\b' + re.escape(term) + r'\b', message))
        advanced_count = sum(1 for term in self.advanced_terms if re.search(r'\b' + re.escape(term) + r'\b', message))
        expert_count = sum(1 for term in self.expert_terms if re.search(r'\b' + re.escape(term) + r'\b', message))
        
        # Count automotive terms from QueryLabels
        automotive_terms_count = sum(1 for term in self.automotive_terms if re.search(r'\b' + re.escape(term) + r'\b', message))
        
        # Weight by expertise level
        score = (
            basic_count * 0.5 + 
            intermediate_count * 1.5 + 
            advanced_count * 3.0 + 
            expert_count * 4.5 +
            automotive_terms_count * 0.8
        )
        
        # Normalize to a 0-10 scale
        # A score of 20+ would be considered a 10
        return min(10, score / 2)
    
    def _calculate_complexity_score(self, message):
        """
        Calculate score based on sentence structure and complexity.
        
        Args:
            message (str): Normalized user message
            
        Returns:
            float: Complexity score
        """
        # Split into sentences
        sentences = re.split(r'[.!?]+', message)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return 0
        
        # Calculate average sentence length (in words)
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
        
        # Calculate vocabulary diversity (unique words / total words)
        words = message.split()
        if words:
            vocabulary_diversity = len(set(words)) / len(words)
        else:
            vocabulary_diversity = 0
        
        # Calculate linking words ratio (words like 'because', 'therefore', 'however')
        linking_words = {"because", "therefore", "however", "furthermore", "consequently", 
                        "nevertheless", "additionally", "moreover", "thus", "hence", 
                        "since", "due to", "as a result", "in contrast", "although"}
        
        linking_count = sum(1 for word in words if word.lower() in linking_words)
        linking_ratio = linking_count / len(words) if words else 0
        
        # Combine metrics
        complexity_score = (
            min(10, avg_sentence_length / 2) * 0.4 +  # Longer sentences suggest expertise
            min(10, vocabulary_diversity * 15) * 0.4 +  # Greater diversity suggests expertise
            min(10, linking_ratio * 100) * 0.2  # More linking words suggest logical argumentation
        )
        
        return min(10, complexity_score)
    
    def _calculate_specific_value_score(self, message):
        """
        Calculate score based on knowledge of specific values.
        
        Args:
            message (str): Normalized user message
            
        Returns:
            float: Specific value score
        """
        # Look for specific numeric values with units
        numeric_patterns = [
            r'\b\d+(?:\.\d+)?\s*(?:hp|kw|nm|mm|liters?|l|cc|kwh|mph|km/h)\b',  # Numbers with units
            r'\b\d{1,2}[.,]\d\s*(?:seconds?|s)\b',  # Acceleration times
            r'\b\d+\s*(?:to|-)(?:\d+)\s*(?:km/h|mph)\b',  # Speed ranges
            r'\b\d+[.,]\d+\s*(?:l/100km|mpg)\b'  # Fuel economy
        ]
        
        numeric_matches = sum(len(re.findall(pattern, message)) for pattern in numeric_patterns)
        
        # Look for specific automotive values from QueryLabels
        automotive_value_count = sum(1 for value in self.automotive_values if re.search(r'\b' + re.escape(value) + r'\b', message))
        
        # Calculate score based on specific value mentions
        score = numeric_matches * 2 + automotive_value_count
        
        # Normalize to a 0-10 scale
        # 5+ specific values would be considered a 10
        return min(10, score * 2)
    
    def _calculate_question_score(self, message):
        """
        Calculate score based on question sophistication.
        
        Args:
            message (str): Normalized user message
            
        Returns:
            float: Question sophistication score
        """
        # Check if the message contains questions
        questions = re.findall(r'[^.!?]+\?', message)
        
        if not questions:
            return 5  # Neutral score if no questions
        
        # Basic question patterns (who, what, where, when, yes/no)
        basic_patterns = [
            r'\b(?:what|which|where|when|is|are|do|does|can|could|will|would)\b.*?\?'
        ]
        
        # Advanced question patterns (why, how, comparison, trade-offs)
        advanced_patterns = [
            r'\b(?:why|how)\b.*?\?',
            r'\b(?:difference|compare|versus|vs|better|worse|trade-offs?)\b.*?\?',
            r'\b(?:advantages?|disadvantages?|pros|cons|benefits|drawbacks)\b.*?\?'
        ]
        
        # Expert question patterns (technical implications, engineering decisions)
        expert_patterns = [
            r'\b(?:engineering|designed|implemented|optimized|efficiency|performance)\b.*?\?',
            r'\b(?:implications|effects?|impacts?|influenced?|correlation)\b.*?\?',
            r'\b(?:algorithm|system|architecture|platform|framework)\b.*?\?'
        ]
        
        # Count question types
        basic_count = sum(1 for q in questions for pattern in basic_patterns if re.search(pattern, q.lower()))
        advanced_count = sum(1 for q in questions for pattern in advanced_patterns if re.search(pattern, q.lower()))
        expert_count = sum(1 for q in questions for pattern in expert_patterns if re.search(pattern, q.lower()))
        
        # Calculate weighted score
        question_score = (
            basic_count * 2 +
            advanced_count * 5 +
            expert_count * 8
        ) / max(1, len(questions))
        
        return min(10, question_score)
    
    def _combine_scores(self, technical_score, complexity_score, value_score, question_score):
        """
        Combine different component scores into a final expertise score.
        
        Args:
            technical_score (float): Score based on technical terminology
            complexity_score (float): Score based on sentence complexity
            value_score (float): Score based on specific value knowledge
            question_score (float): Score based on question sophistication
            
        Returns:
            float: Combined expertise score
        """
        # Weight the component scores
        weighted_score = (
            technical_score * 0.4 +   # Technical terminology is most important
            complexity_score * 0.2 +  # Sentence complexity is somewhat important
            value_score * 0.3 +       # Specific value knowledge is important
            question_score * 0.1      # Question sophistication is least important
        )
        
        return weighted_score


# Example usage
if __name__ == "__main__":
    analyst = ExpertiseAnalyst()
    
    # Test with different expertise levels
    test_messages = [
        # Novice level message
        "I want a nice car that looks cool and doesn't cost too much. Is red a good color?",
        
        # Intermediate level message
        "I'm looking for a mid-size SUV with good fuel economy and at least 6 airbags. Does it have blind spot detection?",
        
        # Advanced level message
        "I prefer vehicles with at least 250 horsepower and good torque distribution. The chassis height should be around 160mm for occasional off-road use, and I need a wheelbase of at least 2800mm for interior space.",
        
        # Expert level message
        "I'm comparing the energy efficiency of modern 800V EV architectures versus traditional 400V systems. The silicon carbide inverters seem to offer better thermal management, but I'm concerned about the power-to-weight ratio impacts with the current battery chemistry constraints."
    ]
    
    for message in test_messages:
        expertise_level = analyst.analyze_expertise(message)
        category = analyst.get_expertise_category()
        print(f"Message: {message}")
        print(f"Expertise level: {expertise_level}/10 ({category})")
        print(f"Maximum expertise level: {analyst.get_expertise_level()}/10")
        print("-" * 80) 