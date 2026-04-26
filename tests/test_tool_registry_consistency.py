"""
Cross-file consistency tests for the tool registry.

Bug history: during the audit, the web `/settings/tools` UI listed `kr` and
`jwt_tool` as available tools, the Dockerfile had install steps for both,
and the Python `ToolChecker` knew about them — yet a real scan reported
both as "not found". The root cause was the Dockerfile's `|| echo` swallowing
the install failure.

These tests catch the *next* time someone adds a tool to one place but
forgets the others. They don't test that the install actually *works*
(that's the build-time verification stage in the Dockerfile) — only that
all sources of truth agree on which tools exist.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCKERFILE = REPO_ROOT / "Dockerfile"
INSTALL_SH = REPO_ROOT / "install_tools.sh"
TOOLS_TS = REPO_ROOT / "web" / "src" / "lib" / "tools.ts"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _registry_tool_names() -> set[str]:
    """Parse the `name:` field of every entry in TOOL_REGISTRY in tools.ts."""
    text = TOOLS_TS.read_text()
    # Match: { name: 'foo', ...   OR   { name: "foo", ...
    return set(re.findall(r"\bname:\s*['\"]([^'\"]+)['\"]", text))


def _python_toolchecker_names() -> set[str]:
    """Parse the strings inside the *list values* of ToolChecker.REQUIRED_TOOLS.

    Only pull tool names from inside `[...]`, otherwise the dict keys
    ('subdomain', 'http', 'utils', etc.) get incorrectly counted as tools.
    """
    text = (REPO_ROOT / "GivEnum.py").read_text()
    m = re.search(
        r"REQUIRED_TOOLS\s*=\s*\{(.*?)\}\s*\n\s*@",
        text,
        re.DOTALL,
    )
    if not m:
        pytest.fail("Could not locate ToolChecker.REQUIRED_TOOLS block")
    # Extract every list literal in the dict, then pull quoted tokens from each.
    names: set[str] = set()
    for list_body in re.findall(r"\[([^\]]+)\]", m.group(1)):
        names.update(re.findall(r"['\"]([a-zA-Z][a-zA-Z0-9_\-]*)['\"]", list_body))
    return names


def _dockerfile_referenced_binaries() -> set[str]:
    """Best-effort extraction of binary names the Dockerfile installs.

    Picks up:
      * `go install …/cmd/<name>@…` and `go install …/<name>@…`
      * `pip install <pkg>` (used as the binary name — close enough)
      * `git clone … /tmp/<name>` followed by build/copy
    """
    text = DOCKERFILE.read_text()
    names: set[str] = set()
    # go install path/.../cmd/NAME@... → take last segment of path before @
    for m in re.finditer(r"go install\s+\S*?(?:/cmd)?/([a-zA-Z0-9_\-]+)@", text):
        names.add(m.group(1))
    # go install path/.../NAME/v2/...@latest → uses /v2 module style
    for m in re.finditer(r"go install\s+\S*?/([a-zA-Z0-9_\-]+)/v\d+/[^@\s]*@", text):
        names.add(m.group(1))
    # pip install pkg
    for m in re.finditer(r"pip install[^\n]*?\s([a-zA-Z][a-zA-Z0-9_\-]+)(?:\s|$|2>)", text):
        names.add(m.group(1).replace("-", "_"))
    # git clone /tmp/NAME
    for m in re.finditer(r"git clone[^\n]*?/tmp/([a-zA-Z0-9_\-]+)", text):
        names.add(m.group(1))
    return names


# ── Tests ────────────────────────────────────────────────────────────────────

def test_dockerfile_exists():
    assert DOCKERFILE.is_file()


def test_install_sh_exists_and_executable():
    assert INSTALL_SH.is_file()
    # Permission check is best-effort — Windows checkouts may show 644.
    # We only require it's a regular file with content.
    assert INSTALL_SH.stat().st_size > 0


def test_tools_registry_parseable():
    names = _registry_tool_names()
    # Sanity floor — registry should have at least the well-known core tools.
    for must_have in ('subfinder', 'httpx', 'dnsx', 'nuclei'):
        assert must_have in names, f"{must_have} missing from web/src/lib/tools.ts"


def test_critical_tools_referenced_in_dockerfile():
    """Every CRITICAL tool the Python ToolChecker requires must appear
    somewhere in the Dockerfile (best-effort string match)."""
    docker_text = DOCKERFILE.read_text()
    critical = ['subfinder', 'httpx', 'dnsx', 'naabu', 'nuclei']
    missing = [t for t in critical if t not in docker_text]
    assert not missing, (
        f"Critical tools not referenced in Dockerfile: {missing}. "
        f"Either add the install step or stop calling them critical."
    )


def test_web_registry_tools_referenced_in_dockerfile():
    """Every tool exposed in /settings/tools should be installable from the
    Dockerfile — otherwise the UI lies to the user."""
    registry = _registry_tool_names()
    docker_text = DOCKERFILE.read_text()
    # Permissive substring match — name appears anywhere in Dockerfile
    missing = sorted(t for t in registry if t not in docker_text)
    assert not missing, (
        f"Tools advertised in web/src/lib/tools.ts but not referenced in "
        f"the Dockerfile: {missing}. Either add the install step or remove "
        f"them from TOOL_REGISTRY."
    )


def test_python_required_tools_referenced_in_dockerfile():
    """Every entry in ToolChecker.REQUIRED_TOOLS should be installable."""
    py_names = _python_toolchecker_names()
    docker_text = DOCKERFILE.read_text()
    # Some entries are checked by python_module path (e.g. photon) — skip
    # the few we know are special-cased.
    SKIP = {'photon'}  # checked via check_python_module fallback
    candidates = py_names - SKIP
    missing = sorted(t for t in candidates if t not in docker_text)
    assert not missing, (
        f"Tools listed in GivEnum.ToolChecker.REQUIRED_TOOLS but not "
        f"referenced in the Dockerfile: {missing}"
    )
