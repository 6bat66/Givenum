"""
Tests for the GitDumper failure-mode classification (TASK #54).

Background: previous GitDumper logged every requests exception as
"Git dump failed" — including SSL hostname mismatches and unreachable
hosts that aren't actionable. Tesla/Paypal scans produced ~50 useless
warnings each.

The new behaviour distinguishes:
  * SSLError       → silent count (target's cert is broken, not our bug)
  * ConnectionError → silent count (network/IPv4 issue handled in TASK #22)
  * other Exception → log up to 5, count the rest

These tests stub requests.get with each exception class and verify the
dumper returns gracefully and prints the one-line summary at the end.
"""
from __future__ import annotations

from unittest.mock import patch
import requests

import pytest

from GivEnum import GitDumper, OutputManager


@pytest.fixture
def dumper(tmp_path):
    om = OutputManager(str(tmp_path), "example.com")
    return GitDumper(om)


def _alive_file(tmp_path, urls):
    p = tmp_path / "alive.txt"
    p.write_text('\n'.join(urls) + '\n')
    return p


def test_ssl_error_does_not_raise(dumper, tmp_path, capsys):
    alive = _alive_file(tmp_path, [
        "https://broken-cert.example.com",
        "https://another-broken.example.com",
    ])
    with patch("GivEnum.requests.get", side_effect=requests.exceptions.SSLError("bad cert")):
        dumper.check_and_dump(alive)
    out = capsys.readouterr().out
    # Old behaviour: "Git dump failed for https://..." per host.
    # New behaviour: a single "git-check: skipped X (SSL mismatch)..." line.
    assert "Git dump failed" not in out, "old per-host warning storm leaked"
    assert "SSL mismatch" in out


def test_connection_error_does_not_raise(dumper, tmp_path, capsys):
    alive = _alive_file(tmp_path, ["https://unreachable.example.com"])
    with patch(
        "GivEnum.requests.get",
        side_effect=requests.exceptions.ConnectionError("network unreachable"),
    ):
        dumper.check_and_dump(alive)
    out = capsys.readouterr().out
    assert "unreachable" in out


def test_unexpected_exception_caps_log_at_5(dumper, tmp_path, capsys):
    """A flood of unexpected errors should produce at most 5 individual
    warnings — anything beyond that is summarised."""
    alive = _alive_file(tmp_path, [f"https://h{i}.example.com" for i in range(20)])
    with patch("GivEnum.requests.get", side_effect=RuntimeError("weird thing")):
        dumper.check_and_dump(alive)
    out = capsys.readouterr().out
    warnings = [l for l in out.splitlines() if "Git check unexpected error" in l]
    assert len(warnings) <= 5, (
        f"expected ≤5 warnings, got {len(warnings)} — log should be capped"
    )


def test_real_404_response_does_not_count_as_error(dumper, tmp_path, capsys):
    """A clean HTTP 404 means the host responded but had no /.git/config.
    That's the success path — no error, no exposed list, no skip count."""

    class Fake404:
        status_code = 404
        text = ''

    alive = _alive_file(tmp_path, ["https://no-git.example.com"])
    with patch("GivEnum.requests.get", return_value=Fake404()):
        dumper.check_and_dump(alive)
    out = capsys.readouterr().out
    # Must NOT print the failure-summary line at all when there were no errors.
    assert "git-check: skipped" not in out
    assert "No exposed .git repositories found" in out
