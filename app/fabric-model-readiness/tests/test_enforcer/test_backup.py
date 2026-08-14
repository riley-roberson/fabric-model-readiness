"""Backup and restore around an enforcement run."""

from __future__ import annotations

import shutil

import pytest

from enforcer import backup as backup_mod
from enforcer.backup import create_backup, list_backups, restore_backup


@pytest.fixture(autouse=True)
def isolated_backup_dir(tmp_path, monkeypatch):
    """Keep tests out of the real .backups/ directory."""
    target = tmp_path / "backups"
    target.mkdir()
    monkeypatch.setattr(backup_mod, "BACKUP_DIR", target)
    return target


@pytest.fixture
def model_folder(tmp_path):
    root = tmp_path / "Demo.SemanticModel"
    (root / "definition" / "tables").mkdir(parents=True)
    (root / "definition" / "tables" / "Customer.tmdl").write_text(
        "table Customer\n\tlineageTag: abc\n", encoding="utf-8"
    )
    (root / "definition" / "model.tmdl").write_text("model Model\n", encoding="utf-8")
    return root


def test_backup_copies_the_tree(model_folder):
    bk = create_backup(model_folder)
    assert (bk.backup_path / "definition" / "tables" / "Customer.tmdl").exists()
    assert (bk.backup_path / "definition" / "model.tmdl").exists()


def test_backup_skips_transient_desktop_state(model_folder):
    pbi = model_folder / ".pbi"
    pbi.mkdir()
    (pbi / "cache.abf").write_bytes(b"x" * 32)
    bk = create_backup(model_folder)
    assert not (bk.backup_path / ".pbi" / "cache.abf").exists()


def test_restore_undoes_edits(model_folder):
    original = (model_folder / "definition" / "tables" / "Customer.tmdl").read_text(encoding="utf-8")
    bk = create_backup(model_folder)

    (model_folder / "definition" / "tables" / "Customer.tmdl").write_text("wrecked", encoding="utf-8")
    restore_backup(bk)

    assert (model_folder / "definition" / "tables" / "Customer.tmdl").read_text(encoding="utf-8") == original


def test_restore_removes_files_added_after_the_backup(model_folder):
    bk = create_backup(model_folder)
    stray = model_folder / "definition" / "tables" / "Stray.tmdl"
    stray.write_text("table Stray\n", encoding="utf-8")

    restore_backup(bk)
    assert not stray.exists()


def test_restore_leaves_no_quarantine_behind(model_folder):
    bk = create_backup(model_folder)
    restore_backup(bk)
    assert not model_folder.with_name(model_folder.name + ".failed-restore").exists()


def test_two_backups_in_the_same_second_do_not_collide(model_folder):
    first = create_backup(model_folder, tag="run")
    second = create_backup(model_folder, tag="run")
    assert first.backup_path != second.backup_path
    assert first.backup_path.exists() and second.backup_path.exists()


def test_list_backups_is_newest_first(model_folder):
    create_backup(model_folder, tag="a")
    create_backup(model_folder, tag="b")
    entries = list_backups("Demo.SemanticModel")
    assert len(entries) == 2
    assert entries == sorted(entries, key=lambda p: p.name, reverse=True)


def test_backup_rejects_a_missing_folder(tmp_path):
    with pytest.raises(FileNotFoundError):
        create_backup(tmp_path / "nope.SemanticModel")


def test_restore_rejects_a_missing_backup(model_folder):
    bk = create_backup(model_folder)
    shutil.rmtree(bk.backup_path)
    with pytest.raises(FileNotFoundError):
        restore_backup(bk)
