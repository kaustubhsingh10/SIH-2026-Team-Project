"""CrimeGraph AI — REST API Server Runner.

Usage:
    python run_server.py [--port 8000] [--host 127.0.0.1] [--reload]
"""

import argparse
import sys
from pathlib import Path

# Ensure src/ is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Start the CrimeGraph AI REST API server.")
    parser.add_argument("--host", default="127.0.0.1", help="Host address to bind to (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload on file changes")
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print(" CrimeGraph AI — REST API Backend Server")
    print("=" * 70)
    print(f" • Server running at:       http://{args.host}:{args.port}")
    print(f" • Interactive API Docs:   http://{args.host}:{args.port}/docs")
    print(f" • Alternative ReDoc:      http://{args.host}:{args.port}/redoc")
    print("=" * 70 + "\n")

    uvicorn.run("crimegraph.api.app:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
