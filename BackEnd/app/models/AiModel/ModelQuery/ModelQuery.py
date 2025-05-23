import tomllib as tomli
import json
import os
from pathlib import Path
#from pprint import pp

class CarModelQuery:
    def __init__(self):
        # query tree and vehicle date configure path
        self.label_tree_path = Path(os.path.dirname(__file__)).parent.joinpath("Config", "LabelsTree.json")
        self.vehicle_file_dir = Path(os.path.dirname(__file__)).parent.parent.parent.parent.parent.joinpath("DataInUse", "VehicleData")
        # print(f"label_tree_path: {self.label_tree_path.exists()}")
        # print(f"label_tree_path: {self.label_tree_path.exists()}")

        self.vehicle_data_list =[]
        self.precise_labels={}
        self.ambiguous_labels={}
        self.vehicle_category_tree={
            "sedan":["micro sedan","compact sedan","b-segment sedan","c-segment sedan","d-segment sedan"],
            "suv":["compact suv","mid-size suv","mid-to-large suv","off-road suv","all-terrain suv"],
            "mpv":["compact mpv","mid-size mpv","large mpv","mid-size business mpv","large-size business mpv"],
            "sports car":["two-door convertible sports car","four-door convertible sports car","two-door hardtop sports car","four-door hardtop sports car"],
            "small sedan":["micro sedan","compact sedan"],
            "mid-size sedan":["b-segment sedan"],
            "mid-large sedan":["c-segment sedan","d-segment sedan"],
            "crossover suv":["compact suv","mid-size suv","mid-to-large suv"],
            "body-on-frame suv":["off-road suv","all-terrain suv"],
            "family mpv":["compact mpv","mid-size mpv","large mpv"],
            "business mpv":["mid-size business mpv","large-size business mpv"],
            "convertible sports car":["two-door convertible sports car","four-door convertible sports car"],
            "hardtop sports car":["two-door hardtop sports car","four-door hardtop sports car"]
            }
        self.brand_tree={
            "european":["volkswagen","audi","porsche","bentley","bugatti","lamborghini","bmw","mercedes-benz","peugeot","renault","jaguar","land rover","rolls-royce","volvo"],
            "american":["chevrolet","buick","cadillac","ford","tesla"],
            "asian":["toyota","honda","nissan","suzuki","mazda","hyundai","byd","geely","changan","great wall motor","nio","xiaomi","xpeng"],            
            "germany":["volkswagen","audi","porsche","bentley","bugatti","lamborghini","bmw","mercedes-benz"],            
            "france":["peugeot","renault"],
            "united kingdom":["jaguar","land rover","rolls-royce"],
            "sweden":["volvo"],
            "usa":["chevrolet","buick","cadillac","ford","tesla"],
            "japan":["toyota","honda","nissan","suzuki","mazda"],
            "korea":["hyundai"],
            "china":["byd","geely","changan","great wall motor","nio","xiaomi","xpeng"],
        }

        self.all_model_names = []
        self.all_model_infos = {}
        # load query tree data
        with open(self.label_tree_path, 'r', encoding='utf-8') as query_tree_file:
            self.query_tree = json.load(query_tree_file)
            self.precise_labels=self.query_tree["precise_needs"]
            self.ambiguous_labels=self.query_tree["ambiguous_needs"]

        # load vehicle data
        vehicle_files = self._get_all_vehicle_files_path()
        for vehicle_file in vehicle_files:
            vehicle_data = self._load_car_data(vehicle_file)
            if vehicle_data:
                self.vehicle_data_list.append(vehicle_data)
                self.all_model_names.append(vehicle_data["car_model"])
                self.all_model_infos[vehicle_data["car_model"]] = dict()
                self.all_model_infos[vehicle_data["car_model"]] = vehicle_data
        ...
        
            
    def get_all_model_names(self):
        return self.all_model_names
    
    def get_all_model_infos(self):
        return self.all_model_infos
    
    def get_car_model_info(self, model_name: str):
        return self.all_model_infos[model_name]
    
    def query_car_model(self, dict_query: dict):
        """
        based on the input query dict returen matched car model dict
        
        Args:
            dict_query: query dict, key is label name, value is label value
            
        Returns:
            matched car model
        """
        # if dict_query empty return
        if not dict_query:
            return [],{}
        matched_models = []

        # firstly match with all dict_query
        for car_data in self.vehicle_data_list:
            if self._match_car_with_query(car_data, dict_query):
                matched_models.append(car_data["car_model"])
        
        # if no matched, match with precise_query only
        if matched_models:
            return matched_models,dict_query
        else:
            precise_query= self._query_dispatch(dict_query)
            if precise_query:
                for car_data in self.vehicle_data_list:
                    if self._match_car_with_query(car_data, precise_query):
                        matched_models.append(car_data["car_model"])
        if matched_models:
            return matched_models,precise_query

        return matched_models,dict_query
    
    def _get_all_vehicle_files_path(self):
        """
        get all car model file path
        
        Returns:
            dict of all car model file path
        """
        vehicle_files_path = []
        
        if os.path.exists(self.vehicle_file_dir):
            for root, _, files in os.walk(self.vehicle_file_dir):
                for file in files:
                    if file.endswith('.toml') and file != 'CarLabels.toml':
                        vehicle_files_path.append(os.path.join(root, file))
        
        return vehicle_files_path
    
    def _load_car_data(self, car_file):
        """
        load car data from the path
        
        Args:
            car_file: the car data path
            
        Returns:
            car datas list, key=label, value=label value
        """
        try:
            with open(car_file, 'rb') as f:
                car_data = tomli.load(f)
                return car_data
        except Exception as e:
            print(f"Error loading car data from {car_file}: {e}")
            return {}

    def _query_dispatch(self,dict_query):
        """
        based on the input query, return only precise query
        
        Args:
            dict_query: the request query data
            
        Returns:
            precise qury dict
        """
        precise_query={}

        for query_key,query_value in dict_query.items():
            if query_key not in ["size","vehicle_usability","aesthetics","energy_consumption_level","comfort_level","smartness","family_friendliness"]:
                precise_query[query_key]=query_value

        return precise_query

    def _match_car_with_query(self, car_data, query):
        """
        check if car data match the query condition
        
        Args:
            car_data: the dict of car data
            query: the query data dict
            
        Returns:
            wether the car data matched
        """
        if not car_data:
            return False
        
        # get vehicle data
        vehicle_data = car_data['PriciseLabels']|car_data['AmbiguousLabels']

        for query_key,query_value in query.items():
            if query_key.endswith('_alias'):
                # convert alias query
                if isinstance(query_value,str):
                    query_value=self._get_actual_value_from_alias(query_key,query_value)
                    query_key=query_key.replace('_alias', '')
                else:
                    query_value_list=[]
                    for alias_item_value in query_value:
                        alias_item_value=self._get_actual_value_from_alias(query_key,alias_item_value)
                        query_value_list.append(alias_item_value)
                    query_value=query_value_list

            # check vehicle data with query value
            if query_key in vehicle_data:
                if isinstance(query_value,str):
                    if vehicle_data[query_key].lower()!=query_value:
                        return False
                else:
                    if vehicle_data[query_key].lower() not in query_value:
                        return False
            else:
                #check vehicle category and brand key
                match query_key:
                    case "vehicle_category_top" | "vehicle_category_middle":
                        if isinstance(query_value,str):
                            if vehicle_data["vehicle_category_bottom"].lower() not in self.vehicle_category_tree[query_value]:
                                return False
                        else:
                            allowed_value_list=[]
                            for query_value_item in query_value:
                                allowed_value_list.extend(self.vehicle_category_tree[query_value_item])
                            if vehicle_data["vehicle_category_bottom"].lower() not in allowed_value_list:
                                    return False
                    case "brand_area" | "brand_country":
                        if isinstance(query_value,str):
                            if vehicle_data["brand"].lower() not in self.brand_tree[query_value]:
                                return False
                        else:
                            allowed_value_list=[]
                            for query_value_item in query_value:
                                allowed_value_list.extend(self.brand_tree[query_value_item])
                            if vehicle_data["brand"].lower() not in allowed_value_list:
                                return False
                    case _:
                        return False

        return True
    
    def _get_actual_value_from_alias(self, key, alias_value):
        """
        get actual value from alias label
        
        Args:
            key: label name
            alias_value: alias value
            
        Returns:
            actual value
        """
        # check if input key exist
        alias_key=key.replace('_alias', '')

        if self.precise_labels[alias_key]:
            alias_candidates = self.precise_labels[key]
            key_candidates = self.precise_labels[alias_key]
            
            # find the index and convert
            try:
                index = alias_candidates.index(alias_value)
                # use the index to get actual value
                if index < len(key_candidates):
                    actual_value = key_candidates[index]
                    return actual_value
            except ValueError:
                pass
        
        return ""

# test code
#if __name__ == "__main__":
#    c = CarModelQuery()
    # test query
#    result = c.query_car_model({"vehicle_category_middle": ["sedan","suv"],"brand_country":["sweden","china"],"size":["small","middle"]})
#    print("query results:")
#    pp(result)