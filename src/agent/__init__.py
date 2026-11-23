"""
AutoVend Sales Agent — Pure AI conversation logic.

This package is fully decoupled from the backend (FastAPI, storage, ChromaDB).
It depends only on: LangGraph, LangChain, Pydantic schemas.

Entry points:
- `LangGraphSalesAgent` (`src.agent.langgraph_agent`)
- `SalesAgent` (`src.agent.sales_agent`)
"""
