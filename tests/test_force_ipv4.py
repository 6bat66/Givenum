"""
Regression test for TASK #22 — Network unreachable bug.

The Docker container's bridge network has no usable IPv6 route. When
Python `requests` honored AAAA records returned by the system resolver,
4 scans in a row showed:
  * crt.sh failing mid-scan with Network unreachable
  * VirusTotal / AlienVault Connection refused
  * 0/50 JS files downloaded
  * ~50 git-dumper hosts unreachable

Disabling IPv6 at the urllib3 layer (HAS_IPV6 = False) makes urllib3
skip AAAA addresses entirely. This test makes sure that flag is in fact
flipped to False at GivEnum import time — if a future refactor removes
the patch, the test fails before the next scan does.
"""
from __future__ import annotations

import urllib3.util.connection as _urllib3_conn

# Importing GivEnum runs the module-level patch.
import GivEnum  # noqa: F401  (import is the side-effect under test)


def test_ipv6_disabled_after_givenum_import():
    """GivEnum's top-level setup must flip urllib3's HAS_IPV6 to False so
    that all Python HTTP calls prefer A records and skip AAAA."""
    assert _urllib3_conn.HAS_IPV6 is False, (
        "urllib3.util.connection.HAS_IPV6 should be False after importing "
        "GivEnum — the IPv6 fallback is what caused the Network unreachable "
        "errors in 4 scans in a row (TASK #22)."
    )
