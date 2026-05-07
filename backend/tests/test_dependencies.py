"""Verifies pyproject.toml declares the AstaLink Phase 0 dependencies.

This is a structural test — it parses pyproject.toml, not the lockfile, so it
catches missing/obsolete declarations even before `uv sync` is run.
"""
from pathlib import Path
import tomllib


def test_pyproject_declares_phase0_dependencies() -> None:
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text())
    deps = data["project"]["dependencies"]
    deps_str = " ".join(deps).lower()

    # LLM swap
    assert "langchain-google-genai" in deps_str, "must use Gemini, not OpenAI"
    assert "langchain-openai" not in deps_str, "OpenAI dep must be removed"

    # RAG stack
    assert "pinecone" in deps_str
    assert "rank-bm25" in deps_str
    assert "langchain-pinecone" in deps_str

    # Quantitative libs
    for lib in ("scipy", "numpy", "cvxpy", "yfinance", "pandas"):
        assert lib in deps_str, f"missing {lib}"

    # Observability + quality
    assert "prometheus-fastapi-instrumentator" in deps_str
    assert "deepeval" in deps_str

    # PDF ingestion (used by Phase 1 but added here so deps are stable)
    assert "pypdf" in deps_str
