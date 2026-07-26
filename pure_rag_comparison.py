#!/usr/bin/env python3
"""
Pure RAG System Comparison
Compare hybrid pipeline vs pure RAG system performance
"""

import sys
import time
import statistics
from pathlib import Path
from typing import Dict, Any, List
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.rag.embeddings import BGEEmbeddingModel
from src.rag.vector_store import ChromaVectorStore
from src.rag.retriever import VehicleRetriever
from src.models.query import Query
from src.filter.label_registry import LabelRegistry
from src.filter.vehicle_db import VehicleDB
from src.filter.filter_engine import FilterEngine
from src.filter.query_parser import QueryParser
from src.retrieval.hybrid_pipeline import HybridPipeline
from src.utils.logger import get_logger

class PureRAGComparison:
    """Compare Pure RAG vs Hybrid Pipeline performance"""
    
    def __init__(self):
        self.logger = get_logger()
        self.embedding_model = BGEEmbeddingModel()
        self.vector_store = ChromaVectorStore()
        
        # Pure RAG system (no filtering)
        self.rag_retriever = VehicleRetriever(
            self.embedding_model, 
            self.vector_store, 
            similarity_threshold=0.3, 
            price_tolerance=0.2
        )
        
        # Hybrid pipeline (with structured filtering)
        self.registry = LabelRegistry()
        self.db = VehicleDB(registry=self.registry)
        
        if self.db.count() == 0:
            self.db.import_from_toml_dir()
        
        self.filter_engine = FilterEngine(db=self.db, registry=self.registry)
        self.query_parser = QueryParser(registry=self.registry)
        
        self.hybrid_pipeline = HybridPipeline(
            registry=self.registry,
            db=self.db,
            filter_engine=self.filter_engine,
            query_parser=self.query_parser,
            retriever=self.rag_retriever
        )
    
    def test_pure_rag_performance(self, queries: List[str]) -> Dict[str, Any]:
        """Test pure RAG system performance"""
        self.logger.info("Testing Pure RAG system performance...")
        
        retrieval_times = []
        success_count = 0
        similarity_scores = []
        result_counts = []
        
        for query_text in queries:
            try:
                start_time = time.time()
                query = Query(text=query_text, top_k=5)
                result = self.rag_retriever.search(query)
                end_time = time.time()
                
                retrieval_time = end_time - start_time
                retrieval_times.append(retrieval_time)
                
                if result and result.results:
                    success_count += 1
                    top_result = result.results[0]
                    similarity_scores.append(top_result.score.semantic_score)
                    result_counts.append(len(result.results))
                else:
                    similarity_scores.append(0.0)
                    result_counts.append(0)
                    
            except Exception as e:
                self.logger.error(f"Pure RAG query failed: {query_text} - {e}")
                retrieval_times.append(0.0)
                similarity_scores.append(0.0)
                result_counts.append(0)
        
        results = {
            'system_type': 'Pure RAG',
            'total_queries': len(queries),
            'successful_queries': success_count,
            'success_rate': success_count / len(queries),
            'avg_retrieval_time': statistics.mean(retrieval_times),
            'min_retrieval_time': min(retrieval_times),
            'max_retrieval_time': max(retrieval_times),
            'avg_similarity_score': statistics.mean(similarity_scores),
            'avg_result_count': statistics.mean(result_counts),
            'retrieval_times': retrieval_times,
            'similarity_scores': similarity_scores
        }
        
        self.logger.info(f"Pure RAG performance test completed")
        return results
    
    def test_hybrid_pipeline_performance(self, queries: List[str]) -> Dict[str, Any]:
        """Test hybrid pipeline performance"""
        self.logger.info("Testing Hybrid Pipeline performance...")
        
        retrieval_times = []
        success_count = 0
        similarity_scores = []
        result_counts = []
        
        for query in queries:
            try:
                start_time = time.time()
                result = self.hybrid_pipeline.search(query, top_k=5)
                end_time = time.time()
                
                retrieval_time = end_time - start_time
                retrieval_times.append(retrieval_time)
                
                if result.search_response and result.search_response.results:
                    success_count += 1
                    top_result = result.search_response.results[0]
                    similarity_scores.append(top_result.score.semantic_score)
                    result_counts.append(len(result.search_response.results))
                else:
                    similarity_scores.append(0.0)
                    result_counts.append(0)
                    
            except Exception as e:
                self.logger.error(f"Hybrid query failed: {query} - {e}")
                retrieval_times.append(0.0)
                similarity_scores.append(0.0)
                result_counts.append(0)
        
        results = {
            'system_type': 'Hybrid Pipeline',
            'total_queries': len(queries),
            'successful_queries': success_count,
            'success_rate': success_count / len(queries),
            'avg_retrieval_time': statistics.mean(retrieval_times),
            'min_retrieval_time': min(retrieval_times),
            'max_retrieval_time': max(retrieval_times),
            'avg_similarity_score': statistics.mean(similarity_scores),
            'avg_result_count': statistics.mean(result_counts),
            'retrieval_times': retrieval_times,
            'similarity_scores': similarity_scores
        }
        
        self.logger.info(f"Hybrid pipeline performance test completed")
        return results
    
    def test_query_accuracy_comparison(self) -> Dict[str, Any]:
        """Test accuracy comparison between systems"""
        self.logger.info("Testing accuracy comparison...")
        
        # Test queries for accuracy comparison
        test_queries = [
            # Basic category queries
            "SUV",
            "Sedan", 
            "MPV",
            
            # Basic brand queries
            "Toyota",
            "BMW",
            "Mercedes-Benz",
            
            # Basic powertrain queries
            "Electric car",
            "Hybrid vehicle",
            "Gasoline car",
            
            # Origin queries
            "German car",
            "Japanese car",
            
            # Price queries
            "Luxury car",
            "Affordable car"
        ]
        
        pure_rag_results = []
        hybrid_results = []
        
        for query in test_queries:
            try:
                # Test pure RAG
                rag_start = time.time()
                rag_query = Query(text=query, top_k=3)
                rag_result = self.rag_retriever.search(rag_query)
                rag_time = time.time() - rag_start
                
                # Test hybrid pipeline
                hybrid_start = time.time()
                hybrid_result = self.hybrid_pipeline.search(query, top_k=3)
                hybrid_time = time.time() - hybrid_start
                
                # Analyze results
                rag_analysis = self._analyze_query_result(query, rag_result, "Pure RAG")
                hybrid_analysis = self._analyze_query_result(query, hybrid_result, "Hybrid")
                
                pure_rag_results.append({
                    'query': query,
                    'time': rag_time,
                    'analysis': rag_analysis
                })
                
                hybrid_results.append({
                    'query': query,
                    'time': hybrid_time,
                    'analysis': hybrid_analysis
                })
                
            except Exception as e:
                self.logger.error(f"Accuracy comparison error for {query}: {e}")
        
        # Calculate accuracy statistics
        pure_rag_accuracy = sum(1 for r in pure_rag_results if r['analysis']['match']) / len(pure_rag_results) * 100 if pure_rag_results else 0
        hybrid_accuracy = sum(1 for r in hybrid_results if r['analysis']['match']) / len(hybrid_results) * 100 if hybrid_results else 0
        
        pure_rag_avg_time = statistics.mean([r['time'] for r in pure_rag_results])
        hybrid_avg_time = statistics.mean([r['time'] for r in hybrid_results])
        
        results = {
            'total_queries': len(test_queries),
            'pure_rag': {
                'accuracy': pure_rag_accuracy,
                'avg_time': pure_rag_avg_time,
                'detailed_results': pure_rag_results
            },
            'hybrid': {
                'accuracy': hybrid_accuracy,
                'avg_time': hybrid_avg_time,
                'detailed_results': hybrid_results
            },
            'improvement': {
                'accuracy_improvement': hybrid_accuracy - pure_rag_accuracy,
                'time_overhead': hybrid_avg_time - pure_rag_avg_time,
                'accuracy_ratio': hybrid_accuracy / pure_rag_accuracy if pure_rag_accuracy > 0 else 0,
                'time_ratio': hybrid_avg_time / pure_rag_avg_time if pure_rag_avg_time > 0 else 0
            }
        }
        
        self.logger.info(f"Accuracy comparison completed")
        return results
    
    def _analyze_query_result(self, query: str, result, system_type: str) -> Dict[str, Any]:
        """Analyze query result for accuracy"""
        # Handle different result types
        if system_type == "Pure RAG":
            if not result or not result.results:
                return {
                    'match': False,
                    'reason': 'No results',
                    'top_result': None,
                    'similarity_score': 0.0
                }
            top_result = result.results[0]
        else:  # Hybrid Pipeline
            if not result or not result.search_response or not result.search_response.results:
                return {
                    'match': False,
                    'reason': 'No results',
                    'top_result': None,
                    'similarity_score': 0.0
                }
            top_result = result.search_response.results[0]
        vehicle = top_result.vehicle
        
        # Simple matching logic for comparison
        match = False
        match_reason = ""
        
        query_lower = query.lower()
        
        # Check category match
        if any(cat in query_lower for cat in ['suv', 'sedan', 'mpv']):
            category = (vehicle.precise_labels.vehicle_category_bottom or '').lower()
            if any(cat in category for cat in ['suv', 'sedan', 'mpv']):
                match = True
                match_reason = f"Category match: {category}"
        
        # Check brand match
        elif any(brand in query_lower for brand in ['toyota', 'bmw', 'mercedes']):
            brand = (vehicle.precise_labels.brand or '').lower()
            if any(b in brand for b in ['toyota', 'bmw', 'mercedes']):
                match = True
                match_reason = f"Brand match: {brand}"
        
        # Check powertrain match
        elif any(pt in query_lower for pt in ['electric', 'hybrid', 'gasoline']):
            powertrain = (vehicle.precise_labels.powertrain_type or '').lower()
            if any(pt in powertrain for pt in ['electric', 'hybrid', 'gasoline']):
                match = True
                match_reason = f"Powertrain match: {powertrain}"
        
        # Check origin match
        elif any(origin in query_lower for origin in ['german', 'japanese']):
            brand = (vehicle.precise_labels.brand or '').lower()
            german_brands = ['mercedes-benz', 'bmw', 'audi', 'porsche']
            japanese_brands = ['toyota', 'honda', 'nissan', 'mazda']
            
            if 'german' in query_lower and any(gb in brand for gb in german_brands):
                match = True
                match_reason = f"German brand match: {brand}"
            elif 'japanese' in query_lower and any(jb in brand for jb in japanese_brands):
                match = True
                match_reason = f"Japanese brand match: {brand}"
        
        # Check price tier match
        elif any(price in query_lower for price in ['luxury', 'affordable']):
            price_str = (vehicle.precise_labels.prize or '').lower()
            if 'luxury' in query_lower and ('above' in price_str or '100,000' in price_str):
                match = True
                match_reason = f"Luxury price match: {price_str}"
            elif 'affordable' in query_lower and ('below' in price_str or '20,000' in price_str):
                match = True
                match_reason = f"Affordable price match: {price_str}"
        
        if not match:
            match_reason = f"No clear match for: {query}"
        
        return {
            'match': match,
            'reason': match_reason,
            'top_result': vehicle.car_model,
            'similarity_score': top_result.score.semantic_score
        }
    
    def run_comparison(self) -> Dict[str, Any]:
        """Run complete comparison between Pure RAG and Hybrid Pipeline"""
        self.logger.info("Starting Pure RAG vs Hybrid Pipeline comparison...")
        
        # Test queries
        test_queries = [
            "SUV",
            "Toyota", 
            "Electric car",
            "German car",
            "Luxury car",
            "Sedan",
            "BMW",
            "Hybrid vehicle",
            "Japanese car",
            "Affordable car"
        ]
        
        # Performance comparison
        pure_rag_perf = self.test_pure_rag_performance(test_queries)
        hybrid_perf = self.test_hybrid_pipeline_performance(test_queries)
        
        # Accuracy comparison
        accuracy_comp = self.test_query_accuracy_comparison()
        
        # Calculate performance differences
        performance_diff = {
            'time_difference': hybrid_perf['avg_retrieval_time'] - pure_rag_perf['avg_retrieval_time'],
            'time_ratio': hybrid_perf['avg_retrieval_time'] / pure_rag_perf['avg_retrieval_time'],
            'similarity_difference': hybrid_perf['avg_similarity_score'] - pure_rag_perf['avg_similarity_score'],
            'success_rate_difference': hybrid_perf['success_rate'] - pure_rag_perf['success_rate']
        }
        
        results = {
            'comparison_summary': {
                'pure_rag_performance': pure_rag_perf,
                'hybrid_performance': hybrid_perf,
                'accuracy_comparison': accuracy_comp,
                'performance_differences': performance_diff
            },
            'conclusions': self._generate_conclusions(pure_rag_perf, hybrid_perf, accuracy_comp, performance_diff)
        }
        
        self.logger.info("Comparison completed successfully")
        return results
    
    def _generate_conclusions(self, pure_rag_perf, hybrid_perf, accuracy_comp, perf_diff) -> Dict[str, Any]:
        """Generate conclusions from the comparison"""
        conclusions = {}
        
        # Performance conclusion
        if perf_diff['time_ratio'] < 1.5:
            conclusions['performance'] = "Hybrid pipeline has acceptable overhead"
        elif perf_diff['time_ratio'] < 2.0:
            conclusions['performance'] = "Hybrid pipeline has moderate overhead"
        else:
            conclusions['performance'] = "Hybrid pipeline has significant overhead"
        
        # Accuracy conclusion
        if accuracy_comp['improvement']['accuracy_improvement'] > 20:
            conclusions['accuracy'] = "Hybrid pipeline significantly improves accuracy"
        elif accuracy_comp['improvement']['accuracy_improvement'] > 10:
            conclusions['accuracy'] = "Hybrid pipeline moderately improves accuracy"
        elif accuracy_comp['improvement']['accuracy_improvement'] > 0:
            conclusions['accuracy'] = "Hybrid pipeline slightly improves accuracy"
        else:
            conclusions['accuracy'] = "Hybrid pipeline does not improve accuracy"
        
        # Overall recommendation
        if (accuracy_comp['improvement']['accuracy_improvement'] > 15 and 
            perf_diff['time_ratio'] < 2.0):
            conclusions['recommendation'] = "Hybrid pipeline is recommended"
        elif (accuracy_comp['improvement']['accuracy_improvement'] > 5 and 
              perf_diff['time_ratio'] < 1.5):
            conclusions['recommendation'] = "Hybrid pipeline is conditionally recommended"
        else:
            conclusions['recommendation'] = "Pure RAG may be sufficient for basic needs"
        
        return conclusions

