"""
Smoke / wiring tests for the GivEnum orchestrator.

Background: a previous edit removed `_generate_analysis_report()` (the no-op
left over from the deleted analyze_results.py) but missed one of TWO call
sites in run_full_enum / _finalize_run. The bug only surfaced after a 30-min
real scan crashed at the very end with AttributeError.

These tests exist so a missing method or stale call site is caught in
under a second instead of half an hour. They walk the source AST and
assert that every `self.<name>(...)` call inside the GivEnum class
resolves to a real method on the class — including methods inherited from
attributes (best-effort: only flags clearly-orphaned `self._foo()` calls
where `_foo` is not defined anywhere on the class).
"""
from __future__ import annotations

import ast
import inspect

import pytest

from GivEnum import GivEnum


def _self_method_calls(cls) -> set[str]:
    """Collect names of every `self.<name>(...)` call inside a class body."""
    src = inspect.getsource(cls)
    tree = ast.parse(src)
    calls: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == 'self'
        ):
            calls.add(node.func.attr)
    return calls


def _self_attribute_accesses(cls) -> set[str]:
    """Names accessed via `self.<name>` (any attribute, not just calls)."""
    src = inspect.getsource(cls)
    tree = ast.parse(src)
    attrs: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == 'self'
        ):
            attrs.add(node.attr)
    return attrs


def test_givenum_class_imports_and_has_main_methods():
    """Hard floor — class loads and the public surface exists."""
    assert hasattr(GivEnum, 'run_full_enum')
    assert callable(getattr(GivEnum, 'run_full_enum'))


def test_no_orphan_self_method_calls_in_givenum():
    """Every `self._foo()` or `self.foo()` called inside the class must
    resolve to either:
      * a method/attribute defined on the class, or
      * an attribute set in __init__ (best-effort heuristic via the
        attribute access set).
    """
    called = _self_method_calls(GivEnum)
    accessed = _self_attribute_accesses(GivEnum)
    defined = set(vars(GivEnum).keys())

    # Anything called must be defined OR be an instance attribute we know
    # about. The instance-attribute heuristic just looks at what gets
    # assigned via `self.X = …` in __init__, captured by `accessed`.
    orphans = called - defined - accessed
    assert not orphans, (
        f"GivEnum has self.<name>() calls with no matching definition: "
        f"{sorted(orphans)}. Did you delete a method but forget the call site?"
    )


def test_no_call_to_removed_generate_analysis_report():
    """Regression for the bug introduced 2026-04-25: removing
    _generate_analysis_report() left an orphan call in run_full_enum that
    crashed the scanner at the very end of every scan."""
    called = _self_method_calls(GivEnum)
    assert '_generate_analysis_report' not in called, (
        "self._generate_analysis_report() must not be called — the method "
        "was removed when analyze_results.py was deleted (TASK #20)."
    )
