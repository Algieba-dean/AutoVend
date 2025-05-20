import enum
class ProfileTargetDriver(enum):
    SELF="Self"
    WIFE="Wife"
    HUSBAND="Husband"
    SPOUSE="Spouse"
    FATHER="Father"
    MOTHER= "Mother"
    PARENTS="Parents"
    SON="Son"
    DAUGHTER= "Daughter"
    CHILD="Child"
    OTHER="other"

class ProfileUserTitle(enum):
    MR="Mr.",
    MRS="Mrs."
    MISS="Miss."
    MS="Ms."
    UNKNOWN="Unknown"

class ProfileParkingCondition(enum):
    ALLOCATED_PARKING_SPACE="Allocated Parking Space"
    TEMPORARY_PARKING_ALLOWED="Temporary Parking Allowed"
    CHARGING_PILE_FACILITIES_AVAILABLE="Charging Pile Facilities Available"

class ProfileData:
    def __init__(self):
        self.dict = {
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
