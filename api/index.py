"""Vercel entry point for the OmaLocker viewer (Python runtime).

Vercel looks for a top-level `class handler` (a BaseHTTPRequestHandler) in each
api/*.py file, so it is declared here rather than built elsewhere. vercel.json
sends every path to it. The app itself is viewer/omalocker-viewer. Settings and
data live in Turso: TURSO_DATABASE_URL and TURSO_AUTH_TOKEN in the Vercel
project; run `omalocker-viewer --db <url> init` once.
"""
import importlib.machinery
import importlib.util
from http.server import BaseHTTPRequestHandler  # noqa: F401  (what Vercel looks for)
from pathlib import Path

_path = Path(__file__).resolve().parent.parent / "viewer" / "omalocker-viewer"
_loader = importlib.machinery.SourceFileLoader("omalocker_viewer", str(_path))
_viewer = importlib.util.module_from_spec(importlib.util.spec_from_loader("omalocker_viewer", _loader))
_loader.exec_module(_viewer)


class handler(_viewer.Handler):
    viewer = _viewer.vercel_viewer()
