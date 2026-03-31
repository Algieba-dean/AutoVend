"""
索引构建工具

负责构建和管理车辆向量索引，提供增量更新和验证功能。
"""

import time
from pathlib import Path
from typing import List, Optional, Dict, Any

from src.models.vehicle import Vehicle
from src.utils.logger import get_logger, log_performance
from src.utils.config import config
from src.rag.data_loader import VehicleDataLoader
from src.rag.embeddings import BGEEmbeddingModel
from src.rag.vector_store import ChromaVectorStore


class IndexBuilder:
    """索引构建器"""
    
    def __init__(
        self,
        data_dir: Optional[str] = None,
        persist_directory: Optional[str] = None,
        collection_name: Optional[str] = None,
        batch_size: int = 100
    ):
        """
        初始化索引构建器
        
        Args:
            data_dir: 数据目录
            persist_directory: 持久化目录
            collection_name: 集合名称
            batch_size: 批处理大小
        """
        self.data_dir = data_dir or config.vehicle_data_dir
        self.persist_directory = persist_directory or config.chroma_persist_dir
        self.collection_name = collection_name or config.chroma_collection_name
        self.batch_size = batch_size
        
        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        
        # 初始化组件
        self.data_loader = VehicleDataLoader(self.data_dir)
        self.embedding_model = BGEEmbeddingModel()
        self.vector_store = ChromaVectorStore(
            persist_directory=self.persist_directory,
            collection_name=self.collection_name
        )
        
        # 构建统计
        self.build_stats = {
            'total_vehicles': 0,
            'processed_vehicles': 0,
            'failed_vehicles': 0,
            'build_time': 0.0,
            'embedding_time': 0.0,
            'storage_time': 0.0
        }
    
    @log_performance
    def build_index(
        self,
        force_rebuild: bool = False,
        validate_data: bool = True,
        parallel_loading: bool = True
    ) -> Dict[str, Any]:
        """
        构建向量索引
        
        Args:
            force_rebuild: 是否强制重建
            validate_data: 是否验证数据
            parallel_loading: 是否并行加载数据
        
        Returns:
            构建结果统计
        """
        self.logger.info("开始构建车辆向量索引")
        
        start_time = time.time()
        
        # 检查现有索引
        if not force_rebuild:
            existing_count = self.vector_store.collection.count()
            if existing_count > 0:
                self.logger.info(f"发现现有索引，包含 {existing_count} 个文档")
                if not self._confirm_rebuild():
                    return self._get_build_result("cancelled")
        
        # 清空现有索引（如果强制重建）
        if force_rebuild:
            self.logger.info("清空现有索引")
            self.vector_store.clear_collection()
        
        # 加载车辆数据
        self.logger.info("加载车辆数据...")
        vehicles = self.data_loader.load_all_vehicles(parallel=parallel_loading)
        
        if not vehicles:
            self.logger.error("未找到车辆数据")
            return self._get_build_result("failed")
        
        self.build_stats['total_vehicles'] = len(vehicles)
        self.logger.info(f"成功加载 {len(vehicles)} 个车辆数据")
        
        # 验证数据
        if validate_data:
            self.logger.info("验证数据质量...")
            validation_result = self._validate_vehicles(vehicles)
            if not validation_result['valid']:
                self.logger.error(f"数据验证失败: {validation_result['errors']}")
                return self._get_build_result("validation_failed")
        
        # 生成嵌入向量
        self.logger.info("生成嵌入向量...")
        embeddings = self._generate_embeddings(vehicles)
        
        if len(embeddings) != len(vehicles):
            self.logger.error("嵌入向量生成失败")
            return self._get_build_result("embedding_failed")
        
        # 存储到向量数据库
        self.logger.info("存储到向量数据库...")
        self._store_vehicles(vehicles, embeddings)
        
        # 验证索引
        self.logger.info("验证索引质量...")
        validation_result = self._validate_index()
        
        # 计算总时间
        build_time = time.time() - start_time
        self.build_stats['build_time'] = build_time
        
        # 生成构建报告
        result = self._get_build_result("success")
        result['index_validation'] = validation_result
        
        self.logger.info(
            f"索引构建完成: 处理 {self.build_stats['processed_vehicles']} 个车辆，"
            f"失败 {self.build_stats['failed_vehicles']} 个，"
            f"耗时 {build_time:.2f}秒"
        )
        
        return result
    
    def _confirm_rebuild(self) -> bool:
        """确认是否重建索引"""
        # 在实际应用中，这里可以添加用户交互逻辑
        # 为了自动化，我们默认返回True
        return True
    
    def _validate_vehicles(self, vehicles: List[Vehicle]) -> Dict[str, Any]:
        """验证车辆数据"""
        errors = []
        valid_count = 0
        
        for i, vehicle in enumerate(vehicles):
            try:
                # 检查必需字段
                if not vehicle.car_model:
                    errors.append(f"车辆 {i}: 缺少型号信息")
                    continue
                
                # 检查搜索文本
                search_text = vehicle.get_search_text()
                if len(search_text.strip()) < 10:
                    errors.append(f"车辆 {i}: 搜索文本过短")
                    continue
                
                valid_count += 1
                
                # 每100个车辆输出一次进度
                if (i + 1) % 100 == 0:
                    self.logger.info(f"已验证 {i + 1} 个车辆")
                
            except Exception as e:
                errors.append(f"车辆 {i}: 验证失败 - {e}")
        
        return {
            'valid': len(errors) == 0,
            'valid_count': valid_count,
            'error_count': len(errors),
            'errors': errors[:10]  # 只保留前10个错误
        }
    
    def _generate_embeddings(self, vehicles: List[Vehicle]) -> List[List[float]]:
        """生成嵌入向量"""
        start_time = time.time()
        embeddings = []
        
        # 提取搜索文本
        texts = [vehicle.get_search_text() for vehicle in vehicles]
        
        # 批量生成嵌入
        for i in range(0, len(texts), self.batch_size):
            batch_texts = texts[i:i + self.batch_size]
            batch_vehicles = vehicles[i:i + self.batch_size]
            
            try:
                batch_embeddings = self.embedding_model._get_text_embeddings(batch_texts)
                embeddings.extend(batch_embeddings)
                
                self.build_stats['processed_vehicles'] += len(batch_vehicles)
                
                # 输出进度
                progress = (i + len(batch_texts)) / len(texts) * 100
                self.logger.info(f"嵌入生成进度: {progress:.1f}% ({i + len(batch_texts)}/{len(texts)})")
                
            except Exception as e:
                self.logger.error(f"批次 {i//self.batch_size} 嵌入生成失败: {e}")
                self.build_stats['failed_vehicles'] += len(batch_vehicles)
                # 添加空嵌入以保持索引对齐
                embeddings.extend([[0.0] * self.embedding_model.embed_dimension] * len(batch_texts))
        
        embedding_time = time.time() - start_time
        self.build_stats['embedding_time'] = embedding_time
        
        self.logger.info(f"嵌入向量生成完成，耗时 {embedding_time:.2f}秒")
        
        return embeddings
    
    def _store_vehicles(self, vehicles: List[Vehicle], embeddings: List[List[float]]) -> None:
        """存储车辆数据"""
        start_time = time.time()
        
        try:
            self.vector_store.add_vehicles(
                vehicles=vehicles,
                embeddings=embeddings,
                batch_size=self.batch_size
            )
            
            storage_time = time.time() - start_time
            self.build_stats['storage_time'] = storage_time
            
            self.logger.info(f"向量存储完成，耗时 {storage_time:.2f}秒")
            
        except Exception as e:
            self.logger.error(f"向量存储失败: {e}")
            raise
    
    def _validate_index(self) -> Dict[str, Any]:
        """验证索引质量"""
        try:
            # 获取集合信息
            collection_info = self.vector_store.get_collection_info()
            
            # 测试查询
            test_queries = [
                "丰田SUV",
                "家用轿车",
                "新能源车",
                "商务MPV"
            ]
            
            test_results = []
            for query in test_queries:
                try:
                    query_embedding = self.embedding_model._get_text_embedding(query)
                    results = self.vector_store.query(
                        query_embeddings=[query_embedding],
                        n_results=5
                    )
                    
                    if results['ids'] and results['ids'][0]:
                        test_results.append({
                            'query': query,
                            'result_count': len(results['ids'][0]),
                            'top_similarity': 1.0 - results['distances'][0][0] if results['distances'][0] else 0.0
                        })
                    else:
                        test_results.append({
                            'query': query,
                            'result_count': 0,
                            'top_similarity': 0.0
                        })
                        
                except Exception as e:
                    test_results.append({
                        'query': query,
                        'result_count': 0,
                        'top_similarity': 0.0,
                        'error': str(e)
                    })
            
            return {
                'valid': True,
                'collection_info': collection_info,
                'test_queries': test_results,
                'avg_similarity': sum(r['top_similarity'] for r in test_results) / len(test_results)
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }
    
    def _get_build_result(self, status: str) -> Dict[str, Any]:
        """获取构建结果"""
        return {
            'status': status,
            'stats': self.build_stats.copy(),
            'collection_info': self.vector_store.get_collection_info(),
            'embedding_stats': self.embedding_model.get_statistics(),
            'vector_store_stats': self.vector_store.get_statistics()
        }
    
    def update_index(
        self,
        new_vehicles: List[Vehicle],
        incremental: bool = True
    ) -> Dict[str, Any]:
        """
        增量更新索引
        
        Args:
            new_vehicles: 新的车辆数据
            incremental: 是否增量更新
        
        Returns:
            更新结果
        """
        self.logger.info(f"增量更新索引，新增 {len(new_vehicles)} 个车辆")
        
        start_time = time.time()
        
        # 生成嵌入向量
        embeddings = self._generate_embeddings(new_vehicles)
        
        # 存储到向量数据库
        if incremental:
            self.vector_store.add_vehicles(new_vehicles, embeddings)
        else:
            # 非增量模式，重建整个索引
            self.vector_store.clear_collection()
            self.vector_store.add_vehicles(new_vehicles, embeddings)
        
        update_time = time.time() - start_time
        
        result = {
            'status': 'success',
            'updated_count': len(new_vehicles),
            'update_time': update_time,
            'collection_info': self.vector_store.get_collection_info()
        }
        
        self.logger.info(f"索引更新完成，耗时 {update_time:.2f}秒")
        
        return result
    
    def get_index_info(self) -> Dict[str, Any]:
        """获取索引信息"""
        return {
            'collection_info': self.vector_store.get_collection_info(),
            'embedding_model_info': self.embedding_model.get_statistics(),
            'vector_store_stats': self.vector_store.get_statistics(),
            'build_stats': self.build_stats
        }
    
    def backup_index(self, backup_path: Optional[Path] = None) -> None:
        """备份索引"""
        self.logger.info("开始备份索引...")
        
        try:
            self.vector_store.backup_collection(backup_path)
            self.logger.info("索引备份完成")
        except Exception as e:
            self.logger.error(f"索引备份失败: {e}")
            raise
    
    def rebuild_index(self) -> Dict[str, Any]:
        """重建索引"""
        return self.build_index(force_rebuild=True)
