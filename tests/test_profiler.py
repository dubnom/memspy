"""Tests for object-memory and referent-memory snapshots."""
from __future__ import annotations

import fnmatch
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from custom_components.prolog import _cleanup_legacy_entities
from custom_components.prolog.profiler import ProfilerManager
from custom_components.prolog.sensor import ObjectSensor


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


def test_tracemalloc_elapsed_time_is_frozen_after_stop(monkeypatch):
    clock = iter([100.0, 100.0, 103.5])
    current_time = [100.0]

    def fake_monotonic():
        current_time[0] = next(clock, current_time[0])
        return current_time[0]

    monkeypatch.setattr(
        "custom_components.prolog.profiler.time.monotonic", fake_monotonic
    )
    manager = ProfilerManager()

    manager.start_tracemalloc()
    assert manager.tracemalloc_elapsed == 0.0
    manager.stop_tracemalloc()

    assert manager.tracemalloc_elapsed == 3.5
    assert manager.tracemalloc_active is False


def test_snapshot_filter_limits_results_to_matching_directory(monkeypatch):
    manager = ProfilerManager(top_n=10)
    manager.set_snapshot_filter("/tmp/prolog")
    manager.set_snapshot_exclusions("/tmp/prolog/pkg/c.py")

    class FakeSnapshot:
        def filter_traces(self, filters):
            included = [
                filter_.filename_pattern for filter_ in filters if filter_.inclusive
            ]
            excluded = [filter_.filename_pattern for filter_ in filters if not filter_.inclusive]
            return SimpleNamespace(
                statistics=lambda _name: [
                    stat
                    for stat in self.statistics(_name)
                    if (not included or any(
                        fnmatch.fnmatch(stat.traceback[0].filename, pattern)
                        for pattern in included
                    ))
                    and not any(
                        fnmatch.fnmatch(stat.traceback[0].filename, pattern)
                        for pattern in excluded
                    )
                ]
            )

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
    ]


def test_snapshot_exclusions_are_applied_before_top_n():
    manager = ProfilerManager(top_n=2)
    manager.set_snapshot_exclusions("/tmp/noisy/*\n# ignored\n")
    assert manager.snapshot_exclusions == ["/tmp/noisy/*"]


def test_snapshot_exclusions_default_to_empty():
    manager = ProfilerManager()

    assert manager.snapshot_exclusions == []


def test_builtin_snapshot_exclusions_are_combined_with_user_filters():
    manager = ProfilerManager()
    manager.set_snapshot_exclusions("/config/custom_components/noisy/*")

    filters = manager._tracemalloc_filters()

    assert [filter_.filename_pattern for filter_ in filters if not filter_.inclusive] == [
        "/config/custom_components/prolog/*",
        "/config/custom_components/spook/*",
        "/config/custom_components/noisy/*",
    ]


def test_memory_scanning_defaults_to_off():
    manager = ProfilerManager()

    assert manager.memory_scanning is False


def test_class_sensor_friendly_name_has_no_prolog_prefix():
    manager = ProfilerManager()
    manager.last_report = {
        "object_counts": {"dict": 1},
        "memory_counts": {"dict": 128},
    }
    sensor = ObjectSensor(manager, SimpleNamespace(entry_id="test"), 1)

    assert sensor.name == "dict"
    assert sensor._attr_has_entity_name is False


def test_legacy_entity_cleanup_migrates_and_removes_collisions(monkeypatch):
    class FakeRegistry:
        def __init__(self):
            self.entities = {
                "text.prolog_snapshot_filter": SimpleNamespace(
                    entity_id="text.prolog_snapshot_filter",
                    domain="text",
                    unique_id="entry_snapshot_filter",
                    config_entry_id="entry",
                ),
                "text.prolog_snapshot_exclusions": SimpleNamespace(
                    entity_id="text.prolog_snapshot_exclusions",
                    domain="text",
                    unique_id="entry_snapshot_exclusions",
                    config_entry_id="entry",
                ),
                "text.prolog_tracemalloc_exclude": SimpleNamespace(
                    entity_id="text.prolog_tracemalloc_exclude",
                    domain="text",
                    unique_id="entry_tracemalloc_exclude",
                    config_entry_id="entry",
                ),
                "binary_sensor.prolog_tracemalloc_active": SimpleNamespace(
                    entity_id="binary_sensor.prolog_tracemalloc_active",
                    domain="binary_sensor",
                    unique_id="entry_tracemalloc_active",
                    config_entry_id="entry",
                ),
            }
            self.updated = []
            self.removed = []

        def async_get_entity_id(self, domain, _platform, unique_id):
            for entity_id, entity in self.entities.items():
                if entity.domain == domain and entity.unique_id == unique_id:
                    return entity_id
            return None

        def async_get(self, entity_id):
            return self.entities.get(entity_id)

        def async_update_entity(self, entity_id, **changes):
            self.updated.append((entity_id, changes))

        def async_remove(self, entity_id):
            self.removed.append(entity_id)

    registry = FakeRegistry()
    monkeypatch.setattr(
        "custom_components.prolog.er.async_get", lambda _hass: registry
    )

    _cleanup_legacy_entities(SimpleNamespace(), SimpleNamespace(entry_id="entry"))

    assert registry.updated == [
        (
            "text.prolog_snapshot_filter",
            {
                "new_entity_id": "text.prolog_tracemalloc_include",
                "new_unique_id": "entry_tracemalloc_include",
            },
        )
    ]
    assert registry.removed == [
        "text.prolog_snapshot_exclusions",
        "binary_sensor.prolog_tracemalloc_active",
    ]


def test_class_entity_registry_name_is_class_name():
    manager = ProfilerManager()
    manager.last_report = {
        "object_counts": {"dict": 1},
        "memory_counts": {"dict": 128},
    }
    sensor = ObjectSensor(manager, SimpleNamespace(entry_id="entry"), 1)

    assert sensor.name == "dict"


def test_top_n_must_be_positive():
    manager = ProfilerManager()

    try:
        manager.set_top_n(0)
    except ValueError:
        pass
    else:
        raise AssertionError("top_n=0 should raise ValueError")
