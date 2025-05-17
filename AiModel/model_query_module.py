import tomllib as tomli
import json
import os
#from pprint import pp

class CarModelQuery:
    def __init__(self):
        ...
            
    
    def query_car_model(self, dict_query: dict) -> list:
        """
        based on the input query dict returen matched car model dict
        
        Args:
            dict_query: query dict, key is label name, value is label value
            
        Returns:
            matched car model
        """
        return ["Audi A8","BMW 7 Series","Mercedes-Benz S-Class"]
    def get_car_model_info(self, car_model: str) -> dict:
        """
        get car model info
        """
        return {"car_model": car_model, "car_model_info": "car model info"}
    

# test code
#if __name__ == "__main__":
#    c = CarModelQuery()
    # test query
#    result = c.query_car_model({"vehicle_category_middle": "suv","brand":"bmw"})
#    print("query results:")
#    pp(result)