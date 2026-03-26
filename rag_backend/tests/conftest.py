"""
Shared test fixtures for AutoVend RAG Backend tests.
"""

import os

# Set test environment before importing app modules
os.environ["APP_ENVIRONMENT"] = "testing"
os.environ["DEBUG"] = "False"
