"""
AutoVend Sales Agent — Pure AI conversation logic.

This package is fully decoupled from the backend (FastAPI, storage, ChromaDB).
It depends only on: LLM interface, Pydantic schemas, LlamaIndex memory.

Entry point: SalesAgent.process(AgentInput) -> AgentResult
"""
