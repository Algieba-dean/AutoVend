"""
性能指标测试

测试RAG系统的各项性能指标，包括响应时间、准确率、并发性能等。
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import time
import statistics
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
import pytest

from src.rag.embeddings import BGEEmbeddingModel
from src.rag.vector_store import ChromaVectorStore
from src.rag.retriever import VehicleRetriever
from src.models.query import Query
from src.utils.logger import get_logger


class PerformanceMetricsTest:
    """性能指标测试类"""
    
    def __init__(self):
        self.logger = get_logger()
        self.embedding_model = BGEEmbeddingModel()
        self.vector_store = ChromaVectorStore()
        self.retriever = VehicleRetriever(
            self.embedding_model,
            self.vector_store,
            similarity_threshold=0.3,
            price_tolerance=0.2
        )
        
        # 扩展的复杂测试查询集合
        self.test_queries = [
            # 基础查询
            "30万左右的家用SUV",
            "丰田轿车推荐",
            "新能源车推荐",
            "商务MPV",
            "预算20万的家用车",
            "豪华品牌SUV",
            "省油的紧凑型车",
            "7座家用车",
            "运动型轿车",
            "电动车推荐",
            
            # 价格区间测试
            "10万以下的代步车",
            "50万以上的豪华车",
            "15-25万区间的SUV",
            "80万左右的跑车",
            "预算8万的二手车",
            "100万级别的超跑",
            "25万左右的B级车",
            "35万内豪华SUV",
            
            # 品牌测试
            "奔驰宝马奥迪对比",
            "比亚迪新能源车型",
            "特斯拉Model系列",
            "大众途观家族",
            "本田雅阁凯美瑞选哪个",
            "蔚来理想小鹏推荐",
            "保时捷卡宴车型",
            "雷克萨斯ES系列",
            
            # 车型类别测试
            "7座大型SUV推荐",
            "紧凑型两厢车",
            "中大型轿车",
            "小型电动SUV",
            "硬派越野车",
            "旅行车推荐",
            "皮卡车车型",
            "轿跑车选择",
            
            # 使用场景测试
            "城市通勤代步车",
            "长途旅行舒适车",
            "商务接待用车",
            "家庭第二辆车",
            "山区自驾游车辆",
            "网约车运营车型",
            "新手司机友好车",
            "老年人代步车",
            
            # 性能需求测试
            "省油耐用的家用车",
            "动力强劲的运动车",
            "静音舒适的豪华车",
            "安全系数高的车",
            "保值率好的车",
            "操控性好的车",
            "通过性强的SUV",
            "加速快的电动车",
            
            # 新能源专项测试
            "纯电动车续航500公里",
            "插电混动车推荐",
            "氢燃料电池车",
            "换电模式的电动车",
            "快充支持的新能源",
            "增程式电动车",
            "刀片电池车型",
            
            # 配置需求测试
            "带全景天窗的SUV",
            "自动驾驶辅助系统",
            "座椅加热通风车型",
            "HUD抬头显示配置",
            "高级音响系统车型",
            "矩阵式LED大灯",
            "空气悬挂车型",
            "四驱系统SUV",
            
            # 复杂组合查询
            "30万左右带自动驾驶的SUV",
            "20万以内省油的家用轿车推荐",
            "40万级别豪华品牌新能源车",
            "15万左右7座MPV商务车",
            "适合女性的小型SUV自动挡",
            "25万带全景天窗的轿车",
            "60万级别四驱豪华SUV",
            
            # 对比查询
            "汉兰达vs途昂怎么选",
            "Model 3对比汉EV",
            "CR-V和RAV4哪个好",
            "理想L8和问界M7对比",
            "帕萨特迈腾雅阁凯美瑞选哪个",
            "宝马X3奔驰GLC奥迪Q5",
            "比亚迪唐vs理想ONE",
            
            # 细分需求查询
            "适合老年人的车",
            "新手司机友好车型",
            "女生开的SUV推荐",
            "二胎家庭7座车",
            "网约车运营车型",
            "越野能力强的SUV",
            "豪华品牌入门车型",
            "高性能电动车推荐"
        ]
    
    def test_embedding_performance(self) -> Dict[str, Any]:
        """测试嵌入模型性能"""
        self.logger.info("🧪 测试嵌入模型性能...")
        
        # 单次嵌入测试
        single_texts = ["测试文本", "汽车推荐", "家用SUV"]
        single_times = []
        
        for text in single_texts:
            start_time = time.time()
            embedding = self.embedding_model._get_text_embedding(text)
            end_time = time.time()
            single_times.append(end_time - start_time)
        
        # 批量嵌入测试
        batch_texts = [f"测试文本{i}" for i in range(50)]
        start_time = time.time()
        batch_embeddings = self.embedding_model._get_text_embeddings(batch_texts)
        end_time = time.time()
        batch_time = end_time - start_time
        
        # 相似度计算测试
        embedding1 = self.embedding_model._get_text_embedding("汽车")
        embedding2 = self.embedding_model._get_text_embedding("车辆")
        start_time = time.time()
        similarity = self.embedding_model.similarity(embedding1, embedding2)
        end_time = time.time()
        similarity_time = end_time - start_time
        
        results = {
            'single_embedding_avg_time': statistics.mean(single_times),
            'single_embedding_max_time': max(single_times),
            'single_embedding_min_time': min(single_times),
            'batch_embedding_time': batch_time,
            'batch_embedding_avg_per_text': batch_time / len(batch_texts),
            'similarity_calculation_time': similarity_time,
            'embedding_dimension': len(embedding1),
            'batch_size': len(batch_texts)
        }
        
        self.logger.info(f"✅ 嵌入模型性能测试完成")
        return results
    
    def test_retrieval_performance(self) -> Dict[str, Any]:
        """测试检索性能"""
        self.logger.info("🧪 测试检索性能...")
        
        retrieval_times = []
        result_counts = []
        similarity_scores = []
        
        for query_text in self.test_queries:
            query = Query(text=query_text, top_k=10)
            
            start_time = time.time()
            response = self.retriever.search(query)
            end_time = time.time()
            
            retrieval_times.append(end_time - start_time)
            result_counts.append(len(response.results))
            
            if response.results:
                similarity_scores.append(response.results[0].score.overall_score)
        
        results = {
            'avg_retrieval_time': statistics.mean(retrieval_times),
            'max_retrieval_time': max(retrieval_times),
            'min_retrieval_time': min(retrieval_times),
            'avg_result_count': statistics.mean(result_counts),
            'avg_similarity_score': statistics.mean(similarity_scores) if similarity_scores else 0,
            'total_queries': len(self.test_queries),
            'successful_queries': len([r for r in result_counts if r > 0])
        }
        
        self.logger.info(f"✅ 检索性能测试完成")
        return results
    
    def test_concurrent_performance(self, num_threads: int = 5, queries_per_thread: int = 10) -> Dict[str, Any]:
        """测试并发性能"""
        self.logger.info(f"🧪 测试并发性能 ({num_threads} 线程, 每线程 {queries_per_thread} 查询)...")
        
        def worker_thread(thread_id: int) -> List[Dict[str, Any]]:
            """工作线程函数"""
            thread_results = []
            
            for i in range(queries_per_thread):
                query_text = self.test_queries[i % len(self.test_queries)]
                query = Query(text=query_text, top_k=5)
                
                start_time = time.time()
                try:
                    response = self.retriever.search(query)
                    end_time = time.time()
                    
                    thread_results.append({
                        'thread_id': thread_id,
                        'query_id': i,
                        'response_time': end_time - start_time,
                        'result_count': len(response.results),
                        'success': True
                    })
                except Exception as e:
                    end_time = time.time()
                    thread_results.append({
                        'thread_id': thread_id,
                        'query_id': i,
                        'response_time': end_time - start_time,
                        'result_count': 0,
                        'success': False,
                        'error': str(e)
                    })
            
            return thread_results
        
        # 执行并发测试
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker_thread, i) for i in range(num_threads)]
            all_results = []
            
            for future in as_completed(futures):
                try:
                    thread_results = future.result()
                    all_results.extend(thread_results)
                except Exception as e:
                    self.logger.error(f"线程执行失败: {e}")
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 分析结果
        successful_results = [r for r in all_results if r['success']]
        response_times = [r['response_time'] for r in successful_results]
        
        results = {
            'total_time': total_time,
            'total_queries': len(all_results),
            'successful_queries': len(successful_results),
            'success_rate': len(successful_results) / len(all_results),
            'queries_per_second': len(all_results) / total_time,
            'avg_response_time': statistics.mean(response_times) if response_times else 0,
            'max_response_time': max(response_times) if response_times else 0,
            'min_response_time': min(response_times) if response_times else 0,
            'num_threads': num_threads,
            'queries_per_thread': queries_per_thread
        }
        
        self.logger.info(f"✅ 并发性能测试完成")
        return results
    
    def test_memory_usage(self) -> Dict[str, Any]:
        """测试内存使用情况"""
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            
            # 基线内存使用
            baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # 加载嵌入模型后的内存使用
            model_memory = process.memory_info().rss / 1024 / 1024
            
            # 执行一些查询后的内存使用
            for query_text in self.test_queries[:5]:
                query = Query(text=query_text, top_k=5)
                self.retriever.search(query)
            
            peak_memory = process.memory_info().rss / 1024 / 1024
            
            results = {
                'baseline_memory_mb': baseline_memory,
                'model_memory_mb': model_memory,
                'peak_memory_mb': peak_memory,
                'model_overhead_mb': model_memory - baseline_memory,
                'query_overhead_mb': peak_memory - model_memory,
                'total_memory_mb': peak_memory
            }
            
            self.logger.info(f"✅ 内存使用测试完成")
            return results
            
        except ImportError:
            self.logger.warning("psutil未安装，跳过内存使用测试")
            return {'error': 'psutil not available'}
    
    def test_accuracy_metrics(self) -> Dict[str, Any]:
        """测试准确性指标"""
        self.logger.info("🧪 测试准确性指标...")
        
        # 扩展的准确性测试用例 - 基于实际车辆数据
        test_cases = [
            # 基础类别测试
            {
                'query': 'SUV',
                'expected_category': 'SUV',
                'description': 'SUV车型查询'
            },
            {
                'query': '轿车',
                'expected_category': 'Sedan',
                'description': '轿车车型查询'
            },
            {
                'query': 'MPV',
                'expected_category': 'MPV',
                'description': 'MPV车型查询'
            },
            
            # 品牌测试
            {
                'query': '丰田',
                'expected_brand': 'Toyota',
                'description': '丰田品牌查询'
            },
            {
                'query': '奔驰',
                'expected_brand': 'Mercedes-Benz',
                'description': '奔驰品牌查询'
            },
            {
                'query': '宝马',
                'expected_brand': 'BMW',
                'description': '宝马品牌查询'
            },
            {
                'query': '特斯拉',
                'expected_brand': 'Tesla',
                'description': '特斯拉品牌查询'
            },
            {
                'query': '比亚迪',
                'expected_brand': 'BYD',
                'description': '比亚迪品牌查询'
            },
            
            # 价格区间测试
            {
                'query': '10万以下',
                'expected_price_range': (0, 120000),
                'description': '低价位查询'
            },
            {
                'query': '30万左右',
                'expected_price_range': (250000, 350000),
                'description': '中等价位查询'
            },
            {
                'query': '50万以上',
                'expected_price_range': (450000, 2000000),
                'description': '高价位查询'
            },
            {
                'query': '15-25万',
                'expected_price_range': (140000, 260000),
                'description': '精确价格区间查询'
            },
            
            # 动力类型测试
            {
                'query': '新能源',
                'expected_powertrain': 'Electric',
                'description': '新能源车型查询'
            },
            {
                'query': '纯电动',
                'expected_powertrain': 'Electric',
                'description': '纯电动车型查询'
            },
            {
                'query': '混动',
                'expected_powertrain': 'Hybrid',
                'description': '混动车型查询'
            },
            {
                'query': '燃油车',
                'expected_powertrain': 'Gasoline',
                'description': '燃油车型查询'
            },
            
            # 使用场景测试
            {
                'query': '家用',
                'expected_usage': '家用',
                'description': '家用场景查询'
            },
            {
                'query': '商务',
                'expected_usage': '商务',
                'description': '商务场景查询'
            },
            {
                'query': '越野',
                'expected_usage': '越野',
                'description': '越野场景查询'
            },
            
            # 车型尺寸测试
            {
                'query': '紧凑型',
                'expected_size': '紧凑型',
                'description': '紧凑型车查询'
            },
            {
                'query': '中型',
                'expected_size': '中型',
                'description': '中型车查询'
            },
            {
                'query': '大型',
                'expected_size': '大型',
                'description': '大型车查询'
            },
            
            # 复合查询测试
            {
                'query': '豪华SUV',
                'expected_brand': ['Mercedes-Benz', 'BMW', 'Audi', 'Lexus'],
                'expected_category': 'SUV',
                'description': '豪华品牌SUV查询'
            },
            {
                'query': '新能源轿车',
                'expected_powertrain': 'Electric',
                'expected_category': 'Sedan',
                'description': '新能源轿车查询'
            },
            {
                'query': '7座MPV',
                'expected_category': 'MPV',
                'expected_seats': 7,
                'description': '7座MPV查询'
            },
            
            # 具体车型测试
            {
                'query': '汉兰达',
                'expected_model': 'Highlander',
                'description': '具体车型查询'
            },
            {
                'query': 'Model 3',
                'expected_model': 'Model 3',
                'description': '特斯拉Model 3查询'
            },
            {
                'query': '雅阁',
                'expected_model': 'Accord',
                'description': '本田雅阁查询'
            },
            
            # 配置特征测试
            {
                'query': '四驱',
                'expected_drive': 'AWD',
                'description': '四驱系统查询'
            },
            {
                'query': '自动挡',
                'expected_transmission': 'Automatic',
                'description': '自动变速箱查询'
            },
            {
                'query': '全景天窗',
                'expected_feature': '天窗',
                'description': '天窗配置查询'
            }
        ]
        
        accuracy_results = []
        
        for test_case in test_cases:
            query = Query(text=test_case['query'], top_k=10)
            response = self.retriever.search(query)
            
            if response.results:
                top_result = response.results[0]
                vehicle = top_result.vehicle
                
                # 扩展的匹配检查逻辑
                # 检查类别匹配
                category_match = False
                if 'expected_category' in test_case:
                    category = vehicle.precise_labels.vehicle_category_bottom or ''
                    if isinstance(test_case['expected_category'], str):
                        category_match = test_case['expected_category'].lower() in category.lower()
                
                # 检查品牌匹配
                brand_match = False
                if 'expected_brand' in test_case:
                    brand = vehicle.precise_labels.brand or ''
                    if isinstance(test_case['expected_brand'], list):
                        # 多个品牌匹配
                        brand_match = any(
                            expected_brand.lower() in brand.lower() 
                            for expected_brand in test_case['expected_brand']
                        )
                    else:
                        # 单个品牌匹配
                        brand_match = test_case['expected_brand'].lower() in brand.lower()
                
                # 检查价格匹配
                price_match = False
                if 'expected_price_range' in test_case:
                    price_range = vehicle.get_price_range()
                    if price_range:
                        min_price, max_price = price_range
                        expected_min, expected_max = test_case['expected_price_range']
                        # 检查价格区间是否有重叠
                        price_match = not (max_price < expected_min or min_price > expected_max)
                
                # 检查动力类型匹配
                powertrain_match = False
                if 'expected_powertrain' in test_case:
                    powertrain = vehicle.precise_labels.powertrain_type or ''
                    powertrain_match = test_case['expected_powertrain'].lower() in powertrain.lower()
                
                # 检查使用场景匹配
                usage_match = False
                if 'expected_usage' in test_case:
                    search_text = vehicle.get_search_text().lower()
                    usage_match = test_case['expected_usage'].lower() in search_text
                
                # 检查尺寸匹配
                size_match = False
                if 'expected_size' in test_case:
                    search_text = vehicle.get_search_text().lower()
                    size_match = test_case['expected_size'].lower() in search_text
                
                # 检查车型匹配
                model_match = False
                if 'expected_model' in test_case:
                    model = vehicle.car_model or ''
                    model_match = test_case['expected_model'].lower() in model.lower()
                
                # 检查座位数匹配
                seats_match = False
                if 'expected_seats' in test_case:
                    seat_layout = vehicle.precise_labels.seat_layout or ''
                    # 从座位布局中提取座位数，如"7座" -> 7
                    import re
                    seats_match = any(
                        str(test_case['expected_seats']) in seat_layout or
                        re.search(rf'{test_case["expected_seats"]}[座席]', seat_layout)
                        for expected_seats in [test_case['expected_seats']]
                    )
                
                # 检查驱动方式匹配
                drive_match = False
                if 'expected_drive' in test_case:
                    drive = vehicle.precise_labels.drive_type or ''
                    drive_match = test_case['expected_drive'].lower() in drive.lower()
                
                # 检查变速箱匹配 - 使用搜索文本
                transmission_match = False
                if 'expected_transmission' in test_case:
                    search_text = vehicle.get_search_text().lower()
                    if test_case['expected_transmission'] == 'Automatic':
                        transmission_match = any(term in search_text for term in ['自动', 'automatic', 'at'])
                    else:
                        transmission_match = test_case['expected_transmission'].lower() in search_text
                
                # 检查配置特征匹配
                feature_match = False
                if 'expected_feature' in test_case:
                    search_text = vehicle.get_search_text().lower()
                    feature_match = test_case['expected_feature'].lower() in search_text
                
                accuracy_results.append({
                    'query': test_case['query'],
                    'description': test_case['description'],
                    'top_result': vehicle.car_model,
                    'similarity_score': top_result.score.overall_score,
                    'category_match': category_match,
                    'brand_match': brand_match,
                    'price_match': price_match,
                    'powertrain_match': powertrain_match,
                    'usage_match': usage_match,
                    'size_match': size_match,
                    'model_match': model_match,
                    'seats_match': seats_match,
                    'drive_match': drive_match,
                    'transmission_match': transmission_match,
                    'feature_match': feature_match,
                    'found_results': len(response.results)
                })
        
        # 计算总体准确率 - 扩展指标
        total_tests = len(accuracy_results)
        
        # 基础准确率
        category_accuracy = sum(1 for r in accuracy_results if r.get('category_match', False)) / total_tests * 100
        brand_accuracy = sum(1 for r in accuracy_results if r.get('brand_match', False)) / total_tests * 100
        price_accuracy = sum(1 for r in accuracy_results if r.get('price_match', False)) / total_tests * 100
        powertrain_accuracy = sum(1 for r in accuracy_results if r.get('powertrain_match', False)) / total_tests * 100
        
        # 扩展准确率
        usage_accuracy = sum(1 for r in accuracy_results if r.get('usage_match', False)) / total_tests * 100
        size_accuracy = sum(1 for r in accuracy_results if r.get('size_match', False)) / total_tests * 100
        model_accuracy = sum(1 for r in accuracy_results if r.get('model_match', False)) / total_tests * 100
        seats_accuracy = sum(1 for r in accuracy_results if r.get('seats_match', False)) / total_tests * 100
        drive_accuracy = sum(1 for r in accuracy_results if r.get('drive_match', False)) / total_tests * 100
        transmission_accuracy = sum(1 for r in accuracy_results if r.get('transmission_match', False)) / total_tests * 100
        feature_accuracy = sum(1 for r in accuracy_results if r.get('feature_match', False)) / total_tests * 100
        
        # 综合准确率
        comprehensive_accuracy = sum(
            (r.get('category_match', False) + 
             r.get('brand_match', False) + 
             r.get('price_match', False) + 
             r.get('powertrain_match', False) +
             r.get('usage_match', False) +
             r.get('size_match', False) +
             r.get('model_match', False) +
             r.get('seats_match', False) +
             r.get('drive_match', False) +
             r.get('transmission_match', False) +
             r.get('feature_match', False)) 
            for r in accuracy_results
        ) / (total_tests * 11) * 100
        
        results = {
            'total_tests': total_tests,
            # 基础准确率
            'category_accuracy': category_accuracy,
            'brand_accuracy': brand_accuracy,
            'price_accuracy': price_accuracy,
            'powertrain_accuracy': powertrain_accuracy,
            # 扩展准确率
            'usage_accuracy': usage_accuracy,
            'size_accuracy': size_accuracy,
            'model_accuracy': model_accuracy,
            'seats_accuracy': seats_accuracy,
            'drive_accuracy': drive_accuracy,
            'transmission_accuracy': transmission_accuracy,
            'feature_accuracy': feature_accuracy,
            # 综合指标
            'comprehensive_accuracy': comprehensive_accuracy,
            'avg_similarity_score': statistics.mean([r['similarity_score'] for r in accuracy_results]),
            'detailed_results': accuracy_results
        }
        
        self.logger.info(f"✅ 准确性指标测试完成")
        return results
    
    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有性能测试"""
        self.logger.info("🚀 开始运行完整性能测试套件...")
        
        start_time = time.time()
        
        results = {
            'test_suite_start_time': start_time,
            'embedding_performance': self.test_embedding_performance(),
            'retrieval_performance': self.test_retrieval_performance(),
            'concurrent_performance': self.test_concurrent_performance(),
            'memory_usage': self.test_memory_usage(),
            'accuracy_metrics': self.test_accuracy_metrics()
        }
        
        end_time = time.time()
        results['test_suite_duration'] = end_time - start_time
        
        self.logger.info(f"✅ 完整性能测试套件执行完成，耗时 {results['test_suite_duration']:.2f}秒")
        
        return results


