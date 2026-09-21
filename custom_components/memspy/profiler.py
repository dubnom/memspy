"""Garbage-collected object statistics for Memspy."""
from __future__ import annotations

import gc
import sys
import time
import tracemalloc
from collections.abc import Callable
from datetime import datetime, timezone

from .const import DEFAULT_REFRESH_FREQUENCY, DEFAULT_RESULTS_LIMIT

DEFAULT_SNAPSHOT_EXCLUSIONS = (
    "/config/custom_components/memspy/*",
    "/config/custom_components/spook/*",
)


class ProfilerManager:
    """Collects current object count and referent memory snapshots."""

    def __init__(
        self,
        results_limit: int = DEFAULT_RESULTS_LIMIT,
        snapshot_filter: str = "/config/custom_components",
        snapshot_exclusions: str = "",
    ) -> None:
        self.results_limit = results_limit
        self.snapshot_filter = snapshot_filter
        self.snapshot_exclusions = self._parse_snapshot_exclusions(snapshot_exclusions)
        self.refresh_frequency = DEFAULT_REFRESH_FREQUENCY
        self.memory_scanning = False
        self.last_report: dict | None = None
        self._refresh_listeners: list[Callable[[], None]] = []
        self._refresh_unsub: Callable[[], None] | None = None
        self._config_unsub: Callable[[], None] | None = None
        self._tracemalloc_started = False
        self._tracemalloc_started_at: float | None = None
        self._tracemalloc_elapsed = 0.0
        self.last_tracemalloc_snapshot: list[dict[str, object]] | None = None

    def add_refresh_listener(self, listener: Callable[[], None]) -> None:
        """Register a callback notified after each snapshot."""
        self._refresh_listeners.append(listener)

    def notify_refresh_listeners(self) -> None:
        """Notify listeners after a snapshot on Home Assistant's event loop."""
        for listener in self._refresh_listeners:
            listener()

    def set_results_limit(self, results_limit: int) -> None:
        """Set the number of highest-memory classes that support sensors."""
        if results_limit < 1:
            raise ValueError("results_limit must be at least 1")
        self.results_limit = results_limit

    def set_snapshot_filter(self, snapshot_filter: str | None) -> None:
        """Set the directory prefix used to include tracemalloc entries."""
        value = (snapshot_filter or "*").strip()
        if not value:
            value = "*"
        self.snapshot_filter = value

    @staticmethod
    def _parse_snapshot_exclusions(value: str | None) -> list[str]:
        """Parse newline-separated tracemalloc exclusion patterns."""
        return [
            line.strip()
            for line in (value or "").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]

    def set_snapshot_exclusions(self, value: str | None) -> None:
        """Set newline-separated tracemalloc exclusion patterns."""
        self.snapshot_exclusions = self._parse_snapshot_exclusions(value)

    def _tracemalloc_filters(self) -> list[tracemalloc.Filter]:
        """Build native tracemalloc include and exclusion filters."""
        filters: list[tracemalloc.Filter] = []
        if self.snapshot_filter not in ("*", ""):
            filters.append(
                tracemalloc.Filter(
                    True, f"{self.snapshot_filter.rstrip('/')}/*"
                )
            )
        filters.extend(
            tracemalloc.Filter(False, pattern)
            for pattern in (*DEFAULT_SNAPSHOT_EXCLUSIONS, *self.snapshot_exclusions)
        )
        return filters

    @property
    def class_names(self) -> list[str]:
        """Return the object classes available in the latest snapshot."""
        if not self.last_report:
            return []
        return self.supported_class_names

    @property
    def supported_class_names(self) -> list[str]:
        """Return the classes with the highest current memory usage."""
        if not self.last_report:
            return []
        return [
            name
            for name, _memory in sorted(
                self.last_report["memory_counts"].items(),
                key=lambda item: (-item[1], item[0]),
            )[: self.results_limit]
        ]

    def refresh(self) -> dict:
        """Capture current object counts and referent memory estimates."""
        object_counts: dict[str, int] = {}
        memory_counts: dict[str, int] = {}
        for obj in gc.get_objects():
            class_name = type(obj).__name__
            object_counts[class_name] = object_counts.get(class_name, 0) + 1
            memory_counts[class_name] = memory_counts.get(class_name, 0) + (
                sys.getsizeof(obj) + sum(sys.getsizeof(ref) for ref in gc.get_referents(obj))
            )

        object_counts = dict(sorted(object_counts.items()))
        memory_counts = dict(sorted(memory_counts.items()))
        gc_stats = [dict(stats) for stats in gc.get_stats()]
        report = {
            "refreshed_at": datetime.now(timezone.utc).isoformat(),
            "object_counts": object_counts,
            "memory_counts": memory_counts,
            "gc_stats": gc_stats,
            "garbage": len(gc.garbage),
            "collections": sum(gc.get_count()),
            "collected": sum(stats.get("collected", 0) for stats in gc_stats),
            "uncollectable": sum(stats.get("uncollectable", 0) for stats in gc_stats),
            "summary": {
                "object_count": sum(object_counts.values()),
                "memory": sum(memory_counts.values()),
                "object_type_count": len(object_counts),
            },
        }

        self.last_report = report
        return report

    def start_tracemalloc(self) -> None:
        """Start a tracemalloc session for later snapshots."""
        if self._tracemalloc_started:
            return
        tracemalloc.start()
        self._tracemalloc_started = True
        self._tracemalloc_started_at = time.monotonic()
        self._tracemalloc_elapsed = 0.0

    def stop_tracemalloc(self) -> None:
        """Stop an active tracemalloc session and release resources."""
        if not self._tracemalloc_started:
            return
        if self._tracemalloc_started_at is not None:
            self._tracemalloc_elapsed = time.monotonic() - self._tracemalloc_started_at
        tracemalloc.stop()
        self._tracemalloc_started = False
        self._tracemalloc_started_at = None

    @property
    def tracemalloc_active(self) -> bool:
        """Return whether tracemalloc is currently collecting allocations."""
        return self._tracemalloc_started

    @property
    def tracemalloc_elapsed(self) -> float:
        """Return elapsed seconds for the current or most recent session."""
        if self._tracemalloc_started and self._tracemalloc_started_at is not None:
            return time.monotonic() - self._tracemalloc_started_at
        return self._tracemalloc_elapsed

    def snapshot_tracemalloc(self) -> list[dict[str, object]]:
        """Take a tracemalloc snapshot and return the top-N filtered entries."""
        if not self._tracemalloc_started:
            self.start_tracemalloc()

        snapshot = tracemalloc.take_snapshot()
        filters = self._tracemalloc_filters()
        if filters:
            snapshot = snapshot.filter_traces(filters)
        rows: list[dict[str, object]] = []
        for stat in snapshot.statistics("lineno"):
            filename = stat.traceback[0].filename
            rows.append(
                {
                    "filename": filename,
                    "lineno": stat.traceback[0].lineno,
                    "size": stat.size,
                    "count": stat.count,
                }
            )
            if len(rows) >= max(1, self.results_limit):
                break

        self.last_tracemalloc_snapshot = rows
        return rows
