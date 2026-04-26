"""
Tests for scan_runner.load_job (TASK #29).

The original implementation used a bare `except Exception: pass` which
silently treated JSON corruption, IO errors, and even bugs as "no job
file". This made debugging the web → runner → scanner pipeline painful.

These tests verify the new behaviour: missing → None silent, corrupt /
unreadable → None plus a clear stderr message, valid → dict.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


# scan_runner imports argparse + sys + others at module-level. Importing
# here (not inside the test) catches a future import-time regression.
import importlib.util

REPO_ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "scan_runner", str(REPO_ROOT / "scan_runner.py")
)
scan_runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(scan_runner)


def test_missing_file_returns_none(tmp_path):
    out = scan_runner.load_job(tmp_path / "does-not-exist.json")
    assert out is None


def test_valid_file_returns_dict(tmp_path):
    p = tmp_path / "job.json"
    p.write_text(json.dumps({"id": "abc", "status": "running"}))
    out = scan_runner.load_job(p)
    assert out == {"id": "abc", "status": "running"}


def test_corrupt_json_returns_none_and_logs(tmp_path, capsys):
    p = tmp_path / "job.json"
    p.write_text("{not valid json")
    out = scan_runner.load_job(p)
    assert out is None
    err = capsys.readouterr().err
    assert "corrupt job file" in err, "stderr should explain why None was returned"


def test_non_dict_returns_none(tmp_path):
    """A valid JSON list/scalar at the top level is not a job — return None."""
    p = tmp_path / "job.json"
    p.write_text(json.dumps([1, 2, 3]))
    assert scan_runner.load_job(p) is None
