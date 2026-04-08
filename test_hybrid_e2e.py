#!/usr/bin/env python3
"""
Hybrid Retrieval System End-to-End Test

This script tests the complete hybrid retrieval pipeline:
1. Initialize all components (LabelRegistry, VehicleDB, IndexBuilder, HybridPipeline)
2. Build vector index if needed
3. Run sample queries through the full pipeline
4. Display results with performance metrics

Usage:
    python test_hybrid_e2e.py
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.filter.filter_engine import FilterEngine
from src.filter.label_registry import LabelRegistry
from src.filter.llm_parser import LLMParser
from src.filter.query_parser import QueryParser
from src.filter.vehicle_db import VehicleDB
from src.llm.factory import LLMFactory
from src.rag.embeddings import BGEEmbeddingModel
from src.rag.index_builder import IndexBuilder
from src.rag.retriever import VehicleRetriever
from src.rag.vector_store import ChromaVectorStore
from src.retrieval.hybrid_pipeline import HybridPipeline
from src.utils.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__)


def setup_rag_components():
    """Initialize RAG components for semantic search"""
    logger.info("Initializing RAG components...")

    # Initialize embedding model
    embedding_model = BGEEmbeddingModel()

    # Initialize vector store
    vector_store = ChromaVectorStore(
        persist_directory=config.chroma_persist_dir,
        collection_name=config.chroma_collection_name,
    )

    # Initialize retriever
    retriever = VehicleRetriever(
        embedding_model=embedding_model, vector_store=vector_store
    )

    logger.info("RAG components initialized successfully")
    return retriever


def build_vector_index_if_needed():
    """Build vector index if it doesn't exist or is empty"""
    logger.info("Checking vector index...")

    # Initialize index builder
    index_builder = IndexBuilder()

    # Check existing index
    try:
        index_info = index_builder.get_index_info()
        collection_info = index_info["collection_info"]

        if collection_info.get("count", 0) > 0:
            logger.info(
                f"Vector index already exists with {collection_info['count']} documents"
            )
            return index_builder
        else:
            logger.info("Vector index is empty, building new index...")
    except Exception as e:
        logger.warning(f"Could not check existing index: {e}")
        logger.info("Building new index...")

    # Build index only if needed
    try:
        # First try to use existing index without rebuilding
        try:
            index_info = index_builder.get_index_info()
            collection_info = index_info["collection_info"]
            if collection_info.get("count", 0) > 0:
                logger.info(
                    f"Using existing vector index with {collection_info['count']} documents"
                )
                return index_builder
        except:
            pass

        # If no valid index exists, try to build
        logger.info("Attempting to build vector index...")
        result = index_builder.build_index(force_rebuild=False)

        if result["status"] == "success":
            logger.info(f"Vector index built successfully: {result['stats']}")
            return index_builder
        else:
            logger.error(f"Failed to build vector index: {result['status']}")
            logger.warning(
                "Continuing without vector index - semantic search will be disabled"
            )
            return None

    except Exception as e:
        logger.error(f"Error building vector index: {e}")
        logger.warning(
            "Continuing without vector index - semantic search will be disabled"
        )
        return None


def initialize_hybrid_pipeline():
    """Initialize the complete hybrid pipeline"""
    logger.info("Initializing hybrid pipeline...")

    # Initialize shared components
    registry = LabelRegistry()
    db = VehicleDB(registry=registry)

    # Ensure database is loaded
    if db.count() == 0:
        logger.info("Loading vehicle data into SQLite database...")
        db.import_from_toml_dir()
        logger.info(f"Loaded {db.count()} vehicles into database")
    else:
        logger.info(f"SQLite database already contains {db.count()} vehicles")

    # Initialize filter components
    filter_engine = FilterEngine(db=db, registry=registry)
    query_parser = QueryParser(registry=registry)

    # Initialize LLM parser (optional)
    llm_parser = None
    try:
        llm = LLMFactory.create_llm()
        if llm and llm.is_available():
            llm_parser = LLMParser(llm=llm, registry=registry)
            logger.info("LLM parser initialized successfully")
        else:
            logger.warning("LLM not available, using rule-based parser only")
    except Exception as e:
        logger.warning(f"Failed to initialize LLM parser: {e}")

    # Initialize RAG components
    retriever = setup_rag_components()

    # Initialize hybrid pipeline
    pipeline = HybridPipeline(
        registry=registry,
        db=db,
        filter_engine=filter_engine,
        query_parser=query_parser,
        llm_parser=llm_parser,
        retriever=retriever,
    )

    logger.info("Hybrid pipeline initialized successfully")
    return pipeline


