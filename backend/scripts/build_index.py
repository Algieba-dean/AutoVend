"""
One-shot script to build the ChromaDB vehicle knowledge index.
Usage: python -m scripts.build_index
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
    """Build the vehicle knowledge index from TOML files."""
    from app.config import CHROMA_PERSIST_DIR, VEHICLE_DATA_DIR
    from app.ingestion.index_builder import build_vehicle_index

    logger.info("=== AutoVend Vehicle Knowledge Index Builder ===")
    logger.info(f"Vehicle data dir: {VEHICLE_DATA_DIR}")
    logger.info(f"ChromaDB persist dir: {CHROMA_PERSIST_DIR}")

    start = time.time()
    try:
        build_vehicle_index()
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
