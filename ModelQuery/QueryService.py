class CarModelQuery:
    def query_car_model(self, dict_query: dict) -> str:
        dict_query = {
            "size": "Small",
            "vehicle_category_bottom": "Micro Sedan",
        }

        model_names = ["Volvo-XC60 Recharge T8 eAWD R-Design", "Volvo-XC40 Recharge T8 eAWD R-Design", "Volvo-XC90 Recharge T8 eAWD R-Design"]
        return model_names