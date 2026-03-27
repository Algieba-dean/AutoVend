"""
Build and manage ChromaDB vector index for vehicle knowledge base.

Uses bge-m3 (local HuggingFace) for embeddings and ChromaDB for persistent
vector storage with metadata filtering support.
"""

import logging
from pathlib import Path
from typing import List, Optional

import chromadb
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.schema import Document
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

from app.config import CHROMA_COLLECTION_NAME, CHROMA_PERSIST_DIR, EMBEDDING_MODEL
from app.ingestion.toml_parser import parse_all_vehicles

logger = logging.getLogger(__name__)


def get_embedding_model(model_name: Optional[str] = None) -> HuggingFaceEmbedding:
    """
    Initialize the HuggingFace embedding model.

    Args:
        model_name: HuggingFace model name. Defaults to config EMBEDDING_MODEL.

    Returns:
        HuggingFaceEmbedding instance.
    """
    model_name = model_name or EMBEDDING_MODEL
    logger.info(f"Loading embedding model: {model_name}")
    return HuggingFaceEmbedding(model_name=model_name)


def get_chroma_client(persist_dir: Optional[str] = None) -> chromadb.ClientAPI:
    """
    Get a persistent ChromaDB client.

    Args:
        persist_dir: Directory for ChromaDB persistence.
                     Defaults to config CHROMA_PERSIST_DIR.

    Returns:
        ChromaDB PersistentClient instance.
    """
    persist_dir = persist_dir or CHROMA_PERSIST_DIR
    Path(persist_dir).mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=persist_dir)


def get_chroma_vector_store(
    chroma_client: Optional[chromadb.ClientAPI] = None,
    collection_name: Optional[str] = None,
) -> ChromaVectorStore:
    """
    Get a ChromaVectorStore backed by the given client.

    Args:
        chroma_client: ChromaDB client. Creates a new one if None.
        collection_name: Collection name. Defaults to config.

    Returns:
        ChromaVectorStore instance.
    """
    if chroma_client is None:
        chroma_client = get_chroma_client()
    collection_name = collection_name or CHROMA_COLLECTION_NAME

    chroma_collection = chroma_client.get_or_create_collection(collection_name)
    return ChromaVectorStore(chroma_collection=chroma_collection)


def build_index(
    documents: List[Document],
    embed_model: Optional[HuggingFaceEmbedding] = None,
    vector_store: Optional[ChromaVectorStore] = None,
) -> VectorStoreIndex:
    """
    Build a VectorStoreIndex from documents.

    Args:
        documents: List of LlamaIndex Document objects.
        embed_model: Embedding model. Creates default if None.
        vector_store: ChromaVectorStore. Creates default if None.

    Returns:
        VectorStoreIndex with all documents indexed.
    """
    if embed_model is None:
        embed_model = get_embedding_model()
    if vector_store is None:
        vector_store = get_chroma_vector_store()

    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    logger.info(f"Building index from {len(documents)} documents...")
    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        embed_model=embed_model,
        show_progress=True,
    )
    logger.info("Index built successfully.")
    return index


def load_index(
    embed_model: Optional[HuggingFaceEmbedding] = None,
    vector_store: Optional[ChromaVectorStore] = None,
) -> VectorStoreIndex:
    """
    Load an existing VectorStoreIndex from persistent ChromaDB.

    Args:
        embed_model: Embedding model. Creates default if None.
        vector_store: ChromaVectorStore. Creates default if None.

    Returns:
        VectorStoreIndex loaded from the persistent store.
    """
    if embed_model is None:
        embed_model = get_embedding_model()
    if vector_store is None:
        vector_store = get_chroma_vector_store()

    return VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        embed_model=embed_model,
    )


def build_vehicle_index(
    vehicle_data_dir: Optional[str] = None,
    persist_dir: Optional[str] = None,
    collection_name: Optional[str] = None,
    embedding_model_name: Optional[str] = None,
) -> VectorStoreIndex:
    """
    End-to-end: parse TOML files and build a persistent ChromaDB index.

    This is the main entry point for index construction.

    Args:
        vehicle_data_dir: Path to vehicle TOML data directory.
        persist_dir: ChromaDB persistence directory.
        collection_name: ChromaDB collection name.
        embedding_model_name: HuggingFace embedding model name.

    Returns:
        VectorStoreIndex with all vehicle documents indexed.

    Raises:
        ValueError: If no documents were parsed from the data directory.
    """
    from app.config import VEHICLE_DATA_DIR

    vehicle_data_dir = vehicle_data_dir or VEHICLE_DATA_DIR

    # Parse TOML files
    documents = parse_all_vehicles(vehicle_data_dir)
    if not documents:
        raise ValueError(
            f"No vehicle documents parsed from {vehicle_data_dir}. "
            "Check that the directory exists and contains valid TOML files."
        )

    # Set up components
    embed_model = get_embedding_model(embedding_model_name)
    chroma_client = get_chroma_client(persist_dir)
    vector_store = get_chroma_vector_store(chroma_client, collection_name)

    # Build and return index
    return build_index(documents, embed_model, vector_store)
