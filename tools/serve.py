"""Local instructor preview, loading private project environment values."""
import os
from pathlib import Path
import sys
from run_tidb_mcp import load_env

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
path = ROOT / ".env.vercel"
if not path.exists():
    path = ROOT / ".env"
os.environ.update(load_env(path))
from app.web import app
app.run(host="127.0.0.1", port=8080, debug=False)
