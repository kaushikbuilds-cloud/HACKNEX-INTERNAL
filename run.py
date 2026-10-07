"""One-command launcher: starts the backend and frontend together.

    python run.py

Loads .env (if present), starts the FastAPI backend in the background,
waits for it to come up, then runs the Streamlit frontend in the
foreground — closing the terminal or Ctrl+C stops both.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"
BACKEND_PORT = 8000


def load_env_file() -> None:
    if not ENV_FILE.exists():
        print("(no .env found — copy .env.example to .env to set OLLAMA_MODEL; using defaults)")
        return
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if key and key not in os.environ:  # real env vars win over .env
            os.environ[key] = value


def wait_for_backend(timeout: int = 60) -> bool:
    import urllib.error
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://localhost:{BACKEND_PORT}/health", timeout=2)
            return True
        except (urllib.error.URLError, ConnectionError, OSError):
            time.sleep(1)
    return False


def main() -> None:
    load_env_file()
    model = os.environ.get("OLLAMA_MODEL", "(backend default)")
    print(f"Starting AI Software Engineering Agent — model: {model}")

    print("Starting backend...")
    backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.app:app", "--port", str(BACKEND_PORT)],
        cwd=ROOT,
    )

    try:
        if not wait_for_backend():
            print("Backend did not become healthy in time — check the logs above.")
            return

        print(f"Backend is up at http://localhost:{BACKEND_PORT}")
        print("Starting frontend — this will open your browser...")
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", "frontend/app.py"],
            cwd=ROOT,
        )
    except KeyboardInterrupt:
        pass
    finally:
        print("Stopping backend...")
        backend.terminate()
        try:
            backend.wait(timeout=10)
        except subprocess.TimeoutExpired:
            backend.kill()


if __name__ == "__main__":
    main()
