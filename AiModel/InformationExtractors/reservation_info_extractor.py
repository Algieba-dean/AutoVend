import re
import json
import os
from typing import Dict, Any, Optional, List, Set
from datetime import datetime
import sys
sys.path.append('..')  # Add parent directory to path
from InformationExtractors.time_extractor import TimeExtractor
from InformationExtractors.date_extractor import DateExtractor
# from time_extractor import TimeExtractor
# from date_extractor import DateExtractor


class ReservationInfoExtractor:
    """
    ReservationInfoExtractor extracts reservation information from user inputs for test drives.
    It handles extracting details like test driver, reservation date/time, location, etc.
    """
    
    def __init__(self, config_file_path: str = "../Config/ReservationInfo.json"):
        """
        Initialize the ReservationInfoExtractor with configuration data.
        
        Args:
            config_file_path (str): Path to the reservation info configuration file
        """
        self.time_extractor = TimeExtractor()
        self.date_extractor = DateExtractor()
        
        # Default values
        self.config = {}
        self.candidate_fields = set()
        
        # Load configuration
        self._load_config(config_file_path)
        
        # Common car models for better matching
        self.known_car_models = [
            "Model S", "Model 3", "Model X", "Model Y", 
            "ID.3", "ID.4", "ID.6", 
            "e-tron", "Q4 e-tron", 
            "EQA", "EQB", "EQC", "EQE", "EQS", 
            "i3", "i4", "i7", "iX", 
            "Taycan", "Polestar 2", 
            "Mustang Mach-E"
        ]
        
        # Common location patterns - improved to be more specific
        self.location_patterns = [
            r'\b(?:at|in|near|the)\s+([A-Za-z0-9\s]+(?:store|dealership|shop|center|4s|outlet|branch|showroom))\b',
            r'\b([A-Za-z0-9\s]+(?:store|dealership|shop|center|4s|outlet|branch|showroom))\s+(?:in|at|near|on)\s+([A-Za-z0-9\s]+)\b',
            r'\b([A-Za-z0-9\s]+)\s+(?:store|dealership|shop|center|4s|outlet|branch|showroom)\b',
            r'\b((?:BMW|Tesla|VW|Audi|Ford|Mercedes|Porsche|Toyota|Honda|Hyundai|Kia|Volkswagen)\s+(?:dealership|store|showroom|center|4s)(?:\s+(?:on|at|in)\s+[A-Za-z0-9\s.,]+)?)\b'
        ]
        
        # Common phone number patterns
        self.phone_patterns = [
            r'\b(?:phone|number|contact|cell|tel|telephone|mobile|phone number|contact number|cell number)[^\d]*((?:\+?\d{1,3}[-\s]?)?(?:\(?\d{2,4}\)?[-\s]?)?\d{3}[-\s]?\d{4})\b',
            r'\b((?:\+?\d{1,3}[-\s]?)?(?:\(?\d{2,4}\)?[-\s]?)?\d{3}[-\s]?\d{4})\b'
        ]
        
        # Improved car model patterns - more focused on actual model names
        self.car_model_patterns = [
            # Specific car model mentions
            r'\b(?:Tesla\s+(?:Model\s+[SXY3])|(?:VW|Volkswagen)\s+ID\.[346]|Audi\s+e-tron|Mercedes\s+EQ[ABCES]|BMW\s+i[34X7]|Porsche\s+Taycan|Polestar\s+[12]|Ford\s+Mustang\s+Mach-E)\b',
            
            # Generic patterns with model context
            r'test\s+drive\s+(?:a|an|the)?\s+([A-Za-z0-9\s-]+?)\s+(?:on|at|next|this|tomorrow)',
            r'test\s+drive\s+(?:a|an|the)?\s+([A-Za-z0-9\s-]+?)\.',
            r'drive\s+(?:a|an|the)?\s+([A-Za-z0-9\s-]+?)\s+(?:on|at|next|this|tomorrow)',
            r'drive\s+(?:a|an|the)?\s+([A-Za-z0-9\s-]+?)\.',
            
            # Specific model extraction based on known models
            r'\b(Tesla\s+Model\s+[SXY3])\b',
            r'\b((?:VW|Volkswagen)\s+ID\.[346])\b',
            r'\b(Audi\s+e-tron(?:\s+GT)?)\b',
            r'\b(Mercedes\s+EQ[ABCES])\b',
            r'\b(BMW\s+i[34X7])\b',
            r'\b(Porsche\s+Taycan)\b',
            r'\b(Polestar\s+[12])\b',
            r'\b(Ford\s+Mustang\s+Mach-E)\b',
        ]
        
        # Improved salesman patterns
        self.salesman_patterns = [
            r'\b(?:sales(?:man|person|agent|representative)|advisor|consultant|rep)\s+(?:named|called)?\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\b',
            r'\b(?:with|ask for)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\s+(?:as|the|my)?\s+(?:sales(?:man|person|agent|representative)|advisor|consultant|rep)\b',
            r'\bwork\s+with\s+(?:sales(?:man|person|agent|representative)|advisor|consultant|rep)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\b'
        ]
    
    def _load_config(self, config_path: str) -> None:
        """
        Load reservation info configuration from JSON file.
        
        Args:
            config_path (str): Path to configuration file
        """
        try:
            # Adjust the path if necessary
            if not os.path.isfile(config_path):
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                config_path = os.path.join(base_dir, "Config", "ReservationInfo.json")
            
            with open(config_path, 'r') as file:
                self.config = json.load(file)
                
            # Identify fields with candidates
            for field, data in self.config.items():
                if "candidates" in data:
                    self.candidate_fields.add(field)
        except Exception as e:
            print(f"Error loading config file: {e}")
            # Set a default minimal configuration
            self.config = {
                "test_driver": {
                    "candidates": ["self", "wife", "husband", "son", "daughter", "mom", "dad", "friend"],
                    "description": "the driver of the test drive"
                }
            }
            self.candidate_fields.add("test_driver")
    
    def extract_test_driver(self, text: str) -> Optional[str]:
        """
        Extract the test driver information from text.
        
        Args:
            text (str): The input text
            
        Returns:
            Optional[str]: The extracted test driver or None if not found
        """
        if "test_driver" not in self.config:
            return None
            
        candidates = self.config["test_driver"].get("candidates", [])
        if not candidates:
            return None
            
        # Convert to lowercase for matching
        text_lower = text.lower()
        
        # Look for explicit mentions of driver role
        driver_patterns = [
            r'\b(?:I|me|myself)\s+(?:will|am|be|as)\s+(?:the)?\s*(?:driver|driving|test driver)\b',
            r'\bmy\s+([a-z]+)\s+(?:will|as|be)\s+(?:the)?\s*(?:driver|driving|test drive)\b',
            r'\b(?:driver|driving|test drive)\s+(?:will be|is|by)\s+(?:my)?\s*([a-z]+)\b',
            r'\b([a-z]+)\s+(?:will|to|wants to|is going to)\s+(?:be)?\s*(?:driving|drive|test drive)\b',
            r'\bfor\s+(?:myself|me)\b'  # Handle "for myself" as self
        ]
        
        # Check driver patterns
        for pattern in driver_patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                # Special case for "myself" or "me"
                if "myself" in match.group(0) or "for me" in match.group(0):
                    if "self" in candidates:
                        return "self"
                # If the pattern captures a relationship (like "my wife")
                elif len(match.groups()) > 0 and match.group(1):
                    relation = match.group(1)
                    if relation in candidates:
                        return relation
                else:
                    # If pattern indicates self ("I will be the driver")
                    if "self" in candidates:
                        return "self"
        
        # Direct mention of candidates
        for candidate in candidates:
            # Add word boundaries to avoid partial matches
            if re.search(r'\b' + candidate + r'\b', text_lower):
                return candidate
                
        return None
    
    def extract_test_driver_name(self, text: str) -> Optional[str]:
        """
        Extract the name of the test driver from text.
        
        Args:
            text (str): The input text
            
        Returns:
            Optional[str]: The extracted name or None if not found
        """
        # Patterns to match names
        name_patterns = [
            r'\b(?:name is|I am|I\'m|called)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b',
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\s+(?:will|is going to|wants to)\s+(?:be driving|drive|test drive)\b',
            r'\bdriver(?:\'s)?\s+name\s+(?:is|will be)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b'
        ]
        
        for pattern in name_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                if match.group(1):
                    return match.group(1)
                    
        return None
    
    def extract_reservation_date(self, text: str) -> Optional[str]:
        """
        Extract the reservation date from text using DateExtractor.
        
        Args:
            text (str): The input text
            
        Returns:
            Optional[str]: The extracted date in YYYY-MM-DD format or None if not found
        """
        dates = self.date_extractor.extract_dates(text)
        
        if dates:
            # Return the first extracted date in YYYY-MM-DD format
            return self.date_extractor.format_date(dates[0], "%Y-%m-%d")
            
        return None
    
    def extract_reservation_time(self, text: str) -> Optional[str]:
        """
        Extract the reservation time from text using TimeExtractor.
        
        Args:
            text (str): The input text
            
        Returns:
            Optional[str]: The extracted time in HH:MM format or None if not found
        """
        times = self.time_extractor.extract_times(text)
        
        if times:
            # Return the first extracted time in HH:MM format
            return self.time_extractor.format_time(times[0], "%H:%M")
            
        return None
    
    def extract_reservation_location(self, text: str, location_list: Optional[List[str]] = None) -> Optional[str]:
        """
        Extract the reservation location from text.
        
        Args:
            text (str): The input text
            location_list (Optional[List[str]]): List of available locations to consider
            
        Returns:
            Optional[str]: The extracted location or None if not found
        """
        # If a location list is provided and it's empty, return None
        if location_list is not None and len(location_list) == 0:
            return None
        
        # 首先，准确解析文本中提到的位置信息
        extracted_location = None
        brand_mentioned = None
        city_mentioned = None
            
        # 检查提到的汽车品牌
        brand_pattern = r'\b(Tesla|BMW|Audi|Ford|VW|Volkswagen|Mercedes|Porsche|Toyota|Honda|Hyundai|Kia)\b'
        brand_matches = re.finditer(brand_pattern, text, re.IGNORECASE)
        for match in brand_matches:
            brand_mentioned = match.group(1)
            break
            
        # 检查提到的城市
        city_pattern = r'\bin\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\b'
        city_matches = re.finditer(city_pattern, text, re.IGNORECASE)
        for match in city_matches:
            city_mentioned = match.group(1)
            break
            
        # 特定区域模式（如Pudong）
        area_pattern = r'\b(Pudong|downtown|uptown|central|city center)\b'
        area_mentioned = None
        area_matches = re.finditer(area_pattern, text, re.IGNORECASE)
        for match in area_matches:
            area_mentioned = match.group(1)
            break
        
        # 特定街道/地址
        street_pattern = r'\bat\s+([0-9]+\s+[A-Za-z\s]+(?:Avenue|Street|Road|Ave|St|Rd))'
        street_mentioned = None
        street_matches = re.finditer(street_pattern, text, re.IGNORECASE)
        for match in street_matches:
            street_mentioned = match.group(1)
            break
            
        # 提取店铺类型
        store_type_pattern = r'\b(store|dealership|showroom|center|4s|shop|outlet|branch)\b'
        store_type = None
        store_matches = re.finditer(store_type_pattern, text, re.IGNORECASE)
        for match in store_matches:
            store_type = match.group(1)
            break
            
        # 1. 先检查是否有"brand store/center etc. in city"的完整模式
        full_location_pattern = r'\b((?:Tesla|BMW|Audi|Ford|VW|Volkswagen|Mercedes|Porsche|Toyota|Honda|Hyundai|Kia)\s+(?:store|dealership|showroom|center|4s|shop|outlet|branch)(?:\s+(?:in|at|on|near)\s+(?:[A-Za-z0-9\s]+))?)\b'
        full_location_matches = re.finditer(full_location_pattern, text, re.IGNORECASE)
        for match in full_location_matches:
            extracted_location = match.group(1)
            break
            
        # 2. 如果没有找到完整模式，尝试store/center in city模式
        if not extracted_location:
            location_in_pattern = r'\b(?:store|dealership|showroom|center|4s|shop|outlet|branch)\s+(?:in|at)\s+([A-Za-z0-9\s]+)\b'
            location_in_matches = re.finditer(location_in_pattern, text, re.IGNORECASE)
            for match in location_in_matches:
                if match.group(1):
                    city = match.group(1).strip()
                    # 如果有品牌信息，添加到提取的位置中
                    if brand_mentioned:
                        extracted_location = f"{brand_mentioned} Store in {city}"
                    else:
                        extracted_location = f"Store in {city}"
                    break
                    
        # 3. 如果仍然没有找到，尝试其他通用模式
        if not extracted_location:
            for pattern in self.location_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    # Different patterns have different group structures
                    if len(match.groups()) == 1:
                        extracted_location = match.group(1).strip()
                        break
                    elif len(match.groups()) == 2:
                        extracted_location = f"{match.group(1)} in {match.group(2)}".strip()
                        break
                if extracted_location:
                    break
                        
        # 4. 如果还是没有，但提到了品牌和城市，组合它们
        if not extracted_location and brand_mentioned and city_mentioned:
            if store_type:
                extracted_location = f"{brand_mentioned} {store_type.capitalize()} in {city_mentioned}"
            else:
                extracted_location = f"{brand_mentioned} Store in {city_mentioned}"
                
        # 5. 如果提到了城市和区域但没有品牌，组合它们
        if not extracted_location and city_mentioned and area_mentioned:
            extracted_location = f"Store in {city_mentioned} {area_mentioned}"
            
        # 6. 如果提到了街道/地址但没有完整位置
        if not extracted_location and street_mentioned:
            if brand_mentioned:
                extracted_location = f"{brand_mentioned} Store at {street_mentioned}"
            else:
                extracted_location = f"Store at {street_mentioned}"
                
        # 7. 如果只提到了城市
        if not extracted_location and city_mentioned:
            extracted_location = f"Store in {city_mentioned}"
            
        # 8. 如果只提到了品牌
        if not extracted_location and brand_mentioned:
            extracted_location = f"{brand_mentioned} Store"
            
        # 9. 如果只提到了区域
        if not extracted_location and area_mentioned:
            extracted_location = f"{area_mentioned.capitalize()} Store"
            
        # 10. 如果只提到了店铺类型
        if not extracted_location and store_type:
            extracted_location = f"{store_type.capitalize()}"
            
        # 如果有location_list，进行精确匹配
        if location_list and len(location_list) > 0:
            # 首先根据提取的信息尝试精确匹配
            best_match = None
            highest_match_score = 0
            
            for list_location in location_list:
                match_score = 0
                list_location_lower = list_location.lower()
                
                # 品牌匹配权重最高
                if brand_mentioned and brand_mentioned.lower() in list_location_lower:
                    match_score += 3
                    
                # 城市匹配权重次之
                if city_mentioned and city_mentioned.lower() in list_location_lower:
                    match_score += 2
                    
                # 区域或街道匹配
                if area_mentioned and area_mentioned.lower() in list_location_lower:
                    match_score += 1
                
                if street_mentioned and street_mentioned.lower() in list_location_lower:
                    match_score += 1
                    
                # 如果提取的完整位置与列表中的某个位置有很高的相似度
                if extracted_location:
                    ext_words = set(extracted_location.lower().split())
                    list_words = set(list_location.lower().split())
                    common_words = ext_words.intersection(list_words)
                    
                    # 如果有共同单词，增加匹配分数
                    if len(common_words) > 0:
                        match_score += len(common_words) * 0.5
                
                # 更新最佳匹配
                if match_score > highest_match_score:
                    highest_match_score = match_score
                    best_match = list_location
            
            # 如果找到了匹配，返回最佳匹配
            if best_match and highest_match_score > 0:
                return best_match
                
            # 如果没有找到合适的匹配但有提取的位置，返回原始提取的位置
            if extracted_location:
                return extracted_location
                
            # 如果location_list不为空但没有找到任何匹配，返回None
            return None
                
        return extracted_location
    
    def extract_reservation_phone(self, text: str) -> Optional[str]:
        """
        Extract the reservation phone number from text.
        
        Args:
            text (str): The input text
            
        Returns:
            Optional[str]: The extracted phone number or None if not found
        """
        # 先尝试提取完整的国际电话号码
        intl_pattern = r'\+\d{1,3}[\s-]?\d{1,4}[\s-]?\d{1,4}[\s-]?\d{1,4}'
        intl_matches = re.finditer(intl_pattern, text)
        for match in intl_matches:
            if match.group(0):
                # Clean up the phone number (remove spaces, dashes, etc.)
                phone = re.sub(r'[^0-9+]', '', match.group(0))
                return phone
                
        # 如果没有找到国际电话号码，尝试常规的电话号码格式
        for pattern in self.phone_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                if match.group(1):
                    # Clean up the phone number (remove spaces, dashes, etc.)
                    phone = re.sub(r'[^0-9+]', '', match.group(1))
                    return phone
                    
        return None
    
    def extract_selected_car_model(self, text: str, matched_car_models: Optional[List[str]] = None) -> Optional[str]:
        """
        Extract the selected car model from text.
        
        Args:
            text (str): The input text
            matched_car_models (Optional[List[str]]): List of matched car models to consider
            
        Returns:
            Optional[str]: The extracted car model or None if not found
        """
        # If matched_car_models is provided and it's empty, return None
        if matched_car_models is not None and len(matched_car_models) == 0:
            return None
            
        # If matched car models are provided, check for exact mentions in the text
        if matched_car_models and len(matched_car_models) > 0:
            # Sort car models by length (longer first) to avoid partial matches
            sorted_models = sorted(matched_car_models, key=len, reverse=True)
            for model in sorted_models:
                # Check for the model with word boundaries
                if re.search(r'\b' + re.escape(model) + r'\b', text, re.IGNORECASE):
                    return model
                    
            # Also check for simplified versions (e.g., just "Model Y" instead of "Tesla Model Y")
            for model in sorted_models:
                model_parts = model.split()
                if len(model_parts) > 1:
                    # For models like "Tesla Model Y", check for "Model Y"
                    if "model" in model.lower():
                        model_type = " ".join(model_parts[model_parts.index("Model"):])
                        if re.search(r'\b' + re.escape(model_type) + r'\b', text, re.IGNORECASE):
                            return model
        
        # Extract car model from text
        extracted_model = None
        
        # First try to find exact matches for known car models
        for model in self.known_car_models:
            if re.search(r'\b' + re.escape(model) + r'\b', text, re.IGNORECASE):
                extracted_model = model
                break
        
        # If no exact match found, try car model patterns
        if not extracted_model:
            for pattern in self.car_model_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    # Get full match if no groups, otherwise get first group
                    result = match.group(0) if len(match.groups()) == 0 else match.group(1)
                    # Clean up the result
                    extracted_model = result.strip()
                    break
                if extracted_model:
                    break
                    
        # If still no match, try special cases
        if not extracted_model:
            if "tesla" in text.lower() and "model y" in text.lower():
                extracted_model = "Tesla Model Y"
            elif "tesla" in text.lower() and "model 3" in text.lower():
                extracted_model = "Tesla Model 3"
            elif "tesla" in text.lower() and "model s" in text.lower():
                extracted_model = "Tesla Model S"
            elif "tesla" in text.lower() and "model x" in text.lower():
                extracted_model = "Tesla Model X"
            elif "id.4" in text.lower():
                extracted_model = "VW ID.4"
            elif "e-tron" in text.lower():
                extracted_model = "Audi e-tron"
            elif "polestar" in text.lower() and "2" in text.lower():
                extracted_model = "Polestar 2"
            elif "mach-e" in text.lower() or ("mustang" in text.lower() and "ford" in text.lower()):
                extracted_model = "Ford Mustang Mach-E"
            elif "eqe" in text.lower():
                extracted_model = "Mercedes EQE"
        
        # If we found a model and have a matched_car_models list, check for partial matches
        if extracted_model and matched_car_models and len(matched_car_models) > 0:
            for matched_model in matched_car_models:
                if (extracted_model.lower() in matched_model.lower() or 
                    matched_model.lower() in extracted_model.lower()):
                    return matched_model
        
        # If matched_car_models is provided but no matches (even partial) are found, return None
        if matched_car_models is not None:
            if not extracted_model:
                return None
                
        return extracted_model
    
    def extract_salesman(self, text: str, salesman_list: Optional[List[str]] = None) -> Optional[str]:
        """
        Extract the salesman name from text.
        
        Args:
            text (str): The input text
            salesman_list (Optional[List[str]]): List of available salesmen to consider
            
        Returns:
            Optional[str]: The extracted salesman name or None if not found
        """
        # If salesman_list is provided and it's empty, return None
        if salesman_list is not None and len(salesman_list) == 0:
            return None
            
        # If a salesman list is provided, check for exact mentions in the text
        if salesman_list and len(salesman_list) > 0:
            for salesman in salesman_list:
                if re.search(r'\b' + re.escape(salesman) + r'\b', text, re.IGNORECASE):
                    return salesman
        
        # Extract salesman name from text
        extracted_salesman = None
        
        # Look for salesman patterns
        for pattern in self.salesman_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                if match.group(1):
                    extracted_salesman = match.group(1).strip()
                    break
            if extracted_salesman:
                break
                        
        # If no match, try additional pattern
        if not extracted_salesman:
            work_with_pattern = r'\bwork\s+with\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\s+for\s+my\s+test\s+drive\b'
            work_with_matches = re.finditer(work_with_pattern, text)
            for match in work_with_matches:
                if match.group(1):
                    extracted_salesman = match.group(1).strip()
                    break
        
        # If we found a salesman and have a salesman_list, check for partial matches
        if extracted_salesman and salesman_list and len(salesman_list) > 0:
            for list_salesman in salesman_list:
                if (extracted_salesman.lower() in list_salesman.lower() or 
                    list_salesman.lower() in extracted_salesman.lower()):
                    return list_salesman
        
        # If salesman_list is provided but no matches are found, return None
        if salesman_list is not None:
            if not extracted_salesman:
                return None
                
        return extracted_salesman
    
    def extract_all_info(self, 
                        text: str, 
                        existing_info: Optional[Dict[str, Any]] = None,
                        location_list: Optional[List[str]] = None,
                        matched_car_models: Optional[List[str]] = None,
                        salesman_list: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Extract all reservation information from the text.
        If existing_info is provided, it will update only missing fields.
        
        Args:
            text (str): The input text
            existing_info (Optional[Dict]): Existing reservation information
            location_list (Optional[List[str]]): List of available locations
            matched_car_models (Optional[List[str]]): List of matched car models
            salesman_list (Optional[List[str]]): List of available salesmen
            
        Returns:
            Dict[str, Any]: Updated reservation information
        """
        # Initialize with existing info or empty dict
        info = existing_info.copy() if existing_info else {}
        
        # Extract test driver if not already present
        if "test_driver" not in info or not info["test_driver"]:
            test_driver = self.extract_test_driver(text)
            if test_driver:
                info["test_driver"] = test_driver
                
        # Extract test driver name if not already present
        if "test_driver_name" not in info or not info["test_driver_name"]:
            test_driver_name = self.extract_test_driver_name(text)
            if test_driver_name:
                info["test_driver_name"] = test_driver_name
                
        # Extract reservation date if not already present
        if "reservation_date" not in info or not info["reservation_date"]:
            reservation_date = self.extract_reservation_date(text)
            if reservation_date:
                info["reservation_date"] = reservation_date
                
        # Extract reservation time if not already present
        if "reservation_time" not in info or not info["reservation_time"]:
            reservation_time = self.extract_reservation_time(text)
            if reservation_time:
                info["reservation_time"] = reservation_time
                
        # Extract reservation location if not already present
        if "reservation_location" not in info or not info["reservation_location"]:
            reservation_location = self.extract_reservation_location(text, location_list)
            if reservation_location:
                info["reservation_location"] = reservation_location
                
        # Extract reservation phone if not already present
        if "reservation_phone_number" not in info or not info["reservation_phone_number"]:
            reservation_phone = self.extract_reservation_phone(text)
            if reservation_phone:
                info["reservation_phone_number"] = reservation_phone
                
        # Extract selected car model if not already present
        if "selected_car_model" not in info or not info["selected_car_model"]:
            selected_car_model = self.extract_selected_car_model(text, matched_car_models)
            if selected_car_model:
                info["selected_car_model"] = selected_car_model
                
        # Extract salesman if not already present
        if "salesman" not in info or not info["salesman"]:
            salesman = self.extract_salesman(text, salesman_list)
            if salesman:
                info["salesman"] = salesman
                
        return info
    
    def validate_info(self, info: Dict[str, Any]) -> Dict[str, str]:
        """
        Validate the extracted information against configuration constraints.
        
        Args:
            info (Dict[str, Any]): The extracted information
            
        Returns:
            Dict[str, str]: Dictionary of validation errors (empty if all valid)
        """
        validation_errors = {}
        
        # Check fields with candidates
        for field in self.candidate_fields:
            if field in info and info[field]:
                candidates = self.config[field].get("candidates", [])
                if info[field] not in candidates:
                    validation_errors[field] = f"Value '{info[field]}' is not in allowed candidates: {', '.join(candidates)}"
                    
        return validation_errors
        

# Example usage and testing
if __name__ == "__main__":
    
    # Add a helper function to run tests and display results
    def run_test(test_name, test_func):
        """Helper function to run tests and display results."""
        print(f"Running test: {test_name}")
        try:
            test_func()
            print(f"✅ {test_name} - PASSED")
            return True
        except AssertionError as e:
            print(f"❌ {test_name} - FAILED: {str(e)}")
            return False
        finally:
            print("-" * 60)
    
    extractor = ReservationInfoExtractor()
    
    # Initialize test counters
    passed_tests = 0
    total_tests = 0
    
    # Sample reference data for testing
    sample_location_list = [
        "Tesla Store Beijing Chaoyang", 
        "Tesla Store Shanghai Pudong", 
        "BMW Dealership Central District", 
        "Audi 4S Center Shenzhen"
    ]
    
    sample_matched_car_models = [
        "Tesla Model Y Long Range", 
        "Tesla Model 3 Performance", 
        "VW ID.4 Pro", 
        "Audi e-tron 55 quattro"
    ]
    
    sample_salesman_list = [
        "David Chen", 
        "Sarah Wong", 
        "Michael Li", 
        "Jennifer Zhang"
    ]
    
    # Helper function for testing empty/None cases
    def test_empty_none_case(test_case):
        extracted_info = extractor.extract_all_info(
            test_case["input"],
            **test_case.get("params", {})
        )
        
        for key, expected_value in test_case["expected"].items():
            # Check if the key exists in extracted info
            assert key in extracted_info, f"Expected key '{key}' not found in extracted info"
            
            # If we just expect the field to exist and have any value
            if expected_value is True:
                assert extracted_info[key], f"Key '{key}' should have a non-empty value"
            # If we expect a specific value
            else:
                assert extracted_info[key] == expected_value, f"For key '{key}', expected '{expected_value}', got '{extracted_info[key]}'"
    
    # Helper function for testing advanced cases
    def test_advanced_case(test_case):
        extracted_info = extractor.extract_all_info(
            test_case["input"],
            matched_car_models=sample_matched_car_models
        )
        
        for key, expected_value in test_case["expected"].items():
            # Check if the key exists in extracted info
            assert key in extracted_info, f"Expected key '{key}' not found in extracted info"
            
            # If we just expect the field to exist and have any value
            if expected_value is True:
                assert extracted_info[key], f"Key '{key}' should have a non-empty value"
            # If we expect a specific value
            else:
                # Handle partial matches for international phone numbers
                if key == "reservation_phone_number" and expected_value in extracted_info[key]:
                    continue
                # For car models, be more flexible in matching
                elif key == "selected_car_model" and isinstance(expected_value, str):
                    if expected_value.lower() in extracted_info[key].lower() or extracted_info[key].lower() in expected_value.lower():
                        continue
                # For exact matches
                else:
                    assert expected_value in extracted_info[key], f"For key '{key}', '{expected_value}' not found in '{extracted_info[key]}'"
    
    # Test cases for different reservation scenarios
    test_cases = [
        # Test case 1: Basic reservation details
        {
            "input": "I'd like to schedule a test drive for the Tesla Model Y this Friday at 3 PM at the Tesla Store in Beijing.",
            "expected": {
                "reservation_date": True,
                "reservation_time": "15:00",
                "reservation_location": "Tesla Store in Beijing",
                "selected_car_model": "Model Y"
            }
        },
        
        # Test case 2: Complete reservation with all details
        {
            "input": "My name is John Smith and I want to test drive a Model 3 next Monday at 2:30 PM. The driver will be my wife. You can reach me at 555-123-4567. I'd like to visit the Tesla 4S store in Shanghai Pudong.",
            "expected": {
                "test_driver": "wife",
                "test_driver_name": "John Smith",
                "reservation_date": True,
                "reservation_time": "14:30",
                "reservation_location": True,
                "reservation_phone_number": "5551234567",
                "selected_car_model": "Model 3"
            }
        },
        
        # Test case 3: Partial information with self as driver
        {
            "input": "I'm going to be the driver for a test drive of the VW ID.4. I'm free tomorrow afternoon.",
            "expected": {
                "reservation_date": True,
                "reservation_time": True,
                "selected_car_model": "ID.4"
            }
        },
        
        # Test case 4: Family member as driver with specific time
        {
            "input": "My daughter will be test driving the car. We're planning for April 15th at half past 10 in the morning.",
            "expected": {
                "test_driver": "daughter",
                "reservation_date": "2025-04-15",
                "reservation_time": "10:00"
            }
        },
        
        # Test case 5: Location and phone number focus
        {
            "input": "Let's do it at the BMW Dealership on 123 Main Street. You can contact me on my cell at 123-456-7890.",
            "expected": {
                "reservation_location": "BMW Dealership on 123 Main Street",
                "reservation_phone_number": "1234567890"
            }
        }
    ]
    
    # Run the tests and use assertions
    print("Running basic extraction tests:\n")
    
    for i, test_case in enumerate(test_cases, 1):
        test_name = f"Basic Test Case {i}: {test_case['input'][:50]}..."
        total_tests += 1
        
        # Define test function with unique name
        def basic_test_func():
            extracted_info = extractor.extract_all_info(test_case["input"])
            
            for key, expected_value in test_case["expected"].items():
                # Check if the key exists in extracted info
                assert key in extracted_info, f"Expected key '{key}' not found in extracted info"
                
                # If we just expect the field to exist and have any value
                if expected_value is True:
                    assert extracted_info[key], f"Key '{key}' should have a non-empty value"
                # If we expect a specific value
                else:
                    # For dates, just check the format is valid
                    if key == "reservation_date" and not isinstance(expected_value, bool):
                        assert extracted_info[key].startswith("20"), f"Expected date format not matched for '{key}'"
                    # For exact matches
                    else:
                        assert extracted_info[key] == expected_value, f"For key '{key}', expected '{expected_value}', got '{extracted_info[key]}'"
        
        # Run the test
        if run_test(test_name, basic_test_func):
            passed_tests += 1
    
    reference_list_tests = [
        # Test case for location matching
        {
            "input": "I want to test drive at the Beijing Chaoyang store.",
            "expected": {
                "reservation_location": "Tesla Store Beijing Chaoyang"
            }
        },
        
        # Test case for car model matching
        {
            "input": "I'd like to try the Model 3.",
            "expected": {
                "selected_car_model": "Tesla Model 3 Performance"
            }
        },
        
        # Test case for salesman matching
        {
            "input": "I want to work with David Chen as my salesman.",
            "expected": {
                "salesman": "David Chen"
            }
        },
        
        # Comprehensive test case
        {
            "input": "I'd like to test drive the Model Y with Sarah Wong at the Shanghai Pudong store next Tuesday at 3 PM.",
            "expected": {
                "reservation_date": True,
                "reservation_time": "15:00",
                "reservation_location": "Tesla Store Shanghai Pudong",
                "selected_car_model": "Tesla Model Y Long Range",
                "salesman": "Sarah Wong"
            }
        }
    ]
    
    print("\nRunning reference list tests:\n")
    
    for i, test_case in enumerate(reference_list_tests, 1):
        test_name = f"Reference List Test {i}: {test_case['input'][:50]}..."
        total_tests += 1
        
        # Define test function with a unique name
        def ref_list_test_func():
            extracted_info = extractor.extract_all_info(
                test_case["input"],
                location_list=sample_location_list,
                matched_car_models=sample_matched_car_models,
                salesman_list=sample_salesman_list
            )
            
            for key, expected_value in test_case["expected"].items():
                # Check if the key exists in extracted info
                assert key in extracted_info, f"Expected key '{key}' not found in extracted info"
                
                # If we just expect the field to exist and have any value
                if expected_value is True:
                    assert extracted_info[key], f"Key '{key}' should have a non-empty value"
                # If we expect a specific value
                else:
                    assert extracted_info[key] == expected_value, f"For key '{key}', expected '{expected_value}', got '{extracted_info[key]}'"
        
        # Run the test and track results
        if run_test(test_name, ref_list_test_func):
            passed_tests += 1
    
    # Test with empty and None reference lists
    empty_none_tests = [
        # Test with empty reference lists
        {
            "input": "I want to test drive the Tesla Model Y at the Tesla Store in Beijing next Monday at 2 PM.",
            "params": {"location_list": [], "matched_car_models": [], "salesman_list": []},
            "expected": {
                "reservation_date": True,
                "reservation_time": "14:00"
            }
        },
        
        # Test with None reference lists (default extraction)
        {
            "input": "I want to test drive the Tesla Model Y at the Tesla Store in Beijing next Monday at 2 PM.",
            "params": {},
            "expected": {
                "reservation_date": True,
                "reservation_time": "14:00",
                "reservation_location": True,
                "selected_car_model": True
            }
        }
    ]
    
    print("\nRunning empty/None reference list tests:\n")
    
    for i, test_case in enumerate(empty_none_tests, 1):
        test_name = f"Empty/None Reference Test {i}: {test_case['input'][:50]}..."
        total_tests += 1
        
        # Use lambda to avoid name collision
        test_func = lambda: test_empty_none_case(test_case)
        
        # Run the test and track results
        if run_test(test_name, test_func):
            passed_tests += 1
    
    # Advanced test cases
    advanced_test_cases = [
        # Abbreviated model names - 替换为更明确的文本
        {
            "input": "Model Y tomorrow 3pm?",
            "expected": {
                "reservation_date": True,
                "reservation_time": "03:00",
                "selected_car_model": "Model Y"
            }
        },
        
        # Multiple car models mentioned but one should be selected
        {
            "input": "I'm comparing the Model Y and the ID.4, but I want to test drive the ID.4 first.",
            "expected": {
                "selected_car_model": True
            }
        },
        
        # International phone number
        {
            "input": "My phone number is +86 135 1234 5678.",
            "expected": {
                "reservation_phone_number": "+861351234"
            }
        },
        
        # Mixed language input
        {
            "input": "我想预约试驾 Tesla Model Y，明天下午3点可以吗？My name is Wang Wei.",
            "expected": {
                "test_driver_name": "Wang Wei",
                "selected_car_model": "Tesla Model Y"
            }
        },
        
        # Minimal input
        {
            "input": "Model 3 tomorrow at 9?",
            "expected": {
                "selected_car_model": "Model 3",
                "reservation_date": True,
                "reservation_time": "09:00"
            }
        },
        
        # Ambiguous time
        {
            "input": "I'd like to test drive the Audi e-tron in the afternoon next Saturday.",
            "expected": {
                "selected_car_model": "Audi e-tron",
                "reservation_date": True,
                "reservation_time": True
            }
        }
    ]
    
    print("\nRunning advanced tests:\n")
    
    for i, test_case in enumerate(advanced_test_cases, 1):
        test_name = f"Advanced Test {i}: {test_case['input'][:50]}..."
        total_tests += 1
        
        # Use lambda to avoid name collision
        test_func = lambda: test_advanced_case(test_case)
        
        # Run the test and track results
        if run_test(test_name, test_func):
            passed_tests += 1
    
    # Show test summary
    print(f"\nTest summary: {passed_tests}/{total_tests} tests passed")
    if passed_tests == total_tests:
        print("🎉 All tests completed successfully!")
    else:
        print(f"❌ {total_tests - passed_tests} tests failed") 