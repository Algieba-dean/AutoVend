import re
from datetime import datetime, timedelta
# from utils import get_current_time, timer_decorator

def get_current_time():
    """
    Get the current time in the format of YYYY-MM-DD HH:MM:SS
    """
    return datetime.now().time().strftime("%H:%M:%S")
class TimeExtractor:
    """
    A class for extracting time information from user input strings.
    Handles explicit time formats, relative times, and special time references.
    Time extraction is accurate to the minute.
    """
    
    def __init__(self):
        # Special time references mapping (in 24-hour format)
        self.special_times = {
            "midnight": "00:00",
            "noon": "12:00",
            "midday": "12:00",
            "lunchtime": "12:00",
            "breakfast time": "08:00",
            "breakfast": "08:00",
            "dinner time": "18:00",
            "dinner": "18:00",
            "morning": "08:00",
            "afternoon": "14:00",
            "evening": "19:00",
            "night": "21:00"
        }
        
        # AM/PM indicators
        self.am_indicators = ["am", "a.m.", "a.m", "morning"]
        self.pm_indicators = ["pm", "p.m.", "p.m", "evening", "night", "afternoon"]
        
        # Time unit mapping (for relative times)
        self.time_units = {
            "minute": 1,
            "minutes": 1,
            "min": 1,
            "mins": 1,
            "hour": 60,
            "hours": 60,
            "hr": 60,
            "hrs": 60
        }
    
    # @timer_decorator
    def extract_times(self, text):
        """
        Extract time information from the given text.
        
        Args:
            text (str): The input text to extract times from
            
        Returns:
            list: A list of datetime objects representing extracted times
        """
        # Get current time as reference
        current_time_str = get_current_time()
        current_time = datetime.strptime(current_time_str, "%H:%M:%S").time()
        current_date = datetime.now().date()
        
        # Create a full datetime object for current time
        current_datetime = datetime.combine(current_date, current_time)
        
        extracted_times = []
        
        # Convert text to lowercase for easier matching
        text = text.lower()
        
        # Extract explicit times (e.g., "3:45", "3:45 PM", "15:45")
        extracted_times.extend(self._extract_explicit_times(text, current_datetime))
        
        # Extract hour-only times (e.g., "at 5", "at 5 PM")
        extracted_times.extend(self._extract_hour_only_times(text, current_datetime))
        
        # Extract special time references (e.g., "at noon", "midnight")
        extracted_times.extend(self._extract_special_times(text, current_datetime))
        
        # Extract relative times (e.g., "in 2 hours", "30 minutes later")
        extracted_times.extend(self._extract_relative_times(text, current_datetime))
        
        # Extract half-hour expressions (e.g., "half past 3", "half to 4")
        extracted_times.extend(self._extract_half_hour_expressions(text, current_datetime))
        
        return extracted_times
    
    def _extract_explicit_times(self, text, current_datetime):
        """
        Extract explicit time mentions like "3:45" or "3:45 PM".
        
        Args:
            text (str): The input text
            current_datetime (datetime): The current datetime
            
        Returns:
            list: List of datetime objects
        """
        times = []
        
        # Pattern for standard time format (e.g., "3:45", "15:45", "03:45")
        time_pattern = r'\b([0-1]?[0-9]|2[0-3]):([0-5][0-9])(?:\s*([ap]\.?m\.?)?)\b'
        time_matches = re.finditer(time_pattern, text)
        
        for match in time_matches:
            hour_str, minute_str, ampm = match.groups()
            
            try:
                hour = int(hour_str)
                minute = int(minute_str)
                
                # Handle AM/PM if specified
                if ampm and ampm.startswith('p') and hour < 12:
                    hour += 12
                elif ampm and ampm.startswith('a') and hour == 12:
                    hour = 0
                
                # Create datetime with current date
                time_obj = current_datetime.replace(hour=hour, minute=minute, second=0, microsecond=0)
                times.append(time_obj)
            except ValueError:
                continue
        
        return times
    
    def _extract_hour_only_times(self, text, current_datetime):
        """
        Extract hour-only time mentions like "at 5" or "at 5 PM".
        
        Args:
            text (str): The input text
            current_datetime (datetime): The current datetime
            
        Returns:
            list: List of datetime objects
        """
        times = []
        
        # Find instances of digits followed by optional AM/PM indicators
        # Look for patterns like "at 5", "at 5pm", "5 in the evening"
        hour_pattern = r'\b(?:at|@)\s*([0-1]?[0-9]|2[0-3])(?!\s*:)(?:\s*([ap]\.?m\.?)?)\b|\b([0-1]?[0-9]|2[0-3])(?!\s*:)\s*(?:([ap]\.?m\.?)|(?:in the|at)\s*(morning|afternoon|evening|night))\b'
        hour_matches = re.finditer(hour_pattern, text)
        
        for match in hour_matches:
            groups = match.groups()
            
            # Extract hour and AM/PM indicator from different match groups
            hour_str = next((g for g in groups[:3] if g is not None), None)
            ampm_indicator = next((g for g in groups[1:] if g is not None), None)
            
            if not hour_str:
                continue
                
            try:
                hour = int(hour_str)
                
                # Determine if it's AM or PM based on indicators
                is_pm = False
                if ampm_indicator:
                    ampm_lower = ampm_indicator.lower()
                    is_pm = any(pm in ampm_lower for pm in self.pm_indicators)
                elif hour < 6:  # Assume PM for ambiguous early hours (1-5)
                    is_pm = True
                
                # Adjust hour for PM
                if is_pm and hour < 12:
                    hour += 12
                elif not is_pm and hour == 12:
                    hour = 0
                
                # Create datetime with current date and minute set to 0
                time_obj = current_datetime.replace(hour=hour, minute=0, second=0, microsecond=0)
                times.append(time_obj)
            except ValueError:
                continue
        
        # Pattern for "X o'clock"
        oclock_pattern = r'\b([0-1]?[0-9]|2[0-3])\s*o\'?clock(?:\s*([ap]\.?m\.?)?)\b'
        oclock_matches = re.finditer(oclock_pattern, text)
        
        for match in oclock_matches:
            hour_str, ampm = match.groups()
            
            try:
                hour = int(hour_str)
                
                # Handle AM/PM
                if ampm and ampm.startswith('p') and hour < 12:
                    hour += 12
                elif ampm and ampm.startswith('a') and hour == 12:
                    hour = 0
                elif hour < 6:  # Assume PM for ambiguous early hours without AM/PM
                    hour += 12
                
                # Create datetime with current date and minute set to 0
                time_obj = current_datetime.replace(hour=hour, minute=0, second=0, microsecond=0)
                times.append(time_obj)
            except ValueError:
                continue
        
        return times
    
    def _extract_special_times(self, text, current_datetime):
        """
        Extract special time references like "noon" or "midnight".
        
        Args:
            text (str): The input text
            current_datetime (datetime): The current datetime
            
        Returns:
            list: List of datetime objects
        """
        times = []
        
        for special_time, time_value in self.special_times.items():
            if special_time in text:
                hour, minute = map(int, time_value.split(':'))
                time_obj = current_datetime.replace(hour=hour, minute=minute, second=0, microsecond=0)
                times.append(time_obj)
        
        return times
    
    def _extract_relative_times(self, text, current_datetime):
        """
        Extract relative time references like "in 2 hours" or "30 minutes later".
        
        Args:
            text (str): The input text
            current_datetime (datetime): The current datetime
            
        Returns:
            list: List of datetime objects
        """
        times = []
        
        # Pattern for "in X hours/minutes" or "X hours/minutes later"
        relative_pattern = r'\b(?:in|after)\s+(\d+)\s+(' + '|'.join(self.time_units.keys()) + r')|(\d+)\s+(' + '|'.join(self.time_units.keys()) + r')\s+(?:later|from now)\b'
        relative_matches = re.finditer(relative_pattern, text)
        
        for match in relative_matches:
            groups = match.groups()
            
            # Extract amount and unit from different match groups
            amount_str = next((g for g in [groups[0], groups[2]] if g is not None), None)
            unit = next((g for g in [groups[1], groups[3]] if g is not None), None)
            
            if amount_str and unit:
                try:
                    amount = int(amount_str)
                    minutes_to_add = amount * self.time_units[unit]
                    
                    # Create new datetime by adding minutes
                    time_obj = current_datetime + timedelta(minutes=minutes_to_add)
                    times.append(time_obj)
                except (ValueError, KeyError):
                    continue
        
        return times
    
    def _extract_half_hour_expressions(self, text, current_datetime):
        """
        Extract half-hour expressions like "half past 3" or "half to 4".
        
        Args:
            text (str): The input text
            current_datetime (datetime): The current datetime
            
        Returns:
            list: List of datetime objects
        """
        times = []
        
        # Pattern for "half past X" (X:30)
        half_past_pattern = r'half\s+past\s+([0-1]?[0-9]|2[0-3])(?:\s*([ap]\.?m\.?)?)?'
        half_past_matches = re.finditer(half_past_pattern, text)
        
        for match in half_past_matches:
            hour_str, ampm = match.groups()
            
            try:
                hour = int(hour_str)
                
                # Handle AM/PM
                if ampm and ampm.startswith('p') and hour < 12:
                    hour += 12
                elif ampm and ampm.startswith('a') and hour == 12:
                    hour = 0
                
                # Create datetime with current date, minute set to 30
                time_obj = current_datetime.replace(hour=hour, minute=30, second=0, microsecond=0)
                times.append(time_obj)
            except ValueError:
                continue
        
        # Pattern for "half to X" (X-1:30)
        half_to_pattern = r'half\s+to\s+([0-1]?[0-9]|2[0-3])(?:\s*([ap]\.?m\.?)?)?'
        half_to_matches = re.finditer(half_to_pattern, text)
        
        for match in half_to_matches:
            hour_str, ampm = match.groups()
            
            try:
                hour = int(hour_str)
                
                # Handle AM/PM
                if ampm and ampm.startswith('p') and hour < 12:
                    hour += 12
                elif ampm and ampm.startswith('a') and hour == 12:
                    hour = 0
                
                # For "half to X", the time is (X-1):30
                # If hour is 1/13, we need to handle midnight/noon special case
                if hour == 1:
                    hour = 0
                elif hour == 13:
                    hour = 12
                else:
                    hour -= 1
                
                # Create datetime with current date, minute set to 30
                time_obj = current_datetime.replace(hour=hour, minute=30, second=0, microsecond=0)
                times.append(time_obj)
            except ValueError:
                continue
        
        # Handle "X thirty" pattern (e.g., "3 thirty", "three thirty")
        thirty_pattern = r'\b([0-1]?[0-9]|2[0-3])\s+thirty(?:\s*([ap]\.?m\.?)?)?'
        thirty_matches = re.finditer(thirty_pattern, text)
        
        for match in thirty_matches:
            hour_str, ampm = match.groups()
            
            try:
                hour = int(hour_str)
                
                # Handle AM/PM
                if ampm and ampm.startswith('p') and hour < 12:
                    hour += 12
                elif ampm and ampm.startswith('a') and hour == 12:
                    hour = 0
                
                # Create datetime with current date, minute set to 30
                time_obj = current_datetime.replace(hour=hour, minute=30, second=0, microsecond=0)
                times.append(time_obj)
            except ValueError:
                continue
        
        return times
    
    def format_time(self, time_obj, format_str="%H:%M"):
        """
        Format a datetime object as time string.
        
        Args:
            time_obj (datetime): The datetime object to format
            format_str (str): The format string
            
        Returns:
            str: Formatted time string
        """
        return time_obj.strftime(format_str)


# Example usage
if __name__ == "__main__":
    extractor = TimeExtractor()
    
    # Test with various time expressions
    test_texts = [
        "Let's meet at 3:30 PM",
        "The meeting is scheduled for 15:45",
        "We'll have a call at 10 o'clock",
        "Let's talk at noon",
        "I'll be there in 2 hours",
        "The event starts at half past 7",
        "I'll call you at 5 in the afternoon",
        "The deadline is at midnight",
        "The train leaves in 30 minutes",
        "Let's meet at 8"
    ]
    
    for text in test_texts:
        times = extractor.extract_times(text)
        print(f"Input: {text}")
        print(f"Extracted times: {[extractor.format_time(t) for t in times]}")
        print() 