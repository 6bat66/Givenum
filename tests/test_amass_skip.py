"""
Tests for the amass skip-fast contract (TASK #25).

amass without API keys duplicates the free sources subfinder/assetfinder/
crt.sh already cover, but runs for 10+ minutes. The `run_amass` method
must short-circuit when no applicable datasource key is configured.

These tests use the real APIConfig + SubdomainEnum classes but stub out:
  * the disk I/O for api_keys.json (via tmp_path + monkeypatch)
  * the subprocess.run call (so we never actually invoke amass)
  * ToolChecker.check_tool to pretend amass is installed
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from GivEnum import APIConfig, OutputManager, SubdomainEnum, ToolChecker


@pytest.fixture
def configured_paths(tmp_path, monkeypatch):
    """Redirect APIConfig to a temp config dir so tests don't touch ~/.config."""
    fake_home = tmp_path / "fakehome"
    (fake_home / ".config" / "givenum").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.delenv("GIVENUM_CONFIG_DIR", raising=False)
    return fake_home


@pytest.fixture
def output_mgr(tmp_path):
    return OutputManager(str(tmp_path / "results"), "example.com")


def _make_enum(output_mgr, api_config) -> SubdomainEnum:
    return SubdomainEnum("example.com", output_mgr, api_config)


# ── Skip path: no keys → no subprocess call ──────────────────────────────────

def test_amass_skipped_when_no_api_keys(configured_paths, output_mgr):
    """With zero API keys, run_amass must NOT invoke subprocess and must
    record the skip in _tool_log."""
    api_config = APIConfig()  # empty config — no keys
    assert api_config.keys == {}, "APIConfig should start empty in the temp HOME"

    enum = _make_enum(output_mgr, api_config)

    # Pretend amass binary exists so the early `check_tool` doesn't short-circuit.
    with patch.object(ToolChecker, "check_tool", return_value=True), \
         patch("GivEnum.subprocess.run") as mock_run:
        result = enum.run_amass()

    assert result == set()
    assert not mock_run.called, "amass subprocess must NOT run when no keys configured"

    from GivEnum import _tool_log
    assert _tool_log["amass"]["status"] == "skipped"
    assert "API key" in _tool_log["amass"]["msg"]


def test_amass_skipped_when_only_irrelevant_keys(configured_paths, output_mgr):
    """Discord webhook is configured, but amass doesn't use it — still skip."""
    api_config = APIConfig()
    api_config.save_key("discord_webhook", "https://discord.com/api/webhooks/x/y")

    enum = _make_enum(output_mgr, api_config)

    with patch.object(ToolChecker, "check_tool", return_value=True), \
         patch("GivEnum.subprocess.run") as mock_run:
        enum.run_amass()

    assert not mock_run.called


# ── Run path: ≥1 key → amass should be invoked ──────────────────────────────

def test_amass_runs_when_at_least_one_key_configured(configured_paths, output_mgr):
    """A single applicable key (Shodan) must un-skip amass."""
    api_config = APIConfig()
    api_config.save_key("shodan", "test-shodan-key-DO-NOT-USE")

    enum = _make_enum(output_mgr, api_config)

    # Stub the subprocess to return a fake "no subdomains found" result so
    # the rest of run_amass() runs without actually invoking the binary.
    class FakeProc:
        returncode = 0
        stdout = ""
        stderr = ""

    with patch.object(ToolChecker, "check_tool", return_value=True), \
         patch("GivEnum.subprocess.run", return_value=FakeProc()) as mock_run:
        enum.run_amass()

    assert mock_run.called, "amass must run when at least one API key is configured"
    # Verify the command actually included -config (proves the generated
    # datasources.yaml reached the CLI invocation).
    invoked_cmd = mock_run.call_args[0][0]
    assert "-config" in invoked_cmd
    cfg_idx = invoked_cmd.index("-config")
    assert invoked_cmd[cfg_idx + 1].endswith("config.yaml")


# ── Skip path when amass binary is missing entirely ──────────────────────────

def test_amass_not_found_status_when_binary_missing(configured_paths, output_mgr):
    api_config = APIConfig()
    api_config.save_key("shodan", "k")
    enum = _make_enum(output_mgr, api_config)

    with patch.object(ToolChecker, "check_tool", return_value=False), \
         patch("GivEnum.subprocess.run") as mock_run:
        result = enum.run_amass()

    assert result == set()
    assert not mock_run.called

    from GivEnum import _tool_log
    assert _tool_log["amass"]["status"] == "not_found"
