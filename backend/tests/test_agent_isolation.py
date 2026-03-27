"""
Import isolation test — verifies that agent/ has ZERO imports from app/.

This is a critical architectural invariant:
- agent/ depends only on: pydantic, llama_index.core, agent.schemas
- agent/ must NEVER import from app.routes, app.models, app.rag, app.config, etc.
"""

import ast
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parent.parent / "agent"
FORBIDDEN_PREFIXES = ("app.", "app/")


def _get_all_python_files(directory: Path):
    """Recursively find all .py files in a directory."""
    return list(directory.rglob("*.py"))


def _extract_imports(filepath: Path):
    """Extract all import module names from a Python file using AST."""
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(filepath))

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


class TestAgentImportIsolation:
    """Verify agent package has no backend imports."""

    def test_agent_dir_exists(self):
        assert AGENT_DIR.exists(), f"Agent directory not found: {AGENT_DIR}"

    def test_no_app_imports_in_agent(self):
        """Every .py file in agent/ must not import from app.*"""
        violations = []
        for py_file in _get_all_python_files(AGENT_DIR):
            rel_path = py_file.relative_to(AGENT_DIR)
            imports = _extract_imports(py_file)
            for imp in imports:
                if imp.startswith("app.") or imp == "app":
                    violations.append(f"  {rel_path}: imports '{imp}'")

        assert not violations, (
            f"Agent package has {len(violations)} forbidden backend imports:\n"
            + "\n".join(violations)
        )

    def test_agent_imports_only_allowed_packages(self):
        """Agent files should only import from: agent, pydantic, llama_index, stdlib, typing."""
        allowed_prefixes = (
            "agent",
            "pydantic",
            "llama_index",
            "typing",
            "enum",
            "json",
            "logging",
            "datetime",
            "collections",
            "abc",
            "os",
            "pathlib",
            "re",
        )
        violations = []
        for py_file in _get_all_python_files(AGENT_DIR):
            rel_path = py_file.relative_to(AGENT_DIR)
            imports = _extract_imports(py_file)
            for imp in imports:
                if not any(imp == p or imp.startswith(p + ".") for p in allowed_prefixes):
                    violations.append(f"  {rel_path}: imports '{imp}'")

        assert not violations, (
            f"Agent package has {len(violations)} unexpected external imports:\n"
            + "\n".join(violations)
        )
