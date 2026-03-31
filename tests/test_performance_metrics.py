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
        
        # 测试查询集合
        self.test_queries = [
            "30万左右的家用SUV",
            "丰田轿车推荐",
            "新能源车",
            "商务MPV",
            "预算20万的家用车",
            "豪华品牌SUV",
            "省油的紧凑型车",
            "7座家用车",
            "运动型轿车",
            "电动车推荐"
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
        
        # 定义测试用例和预期结果类型
        test_cases = [
            {
                'query': 'SUV',
                'expected_category': 'SUV',
                'description': 'SUV车型查询'
            },
            {
                'query': '丰田',
                'expected_brand': 'Toyota',
                'description': '品牌查询'
            },
            {
                'query': '30万左右',
                'expected_price_range': (200000, 400000),
                'description': '价格区间查询'
            },
            {
                'query': '新能源',
                'expected_powertrain': 'Electric',
                'description': '新能源车型查询'
            }
        ]
        
        accuracy_results = []
        
        for test_case in test_cases:
            query = Query(text=test_case['query'], top_k=10)
            response = self.retriever.search(query)
            
            if response.results:
                top_result = response.results[0]
                vehicle = top_result.vehicle
                
                # 检查类别匹配
                category_match = False
                if 'expected_category' in test_case:
                    category = vehicle.precise_labels.vehicle_category_bottom or ''
                    category_match = test_case['expected_category'].lower() in category.lower()
                
                # 检查品牌匹配
                brand_match = False
                if 'expected_brand' in test_case:
                    brand = vehicle.precise_labels.brand or ''
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
                
                accuracy_results.append({
                    'query': test_case['query'],
                    'description': test_case['description'],
                    'top_result': vehicle.car_model,
                    'similarity_score': top_result.score.overall_score,
                    'category_match': category_match,
                    'brand_match': brand_match,
                    'price_match': price_match,
                    'powertrain_match': powertrain_match,
                    'found_results': len(response.results)
                })
        
        # 计算总体准确率
        total_tests = len(accuracy_results)
        category_accuracy = sum(1 for r in accuracy_results if r.get('category_match', False)) / total_tests * 100
        brand_accuracy = sum(1 for r in accuracy_results if r.get('brand_match', False)) / total_tests * 100
        price_accuracy = sum(1 for r in accuracy_results if r.get('price_match', False)) / total_tests * 100
        powertrain_accuracy = sum(1 for r in accuracy_results if r.get('powertrain_match', False)) / total_tests * 100
        
        results = {
            'total_tests': total_tests,
            'category_accuracy': category_accuracy,
            'brand_accuracy': brand_accuracy,
            'price_accuracy': price_accuracy,
            'powertrain_accuracy': powertrain_accuracy,
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
    
    print(f"\n⏱️  总测试时间: {results['test_suite_duration']:.2f}s")
    print("="*60)
    
    return results


if __name__ == "__main__":
    main()
