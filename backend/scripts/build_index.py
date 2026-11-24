"""
One-shot script to build the vehicle knowledge index (SQLite + Vector + BM25).
Usage: python -m backend.scripts.build_index
"""

import logging
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Build the vehicle knowledge index from TOML files via native IndexBuilder."""
    from src.filter.vehicle_db import VehicleDB
    from src.rag.index_builder import IndexBuilder

    logger.info("=== AutoVend Vehicle Knowledge Index Builder ===")

    start = time.time()
    try:
        db = VehicleDB()
        if db.count() == 0:
            db.import_from_toml_dir()
        logger.info(f"SQLite vehicle catalog ready: {db.count()} vehicles")

        builder = IndexBuilder()
        result = builder.build_index()
        if result.get("status") != "success":
            raise ValueError(f"Index build returned status={result.get('status')}")

        elapsed = time.time() - start
        logger.info(f"Index built successfully in {elapsed:.1f}s")
    except ValueError as e:
        logger.error(f"Build failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
