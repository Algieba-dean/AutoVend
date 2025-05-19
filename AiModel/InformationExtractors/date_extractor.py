import re
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import calendar
from utils import get_current_date, timer_decorator

class DateExtractor:
    """
    A class for extracting date information from user input strings.
    Handles explicit dates, relative days, and week-based references.
    """
    
    def __init__(self):
        # Day references mapping
        self.day_references = {
            "today": 0,
            "tomorrow": 1,
            "the day after tomorrow": 2,
            "yesterday": -1,
            "the day before yesterday": -2
        }
        
        # Weekday mapping
        self.weekdays = {
            "monday": 0, "mon": 0,
            "tuesday": 1, "tue": 1, "tues": 1,
            "wednesday": 2, "wed": 2,
            "thursday": 3, "thu": 3, "thur": 3, "thurs": 3,
            "friday": 4, "fri": 4,
            "saturday": 5, "sat": 5,
            "sunday": 6, "sun": 6
        }
        
        # Month mapping
        self.months = {
            "january": 1, "jan": 1,
            "february": 2, "feb": 2,
            "march": 3, "mar": 3,
            "april": 4, "apr": 4,
            "may": 5,
            "june": 6, "jun": 6,
            "july": 7, "jul": 7,
            "august": 8, "aug": 8,
            "september": 9, "sep": 9, "sept": 9,
            "october": 10, "oct": 10,
            "november": 11, "nov": 11,
            "december": 12, "dec": 12
        }
    
    @timer_decorator
    def extract_dates(self, text):
        """
        Extract date information from the given text based on current date.
        
        Args:
            text (str): The input text to extract dates from
            
        Returns:
            list: A list of datetime objects representing extracted dates
        """
        # Get current date as reference
        current_date_str = get_current_date()
        current_date = datetime.strptime(current_date_str, "%Y-%m-%d")
        
        extracted_dates = []
        
        # Convert text to lowercase for easier matching
        text = text.lower()
        
        # Extract explicit dates (e.g., "April 15", "4/15", "15th of April")
        extracted_dates.extend(self._extract_explicit_dates(text, current_date))
        
        # Extract day references (e.g., "today", "tomorrow", "the day after tomorrow")
        extracted_dates.extend(self._extract_day_references(text, current_date))
        
        # Extract weekday references (e.g., "this Monday", "next Friday")
        extracted_dates.extend(self._extract_weekday_references(text, current_date))
        
        # Extract day-of-month references (e.g., "the 15th")
        extracted_dates.extend(self._extract_day_of_month(text, current_date))
        
        return extracted_dates
    
    def _extract_explicit_dates(self, text, current_date):
        """
        Extract explicit date mentions like "April 15" or "4/15".
        
        Args:
            text (str): The input text
            current_date (datetime): The current date
            
        Returns:
            list: List of datetime objects
        """
        dates = []
        
        # Pattern for "Month Day" (e.g., "April 15", "Apr 15", "April 15th")
        month_day_pattern = r'(?:' + '|'.join(self.months.keys()) + r')\s+\d{1,2}(?:st|nd|rd|th)?'
        month_day_matches = re.finditer(month_day_pattern, text)
        
        for match in month_day_matches:
            match_text = match.group(0)
            parts = match_text.split()
            month_name = parts[0]
            day_str = re.sub(r'(?:st|nd|rd|th)', '', parts[1])
            
            try:
                month_num = self.months[month_name]
                day = int(day_str)
                
                # Create date with current year
                date_obj = datetime(current_date.year, month_num, day)
                
                # If date is in the past, it might refer to next year
                if date_obj < current_date and (current_date - date_obj).days > 300:
                    date_obj = datetime(current_date.year + 1, month_num, day)
                
                dates.append(date_obj)
            except (ValueError, KeyError):
                continue
        
        # Pattern for "MM/DD" or "MM-DD" (e.g., "4/15", "04-15")
        numeric_date_pattern = r'\b(0?[1-9]|1[0-2])[/-](0?[1-9]|[12][0-9]|3[01])\b'
        numeric_matches = re.finditer(numeric_date_pattern, text)
        
        for match in numeric_matches:
            month_str, day_str = match.groups()
            try:
                month = int(month_str)
                day = int(day_str)
                
                # Create date with current year
                date_obj = datetime(current_date.year, month, day)
                
                # If date is in the past, it might refer to next year
                if date_obj < current_date and (current_date - date_obj).days > 300:
                    date_obj = datetime(current_date.year + 1, month, day)
                
                dates.append(date_obj)
            except ValueError:
                continue
        
        return dates
    
    def _extract_day_references(self, text, current_date):
        """
        Extract relative day references like "today", "tomorrow".
        
        Args:
            text (str): The input text
            current_date (datetime): The current date
            
        Returns:
            list: List of datetime objects
        """
        dates = []
        
        for day_ref, day_offset in self.day_references.items():
            if day_ref in text:
                date_obj = current_date + timedelta(days=day_offset)
                dates.append(date_obj)
        
        return dates
    
    def _extract_weekday_references(self, text, current_date):
        """
        Extract weekday references like "this Monday", "next Friday".
        
        Args:
            text (str): The input text
            current_date (datetime): The current date
            
        Returns:
            list: List of datetime objects
        """
        dates = []
        current_weekday = current_date.weekday()
        
        # Check for "this [weekday]" pattern
        this_week_pattern = r'this\s+(' + '|'.join(self.weekdays.keys()) + r')'
        this_week_matches = re.finditer(this_week_pattern, text)
        
        for match in this_week_matches:
            weekday_name = match.group(1)
            target_weekday = self.weekdays[weekday_name]
            
            # Calculate days to add
            days_to_add = (target_weekday - current_weekday) % 7
            if days_to_add == 0:  # Today is the target weekday
                days_to_add = 7   # Go to next week
            
            date_obj = current_date + timedelta(days=days_to_add)
            dates.append(date_obj)
        
        # Check for "next [weekday]" pattern
        next_week_pattern = r'next\s+(' + '|'.join(self.weekdays.keys()) + r')'
        next_week_matches = re.finditer(next_week_pattern, text)
        
        for match in next_week_matches:
            weekday_name = match.group(1)
            target_weekday = self.weekdays[weekday_name]
            
            # Calculate days to add (7 days + remaining days to target weekday)
            days_to_add = 7 + (target_weekday - current_weekday) % 7
            
            date_obj = current_date + timedelta(days=days_to_add)
            dates.append(date_obj)
        
        # Check for just "[weekday]" pattern (assumes current week)
        just_weekday_pattern = r'\b(' + '|'.join(self.weekdays.keys()) + r')\b'
        just_weekday_matches = re.finditer(just_weekday_pattern, text)
        
        for match in just_weekday_matches:
            # Skip if it was part of "this" or "next" pattern
            if re.search(r'(?:this|next)\s+' + match.group(1), text):
                continue
                
            weekday_name = match.group(1)
            target_weekday = self.weekdays[weekday_name]
            
            # Calculate days to add
            days_to_add = (target_weekday - current_weekday) % 7
            if days_to_add == 0:  # If today, assume next week
                days_to_add = 7
                
            date_obj = current_date + timedelta(days=days_to_add)
            dates.append(date_obj)
        
        return dates
    
    def _extract_day_of_month(self, text, current_date):
        """
        Extract day of month references like "the 15th".
        
        Args:
            text (str): The input text
            current_date (datetime): The current date
            
        Returns:
            list: List of datetime objects
        """
        dates = []
        
        # Pattern for day of month (e.g., "the 15th", "15th", "the 3rd")
        day_pattern = r'(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)'
        day_matches = re.finditer(day_pattern, text)
        
        for match in day_matches:
            day_str = match.group(1)
            
            try:
                day = int(day_str)
                
                # Create date with current year and month
                date_obj = datetime(current_date.year, current_date.month, day)
                
                # If the day has passed in current month, assume next month
                if date_obj < current_date:
                    date_obj = date_obj + relativedelta(months=1)
                
                dates.append(date_obj)
            except ValueError:
                continue
        
        return dates
    
    def format_date(self, date_obj, format_str="%Y-%m-%d"):
        """
        Format a datetime object as string.
        
        Args:
            date_obj (datetime): The datetime object to format
            format_str (str): The format string
            
        Returns:
            str: Formatted date string
        """
        return date_obj.strftime(format_str)


# Example usage
if __name__ == "__main__":
    extractor = DateExtractor()
    
    # Test with various date expressions
    test_texts = [
        "Let's meet on April 15",
        "The meeting is scheduled for tomorrow",
        "We'll have a call next Monday",
        "The deadline is on the 20th",
        "The event is on this Friday",
        "I'll submit the report by 5/10",
        "Let's discuss this on Wednesday"
    ]
    
    for text in test_texts:
        dates = extractor.extract_dates(text)
        print(f"Input: {text}")
        print(f"Extracted dates: {[extractor.format_date(d) for d in dates]}")
        print() 