def run_sample_queries(pipeline):
    """Run sample queries through the hybrid pipeline"""
    logger.info("\n" + "=" * 60)
    logger.info("Running End-to-End Tests")
    logger.info("=" * 60)

    test_queries = [
        "10-20w SUV",
        " Toyota SUV 20-30w",
        "electric car under 15w",
        "MPV 7 seats",
        "luxury sedan 30-50w",
        "off-road vehicle",
        "family car good fuel consumption",
        "smart car with autopilot",
        "business vehicle",
        "compact car for city",
    ]

    results = []

    for i, query in enumerate(test_queries, 1):
        logger.info(f"\n--- Test {i}: {query} ---")

        try:
            start_time = time.time()
            result = pipeline.search(query, top_k=5, use_llm_fallback=True)
            end_time = time.time()

            # Log results
            summary = result.summary()
            logger.info(f"Parse method: {summary['parse_method']}")
            logger.info(f"Matched keywords: {summary['matched_keywords']}")
            logger.info(f"Candidate count: {summary['candidate_count']}")
            logger.info(f"RAG result count: {summary['rag_result_count']}")
            logger.info(f"Total time: {summary['total_time']}s")

            # Show top results if available
            if result.search_response and result.search_response.results:
                logger.info("Top results:")
                for j, search_result in enumerate(
                    result.search_response.results[:3], 1
                ):
                    vehicle = search_result.vehicle
                    score = search_result.match_score
                    logger.info(f"  {j}. {vehicle.car_model} - {vehicle.brand}")
                    logger.info(
                        f"     Score: {score.overall:.3f} (semantic: {score.semantic:.3f})"
                    )
                    logger.info(
                        f"     Price: {vehicle.prize} | Category: {vehicle.vehicle_category_bottom}"
                    )

            results.append(
                {
                    "query": query,
                    "success": True,
                    "summary": summary,
                    "time": end_time - start_time,
                }
            )

        except Exception as e:
            logger.error(f"Error processing query '{query}': {e}")
            results.append(
                {
                    "query": query,
                    "success": False,
                    "error": str(e),
                    "time": time.time() - start_time,
                }
            )

    return results


def print_test_summary(results):
    """Print test summary"""
    logger.info("\n" + "=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)

    successful = sum(1 for r in results if r["success"])
    total = len(results)

    logger.info(f"Total queries: {total}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {total - successful}")
    logger.info(f"Success rate: {successful/total*100:.1f}%")

    if successful > 0:
        avg_time = sum(r["time"] for r in results if r["success"]) / successful
        logger.info(f"Average response time: {avg_time:.3f}s")

        # Show failed queries
        failed = [r for r in results if not r["success"]]
        if failed:
            logger.info("\nFailed queries:")
            for r in failed:
                logger.info(f"  - {r['query']}: {r['error']}")


def main():
    """Main test function"""
    logger.info("Starting Hybrid Retrieval System End-to-End Test")

    try:
        # Step 1: Build vector index if needed
        index_builder = build_vector_index_if_needed()
        if not index_builder:
            logger.error("Failed to build vector index, exiting")
            return False

        # Step 2: Initialize hybrid pipeline
        pipeline = initialize_hybrid_pipeline()

        # Step 3: Run sample queries
        results = run_sample_queries(pipeline)

        # Step 4: Print summary
        print_test_summary(results)

        # Step 5: Cleanup
        pipeline.close()

        logger.info("\nEnd-to-End test completed successfully!")
        return True

    except Exception as e:
        logger.error(f"End-to-end test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
