#!/usr/bin/env python3
"""JobAutoApply — Entry Point.

Start the web server:

    python run.py              # Default: http://localhost:8000
    python run.py --port 9000  # Custom port
    python run.py --no-open    # Don't auto-open browser
"""

import argparse
import logging
import sys
import webbrowser
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/app.log", mode="a") if Path("logs").exists() else logging.NullHandler(),
    ],
)
logger = logging.getLogger("jobautoapply")


def main():
    parser = argparse.ArgumentParser(description="JobAutoApply — AI-Powered Job Application Automation")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")
    parser.add_argument("--no-open", action="store_true", help="Don't auto-open browser")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload (development)")
    args = parser.parse_args()

    # Ensure directories
    for d in ("data", "logs", "exports"):
        Path(d).mkdir(exist_ok=True)

    logger.info("🚀 JobAutoApply starting on http://%s:%s", args.host, args.port)

    if not args.no_open:
        webbrowser.open(f"http://localhost:{args.port}")

    import uvicorn
    from src.api.app import create_app

    app = create_app()
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