def main():
    """Main function to run the comparison"""
    print("="*80)
    print("         Pure RAG vs Hybrid Pipeline Comparison")
    print("="*80)
    
    comparison = PureRAGComparison()
    results = comparison.run_comparison()
    
    # Print results
    pure_rag = results['comparison_summary']['pure_rag_performance']
    hybrid = results['comparison_summary']['hybrid_performance']
    accuracy = results['comparison_summary']['accuracy_comparison']
    perf_diff = results['comparison_summary']['performance_differences']
    conclusions = results['conclusions']
    
    print(f"\n**Performance Comparison:**")
    print(f"Pure RAG:")
    print(f"  - Average Time: {pure_rag['avg_retrieval_time']:.3f}s")
    print(f"  - Success Rate: {pure_rag['success_rate']*100:.1f}%")
    print(f"  - Avg Similarity: {pure_rag['avg_similarity_score']:.3f}")
    print(f"  - Avg Results: {pure_rag['avg_result_count']:.1f}")
    
    print(f"\nHybrid Pipeline:")
    print(f"  - Average Time: {hybrid['avg_retrieval_time']:.3f}s")
    print(f"  - Success Rate: {hybrid['success_rate']*100:.1f}%")
    print(f"  - Avg Similarity: {hybrid['avg_similarity_score']:.3f}")
    print(f"  - Avg Results: {hybrid['avg_result_count']:.1f}")
    
    print(f"\n**Performance Differences:**")
    print(f"  - Time Overhead: {perf_diff['time_difference']:.3f}s ({perf_diff['time_ratio']:.1f}x)")
    print(f"  - Similarity Improvement: {perf_diff['similarity_difference']:.3f}")
    print(f"  - Success Rate Improvement: {perf_diff['success_rate_difference']*100:.1f}%")
    
    print(f"\n**Accuracy Comparison:**")
    print(f"  - Pure RAG Accuracy: {accuracy['pure_rag']['accuracy']:.1f}%")
    print(f"  - Hybrid Accuracy: {accuracy['hybrid']['accuracy']:.1f}%")
    print(f"  - Accuracy Improvement: {accuracy['improvement']['accuracy_improvement']:.1f}%")
    
    print(f"\n**Conclusions:**")
    for key, value in conclusions.items():
        print(f"  - {key.title()}: {value}")
    
    # Detailed query results
    print(f"\n**Detailed Query Results:**")
    for i, query in enumerate(accuracy['pure_rag']['detailed_results']):
        rag_result = query['analysis']
        hybrid_result = accuracy['hybrid']['detailed_results'][i]['analysis']
        
        print(f"  Query: {query['query']}")
        print(f"    Pure RAG: {rag_result['match']} - {rag_result['top_result']} ({rag_result['similarity_score']:.3f})")
        print(f"    Hybrid: {hybrid_result['match']} - {hybrid_result['top_result']} ({hybrid_result['similarity_score']:.3f})")
        print()
    
    print("="*80)
    
    return results

if __name__ == "__main__":
    main()
