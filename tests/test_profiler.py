"""Tests for object-memory and referent-memory snapshots."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from custom_components.prolog.profiler import ProfilerManager


def _parsed_entities(report) -> list[dict[str, object]]:
    """Return memory values in entity/value form for assertions and debug output."""
    return [{"entity": name, "value": value} for name, value in report["memory_counts"].items()]


def test_refresh_collects_counts_and_memory():
    manager = ProfilerManager()
    report = manager.refresh()

    parsed = _parsed_entities(report)

    print("Parsed object report:", parsed)

    assert "dict" in report["object_counts"] or "set" in report["object_counts"]
    assert "dict" in report["memory_counts"] or "set" in report["memory_counts"]
    assert report["gc_stats"]
    assert "garbage" in report
    assert "collections" in report
    assert "collected" in report
    assert "uncollectable" in report
    assert "object_count" in report["summary"]
    assert report["summary"]["object_count"] > 0
    assert all(isinstance(stats, dict) for stats in report["gc_stats"])
    assert report["summary"]["object_type_count"] > 0
    assert all(isinstance(item["value"], int) for item in parsed)
    assert all(item["value"] >= 0 for item in parsed)
    assert manager.last_report is report


def test_refresh_updates_last_report():
    manager = ProfilerManager()
    first = manager.refresh()
    second = manager.refresh()

    assert manager.last_report is second
    assert first["summary"]["object_count"] >= 0
    assert second["summary"]["memory"] >= 0


def test_parse_report_from_snapshot_map():
    report = {
        "memory_counts": {"dict": 7, "list": 10},
        "summary": {"object_type_count": 2},
    }

    parsed = ProfilerManager()._parse_report(report)
    print("Parsed snapshot:", parsed)

    assert parsed == [
        {"entity": "dict", "value": 7},
        {"entity": "list", "value": 10},
    ]


def test_class_names_and_memory_are_available_per_object_type():
    manager = ProfilerManager(top_n=2)
    manager.last_report = {
        "object_counts": {"dict": 7, "list": 10},
        "memory_counts": {"dict": 128, "list": 256},
    }

    assert manager.class_names == ["list", "dict"]
    assert manager.last_report["object_counts"]["dict"] == 7
    assert manager.last_report["memory_counts"]["dict"] == 128


def test_top_n_filters_supported_classes_and_notifies_listeners():
    manager = ProfilerManager(top_n=1)
    notifications = []
    manager.add_refresh_listener(lambda: notifications.append(manager.class_names))
    manager.last_report = {
        "object_counts": {"dict": 7, "list": 3, "set": 12},
        "memory_counts": {"dict": 7, "list": 3, "set": 12},
    }

    assert manager.class_names == ["set"]
    manager.set_top_n(3)

    assert manager.class_names == ["set", "dict", "list"]
    manager.refresh()
    manager.notify_refresh_listeners()
    assert notifications


def test_tracemalloc_snapshot_uses_top_n_limit():
    manager = ProfilerManager(top_n=2)
    manager.start_tracemalloc()
    try:
        snapshot = manager.snapshot_tracemalloc()
        assert isinstance(snapshot, list)
        assert len(snapshot) <= 2
        assert all("filename" in item for item in snapshot)
        assert all("size" in item for item in snapshot)
    finally:
        manager.stop_tracemalloc()


def test_tracemalloc_snapshot_is_stored_on_manager():
    manager = ProfilerManager(top_n=2)
    manager.start_tracemalloc()
    try:
        snapshot = manager.snapshot_tracemalloc()
        assert manager.last_tracemalloc_snapshot == snapshot
        assert len(snapshot) <= 2
    finally:
        manager.stop_tracemalloc()


def test_snapshot_filter_limits_results_to_matching_directory(monkeypatch):
    manager = ProfilerManager(top_n=10)
    manager.set_snapshot_filter("/tmp/prolog")

    class FakeSnapshot:
        @staticmethod
        def statistics(_name):
            return [
                SimpleNamespace(
                    traceback=(SimpleNamespace(filename="/tmp/prolog/pkg/a.py", lineno=10),),
                    size=50,
                    count=2,
                ),
                SimpleNamespace(
                    traceback=(SimpleNamespace(filename="/tmp/other/pkg/b.py", lineno=20),),
                    size=500,
                    count=10,
                ),
                SimpleNamespace(
                    traceback=(SimpleNamespace(filename="/tmp/prolog/pkg/c.py", lineno=30),),
                    size=25,
                    count=1,
                ),
            ]

    monkeypatch.setattr("custom_components.prolog.profiler.tracemalloc.take_snapshot", lambda: FakeSnapshot())
    manager.start_tracemalloc()
    try:
        snapshot = manager.snapshot_tracemalloc()
    finally:
        manager.stop_tracemalloc()

    assert [entry["filename"] for entry in snapshot] == [
        "/tmp/prolog/pkg/a.py",
        "/tmp/prolog/pkg/c.py",
    ]


def test_top_n_must_be_positive():
    manager = ProfilerManager()

    try:
        manager.set_top_n(0)
    except ValueError:
        pass
    else:
        raise AssertionError("top_n=0 should raise ValueError")
