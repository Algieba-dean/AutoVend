#!/usr/bin/env python3
"""
Filter-Only Test (No RAG)

This script tests only the structured filtering part of the hybrid system,
without requiring the vector embeddings or semantic search.

Usage:
    python test_filter_only.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.filter.label_registry import LabelRegistry
from src.filter.vehicle_db import VehicleDB
from src.filter.filter_engine import FilterEngine
from src.filter.query_parser import QueryParser
from src.utils.logger import get_logger

logger = get_logger(__name__)


def test_filter_pipeline():
    """Test only the structured filtering pipeline"""
    logger.info("Testing Filter-Only Pipeline")
    logger.info("=" * 50)

    # Initialize components
    registry = LabelRegistry()
    db = VehicleDB(registry=registry)

    # Ensure database is loaded
    if db.count() == 0:
        logger.info("Loading vehicle data into SQLite database...")
        db.import_from_toml_dir()
        logger.info(f"Loaded {db.count()} vehicles into database")
    else:
        logger.info(f"SQLite database contains {db.count()} vehicles")

    # Initialize filter components
    filter_engine = FilterEngine(db=db, registry=registry)
    query_parser = QueryParser(registry=registry)

    # Test queries
    test_queries = [
        "10-20w SUV",
        "Toyota SUV 20-30w",
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
            # Parse query
            parsed = query_parser.parse(query)
            logger.info(f"Matched keywords: {parsed.matched_keywords}")
            logger.info(f"Conditions: {parsed.conditions}")

            # Apply filters
            filter_result = filter_engine.filter(parsed.conditions)
            logger.info(f"Candidate count: {len(filter_result.car_models)}")
            logger.info(f"Degrade level: {filter_result.degrade_level}")

            # Show some sample results
            if filter_result.car_models:
                sample_models = filter_result.car_models[:3]
                logger.info(f"Sample candidates: {sample_models}")

            results.append(
                {
                    "query": query,
                    "success": True,
                    "keywords": parsed.matched_keywords,
                    "candidate_count": len(filter_result.car_models),
                    "degrade_level": filter_result.degrade_level,
                }
            )

        except Exception as e:
            logger.error(f"Error processing query '{query}': {e}")
            results.append({"query": query, "success": False, "error": str(e)})

    # Print summary
    logger.info("\n" + "=" * 50)
    logger.info("Filter-Only Test Summary")
    logger.info("=" * 50)

    successful = sum(1 for r in results if r["success"])
    total = len(results)

    logger.info(f"Total queries: {total}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {total - successful}")
    logger.info(f"Success rate: {successful/total*100:.1f}%")

    # Show detailed results
    logger.info("\nDetailed Results:")
    for r in results:
        if r["success"]:
            logger.info(
                f"  {r['query']}: {r['candidate_count']} candidates (degrade: {r['degrade_level']})"
            )
        else:
            logger.info(f"  {r['query']}: FAILED - {r['error']}")

    # Cleanup
    db.close()
    return successful == total


if __name__ == "__main__":
    success = test_filter_pipeline()
    sys.exit(0 if success else 1)
