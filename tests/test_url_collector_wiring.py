"""
Wiring / smoke tests for URLCollector — catch the bug class where
`self.X` is read but the class never sets `X` in __init__.

The previous integration of urlfinder broke this contract: the new
collect_with_urlfinder method read `self.domain`, but URLCollector's
__init__ only accepted `output_mgr`. The first real scan crashed with
AttributeError after 30 minutes of work.

These tests:
  1. Verify URLCollector accepts a domain in its constructor.
  2. Walk the URLCollector class AST and assert every `self.<attr>`
     access has either an `__init__` assignment or a method definition.
"""
from __future__ import annotations

import ast
import inspect
import textwrap
from pathlib import Path

import pytest

from GivEnum import URLCollector, OutputManager


# ── Constructor wiring ───────────────────────────────────────────────────────

def test_url_collector_constructor_accepts_domain(tmp_path):
    om = OutputManager(str(tmp_path), "example.com")
    uc = URLCollector(om, "example.com")
    assert uc.domain == "example.com"


def test_url_collector_constructor_accepts_only_output_mgr_for_backwards_compat(tmp_path):
    """Old callers that didn't pass domain should still work — just with
    a clear skip from any collector that needs it."""
    om = OutputManager(str(tmp_path), "example.com")
    uc = URLCollector(om)
    assert uc.domain == ''


# ── AST scan: every `self.X` must be defined somewhere ──────────────────────

def _self_attr_accesses(cls) -> set[str]:
    """All names that appear as `self.<name>` in any method body."""
    src = inspect.getsource(cls)
    tree = ast.parse(src)
    accessed: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == 'self'
        ):
            accessed.add(node.attr)
    return accessed


def _self_assignments_in_init(cls) -> set[str]:
    """Names assigned via `self.X = ...` inside __init__."""
    init = cls.__init__
    # inspect.getsource on a method returns the indented snippet — dedent
    # before parsing so ast.parse doesn't choke on the leading whitespace.
    src = textwrap.dedent(inspect.getsource(init))
    tree = ast.parse(src)
    assigned: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == 'self'
                ):
                    assigned.add(target.attr)
    return assigned


def test_no_orphan_self_attribute_access_in_url_collector():
    accessed = _self_attr_accesses(URLCollector)
    assigned = _self_assignments_in_init(URLCollector)
    methods = set(vars(URLCollector).keys())

    # Allow access to anything that's either defined as a method/static
    # on the class OR set as an instance attribute in __init__.
    orphans = accessed - methods - assigned
    assert not orphans, (
        f"URLCollector has self.<name> accesses with no matching method or "
        f"__init__ assignment: {sorted(orphans)}. This was the urlfinder "
        f"crash bug — a method read self.domain but the class never set it."
    )
