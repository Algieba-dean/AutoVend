import tomllib as tomli
import json as json
from pprint import pp

class CarModelQuery:
    def query_car_model(self, dict_query: dict) -> str:
        dict_query = {
            "prize": "Small"
        }
        with open('./ModelQuery/LabelsTree.json', 'r') as file_query_tree:
            query_tree = json.load(file_query_tree)
        with open("./ModelQuery/Labels.toml", "rb") as f:
            Labels_dict = tomli.load(f)

        #pp(query_tree)
        for precise_lable,value in query_tree["precise needs"].items():
            pp(precise_lable)
            pp(value)

        model_names = ["Volvo-XC60 Recharge T8 eAWD R-Design", "Volvo-XC40 Recharge T8 eAWD R-Design", "Volvo-XC90 Recharge T8 eAWD R-Design"]
        return model_names

c=CarModelQuery()
c.query_car_model({})