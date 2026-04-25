"""
Tests for GivEnum.OutputManager — the class that owns the per-scan
filesystem layout. Covers the security hardening added in the audit:

  * domain regex rejects unsafe characters
  * resolved base_dir must stay inside the user-supplied output root
  * get_path() rejects filenames that escape the category dir
  * the standard category subdirs are created on init
"""
from __future__ import annotations

import pytest

from GivEnum import OutputManager


# ── Happy path ────────────────────────────────────────────────────────────────

def test_creates_all_category_dirs(tmp_path):
    om = OutputManager(str(tmp_path), "example.com")

    # Sanity: base dir exists and is named "<domain>_<timestamp>"
    assert om.base_dir.is_dir()
    assert om.base_dir.name.startswith("example.com_")

    # Every advertised category should resolve to an existing directory.
    expected = {
        "subdomains", "dns", "http", "ports", "urls", "js",
        "screenshots", "vulnerabilities", "parameters", "git",
        "cloud", "takeover", "api_data", "diff", "reports",
        "logs", "fuzzing",
    }
    for cat in expected:
        assert cat in om.dirs, f"missing category {cat}"
        assert om.dirs[cat].is_dir(), f"category dir not created: {cat}"


def test_get_path_returns_path_inside_category(tmp_path):
    om = OutputManager(str(tmp_path), "example.com")
    p = om.get_path("subdomains", "all_subdomains.txt")
    assert p.parent == om.dirs["subdomains"].resolve()
    assert p.name == "all_subdomains.txt"


def test_wildcard_subdomain_is_accepted(tmp_path):
    # Recon output sometimes carries the leading "*." for wildcards — the
    # validator must allow that or the user can never scan a wildcard root.
    om = OutputManager(str(tmp_path), "*.example.com")
    assert om.base_dir.name.startswith("*.example.com_")


# ── Domain validation: must reject path-traversal payloads ────────────────────

@pytest.mark.parametrize("bad_domain", [
    "../etc/passwd",
    "../../root",
    "..",
    "/absolute/path",
    "example.com/../../etc",
    "example.com\x00.evil",        # NUL byte
    "example.com;rm -rf /",        # shell metachars
    "example com",                 # whitespace
    "exa$mple.com",                # $
    "exa`mple`.com",               # backticks
    "",                            # empty
    "a" * 300,                     # absurdly long
])
def test_rejects_unsafe_domains(tmp_path, bad_domain):
    with pytest.raises(ValueError):
        OutputManager(str(tmp_path), bad_domain)


# ── get_path filename safety ──────────────────────────────────────────────────

@pytest.mark.parametrize("bad_filename", [
    "../escape.txt",
    "../../etc/passwd",
    "subdir/../../escape.txt",
    "/abs/path.txt",
])
def test_get_path_rejects_traversal(tmp_path, bad_filename):
    om = OutputManager(str(tmp_path), "example.com")
    with pytest.raises(ValueError):
        om.get_path("subdomains", bad_filename)


def test_get_path_allows_subdirectory_filenames(tmp_path):
    # filenames *inside* the category dir are fine even with a forward slash
    om = OutputManager(str(tmp_path), "example.com")
    p = om.get_path("urls", "subset/clean.txt")
    # parent dir doesn't have to exist yet — get_path is path-only
    assert om.dirs["urls"].resolve() in p.resolve().parents


# ── Resolved path must stay under base_dir even with absolute base ────────────

def test_base_dir_is_resolved_and_contained(tmp_path):
    # If base_dir is a relative path with ".." the constructor still ends
    # up with an absolute, normalized path.
    rel_base = tmp_path / "results" / ".."  / "results"
    rel_base.mkdir(parents=True, exist_ok=True)
    om = OutputManager(str(rel_base), "example.com")
    assert om.base_dir.is_absolute()
    # The base_dir must be inside the resolved base — the constructor
    # already enforces this via Path.relative_to().
    assert (tmp_path / "results").resolve() in om.base_dir.resolve().parents
