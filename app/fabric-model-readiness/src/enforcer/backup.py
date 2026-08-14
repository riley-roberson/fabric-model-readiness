"""Snapshot and restore a .SemanticModel folder around an enforcement run.

Not optional. Two independent reasons:

  * The MCP export rewrites the whole TMDL tree, so a single wrong argument can
    restructure the folder rather than edit a property. Pointing the export at
    the .SemanticModel root instead of its definition/ subfolder does exactly
    that, and leaves no definition/ behind.
  * Microsoft's own guidance for this server is blunt about it: "Always create a
    backup of your model before performing any operations."
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from shared.config import BACKUP_DIR

# Transient Power BI Desktop state -- large, regenerated, and not worth copying.
EXCLUDE = shutil.ignore_patterns("cache.abf", "*.tmp", "~$*")


@dataclass
class Backup:
    model_root: Path
    backup_path: Path
    created_at: datetime

    @property
    def label(self) -> str:
        return self.backup_path.name


def create_backup(model_root: str | Path, *, tag: str = "") -> Backup:
    """Copy the model folder into .backups/ and return a handle to it."""
    source = Path(model_root).resolve()
    if not source.is_dir():
        raise FileNotFoundError(f"Not a model folder: {source}")

    created_at = datetime.now(timezone.utc)
    stamp = created_at.strftime("%Y%m%dT%H%M%SZ")
    suffix = f"__{tag}" if tag else ""
    destination = BACKUP_DIR / f"{source.name}__{stamp}{suffix}"

    # Unique-ify rather than clobber: a second run in the same second must not
    # overwrite the only copy of the pre-change state.
    counter = 1
    while destination.exists():
        destination = BACKUP_DIR / f"{source.name}__{stamp}{suffix}__{counter}"
        counter += 1

    shutil.copytree(source, destination, ignore=EXCLUDE)
    return Backup(model_root=source, backup_path=destination, created_at=created_at)


def restore_backup(backup: Backup) -> None:
    """Put the model folder back exactly as the backup found it.

    The live folder is moved aside before the restore rather than deleted, so a
    failure part-way through does not leave the user with neither version.
    """
    target = backup.model_root
    if not backup.backup_path.is_dir():
        raise FileNotFoundError(f"Backup is missing: {backup.backup_path}")

    quarantine = target.with_name(target.name + ".failed-restore")
    if quarantine.exists():
        shutil.rmtree(quarantine)

    if target.exists():
        target.rename(quarantine)

    try:
        shutil.copytree(backup.backup_path, target)
    except Exception:
        # Roll the roll-back back.
        if target.exists():
            shutil.rmtree(target)
        quarantine.rename(target)
        raise

    shutil.rmtree(quarantine, ignore_errors=True)


def list_backups(model_name: str | None = None) -> list[Path]:
    """Newest first. Optionally filtered to one model."""
    if not BACKUP_DIR.is_dir():
        return []
    entries = [p for p in BACKUP_DIR.iterdir() if p.is_dir()]
    if model_name:
        entries = [p for p in entries if p.name.startswith(f"{model_name}__")]
    return sorted(entries, key=lambda p: p.name, reverse=True)
