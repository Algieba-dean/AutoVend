"""
Parse vehicle TOML files into LlamaIndex Document objects.

Each TOML file contains structured vehicle data with:
- Top-level: title, car_model
- [PriciseLabels]: precise specification fields + *_comments
- [AmbiguousLabels]: subjective rating fields + *_comments
- [KeyDetails]: key_details text + key_details_comments
"""

import logging
from pathlib import Path
from typing import List, Optional

import toml
from llama_index.core.schema import Document

logger = logging.getLogger(__name__)

# Fields to extract as metadata for filtering
METADATA_FIELDS = [
    "brand",
    "prize",
    "powertrain_type",
    "vehicle_category_bottom",
    "design_style",
    "drive_type",
    "seat_layout",
    "autonomous_driving_level",
    "size",
    "family_friendliness",
    "comfort_level",
    "smartness",
    "energy_consumption_level",
]


def _build_text_from_toml(data: dict) -> str:
    """
    Build a natural language description from TOML data.
    Combines key_details and all *_comments fields into readable text.
    """
    parts: list[str] = []

    car_model = data.get("car_model", "Unknown Vehicle")
    parts.append(f"Vehicle: {car_model}")

    # Key details (most important text)
    key_details_section = data.get("KeyDetails", {})
    key_details = key_details_section.get("key_details", "")
    if key_details:
        parts.append(f"Overview: {key_details}")

    key_details_comments = key_details_section.get("key_details_comments", "")
    if key_details_comments:
        parts.append(f"Details: {key_details_comments}")

    # Collect all comments from PreciseLabels and AmbiguousLabels
    for section_name in ["PriciseLabels", "AmbiguousLabels"]:
        section = data.get(section_name, {})
        for key, value in section.items():
            if key.endswith("_comments") and value:
                field_name = key.replace("_comments", "").replace("_", " ").title()
                parts.append(f"{field_name}: {value}")

    return "\n".join(parts)


def _extract_metadata(data: dict) -> dict:
    """
    Extract structured metadata fields from TOML data for filtering.
    Only includes non-empty values from predefined METADATA_FIELDS.
    """
    metadata: dict = {}

    # Always include car_model
    car_model = data.get("car_model", "")
    if car_model:
        metadata["car_model"] = car_model

    # Extract from PreciseLabels and AmbiguousLabels
    for section_name in ["PriciseLabels", "AmbiguousLabels"]:
        section = data.get(section_name, {})
        for field in METADATA_FIELDS:
            if field in section and section[field]:
                metadata[field] = section[field]

    return metadata


def parse_vehicle_toml(file_path: Path) -> Optional[Document]:
    """
    Parse a single vehicle TOML file into a LlamaIndex Document.

    Args:
        file_path: Path to the .toml file.

    Returns:
        Document with text content and structured metadata,
        or None if parsing fails.
    """
    try:
        data = toml.load(str(file_path))
    except Exception as e:
        logger.warning(f"Failed to parse TOML file {file_path}: {e}")
        return None

    car_model = data.get("car_model", "")
    if not car_model:
        logger.warning(f"No car_model in {file_path}, skipping.")
        return None

    text = _build_text_from_toml(data)
    metadata = _extract_metadata(data)
    metadata["source_file"] = str(file_path.name)

    return Document(
        text=text,
        metadata=metadata,
        excluded_llm_metadata_keys=["source_file"],
        excluded_embed_metadata_keys=["source_file"],
    )


def parse_all_vehicles(data_dir: str) -> List[Document]:
    """
    Parse all vehicle TOML files under the given directory tree.

    Walks all brand subdirectories, skips non-TOML files and
    utility files like model_list.py, CarLabels.toml, etc.

    Args:
        data_dir: Root directory containing brand folders with TOML files.

    Returns:
        List of Document objects, one per vehicle model.
    """
    data_path = Path(data_dir)
    if not data_path.exists():
        logger.error(f"Vehicle data directory not found: {data_dir}")
        return []

    documents: List[Document] = []
    skip_files = {"CarLabels.toml"}

    for toml_file in sorted(data_path.rglob("*.toml")):
        if toml_file.name in skip_files:
            continue

        doc = parse_vehicle_toml(toml_file)
        if doc is not None:
            documents.append(doc)

    logger.info(f"Parsed {len(documents)} vehicle documents from {data_dir}")
    return documents
