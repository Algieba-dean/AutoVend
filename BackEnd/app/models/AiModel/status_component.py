from collections import OrderedDict

class StatusComponent:
    def __init__(self):
        # Initialize state
        self.stage = dict()
        self.stage["current_stage"] = ""
        self.stage["previous_stage"] = ""
        self.user_profile = {
            "phone_number": "",
            "age": "",
            "user_title": "",
            "name": "",
            "target_driver": "",
            "expertise": "",
            "additional_information": {
                "family_size": "",
                "price_sensitivity": "",
                "residence": "",
                "parking_conditions": ""
            },
            "connection_information": {
                "connection_phone_number": "",
                "connection_id_relationship": "",
                "connection_user_name": ""
            }
        }
        self.needs = {
            "explicit": dict(),
            "implicit": dict()
        }
        self.test_drive_info = {
            "test_driver": "",
            "test_driver_name": "",
            "reservation_date": "",
            "selected_car_model": "",
            "brand":"",
            "reservation_time": "",
            "reservation_location": "",
            "reservation_phone_number": "",
            "salesman": ""
        }
        self.matched_car_models = list()
        self.matched_car_model_infos = list()
    
    def is_all_basic_reservation_info_done(self):
        """Check if all basic reservation information is done"""
        for key,value in self.test_drive_info.items():
            if value == "":
                return False
        return True
    
    def is_all_basic_info_done(self):
        """Check if all basic information is done"""
        name_done = self.user_profile.get("user_title","") != ""
        user_title_done = self.user_profile.get("user_title","") !=""
        target_driver_done = self.user_profile.get("target_driver","") !=""
        return name_done and user_title_done and target_driver_done
    
    def is_all_basic_needs_done(self):
        """Check if all basic needs are done"""
        prize_done = self.needs["explicit"].get("prize", "") or self.needs["explicit"].get("price_alias", "")
        # model_category_done = self.needs["explicit"].get("vehicle_category_top", "") or self.needs["explicit"].get("vehicle_category_middle", "") or self.needs["explicit"].get("vehicle_category_bottom", "")
        # brand_done = self.needs["explicit"].get("brand", "") or self.needs["explicit"].get("brand_area", "") or self.needs["explicit"].get("brand_country", "")
        # powertrain_type_done = self.needs["explicit"].get("powertrain_type", "")
        # return prize_done and model_category_done and brand_done and powertrain_type_done
        return prize_done
    
    def update_profile(self, profile_info):
        """Update the user profile with new information"""
        for key, value in profile_info.items():
            if not value:  # Skip if the value is empty
                continue
            # hard code way for name not update

            # First try to update key at the top level
            if key in self.user_profile:
                if isinstance(value, dict) and isinstance(self.user_profile[key], dict):
                    # Recursively update nested dictionaries
                    # Create a new dictionary with non-empty values for recursive update
                    non_empty_value_dict = {k: v for k, v in value.items() if v}
                    if non_empty_value_dict: # only update if there are non-empty values
                        self.user_profile[key].update(non_empty_value_dict)
                else:
                    # Direct assignment for non-dict values
                    if key == "name" and self.user_profile.get("name", ""): # TODO, hard code way is stupid, need to fix
                        continue
                    self.user_profile[key] = value
            else:
                # If not found at top level, try to find it in nested dictionaries
                self._recursive_update(self.user_profile, key, value)
                
    def _recursive_update(self, dictionary, search_key, new_value):
        """Recursively search for a key in nested dictionaries and update its value"""
        if not new_value: # Skip if the new_value is empty
            return False
            
        found = False
        for key, value in dictionary.items():
            if key == search_key:
                if isinstance(new_value, dict) and isinstance(dictionary[key], dict):
                    # Create a new dictionary with non-empty values for recursive update
                    non_empty_new_value_dict = {k: v for k, v in new_value.items() if v}
                    if non_empty_new_value_dict: # only update if there are non-empty values
                        dictionary[key].update(non_empty_new_value_dict)
                else:
                    dictionary[key] = new_value
                found = True
                break
            elif isinstance(value, dict):
                if self._recursive_update(value, search_key, new_value):
                    found = True
                    break
        return found

    def update_stage(self, new_stage):
        """Update the stage
        
        Args:
            stage (str): The new stage
        """
        self.stage["previous_stage"] = self.stage["current_stage"]
        self.stage["current_stage"] = new_stage
        ...

    def update_explicit_needs(self, explicit_needs):
        """Update explicit needs
        
        If a key is new, it will be added to explicit_needs.
        If a key already exists but with a different value, it will be updated.
        """
        for key, value in explicit_needs.items():
            # Add new key or update existing key with new value
            if value: # Only update if value is not empty
                self.needs["explicit"][key] = value

    
    def clear_implicit_needs(self):
        """Clear implicit needs"""
        self.needs["implicit"] = dict()
    
    def update_implicit_needs(self, implicit_needs):
        """Update implicit needs, ensuring no overlap with explicit needs.
        
        Rules:
        1. If a key exists in explicit_needs, it will NOT be added to implicit_needs
        2. If a key already exists in explicit_needs and also in implicit_needs, it will be removed from implicit_needs
        3. Otherwise, the implicit need will be updated as normal
        
        This function should be called after update_explicit_needs
        """
        # First, identify keys that exist in explicit_needs
        explicit_keys = set(self.needs["explicit"].keys())
        
        # Process each key in the provided implicit_needs
        for key, value in implicit_needs.items():
            if key in explicit_keys:
                # This key exists in explicit_needs, so we should not add it to implicit_needs
                # Also, remove it from implicit_needs if it exists there
                if key in self.needs["implicit"]:
                    del self.needs["implicit"][key]
            else:
                # This key does not exist in explicit_needs, so update it
                if value:  # Only update if value is not empty
                    self.needs["implicit"][key] = value
        
    
    def update_test_drive_info(self, test_drive_info, is_before_reservation=False):
        """Update test drive information and potentially update profile connection information
        
        If after updating:
        1. test_driver has a value and is not "Self"
        2. reservation_phone_number has a value
        
        Then:
        - Update profile's connection_id_relationship with test_driver value
        - Update profile's connection_phone_number with reservation_phone_number
        - Update profile's connection_user_name with test_driver_name
        
        If after updating:
        1. test_driver has a value and is "Self"
        
        Then:
        - Update test_drive_info's reservation_phone_number with profile's phone_number
        - Update test_drive_info's test_driver_name with profile's name
        
        If selected_car_model has a value:
        - Try to extract brand from selected_car_model and update the brand field
        """
        # First update the test drive info normally

        if is_before_reservation and test_drive_info.get("selected_car_model", ""):
            self.test_drive_info["selected_car_model"] = test_drive_info.get("selected_car_model")
        else:
            for key, value in test_drive_info.items():
                if key in self.test_drive_info and value:
                    self.test_drive_info[key] = value
        
        # Try to extract brand from selected_car_model
        selected_car_model = self.test_drive_info.get("selected_car_model", "")
        if selected_car_model:
            # Define the list of brands from QueryLabels.json
            brands = [
                "volkswagen", "audi", "porsche", "bentley", "bugatti", "lamborghini", 
                "bmw", "mercedes-benz", "peugeot", "renault", "jaguar", "land rover", 
                "rolls-royce", "volvo", "chevrolet", "buick", "cadillac", "ford", 
                "tesla", "toyota", "honda", "nissan", "suzuki", "mazda", "hyundai", 
                "byd", "geely", "changan", "great wall motor", "nio", "xpeng"
            ]
            
            # Convert selected_car_model to lowercase for case-insensitive matching
            selected_car_model_lower = selected_car_model.lower()
            
            # Try to match a brand
            for brand in brands:
                # Check if the brand is at the beginning of the car model
                if selected_car_model_lower.startswith(brand) or selected_car_model_lower.startswith(brand.replace(" ", "-")):
                    self.test_drive_info["brand"] = brand
                    break
                # Also check if the brand appears after a hyphen (e.g., "some-volkswagen-model")
                elif f"-{brand}" in selected_car_model_lower or f"-{brand.replace(' ', '-')}" in selected_car_model_lower:
                    self.test_drive_info["brand"] = brand
                    break
        
            
        if is_before_reservation:
            return
        # Check conditions for updating profile connection information
        test_driver = self.test_drive_info.get("test_driver", "")
        reservation_phone = self.test_drive_info.get("reservation_phone_number", "")
        
        if test_driver and test_driver.lower() == "self":
            # If test driver is self, synchronize phone number and name from profile
            self.test_drive_info["reservation_phone_number"] = self.user_profile.get("phone_number", "")
            self.test_drive_info["test_driver_name"] = self.user_profile.get("name", "")
        elif test_driver and test_driver.lower() != "self" and reservation_phone:
            # Update connection information in the profile
            self.user_profile["connection_information"]["connection_id_relationship"] = test_driver
            self.user_profile["connection_information"]["connection_phone_number"] = reservation_phone
            self.user_profile["connection_information"]["connection_user_name"] = self.test_drive_info.get("test_driver_name", "")
    
    def update_matched_car_models(self, car_models: list[str]):
        """Update matched car models, up to 3, based on brand diversity rules."""
        if not car_models:
            self.matched_car_models = []
            return

        if len(car_models) <= 3:
            self.matched_car_models = car_models[:]
            return

        # Store models under their brands, maintaining original order of brands and models within brands
        brand_to_models_map = OrderedDict() 
        for model_name in car_models:
            parts = model_name.split('-', 1)
            brand = parts[0] if parts else "UnknownBrand"
            if brand not in brand_to_models_map:
                brand_to_models_map[brand] = []
            brand_to_models_map[brand].append(model_name)

        ordered_unique_brands = list(brand_to_models_map.keys())
        num_unique_brands = len(ordered_unique_brands)
        selected_models = []

        if num_unique_brands <= 3:
            # If 3 or fewer unique brands, take all models from these brands in order of brand appearance,
            # until 3 models are selected or all models from these brands are taken.
            for brand in ordered_unique_brands:
                if len(selected_models) >= 3:
                    break
                models_from_this_brand = brand_to_models_map[brand]
                for model in models_from_this_brand:
                    if len(selected_models) >= 3:
                        break
                    if model not in selected_models: # Should generally be true if iterating correctly
                        selected_models.append(model)
        else: # num_unique_brands > 3
            # If more than 3 unique brands, pick one model from each of the first 3 unique brands.
            for i in range(min(3, num_unique_brands)): # Iterate up to the first 3 unique brands
                brand = ordered_unique_brands[i]
                if brand_to_models_map[brand]: # Check if brand has models
                    # Add the first model listed under this brand that hasn't been accidentally selected
                    # (though with this logic, it shouldn't be an issue)
                    first_model_of_brand = brand_to_models_map[brand][0]
                    if first_model_of_brand not in selected_models: # Precaution
                         selected_models.append(first_model_of_brand)
                    if len(selected_models) >=3: # Should fill up to 3
                        break 
        
        self.matched_car_models = selected_models[:3] # Ensure strictly max 3, though logic above aims for it.

    def update_matched_car_model_infos(self, car_model_infos: list[dict]):
        """Update `self.matched_car_model_infos` to include only those info objects
           from `car_model_infos` whose 'name' attribute matches a model name
           present in `self.matched_car_models`.

           Assumes each dict in `car_model_infos` has a 'name' key for the model name.
           This method relies on `self.matched_car_models` being populated beforehand.
        """
        if not car_model_infos or not self.matched_car_models:
            self.matched_car_model_infos = []
            return

        # `self.matched_car_models` should already contain the desired model names (max 3).
        # We will filter `car_model_infos` to get the details for these models.
        
        selected_infos = []
        # Using a set for efficient lookup of model names from self.matched_car_models.
        target_model_names_set = set(self.matched_car_models)

        # To ensure we add each unique info object only once, even if
        # `car_model_infos` has duplicates or multiple items map to the same selected model name.
        # We track added objects by their identity.
        added_info_object_ids = set() # Store ids of already added objects

        for info_obj in car_model_infos:
            # Assuming the model name key in info_obj is "name".
            # If the key is "car_model" as mentioned in the query, change info_obj.get("name") below.
            model_name_in_info = info_obj.get("car_model") 
            
            if model_name_in_info in target_model_names_set:
                # Check if this exact info object (by identity) has already been added
                if id(info_obj) not in added_info_object_ids:
                    selected_infos.append(info_obj)
                    added_info_object_ids.add(id(info_obj))
        
        self.matched_car_model_infos = selected_infos
    
    def convert_list_need_to_str(self):
        """Convert list values in needs (both explicit and implicit) to string values
        
        For each key in explicit_needs and implicit_needs:
        - If the value is a list with only one element, replace it with that element
        - If the value is a list with multiple elements, replace it with the first element
        - Otherwise leave the value unchanged
        """
        # Process explicit needs
        for key in list(self.needs["explicit"].keys()):
            value = self.needs["explicit"][key]
            if isinstance(value, list):
                if len(value) > 0:
                    # Replace list with its first element
                    self.needs["explicit"][key] = value[0]
        
        # Process implicit needs
        for key in list(self.needs["implicit"].keys()):
            value = self.needs["implicit"][key]
            if isinstance(value, list):
                if len(value) > 0:
                    # Replace list with its first element
                    self.needs["implicit"][key] = value[0]
    
    def reset(self):
        """Reset the status component"""
        self.stage = dict()
        self.stage["current_stage"] = ""
        self.stage["previous_stage"] = ""
        self.user_profile = {
            "phone_number": "",
            "age": "",
            "user_title": "",
            "name": "",
            "target_driver": "",
            "expertise": "",
            "additional_information": {
                "family_size": "",
                "price_sensitivity": "",
                "residence": "",
                "parking_conditions": ""
            },
            "connection_information": {
                "connection_phone_number": "",
                "connection_id_relationship": "",
                "connection_user_name": ""
            }
        }
        self.needs = {
            "explicit": dict(),
            "implicit": dict()
        }
        self.test_drive_info = {
            "test_driver": "",
            "test_driver_name": "",
            "reservation_date": "",
            "selected_car_model": "",
            "brand":"",
            "reservation_time": "",
            "reservation_location": "",
            "reservation_phone_number": "",
            "salesman": ""
        }
        self.matched_car_models = list()
        self.matched_car_model_infos = list()
    