def main():
    """主函数"""
    tester = PerformanceMetricsTest()
    results = tester.run_all_tests()
    
    # 输出测试结果摘要
    print("\n" + "="*60)
    print("📊 AutoVend RAG 系统性能测试报告")
    print("="*60)
    
    # 嵌入性能
    embed_perf = results['embedding_performance']
    print(f"\n🔤 嵌入模型性能:")
    print(f"  单次嵌入平均时间: {embed_perf['single_embedding_avg_time']:.3f}s")
    print(f"  批量嵌入平均时间: {embed_perf['batch_embedding_avg_per_text']:.3f}s/文本")
    print(f"  相似度计算时间: {embed_perf['similarity_calculation_time']:.6f}s")
    
    # 检索性能
    retrieval_perf = results['retrieval_performance']
    print(f"\n🔍 检索性能:")
    print(f"  平均检索时间: {retrieval_perf['avg_retrieval_time']:.3f}s")
    print(f"  成功率: {retrieval_perf['successful_queries']}/{retrieval_perf['total_queries']}")
    print(f"  平均相似度: {retrieval_perf['avg_similarity_score']:.3f}")
    
    # 并发性能
    concurrent_perf = results['concurrent_performance']
    print(f"\n⚡ 并发性能:")
    print(f"  QPS: {concurrent_perf['queries_per_second']:.2f}")
    print(f"  平均响应时间: {concurrent_perf['avg_response_time']:.3f}s")
    print(f"  成功率: {concurrent_perf['success_rate']*100:.1f}%")
    
    # 内存使用
    memory_usage = results['memory_usage']
    if 'error' not in memory_usage:
        print(f"\n💾 内存使用:")
        print(f"  基线内存: {memory_usage['baseline_memory_mb']:.1f}MB")
        print(f"  模型内存: {memory_usage['model_memory_mb']:.1f}MB")
        print(f"  峰值内存: {memory_usage['peak_memory_mb']:.1f}MB")
    
    # 准确性指标
    accuracy = results['accuracy_metrics']
    print(f"\n🎯 准确性指标:")
    print(f"  类别准确率: {accuracy['category_accuracy']:.1f}%")
    print(f"  品牌准确率: {accuracy['brand_accuracy']:.1f}%")
    print(f"  价格准确率: {accuracy['price_accuracy']:.1f}%")
    print(f"  动力类型准确率: {accuracy['powertrain_accuracy']:.1f}%")
    print(f"  使用场景准确率: {accuracy['usage_accuracy']:.1f}%")
    print(f"  尺寸准确率: {accuracy['size_accuracy']:.1f}%")
    print(f"  车型准确率: {accuracy['model_accuracy']:.1f}%")
    print(f"  座位准确率: {accuracy['seats_accuracy']:.1f}%")
    print(f"  驱动准确率: {accuracy['drive_accuracy']:.1f}%")
    print(f"  变速箱准确率: {accuracy['transmission_accuracy']:.1f}%")
    print(f"  配置准确率: {accuracy['feature_accuracy']:.1f}%")
    print(f"  🌟 综合准确率: {accuracy['comprehensive_accuracy']:.1f}%")
    
    print(f"\n⏱️  总测试时间: {results['test_suite_duration']:.2f}s")
    print("="*60)
    
    return results


if __name__ == "__main__":
    main()
