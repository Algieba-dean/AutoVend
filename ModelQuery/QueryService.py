import tomllib as tomli
from pprint import pp

class CarModelQuery:
    def query_car_model(self, dict_query: dict) -> str:
        dict_query = {
            "prize": "Small"
        }

        with open("./ModelQuery/Labels.toml", "rb") as f:
            Labels_dict = tomli.load(f)

        pp(Labels_dict["prize"])

        model_names = ["Volvo-XC60 Recharge T8 eAWD R-Design", "Volvo-XC40 Recharge T8 eAWD R-Design", "Volvo-XC90 Recharge T8 eAWD R-Design"]
        return model_names

c=CarModelQuery()
c.query_car_model({})