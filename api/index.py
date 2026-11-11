"""Vercel entry point for the OmaLocker viewer (Python runtime).

Vercel calls the `handler` class (a BaseHTTPRequestHandler) for every request;
vercel.json sends every path here. The app itself is viewer/omalocker-viewer.
Settings and data live in Turso: set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN
in the Vercel project, and run `omalocker-viewer --db <url> init` once.
"""
import importlib.machinery
import importlib.util
from pathlib import Path

_path = Path(__file__).resolve().parent.parent / "viewer" / "omalocker-viewer"
_loader = importlib.machinery.SourceFileLoader("omalocker_viewer", str(_path))
_viewer = importlib.util.module_from_spec(importlib.util.spec_from_loader("omalocker_viewer", _loader))
_loader.exec_module(_viewer)

handler = _viewer.vercel_handler()
