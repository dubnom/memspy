"""Tests for object-memory and referent-memory snapshots."""
from __future__ import annotations

import fnmatch
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from custom_components.memspy import dashboard
from custom_components.memspy.button import InstallDashboardButton
from custom_components.memspy.profiler import ProfilerManager
from custom_components.memspy.select import TracemallocIncludeSelect
from custom_components.memspy.sensor import ObjectSensor


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
    manager = ProfilerManager(results_limit=2)
    manager.last_report = {
        "object_counts": {"dict": 7, "list": 10},
        "memory_counts": {"dict": 128, "list": 256},
    }

    assert manager.class_names == ["list", "dict"]
    assert manager.last_report["object_counts"]["dict"] == 7
    assert manager.last_report["memory_counts"]["dict"] == 128


def test_results_limit_filters_supported_classes_and_notifies_listeners():
    manager = ProfilerManager(results_limit=1)
    notifications = []
    manager.add_refresh_listener(lambda: notifications.append(manager.class_names))
    manager.last_report = {
        "object_counts": {"dict": 7, "list": 3, "set": 12},
        "memory_counts": {"dict": 7, "list": 3, "set": 12},
    }

    assert manager.class_names == ["set"]
    manager.set_results_limit(3)

    assert manager.class_names == ["set", "dict", "list"]
    manager.refresh()
    manager.notify_refresh_listeners()
    assert notifications


def test_tracemalloc_snapshot_uses_results_limit():
    manager = ProfilerManager(results_limit=2)
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
    manager = ProfilerManager(results_limit=2)
    manager.start_tracemalloc()
    try:
        snapshot = manager.snapshot_tracemalloc()
        assert manager.last_tracemalloc_snapshot == snapshot
        assert len(snapshot) <= 2
        assert len(manager.last_tracemalloc_by_integration) <= 2
    finally:
        manager.stop_tracemalloc()


def test_tracemalloc_snapshot_aggregates_by_integration():
    rows = [
        {"filename": "/config/custom_components/alpha/a.py", "lineno": 10, "size": 40, "count": 2},
        {"filename": "/config/custom_components/alpha/b.py", "lineno": 20, "size": 60, "count": 3},
        {"filename": "/usr/local/lib/python3.13/site-packages/homeassistant/components/beta/c.py", "lineno": 30, "size": 25, "count": 1},
    ]

    result = ProfilerManager.aggregate_tracemalloc_snapshot(rows)

    assert result == [
        {
            "integration": "alpha",
            "memory": 100,
            "allocations": [
                {"filename": "/config/custom_components/alpha/b.py", "line": 20, "memory": 60, "count": 3},
                {"filename": "/config/custom_components/alpha/a.py", "line": 10, "memory": 40, "count": 2},
            ],
        },
        {
            "integration": "beta",
            "memory": 25,
            "allocations": [
                {"filename": "/usr/local/lib/python3.13/site-packages/homeassistant/components/beta/c.py", "line": 30, "memory": 25, "count": 1},
            ],
        },
    ]


def test_tracemalloc_elapsed_time_is_frozen_after_stop(monkeypatch):
    clock = iter([100.0, 100.0, 103.5])
    current_time = [100.0]

    def fake_monotonic():
        current_time[0] = next(clock, current_time[0])
        return current_time[0]

    monkeypatch.setattr(
        "custom_components.memspy.profiler.time.monotonic", fake_monotonic
    )
    manager = ProfilerManager()

    manager.start_tracemalloc()
    assert manager.tracemalloc_elapsed == 0.0
    manager.stop_tracemalloc()

    assert manager.tracemalloc_elapsed == 3.5
    assert manager.tracemalloc_active is False


def test_snapshot_filter_limits_results_to_matching_directory(monkeypatch):
    manager = ProfilerManager(results_limit=10)
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

    monkeypatch.setattr("custom_components.memspy.profiler.tracemalloc.take_snapshot", lambda: FakeSnapshot())
    manager.start_tracemalloc()
    try:
        snapshot = manager.snapshot_tracemalloc()
    finally:
        manager.stop_tracemalloc()

    assert [entry["filename"] for entry in snapshot] == [
        "/tmp/prolog/pkg/a.py",
    ]


