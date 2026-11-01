"""Compatibility launcher for the Flask application in backend-app/."""

import importlib.util
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = PROJECT_ROOT / "backend-app"
sys.path.insert(0, str(BACKEND_ROOT))

backend_run_path = BACKEND_ROOT / "run.py"
spec = importlib.util.spec_from_file_location("_school_backend_run", backend_run_path)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load backend entrypoint: {backend_run_path}")
backend_run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend_run)
app = backend_run.app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
