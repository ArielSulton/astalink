"""Verifies Dockerfiles install the TA-Lib C library.

Without it, `pip install ta-lib` fails inside the container, breaking Phase 3.
"""
from pathlib import Path


def test_dockerfile_dev_installs_ta_lib() -> None:
    df = (Path(__file__).parent.parent / "Dockerfile.dev").read_text()
    assert "ta-lib" in df.lower(), "Dockerfile.dev must install TA-Lib"
    # Must run pip install ta-lib (the Python wrapper) after the C lib is built
    assert "pip install ta-lib" in df.lower() or "uv pip install ta-lib" in df.lower(), \
        "Dockerfile.dev must install the ta-lib Python wrapper"


def test_dockerfile_prod_installs_ta_lib() -> None:
    df = (Path(__file__).parent.parent / "Dockerfile.prod").read_text()
    assert "ta-lib" in df.lower(), "Dockerfile.prod must install TA-Lib"
    assert "pip install ta-lib" in df.lower() or "uv pip install ta-lib" in df.lower(), \
        "Dockerfile.prod must install the ta-lib Python wrapper"
