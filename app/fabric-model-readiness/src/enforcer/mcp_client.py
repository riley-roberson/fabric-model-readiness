"""Minimal stdio JSON-RPC client for the Power BI Modeling MCP server.

Deliberately hand-rolled rather than taking the `mcp` SDK as a dependency: the
surface needed here is three methods, and this keeps the call path synchronous
and the timeouts ours.

The important thing this module encodes is the write protocol, established by
driving the real server (v0.4.0) against a copied model:

    ConnectFolder(<root>.SemanticModel)   -- loads TMDL into an offline model
    <tool>_operations.Update(...)          -- edits are IN MEMORY ONLY
    ExportToTmdlFolder(<root>/definition)  -- the only step that touches disk

Two traps, both found the hard way:

  * Nothing persists until the export. A run that "succeeded" on every Update
    and then skipped the export changes nothing at all.
  * The export path must be the *definition* subfolder. Passing the
    .SemanticModel root writes the TMDL tree at the root and leaves no
    definition/ behind, which destroys the PBIP layout.
"""

from __future__ import annotations

import json
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shared.config import MCP_SERVER_PATH

PROTOCOL_VERSION = "2024-11-05"
CLIENT_NAME = "fabric-model-readiness-enforcer"
DEFAULT_TIMEOUT = 180


class McpError(RuntimeError):
    """The server returned an error, or the transport failed."""


@dataclass
class McpResult:
    """Unwrapped payload from a tools/call response."""

    success: bool
    message: str
    data: Any = None
    raw: dict | None = None


class PowerBiMcpClient:
    """Speaks JSON-RPC over stdio to powerbi-modeling-mcp.exe."""

    def __init__(self, exe_path: str | Path | None = None, *, readwrite: bool = True):
        self.exe_path = Path(exe_path or MCP_SERVER_PATH)
        self._readwrite = readwrite
        self._proc: subprocess.Popen[str] | None = None
        self._next_id = 0
        self._stderr_tail: list[str] = []

    # -- lifecycle ---------------------------------------------------------

    def __enter__(self) -> PowerBiMcpClient:
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()

    def start(self) -> None:
        if not self.exe_path.exists():
            raise McpError(
                f"Power BI Modeling MCP server not found at {self.exe_path}. "
                "Download the extension and extract it under tools/ (see README)."
            )

        args = [str(self.exe_path)]
        if self._readwrite:
            args += ["--readwrite", "--skip-confirmation"]

        self._proc = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        threading.Thread(target=self._drain_stderr, daemon=True).start()

        self._request("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": CLIENT_NAME, "version": "0.1.0"},
        })
        self._notify("notifications/initialized")

    def stop(self) -> None:
        if self._proc is None:
            return
        try:
            self._proc.terminate()
            self._proc.wait(timeout=10)
        except Exception:
            self._proc.kill()
        finally:
            self._proc = None

    def _drain_stderr(self) -> None:
        """The server logs heavily to stderr; keep only a tail for diagnostics."""
        proc = self._proc
        if proc is None or proc.stderr is None:
            return
        for line in proc.stderr:
            self._stderr_tail.append(line.rstrip())
            if len(self._stderr_tail) > 40:
                self._stderr_tail.pop(0)

    # -- transport ---------------------------------------------------------

    def _write(self, payload: dict) -> None:
        if self._proc is None or self._proc.stdin is None:
            raise McpError("MCP client is not started")
        self._proc.stdin.write(json.dumps(payload) + "\n")
        self._proc.stdin.flush()

    def _notify(self, method: str, params: dict | None = None) -> None:
        self._write({"jsonrpc": "2.0", "method": method, "params": params or {}})

    def _request(self, method: str, params: dict | None = None) -> dict:
        if self._proc is None or self._proc.stdout is None:
            raise McpError("MCP client is not started")

        self._next_id += 1
        request_id = self._next_id
        self._write({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}})

        while True:
            line = self._proc.stdout.readline()
            if not line:
                tail = "\n".join(self._stderr_tail[-10:])
                raise McpError(f"MCP server closed the connection during {method}.\n{tail}")
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue  # server occasionally interleaves non-JSON on stdout
            if message.get("id") == request_id:
                return message

    def call(self, tool: str, request: dict) -> McpResult:
        """Invoke an MCP tool and unwrap its JSON text payload."""
        response = self._request("tools/call", {
            "name": tool,
            "arguments": {"request": request},
        })

        result = response.get("result", {})
        content = result.get("content", [])
        text = content[0].get("text", "{}") if content else "{}"

        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            payload = {"success": not result.get("isError", False), "message": text}

        return McpResult(
            success=bool(payload.get("success", not result.get("isError", False))),
            message=str(payload.get("message", "")),
            data=payload.get("data"),
            raw=payload,
        )

    # -- the operations the enforcer actually needs -------------------------

    def connect_folder(self, model_root: str | Path) -> McpResult:
        """Load a .SemanticModel folder into an offline in-memory model."""
        return self.call("connection_operations", {
            "operation": "ConnectFolder",
            "folderPath": str(Path(model_root).resolve()),
        })

    def export_to_folder(self, model_root: str | Path) -> McpResult:
        """Persist the in-memory model back to disk.

        Targets <root>/definition, never the root -- see the module docstring.
        """
        definition = Path(model_root).resolve() / "definition"
        return self.call("database_operations", {
            "operation": "ExportToTmdlFolder",
            "tmdlFolderPath": str(definition),
        })

    def update_tables(self, definitions: list[dict]) -> McpResult:
        return self.call("table_operations", {"operation": "Update", "definitions": definitions})

    def update_columns(self, definitions: list[dict]) -> McpResult:
        return self.call("column_operations", {"operation": "Update", "definitions": definitions})

    def update_measures(self, definitions: list[dict]) -> McpResult:
        return self.call("measure_operations", {"operation": "Update", "definitions": definitions})
