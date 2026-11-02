"""Build a JSON from a research group's public GrupLAC page (Minciencias, Colombia)"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("gruplac-json")
except PackageNotFoundError:  # running from a source tree that was never installed
    __version__ = "0.0.0"

__all__ = ["__version__"]
