"""gruplac-json: turn a public GrupLAC page (Minciencias, Colombia) into one JSON document.

>>> from gruplac_json import extract
>>> data = extract("COL0008423")            # downloads the page; Scienti ids if an apis.colav.co key is set
>>> data["name"], len(data["members"]), len(data["works"])
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("gruplac-json")
except PackageNotFoundError:  # running from a source tree that was never installed
    __version__ = "0.0.0"

from .parser import build, extract, fetch, resolve

__all__ = ["__version__", "build", "extract", "fetch", "resolve"]
