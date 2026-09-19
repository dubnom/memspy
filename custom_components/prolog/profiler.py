"""Garbage-collected object statistics for Prolog."""
from __future__ import annotations

import gc
import sys
import tracemalloc
from collections.abc import Callable
from datetime import datetime, timezone

from .const import DEFAULT_TOP_N


class ProfilerManager:
    """Collects current object count and referent memory snapshots."""

    def __init__(
        self,
        top_n: int = DEFAULT_TOP_N,
    ) -> None:
        self.top_n = top_n
        self.last_report: dict | None = None
        self._refresh_listeners: list[Callable[[], None]] = []
        self._tracemalloc_started = False
        self._tracemalloc_snapshot: tracemalloc.Snapshot | None = None

    def add_refresh_listener(self, listener: Callable[[], None]) -> None:
        """Register a callback notified after each snapshot."""
        self._refresh_listeners.append(listener)

    def notify_refresh_listeners(self) -> None:
        """Notify listeners after a snapshot on Home Assistant's event loop."""
        for listener in self._refresh_listeners:
            listener()

    def set_top_n(self, top_n: int) -> None:
        """Set the number of highest-memory classes that support sensors."""
        if top_n < 1:
            raise ValueError("top_n must be at least 1")
        self.top_n = top_n

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
            )[: self.top_n]
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

    def _parse_report(self, report: dict) -> list[dict]:
        """Convert memory values into entity/value rows for test and UI display."""
        rows: list[dict] = []
        for name, value in report.get("memory_counts", {}).items():
            rows.append({"entity": name, "value": value})
        return rows

    def start_tracemalloc(self) -> None:
        """Start a tracemalloc session for later snapshots."""
        if self._tracemalloc_started:
            return
        tracemalloc.start()
        self._tracemalloc_started = True
        self._tracemalloc_snapshot = None

    def stop_tracemalloc(self) -> None:
        """Stop an active tracemalloc session and release resources."""
        if not self._tracemalloc_started:
            return
        tracemalloc.stop()
        self._tracemalloc_started = False
        self._tracemalloc_snapshot = None

    def snapshot_tracemalloc(self) -> list[dict[str, object]]:
        """Take a tracemalloc snapshot and return the top-N entries."""
        if not self._tracemalloc_started:
            self.start_tracemalloc()

        snapshot = tracemalloc.take_snapshot()
        self._tracemalloc_snapshot = snapshot

        top_n = max(1, self.top_n)
        rows: list[dict[str, object]] = []
        for stat in snapshot.statistics("lineno")[:top_n]:
            rows.append(
                {
                    "filename": stat.traceback[0].filename,
                    "lineno": stat.traceback[0].lineno,
                    "size": stat.size,
                    "count": stat.count,
                }
            )
        return rows
