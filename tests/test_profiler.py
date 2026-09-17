"""Tests for object-count and referent-memory snapshots."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from custom_components.prolog.profiler import ProfilerManager


def _parsed_entities(report) -> list[dict[str, object]]:
    """Return the report in entity/value form for assertions and debug output."""
    return [{"entity": name, "value": value} for name, value in report["object_counts"].items()]


def test_refresh_collects_counts_and_memory():
    manager = ProfilerManager()
    report = manager.refresh()

    parsed = _parsed_entities(report)

    print("Parsed object report:", parsed)

    assert "dict" in report["object_counts"] or "set" in report["object_counts"]
    assert "dict" in report["memory_counts"] or "set" in report["memory_counts"]
    assert report["gc_stats"]
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
        "object_counts": {
            "dict": 7,
            "list": 10,
        },
        "summary": {"object_type_count": 2},
    }

    parsed = ProfilerManager()._parse_report(report)
    print("Parsed snapshot:", parsed)

    assert parsed == [
        {"entity": "dict", "value": 7},
        {"entity": "list", "value": 10},
    ]


def test_class_names_and_memory_are_available_per_object_type():
    manager = ProfilerManager(min_count=0)
    manager.last_report = {
        "object_counts": {"dict": 7, "list": 10},
        "memory_counts": {"dict": 128, "list": 256},
    }

    assert manager.class_names == ["dict", "list"]
    assert manager.last_report["object_counts"]["dict"] == 7
    assert manager.last_report["memory_counts"]["dict"] == 128


def test_count_range_filters_supported_classes_and_notifies_listeners():
    manager = ProfilerManager(min_count=5, max_count=10)
    notifications = []
    manager.add_refresh_listener(lambda: notifications.append(manager.class_names))
    manager.last_report = {
        "object_counts": {"dict": 7, "list": 3, "set": 12},
        "memory_counts": {"dict": 128, "list": 256, "set": 512},
    }

    assert manager.class_names == ["dict"]
    manager.set_count_range(3, 12)

    assert manager.class_names == ["dict", "list", "set"]
    manager.refresh()
    manager.notify_refresh_listeners()
    assert notifications


def test_count_bounds_can_cross_without_invalid_range_error():
    manager = ProfilerManager(min_count=10, max_count=20)

    manager.set_min_count(30)
    assert (manager.min_count, manager.max_count) == (30, 30)

    manager.set_max_count(5)
    assert (manager.min_count, manager.max_count) == (5, 5)