def test_tracemalloc_aggregation_uses_rows_before_result_limit(monkeypatch):
    class FakeSnapshot:
        def filter_traces(self, _filters):
            return self

        @staticmethod
        def statistics(_name):
            return [
                SimpleNamespace(
                    traceback=(SimpleNamespace(filename="/config/custom_components/alpha/a.py", lineno=10),),
                    size=100,
                    count=1,
                ),
                SimpleNamespace(
                    traceback=(SimpleNamespace(filename="/config/custom_components/alpha/b.py", lineno=20),),
                    size=90,
                    count=2,
                ),
                SimpleNamespace(
                    traceback=(SimpleNamespace(filename="/config/custom_components/beta/c.py", lineno=30),),
                    size=150,
                    count=3,
                ),
            ]

    monkeypatch.setattr(
        "custom_components.memspy.profiler.tracemalloc.take_snapshot",
        lambda: FakeSnapshot(),
    )
    manager = ProfilerManager(results_limit=1)
    manager.start_tracemalloc()
    try:
        snapshot = manager.snapshot_tracemalloc()
    finally:
        manager.stop_tracemalloc()

    assert len(snapshot) == 1
    assert manager.last_tracemalloc_by_integration == [
        {
            "integration": "alpha",
            "memory": 190,
            "allocations": [
                {"filename": "/config/custom_components/alpha/a.py", "line": 10, "memory": 100, "count": 1},
                {"filename": "/config/custom_components/alpha/b.py", "line": 20, "memory": 90, "count": 2},
            ],
        }
    ]


def test_snapshot_exclusions_are_applied_before_results_limit():
    manager = ProfilerManager(results_limit=2)
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
        "/config/custom_components/memspy/*",
        "/config/custom_components/spook/*",
        "/config/custom_components/noisy/*",
    ]


def test_memory_scanning_defaults_to_off():
    manager = ProfilerManager()

    assert manager.memory_scanning is False


def test_class_sensor_friendly_name_has_no_memspy_prefix():
    manager = ProfilerManager()
    manager.last_report = {
        "object_counts": {"dict": 1},
        "memory_counts": {"dict": 128},
    }
    sensor = ObjectSensor(manager, SimpleNamespace(entry_id="test"), 1)

    assert sensor.name == "dict"
    assert sensor._attr_has_entity_name is False


def test_class_entity_registry_name_is_class_name():
    manager = ProfilerManager()
    manager.last_report = {
        "object_counts": {"dict": 1},
        "memory_counts": {"dict": 128},
    }
    sensor = ObjectSensor(manager, SimpleNamespace(entry_id="entry"), 1)

    assert sensor.name == "dict"


def test_tracemalloc_include_select_has_special_options():
    manager = ProfilerManager(snapshot_filter="*")
    selector = TracemallocIncludeSelect(
        manager,
        SimpleNamespace(entry_id="entry"),
        ["all", "custom", "homeassistant"],
        {
            "all": "*",
            "custom": "/config/custom_components",
            "homeassistant": "/usr/local/lib/homeassistant",
        },
    )

    assert selector.current_option == "all"
    assert selector.extra_state_attributes["code_location"] == "*"


def test_dashboard_view_includes_version_marker():
    view = dashboard._load_view_sync()

    assert view.get("memspy_view_version") == dashboard.VIEW_VERSION


def test_install_dashboard_button_has_expected_entity_name():
    button = InstallDashboardButton(SimpleNamespace(entry_id="entry"), "test")

    assert button.name == "Install dashboard"


def test_results_limit_must_be_positive():
    manager = ProfilerManager()

    try:
        manager.set_results_limit(0)
    except ValueError:
        pass
    else:
        raise AssertionError("results_limit=0 should raise ValueError")
