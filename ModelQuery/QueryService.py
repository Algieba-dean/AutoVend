import tomllib as tomli
import json
import os
from pprint import pp

class CarModelQuery:
    def __init__(self):
        # 加载标签树和查询标签
        self.query_tree_path = './ModelQuery/LabelsTree.json'
        self.query_labels_path = './ModelQuery/QueryLabels.json'
        self.vehicle_data_path = './DataInUse/VehicleData'
        self.model_query_path = './ModelQuery/VehicelData'
        
        # 加载查询树和查询标签
        with open(self.query_tree_path, 'r', encoding='utf-8') as file_query_tree:
            self.query_tree = json.load(file_query_tree)
        
        with open(self.query_labels_path, 'r', encoding='utf-8') as file_query_labels:
            self.query_labels = json.load(file_query_labels)
    
    def query_car_model(self, dict_query: dict) -> list:
        """
        根据输入的查询条件，返回匹配的车型列表
        
        Args:
            dict_query: 查询条件字典，键为标签名，值为标签值
            
        Returns:
            匹配的车型列表
        """
        # 如果查询字典为空，返回空列表
        if not dict_query:
            return []
        
        # 标准化查询条件（转换为小写）
        normalized_query = {k.lower(): v.lower() if isinstance(v, str) else v for k, v in dict_query.items()}
        
        # 获取所有车型文件
        car_model_files = self._get_all_car_model_files()
        
        # 匹配车型
        matched_models = []
        for car_file in car_model_files:
            car_data = self._load_car_data(car_file)
            if self._match_car_with_query(car_data, normalized_query):
                matched_models.append(car_data.get('car_model', os.path.basename(car_file).replace('.toml', '')))
        
        return matched_models
    
    def _get_all_car_model_files(self):
        """
        获取所有车型文件路径
        
        Returns:
            车型文件路径列表
        """
        car_files = []
        
        # 首先检查DataInUse/VehicleData目录
        if os.path.exists(self.vehicle_data_path):
            for root, dirs, files in os.walk(self.vehicle_data_path):
                for file in files:
                    if file.endswith('.toml') and file != 'CarLabels.toml':
                        car_files.append(os.path.join(root, file))
        
        # 然后检查ModelQuery/VehicelData目录
        if os.path.exists(self.model_query_path):
            for root, dirs, files in os.walk(self.model_query_path):
                for file in files:
                    if file.endswith('.toml'):
                        car_files.append(os.path.join(root, file))
        
        return car_files
    
    def _load_car_data(self, car_file):
        """
        加载车型数据
        
        Args:
            car_file: 车型文件路径
            
        Returns:
            车型数据字典
        """
        try:
            with open(car_file, 'rb') as f:
                car_data = tomli.load(f)
                return car_data
        except Exception as e:
            print(f"Error loading car data from {car_file}: {e}")
            return {}
    
    def _match_car_with_query(self, car_data, query):
        """
        判断车型是否匹配查询条件
        
        Args:
            car_data: 车型数据字典
            query: 查询条件字典
            
        Returns:
            是否匹配
        """
        if not car_data or 'PriciseLabels' not in car_data:
            return False
        
        # 获取车型的精确标签
        precise_labels = car_data['PriciseLabels']
        # 获取车型的模糊标签
        ambiguous_labels = car_data.get('AmbibuousLabels', {})
        
        # 检查每个查询条件
        for key, value in query.items():
            # 标准化键名（去除_alias后缀）
            base_key = key.replace('_alias', '')
            
            # 检查精确标签
            if base_key in precise_labels:
                car_value = precise_labels[base_key].lower() if precise_labels[base_key] else ""
                if car_value and value and value != car_value:
                    return False
            # 检查模糊标签
            elif base_key in ambiguous_labels:
                car_value = ambiguous_labels[base_key].lower() if ambiguous_labels[base_key] else ""
                if car_value and value and value != car_value:
                    return False
            # 如果是别名查询，需要转换为实际值进行比较
            elif key.endswith('_alias') and base_key in precise_labels:
                # 获取别名对应的实际值
                actual_value = self._get_actual_value_from_alias(base_key, value)
                car_value = precise_labels[base_key].lower() if precise_labels[base_key] else ""
                if car_value and actual_value and actual_value != car_value:
                    return False
        
        return True
    
    def _get_actual_value_from_alias(self, key, alias_value):
        """
        根据别名获取实际值
        
        Args:
            key: 标签键名
            alias_value: 别名值
            
        Returns:
            实际值
        """
        # 检查查询标签中是否有该键的别名定义
        alias_key = f"{key}_alias"
        if alias_key in self.query_labels:
            alias_candidates = self.query_labels[alias_key].get('candidates', [])
            key_candidates = self.query_labels[key].get('candidates', [])
            
            # 找到别名在列表中的索引
            try:
                index = [c.lower() for c in alias_candidates].index(alias_value.lower())
                # 使用相同索引获取实际值
                if index < len(key_candidates):
                    return key_candidates[index].lower()
            except ValueError:
                pass
        
        return None

# 测试代码
if __name__ == "__main__":
    c = CarModelQuery()
    # 测试查询
    result = c.query_car_model({"prize": "40,000~60,000", "brand": "Volvo"})
    print("查询结果:")
    pp(result)