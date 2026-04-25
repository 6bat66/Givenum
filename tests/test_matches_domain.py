"""
Tests for GivEnum.matches_domain — the helper that decides whether a
hostname coming back from a recon tool belongs to the target domain.
A bug here means we either drop legit subdomains or include garbage
from unrelated zones.
"""
from __future__ import annotations

import pytest

from GivEnum import matches_domain


@pytest.mark.parametrize("hostname,domain,expected", [
    # Exact root match
    ("example.com", "example.com", True),
    # Subdomain
    ("api.example.com", "example.com", True),
    ("a.b.c.example.com", "example.com", True),
    # Different domain entirely
    ("example.org", "example.com", False),
    # Suffix collision — must NOT match (notexample.com endsWith example.com but isn't a sub)
    ("notexample.com", "example.com", False),
    ("evil-example.com", "example.com", False),
    # Wildcard input from CT logs etc.
    ("*.example.com", "example.com", True),
    ("*.api.example.com", "example.com", True),
    # Case insensitivity
    ("API.EXAMPLE.COM", "example.com", True),
    ("api.example.com", "EXAMPLE.COM", True),
    # Trailing dot (DNS canonical form)
    ("api.example.com.", "example.com", True),
    ("example.com.", "example.com.", True),
    # Whitespace tolerance
    ("  api.example.com  ", "example.com", True),
    # Empty-ish inputs
    ("", "example.com", False),
    ("*.", "example.com", False),
])
def test_matches_domain_table(hostname, domain, expected):
    assert matches_domain(hostname, domain) is expected


def test_matches_domain_does_not_match_parent_zone(tmp_path):
    # com endsWith example.com is False — but make sure parent zone match
    # is rejected too.
    assert matches_domain("com", "example.com") is False
    assert matches_domain("example", "example.com") is False
