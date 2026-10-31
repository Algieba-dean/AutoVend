"""
Shared test fixtures for AutoVend RAG Backend tests.
"""

import os

# Set test environment before importing app modules
os.environ["APP_ENVIRONMENT"] = "testing"
os.environ["DEBUG"] = "False"
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
for _k in ("HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy"):
    os.environ.pop(_k, None)
