"""
车辆数据加载器

负责从TOML文件中加载车辆数据并进行预处理。
"""

import os
import toml
from pathlib import Path
from typing import List, Dict, Any, Generator, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from src.models.vehicle import Vehicle
from src.utils.logger import get_logger, log_performance
from src.utils.config import config


class VehicleDataLoader:
    """车辆数据加载器"""
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        初始化数据加载器
        
        Args:
            data_dir: 数据目录路径，默认使用配置中的路径
        """
        self.data_dir = Path(data_dir or config.vehicle_data_dir)
        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        
        # 支持的文件扩展名
        self.supported_extensions = {'.toml'}
        
        # 统计信息
        self.stats = {
            'total_files': 0,
            'loaded_files': 0,
            'failed_files': 0,
            'loading_time': 0.0
        }
    
    @log_performance
    def load_all_vehicles(self, parallel: bool = True, max_workers: int = 4) -> List[Vehicle]:
        """
        加载所有车辆数据
        
        Args:
            parallel: 是否使用并行加载
            max_workers: 最大工作线程数
        
        Returns:
            车辆数据列表
        """
        self.logger.info(f"开始加载车辆数据，目录: {self.data_dir}")
        
        # 获取所有TOML文件
        toml_files = list(self._get_toml_files())
        self.stats['total_files'] = len(toml_files)
        
        if not toml_files:
            self.logger.warning(f"在目录 {self.data_dir} 中未找到TOML文件")
            return []
        
        self.logger.info(f"找到 {len(toml_files)} 个TOML文件")
        
        start_time = time.time()
        
        if parallel:
            vehicles = self._load_parallel(toml_files, max_workers)
        else:
            vehicles = self._load_sequential(toml_files)
        
        loading_time = time.time() - start_time
        self.stats['loading_time'] = loading_time
        
        self.logger.info(
            f"数据加载完成: 成功 {self.stats['loaded_files']}, "
            f"失败 {self.stats['failed_files']}, "
            f"耗时 {loading_time:.2f}秒"
        )
        
        return vehicles
    
    def _get_toml_files(self) -> Generator[Path, None, None]:
        """获取所有TOML文件路径"""
        if not self.data_dir.exists():
            self.logger.error(f"数据目录不存在: {self.data_dir}")
            return
        
        for file_path in self.data_dir.rglob("*.toml"):
            if file_path.is_file():
                yield file_path
    
    def _load_sequential(self, files: List[Path]) -> List[Vehicle]:
        """顺序加载文件"""
        vehicles = []
        
        for file_path in files:
            vehicle = self._load_single_file(file_path)
            if vehicle:
                vehicles.append(vehicle)
        
        return vehicles
    
    def _load_parallel(self, files: List[Path], max_workers: int) -> List[Vehicle]:
        """并行加载文件"""
        vehicles = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_file = {
                executor.submit(self._load_single_file, file_path): file_path 
                for file_path in files
            }
            
            # 收集结果
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    vehicle = future.result()
                    if vehicle:
                        vehicles.append(vehicle)
                except Exception as e:
                    self.logger.error(f"加载文件失败 {file_path}: {e}")
                    self.stats['failed_files'] += 1
        
        return vehicles
    
    def _load_single_file(self, file_path: Path) -> Optional[Vehicle]:
        """
        加载单个TOML文件
        
        Args:
            file_path: TOML文件路径
        
        Returns:
            车辆对象或None
        """
        try:
            # 读取TOML文件
            with open(file_path, 'r', encoding='utf-8') as f:
                data = toml.load(f)
            
            # 验证数据格式
            if not self._validate_data(data):
                self.logger.warning(f"数据格式不正确: {file_path}")
                self.stats['failed_files'] += 1
                return None
            
            # 创建车辆对象
            vehicle = Vehicle(**data)
            vehicle.raw_data = data  # 保存原始数据
            
            self.stats['loaded_files'] += 1
            
            # 每加载100个文件输出一次进度
            if self.stats['loaded_files'] % 100 == 0:
                self.logger.info(f"已加载 {self.stats['loaded_files']} 个文件")
            
            return vehicle
            
        except Exception as e:
            self.logger.error(f"加载文件失败 {file_path}: {e}")
            self.stats['failed_files'] += 1
            return None
    
    def _validate_data(self, data: Dict[str, Any]) -> bool:
        """
        验证数据格式
        
        Args:
            data: TOML数据
        
        Returns:
            是否有效
        """
        # 检查必需字段
        required_fields = ['car_model', 'PriciseLabels', 'AmbiguousLabels', 'KeyDetails']
        
        for field in required_fields:
            if field not in data:
                return False
        
        # 检查car_model不为空
        if not data.get('car_model'):
            return False
        
        return True
    
    def get_vehicle_by_model(self, model_name: str, vehicles: List[Vehicle]) -> Optional[Vehicle]:
        """
        根据型号查找车辆
        
        Args:
            model_name: 车型名称
            vehicles: 车辆列表
        
        Returns:
            匹配的车辆或None
        """
        for vehicle in vehicles:
            if model_name.lower() in vehicle.car_model.lower():
                return vehicle
        return None
    
    def filter_vehicles_by_brand(self, brand: str, vehicles: List[Vehicle]) -> List[Vehicle]:
        """
        按品牌过滤车辆
        
        Args:
            brand: 品牌名称
            vehicles: 车辆列表
        
        Returns:
            过滤后的车辆列表
        """
        brand_lower = brand.lower()
        return [
            vehicle for vehicle in vehicles
            if vehicle.precise_labels.brand and brand_lower in vehicle.precise_labels.brand.lower()
        ]
    
    def filter_vehicles_by_price_range(
        self, 
        min_price: int, 
        max_price: int, 
        vehicles: List[Vehicle],
        tolerance: float = 0.2
    ) -> List[Vehicle]:
        """
        按价格区间过滤车辆
        
        Args:
            min_price: 最低价格
            max_price: 最高价格
            vehicles: 车辆列表
            tolerance: 价格容忍度
        
        Returns:
            过滤后的车辆列表
        """
        filtered_vehicles = []
        
        for vehicle in vehicles:
            price_range = vehicle.get_price_range()
            if not price_range:
                # 如果没有价格信息，根据其他条件决定是否包含
                continue
            
            vehicle_min, vehicle_max = price_range
            
            # 检查价格区间是否有重叠
            if (vehicle_max >= min_price * (1 - tolerance) and 
                vehicle_min <= max_price * (1 + tolerance)):
                filtered_vehicles.append(vehicle)
        
        return filtered_vehicles
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取加载统计信息"""
        return {
            **self.stats,
            'success_rate': self.stats['loaded_files'] / max(self.stats['total_files'], 1),
            'avg_loading_time': self.stats['loading_time'] / max(self.stats['loaded_files'], 1)
        }
    
    def get_data_summary(self, vehicles: List[Vehicle]) -> Dict[str, Any]:
        """
        获取数据摘要信息
        
        Args:
            vehicles: 车辆列表
        
        Returns:
            数据摘要
        """
        if not vehicles:
            return {}
        
        # 统计品牌分布
        brands = {}
        categories = {}
        price_ranges = {"0-10万": 0, "10-20万": 0, "20-30万": 0, "30-40万": 0, "40万+": 0}
        
        for vehicle in vehicles:
            # 品牌统计
            brand = vehicle.precise_labels.brand or "未知"
            brands[brand] = brands.get(brand, 0) + 1
            
            # 车型统计
            category = vehicle.precise_labels.vehicle_category_bottom or "未知"
            categories[category] = categories.get(category, 0) + 1
            
            # 价格区间统计
            price_range = vehicle.get_price_range()
            if price_range:
                avg_price = (price_range[0] + price_range[1]) / 2
                if avg_price < 100000:
                    price_ranges["0-10万"] += 1
                elif avg_price < 200000:
                    price_ranges["10-20万"] += 1
                elif avg_price < 300000:
                    price_ranges["20-30万"] += 1
                elif avg_price < 400000:
                    price_ranges["30-40万"] += 1
                else:
                    price_ranges["40万+"] += 1
        
        return {
            'total_vehicles': len(vehicles),
            'brands': brands,
            'categories': categories,
            'price_ranges': price_ranges,
            'top_brands': sorted(brands.items(), key=lambda x: x[1], reverse=True)[:10]
        }
