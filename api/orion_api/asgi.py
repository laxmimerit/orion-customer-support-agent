"""ASGI entrypoint for the Vercel deployment (vercel.json, service "api").

Locally the API runs from the create_app factory (.claude/launch.json). On Vercel,
settings come from the project's environment variables, and the embedding model
is cached under /tmp, the only writable directory in a Vercel Function.
"""
import os

os.environ.setdefault("FASTEMBED_CACHE_PATH", "/tmp/fastembed")

from orion_api.main import create_app  # noqa: E402  (reads FASTEMBED_CACHE_PATH at import)

app = create_app()
