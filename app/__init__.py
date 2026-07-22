from pathlib import Path

__all__ = ["__version__"]

_version_file = Path(__file__).resolve().parent.parent / "VERSION"
__version__ = _version_file.read_text().strip() if _version_file.exists() else "0.0.0"
