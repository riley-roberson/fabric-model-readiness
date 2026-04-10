"""Serializes scan results to JSON and writes to the findings directory."""

from __future__ import annotations

import json
from pathlib import Path

from shared.config import FINDINGS_DIR
from shared.model import ScanReport


def sanitize_model_name(model_path: str) -> str:
    """Convert a model path to a safe directory name for findings storage."""
    model_name = Path(model_path).stem or Path(model_path).name
    return model_name.replace(" ", "_").replace("+", "").strip("._") or "model"


def save_report(report: ScanReport) -> Path:
    """Write the scan report to findings/[model-name]/[scan-id].json and update latest.json."""
    safe_name = sanitize_model_name(report.model_path)
    model_dir = FINDINGS_DIR / safe_name
    model_dir.mkdir(parents=True, exist_ok=True)

    report_path = model_dir / f"{report.scan_id}.json"
    data = report.model_dump(mode="json")
    report_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    # Write latest.json as a copy (symlinks are unreliable on Windows)
    latest_path = model_dir / "latest.json"
    latest_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    return report_path


def load_latest_report(model_name: str) -> ScanReport | None:
    """Load the most recent scan report for a model, if it exists."""
    for model_dir in FINDINGS_DIR.iterdir():
        if model_name.lower() in model_dir.name.lower():
            latest = model_dir / "latest.json"
            if latest.exists():
                data = json.loads(latest.read_text(encoding="utf-8"))
                return ScanReport(**data)
    return None
