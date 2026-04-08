#!/usr/bin/env python3
"""
Test RAG + LLM integration
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_rag_llm_integration():
    """Test RAG + LLM integration"""
    from src.llm import LLMFactory
    from src.rag.retriever import VehicleRetriever
    from src.rag.embeddings import BGEEmbeddingModel
    from src.rag.vector_store import ChromaVectorStore
    from src.utils.config import config

    print("Testing RAG + LLM Integration")
    print("=" * 50)

    # Initialize LLM
    print("1. Initializing LLM...")
    llm = LLMFactory.create_llm(use_mock=True)  # Use mock for now
    print(f"LLM: {llm.get_config()}")

    # Initialize RAG components
    print("\n2. Initializing RAG components...")
    try:
        embedding_model = BGEEmbeddingModel(
            model_name=config.embedding_model, device=config.embedding_device
        )

        vector_store = ChromaVectorStore(
            persist_directory=config.chroma_persist_dir,
            collection_name=config.chroma_collection_name,
        )

        retriever = VehicleRetriever(
            embedding_model=embedding_model,
            vector_store=vector_store,
            similarity_threshold=0.1,  # Lower threshold for testing
        )

        print("RAG components initialized successfully!")

    except Exception as e:
        print(f"RAG initialization error: {e}")
        return

    # Test RAG search
    print("\n3. Testing RAG search...")
    try:
        from src.models.query import Query

        query_text = "SUV"
        query = Query(text=query_text)

        search_response = retriever.search(query)
        search_results = search_response.results

        print(f"Found {len(search_results)} vehicles")
        for i, result in enumerate(search_results[:3], 1):
            brand = result.vehicle.precise_labels.brand or "Unknown"
            model = result.vehicle.car_model or "Unknown"
            price = result.vehicle.precise_labels.prize or "Unknown"
            print(f"{i}. {brand}-{model}")
            print(f"   Score: {result.score.overall_score:.3f}")
            print(f"   Price: {price}")

    except Exception as e:
        print(f"RAG search error: {e}")
        return

    # Test LLM response generation
    print("\n4. Testing LLM response generation...")
    try:
        if search_results:
            # Create a simple prompt with search results
            vehicle_info = "\n".join(
                [
                    f"- {result.vehicle.precise_labels.brand or 'Unknown'}-{result.vehicle.car_model or 'Unknown'} ({result.vehicle.precise_labels.prize or 'Unknown'})"
                    for result in search_results
                ]
            )

            prompt = f"""User is looking for: {query}
            
Found vehicles:
{vehicle_info}

Please provide a helpful response recommending the best option."""

            response = llm.complete(prompt)
            print(f"LLM Response: {response}")

    except Exception as e:
        print(f"LLM response error: {e}")

    print("\nRAG + LLM Integration Test Completed!")


if __name__ == "__main__":
    test_rag_llm_integration()