if __name__ == "__main__":
    # Create a new instance of StatusComponent
    status_component = StatusComponent()
    
    # Test 1: Update profile information
    print("\n=== Test 1: Update Profile ===")
    status_component.update_profile({
        "phone_number": "1234567890",
        "age": "30",
        "user_title": "Mr.",
        "name": "John Doe",
        "target_driver": "self",
        "expertise": 5,
        "additional_information": {
            "family_size": "2",
            "price_sensitivity": "medium",
            "residence": "apartment",
            "parking_conditions": "limited"
        },
        "connection_information": {
            "connection_phone_number": "1234567890",
            "connection_id_relationship": "friend",
            "connection_user_name": "Jane Smith"
        }
    })
    print("Profile after update:")
    print(status_component.user_profile)
    
    # Test nested key update
    status_component.update_profile({"parking_conditions": "limited22"})
    print("\nProfile after nested key update:")
    print(status_component.user_profile)
    
    # Test 2: Update explicit and implicit needs with list values
    print("\n=== Test 2: Update Needs ===")
    # Update explicit needs with some list values
    status_component.update_explicit_needs({
        "budget": ["$30,000-$40,000", "$40,000-$50,000"],
        "color": ["red", "blue", "black"],
        "body_type": "SUV",
        "fuel_type": ["gasoline"]
    })
    print("Explicit needs before conversion:")
    print(status_component.needs["explicit"])
    
    # Update implicit needs (with some overlapping keys)
    status_component.update_implicit_needs({
        "budget": ["$20,000-$30,000"],  # This should be ignored as it exists in explicit
        "color": ["green", "silver"],   # This should be ignored as it exists in explicit
        "seating_capacity": ["5", "7"],
        "technology": ["navigation", "bluetooth", "backup camera"]
    })
    print("\nImplicit needs after update (notice budget and color are removed):")
    print(status_component.needs["implicit"])
    
    # List values have been automatically converted to strings by the convert_list_need_to_str function
    print("\nFinal explicit needs (after list to string conversion):")
    print(status_component.needs["explicit"])
    print("\nFinal implicit needs (after list to string conversion):")
    print(status_component.needs["implicit"])
    
    # Test 3: Test drive information and auto-update of connection info
    print("\n=== Test 3: Test Drive Information ===")
    status_component.update_test_drive_info({
        "test_driver": "Wife",
        "test_driver_name": "Mary Doe",
        "reservation_date": "2023-12-15",
        "selected_car_model": "ModelX",
        "reservation_time": "14:00",
        "reservation_location": "Downtown Dealership",
        "reservation_phone_number": "9876543210",
        "salesman": "Bob Smith"
    })
    print("Test drive information:")
    print(status_component.test_drive_info)
    print("\nConnection information (automatically updated):")
    print(status_component.user_profile["connection_information"])
    
    # Test 3b: Test when test_driver is "Self" - should sync profile info to test drive info
    print("\n=== Test 3b: Test Drive Information with Self as driver ===")
    # First update profile with some data
    status_component = StatusComponent()
    status_component.update_profile({
        "name": "John Smith",
        "phone_number": "5559876543"
    })
    
    # Now update test drive info with Self as driver
    status_component.update_test_drive_info({
        "test_driver": "Self",
        "reservation_date": "2023-12-20",
        "selected_car_model": "ModelY",
        "reservation_time": "10:30",
        "reservation_location": "North Dealership",
        "salesman": "Alice Johnson"
    })
    
    # Verify that test_driver_name and reservation_phone_number were synchronized from profile
    print("Test drive information after setting Self as driver:")
    print(f"Driver name (should be 'John Smith'): {status_component.test_drive_info['test_driver_name']}")
    print(f"Reservation phone (should be '5559876543'): {status_component.test_drive_info['reservation_phone_number']}")
    print(f"Other test drive details: Date={status_component.test_drive_info['reservation_date']}, Model={status_component.test_drive_info['selected_car_model']}")
    
    # Test 3c: Test brand extraction from selected_car_model
    print("\n=== Test 3c: Brand Extraction from Car Model ===")
    
    # Test with different car model formats
    test_models = [
        "volkswagen-golf", 
        "Toyota Camry", 
        "bmw-x5", 
        "some-mercedes-benz-class", 
        "great wall motor-haval",
        "unknown-model"
    ]
    
    for model in test_models:
        status_component = StatusComponent()
        status_component.update_test_drive_info({"selected_car_model": model})
        print(f"Model: {model} -> Extracted Brand: {status_component.test_drive_info.get('brand', 'Not detected')}")
    
    # Test 4: Update matched car models
    print("\n=== Test 4: Matched Car Models ===")
    car_models = ["ModelX", "ModelY", "ModelZ"]
    status_component.update_matched_car_models(car_models)
    
    car_model_infos = [
        {"model": "ModelX", "price": "$35,000", "features": ["AWD", "Sunroof", "Navigation"]},
        {"model": "ModelY", "price": "$42,000", "features": ["AWD", "Premium Audio", "Self-Parking"]},
        {"model": "ModelZ", "price": "$28,000", "features": ["Fuel Efficient", "Compact", "Bluetooth"]}
    ]
    status_component.update_matched_car_model_infos(car_model_infos)
    
    print("Matched car models:")
    print(status_component.matched_car_models)
    print("\nMatched car model details:")
    for model_info in status_component.matched_car_model_infos:
        print(f"- {model_info['model']}: {model_info['price']}")
    
    # Test 5: Testing recursive profile update with nested keys
    print("\n=== Test 5: Recursive Profile Update ===")
    status_component = StatusComponent()  # Create a fresh instance
    
    # Update profile with basic info
    status_component.update_profile({
        "name": "Alex Johnson",
        "phone_number": "5551234567"
    })
    
    # Update a deeply nested key that doesn't exist at top level
    status_component.update_profile({
        "residence": "suburban house"  # This exists in additional_information
    })
    
    print("Profile after recursive update:")
    print(status_component.user_profile)
    print(f"Residence value: {status_component.user_profile['additional_information']['residence']}")
    
    # Test 6: Testing convert_list_need_to_str with empty lists
    print("\n=== Test 6: List Conversion Edge Cases ===")
    status_component.needs["explicit"] = {
        "feature1": ["premium"],  # Single item list
        "feature2": [],           # Empty list
        "feature3": ["basic", "standard", "premium"],  # Multiple items
        "feature4": "not a list"  # Not a list
    }
    
    # Call the conversion function
    status_component.convert_list_need_to_str()
    
    print("Explicit needs after conversion:")
    print(status_component.needs["explicit"])
    
    # Test 7: Reset status component
    print("\n=== Test 7: Reset Status Component ===")
    status_component.reset()
    print("After reset, explicit needs:")
    print(status_component.needs["explicit"])
    print("After reset, matched car models:")
    print(status_component.matched_car_models)
        