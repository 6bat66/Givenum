"""
Concurrency test for GivEnum._tool_log.

The audit added a threading.Lock plus record_tool_log/snapshot_tool_log
helpers. These tests prove:

  1. Concurrent writes from many threads don't lose entries
  2. snapshot_tool_log() can be called while writes are in flight
     without raising "dictionary changed size during iteration"
"""
from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from GivEnum import (
    record_tool_log,
    reset_tool_log,
    snapshot_tool_log,
)


@pytest.fixture(autouse=True)
def _clean_log():
    reset_tool_log()
    yield
    reset_tool_log()


def test_concurrent_writes_keep_all_entries():
    N = 200
    def writer(i: int) -> None:
        record_tool_log(f"tool_{i}", {"status": "ok", "rc": 0, "elapsed": 0.1})

    with ThreadPoolExecutor(max_workers=32) as pool:
        list(pool.map(writer, range(N)))

    snap = snapshot_tool_log()
    assert len(snap) == N
    assert all(snap[f"tool_{i}"]["status"] == "ok" for i in range(N))


def test_snapshot_during_writes_does_not_raise():
    """Reader iterates while writers append — must not raise."""
    stop = threading.Event()
    errors: list[BaseException] = []

    def writer():
        i = 0
        while not stop.is_set():
            record_tool_log(f"w_{i % 50}", {"status": "ok", "rc": 0, "elapsed": 0.1})
            i += 1

    def reader():
        try:
            while not stop.is_set():
                snap = snapshot_tool_log()
                # iterate to trigger any partial-state issues
                for _name, entry in snap.items():
                    _ = entry.get("status")
        except BaseException as e:  # pragma: no cover — defensive
            errors.append(e)

    threads = [
        threading.Thread(target=writer, daemon=True) for _ in range(8)
    ] + [threading.Thread(target=reader, daemon=True) for _ in range(4)]

    for t in threads:
        t.start()
    time.sleep(0.5)  # let them race
    stop.set()
    for t in threads:
        t.join(timeout=2)

    assert not errors, f"reader/writer raised under contention: {errors!r}"


def test_reset_tool_log_clears_state():
    record_tool_log("foo", {"status": "ok"})
    assert "foo" in snapshot_tool_log()
    reset_tool_log()
    assert snapshot_tool_log() == {}


def test_snapshot_returns_independent_copy():
    record_tool_log("foo", {"status": "ok"})
    snap = snapshot_tool_log()
    # Mutating the snapshot must not affect the live store
    snap["bar"] = {"status": "fail"}
    assert "bar" not in snapshot_tool_log()
