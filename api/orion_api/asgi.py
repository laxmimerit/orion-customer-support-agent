"""ASGI entrypoint for the Vercel deployment (vercel.json, service "api").

Locally the API runs from the create_app factory (.claude/launch.json). On Vercel,
settings come from the project's environment variables, and the embedding model
is cached under /tmp, the only writable directory in a Vercel Function. fastembed's
cache is not enough: the Hugging Face client downloads the model file through its
own cache under HF_HOME, which otherwise sits in the read-only home directory.
"""
import os

os.environ.setdefault("FASTEMBED_CACHE_PATH", "/tmp/fastembed")
os.environ.setdefault("HF_HOME", "/tmp/huggingface")

from orion_api.main import create_app  # noqa: E402  (both caches are read at import)

app = create_app()
