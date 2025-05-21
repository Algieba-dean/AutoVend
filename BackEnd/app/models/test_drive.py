from datetime import datetime, UTC

class TestDrive:
    """Test drive reservation model for AutoVend application"""
    
    def __init__(self, test_driver : str, brand: str, reservation_date : str, selected_car_model : str, 
                 reservation_time: str, reservation_location: str, reservation_phone_number = str,
                 salesman: str="", status= str or "Pending", notes= str or "empty"):
        """Initialize a new test drive reservation"""
        self.created_at = datetime.now(UTC).isoformat()
        self.updated_at = self.created_at
        self.test_drive_info = {
            "test_driver": test_driver,
            "brand": brand,
            "reservation_date": reservation_date,
            "selected_car_model": selected_car_model,
            "reservation_time": reservation_time,
            "reservation_location": reservation_location,
            "reservation_phone_number": reservation_phone_number,
            "salesman": salesman,
            "status": status,
            "notes": notes
        }
    
    @classmethod
    def created_from_dict(cls, data):
        """Create a TestDrive instance from a dictionary"""
        test_drive_info=data["test_drive_info"]
        test_drive = cls(
            test_driver=test_drive_info.get("test_driver", ""),
            brand=test_drive_info.get("brand",""),
            reservation_date=test_drive_info.get("reservation_date", ""),
            selected_car_model=test_drive_info.get("selected_car_model", ""),
            reservation_time=test_drive_info.get("reservation_time", ""),
            reservation_location=test_drive_info.get("reservation_location", ""),
            reservation_phone_number=test_drive_info.get("reservation_phone_number", ""),
            status=test_drive_info.get("status", "Pending"),
            notes=test_drive_info.get("notes","empty")
        )
        test_drive.created_at = data.get("created_at", test_drive.created_at)
        test_drive.updated_at = data.get("updated_at", test_drive.updated_at)
        return test_drive
    
    def convert_to_dict(self):
        """Convert the test drive reservation to a dictionary"""
        return {
            "test_drive_info": self.test_drive_info,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    def update(self, test_drive_info):
        """Update the test drive reservation information"""
        # Update only provided fields
        for key, value in test_drive_info.items():
            if key in self.test_drive_info and value:
                self.test_drive_info[key] = value
        
        # Update timestamp
        self.updated_at = datetime.now(UTC).isoformat()
        return True