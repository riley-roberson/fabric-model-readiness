"""FastAPI server wrapping Scout, Enforcer, and Historian agents."""

from __future__ import annotations

import argparse
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure src/ is on the Python path so agent imports work
src_dir = str(Path(__file__).resolve().parent.parent)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from api.routes import enforcer, historian, scout
from shared.config import API_HOST, API_PORT


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Fabric Semantic Model AI Readiness",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scout.router)
app.include_router(enforcer.router)
app.include_router(historian.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--port", type=int, default=API_PORT)
    arg_parser.add_argument("--host", type=str, default=API_HOST)
    args = arg_parser.parse_args()

    port = args.port or API_PORT

    config = uvicorn.Config(app, host=args.host, port=port, log_level="info")
    server = uvicorn.Server(config)

    # If port is 0, uvicorn picks a random port. Print it so Electron can read it.
    if port == 0:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((args.host, 0))
        port = sock.getsockname()[1]
        sock.close()
        config = uvicorn.Config(app, host=args.host, port=port, log_level="info")
        server = uvicorn.Server(config)

    print(f"BACKEND_PORT={port}", flush=True)
    server.run()


if __name__ == "__main__":
    main()
