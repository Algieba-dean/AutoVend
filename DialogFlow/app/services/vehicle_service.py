"""
Vehicle service for managing vehicle data and recommendations.
"""
import json
import logging
import os
from typing import Dict, List, Optional, Any

from app.config import VEHICLES_DIR
from app.models import Vehicle, VehicleSpecs

# Configure logging
logger = logging.getLogger(__name__)


class VehicleService:
    """
    Service for managing vehicle data and recommendations.
    """
    
    def get_all_vehicles(self) -> List[Vehicle]:
        """
        Get all vehicles.
        
        Returns:
            List of Vehicle objects
        """
        vehicles = []
        try:
            combined_file = os.path.join(VEHICLES_DIR, "vehicles.json")
            
            if os.path.exists(combined_file):
                with open(combined_file, 'r') as f:
                    data = json.load(f)
                    
                    for vehicle_data in data:
                        # Convert specs to VehicleSpecs object
                        specs_data = vehicle_data.pop("specs", {})
                        specs = VehicleSpecs(**specs_data)
                        vehicle_data["specs"] = specs
                        
                        vehicles.append(Vehicle(**vehicle_data))
            else:
                # If combined file doesn't exist, read individual files
                if os.path.exists(VEHICLES_DIR):
                    for filename in os.listdir(VEHICLES_DIR):
                        if filename.endswith('.json') and filename != "vehicles.json":
                            filepath = os.path.join(VEHICLES_DIR, filename)
                            
                            with open(filepath, 'r') as f:
                                vehicle_data = json.load(f)
                                
                                # Convert specs to VehicleSpecs object
                                specs_data = vehicle_data.pop("specs", {})
                                specs = VehicleSpecs(**specs_data)
                                vehicle_data["specs"] = specs
                                
                                vehicles.append(Vehicle(**vehicle_data))
        except Exception as e:
            logger.error(f"Error retrieving vehicles: {str(e)}")
        
        return vehicles
    
    def get_vehicle_by_id(self, vehicle_id: str) -> Optional[Vehicle]:
        """
        Get a vehicle by ID.
        
        Args:
            vehicle_id: The ID of the vehicle to retrieve
            
        Returns:
            The Vehicle object if found, None otherwise
        """
        try:
            filepath = os.path.join(VEHICLES_DIR, f"{vehicle_id}.json")
            
            if not os.path.exists(filepath):
                return None
                
            with open(filepath, 'r') as f:
                vehicle_data = json.load(f)
                
                # Convert specs to VehicleSpecs object
                specs_data = vehicle_data.pop("specs", {})
                specs = VehicleSpecs(**specs_data)
                vehicle_data["specs"] = specs
                
                return Vehicle(**vehicle_data)
        except Exception as e:
            logger.error(f"Error retrieving vehicle {vehicle_id}: {str(e)}")
            return None
    
    def recommend_vehicles(self, needs: Dict[str, Any], limit: int = 5) -> List[Vehicle]:
        """
        Recommend vehicles based on needs.
        
        Args:
            needs: Dictionary of needs
            limit: Maximum number of recommendations
            
        Returns:
            List of recommended Vehicle objects
        """
        # Get all vehicles
        all_vehicles = self.get_all_vehicles()
        
        # Score each vehicle based on how well it matches the needs
        scored_vehicles = []
        for vehicle in all_vehicles:
            score = self._calculate_match_score(vehicle, needs)
            scored_vehicles.append((vehicle, score))
        
        # Sort by score (descending)
        scored_vehicles.sort(key=lambda x: x[1], reverse=True)
        
        # Return top N vehicles
        return [vehicle for vehicle, score in scored_vehicles[:limit]]
    
    def _calculate_match_score(self, vehicle: Vehicle, needs: Dict[str, Any]) -> float:
        """
        Calculate how well a vehicle matches the needs.
        
        Args:
            vehicle: The Vehicle object
            needs: Dictionary of needs
            
        Returns:
            Match score (0-100)
        """
        score = 0.0
        total_weight = 0.0
        
        # Budget match (higher weight)
        if "budget" in needs:
            weight = 25.0
            total_weight += weight
            
            try:
                budget = float(needs["budget"])
                if vehicle.price <= budget:
                    # Perfect match if price is under budget
                    score += weight
                else:
                    # Partial match if price is close to budget
                    overbudget_percent = (vehicle.price - budget) / budget
                    if overbudget_percent <= 0.1:  # Within 10% of budget
                        score += weight * (1 - overbudget_percent * 10)
            except (ValueError, TypeError):
                # If budget is not a valid number, skip this criterion
                total_weight -= weight
        
        # Vehicle category match (high weight)
        if "vehicle_category" in needs:
            weight = 20.0
            total_weight += weight
            
            if isinstance(needs["vehicle_category"], list):
                categories = needs["vehicle_category"]
            else:
                categories = [needs["vehicle_category"]]
            
            for category in categories:
                category_value = category
                if isinstance(category, dict) and "value" in category:
                    category_value = category["value"]
                
                if category_value.lower() == vehicle.category.lower():
                    score += weight
                    break
        
        # Brand match (medium weight)
        if "brand" in needs:
            weight = 15.0
            total_weight += weight
            
            if isinstance(needs["brand"], list):
                brands = needs["brand"]
            else:
                brands = [needs["brand"]]
            
            for brand in brands:
                brand_value = brand
                if isinstance(brand, dict) and "value" in brand:
                    brand_value = brand["value"]
                
                if brand_value.lower() == vehicle.brand.lower():
                    score += weight
                    break
        
        # Seating capacity match (medium weight)
        if "seats" in needs:
            weight = 10.0
            total_weight += weight
            
            seats_value = needs["seats"]
            if isinstance(seats_value, dict) and "value" in seats_value:
                seats_value = seats_value["value"]
            
            try:
                needed_seats = int(seats_value)
                if vehicle.specs.seats >= needed_seats:
                    score += weight
            except (ValueError, TypeError):
                # If seats is not a valid number, skip this criterion
                total_weight -= weight
        
        # Tag-based matching for remaining criteria (lower weights)
        weight_per_tag = 5.0
        
        # Engine type match
        if "engine_type" in needs:
            weight = weight_per_tag
            total_weight += weight
            
            if isinstance(needs["engine_type"], list):
                engine_types = needs["engine_type"]
            else:
                engine_types = [needs["engine_type"]]
            
            for engine_type in engine_types:
                engine_value = engine_type
                if isinstance(engine_type, dict) and "value" in engine_type:
                    engine_value = engine_type["value"]
                
                if engine_value.lower() in vehicle.specs.engine.lower():
                    score += weight
                    break
        
        # Transmission match
        if "transmission" in needs:
            weight = weight_per_tag
            total_weight += weight
            
            if isinstance(needs["transmission"], list):
                transmissions = needs["transmission"]
            else:
                transmissions = [needs["transmission"]]
            
            for transmission in transmissions:
                transmission_value = transmission
                if isinstance(transmission, dict) and "value" in transmission:
                    transmission_value = transmission["value"]
                
                if transmission_value.lower() in vehicle.specs.transmission.lower():
                    score += weight
                    break
        
        # Size match (indirect - use category as proxy)
        if "size" in needs:
            weight = weight_per_tag
            total_weight += weight
            
            size_value = needs["size"]
            if isinstance(size_value, dict) and "value" in size_value:
                size_value = size_value["value"]
            
            size_value = size_value.lower()
            category = vehicle.category.lower()
            
            if size_value == "small" and any(c in category for c in ["compact", "hatchback", "coupe"]):
                score += weight
            elif size_value == "medium" and any(c in category for c in ["sedan", "mid"]):
                score += weight
            elif size_value == "large" and any(c in category for c in ["suv", "crossover", "truck", "van"]):
                score += weight
        
        # Feature matching based on tags
        vehicle_tags = [tag.lower() for tag in vehicle.tags]
        
        # Usage match
        if "usage" in needs:
            weight = weight_per_tag
            total_weight += weight
            
            if isinstance(needs["usage"], list):
                usages = needs["usage"]
            else:
                usages = [needs["usage"]]
            
            for usage in usages:
                usage_value = usage
                if isinstance(usage, dict) and "value" in usage:
                    usage_value = usage["value"]
                
                usage_value = usage_value.lower()
                
                if usage_value == "family" and any(t in vehicle_tags for t in ["family", "spacious", "safety"]):
                    score += weight
                    break
                elif usage_value == "commuting" and any(t in vehicle_tags for t in ["commuter", "fuel-efficient", "reliable"]):
                    score += weight
                    break
                elif usage_value == "adventure" and any(t in vehicle_tags for t in ["off-road", "rugged", "utility", "adventure"]):
                    score += weight
                    break
                elif usage_value == "luxury" and any(t in vehicle_tags for t in ["luxury", "premium", "comfort", "status"]):
                    score += weight
                    break
        
        # Style match
        if "style" in needs:
            weight = weight_per_tag
            total_weight += weight
            
            if isinstance(needs["style"], list):
                styles = needs["style"]
            else:
                styles = [needs["style"]]
            
            for style in styles:
                style_value = style
                if isinstance(style, dict) and "value" in style:
                    style_value = style["value"]
                
                style_value = style_value.lower()
                
                if style_value in vehicle_tags:
                    score += weight
                    break
        
        # If no criteria were matched (unlikely), avoid division by zero
        if total_weight == 0:
            return 0.0
        
        # Convert to percentage
        return (score / total_weight) * 100.0


# Create a singleton instance
vehicle_service = VehicleService() 