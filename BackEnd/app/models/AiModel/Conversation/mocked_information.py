class MockedInformation:
    def __init__(self):
        """
        Initialize the mocked information with predefined data
        """
        # Import date extractor
        from InformationExtractors.date_extractor import DateExtractor
        self.date_extractor = DateExtractor()
        
        # Mocked salesman names
        self.salesman_names = [
            "Alex Johnson", "Sarah Chen", "Michael Wang", "Lisa Zhang", 
            "David Liu", "Emma Wu", "Robert Lee", "Jennifer Li",
            "Thomas Yang", "Jessica Zhao", "Daniel Huang", "Michelle Lin",
            "Kevin Sun", "Rachel Gao", "Brian Xu", "Sophia Tang"
        ]
        
        # Mocked 4S stores
        self.stores = [
            "Elite Auto Center", "Premium Motors", "Golden Star Automotive",
            "First Class Auto Mall", "Luxury Vehicle Emporium", "Superior Cars",
            "Diamond Auto Plaza", "Royal Motors", "Prestige Auto Gallery",
            "Crown Automobile Center", "Star Auto Experience", "Pinnacle Motors"
        ]
        
        # Mocked appointment dates with diverse expressions
        self.appointment_dates = [
            "tomorrow", 
            "the day after tomorrow",
            "next Monday", 
            "next Wednesday",
            "this Friday", 
            "next Sunday",
            "May 15th", 
            "June 5th",
            "July 10th", 
            "August 22nd",
            "the 25th", 
            "the 30th",
            "June 1st", 
            "May 20th",
            "next Tuesday", 
            "this Saturday"
        ]
        self.mocked_stores = self.get_random_stores(count=3)
        self.mocked_dates = self.get_random_appointment_dates(count=3)
        self.salesman_names = self.get_random_salesmen(count=3)

    def get_random_salesmen(self, count=1):
        """
        Get random unique salesman names
        
        Args:
            count (int): Number of names to return
            
        Returns:
            list: List of randomly selected unique salesman names
        """
        return self._get_random_samples(self.salesman_names, count)
    
    def get_random_stores(self, count=1):
        """
        Get random unique store names
        
        Args:
            count (int): Number of stores to return
            
        Returns:
            list: List of randomly selected unique store names
        """
        return self._get_random_samples(self.stores, count)
    
    def get_random_appointment_dates(self, count=1):
        """
        Get random unique appointment dates with validation using DateExtractor
        
        Args:
            count (int): Number of appointment dates to return
            
        Returns:
            list: List of randomly selected unique appointment dates
        """
        from datetime import datetime
        
        # Get initial random date expressions
        date_expressions = self._get_random_samples(self.appointment_dates, count)
        
        # Keep track of unique dates by their normalized form (YYYY-MM-DD)
        unique_dates = {}
        result_dates = []
        
        # Process each date expression
        for date_expr in date_expressions:
            # Extract the date from the expression
            extracted_dates = self.date_extractor.extract_dates(date_expr)
            
            if extracted_dates:
                # Format the date to standard format
                formatted_date = self.date_extractor.format_date(extracted_dates[0], "%Y-%m-%d")
                
                # Only add if we haven't seen this date yet
                if formatted_date not in unique_dates:
                    unique_dates[formatted_date] = date_expr
                    result_dates.append(date_expr)
        
        # If we need more dates (due to duplicates being filtered out)
        if len(result_dates) < count:
            remaining_expressions = [expr for expr in self.appointment_dates if expr not in date_expressions]
            additional_dates = self.get_random_appointment_dates(count - len(result_dates))
            result_dates.extend(additional_dates)
        
        return result_dates[:count]
    
    
    
    def _get_random_samples(self, data_list, count=1):
        """
        Helper method to get random unique samples from a data list
        
        Args:
            data_list (list): The data list to sample from
            count (int): Number of samples to return
            
        Returns:
            list: List of randomly selected unique samples
        """
        import random
        
        # Validate the count
        if count < 1:
            return []
            
        # Make sure we don't try to get more samples than available
        valid_count = min(count, len(data_list))
        
        # Return random unique samples
        return random.sample(data_list, valid_count)
mocked_information = MockedInformation()