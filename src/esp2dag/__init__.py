"""ESP to Airflow DAG Factory Builder — compiler package."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("esp2dag")
except PackageNotFoundError:  # pragma: no cover - editable / source tree
    __version__ = "0.1.0"

__all__ = ["__version__"]
