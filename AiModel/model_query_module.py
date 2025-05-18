import tomllib as tomli
import json
import os
#from pprint import pp

class CarModelQuery:
    def __init__(self):
        # load all car model infos at beginning, to boost get_car_model_info
        self.all_model_names = list()
        self.all_model_infos = dict()
        ...
    def __initialize_model_information(self):
        self.all_model_names = self.__load_car_model_names()
        self.all_model_infos = { model_name:dict() for model_name in self.all_model_names}
        for model_name in self.all_model_names:
            model_info = self.get_car_model_info(model_name)
            self.all_model_infos[model_name] = model_info

    def __load_car_model_names(self)->list:
        """
        read all model names from model folders
        """
        return_list = list()
        # TODO, not done yet
        return return_list

    def __load_car_model_info(self,car_model:str)->dict:
        """
        get car model information from a car_model name, currently will read directly the file content
        """
        return_dict = dict()
        # TODO, not done yet, will do it after the real query model is integrated
        return return_dict

    def query_car_model(self, dict_query: dict) -> list:
        """
        based on the input query dict return matched car model dict
        
        Args:
            dict_query: query dict, key is label name, value is label value
            
        Returns:
            matched car model
        """
        return ["Audi A8","BMW 7 Series","Mercedes-Benz S-Class"], dict_query
    def get_car_model_info(self, car_model: str) -> dict:
        """
        get car model info
        """
        # return self.all_model_infos.get(car_model,dict())
        return {"car_model": car_model, "car_model_info": "car model info"}


# test code
#if __name__ == "__main__":
#    c = CarModelQuery()
    # test query
#    result = c.query_car_model({"vehicle_category_middle": "suv","brand":"bmw"})
#    print("query results:")
#    pp(result)