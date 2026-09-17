"""Garbage-collected object statistics for Prolog."""
from __future__ import annotations

import gc
from datetime import datetime, timezone
from collections.abc import Callable

from .const import DEFAULT_MAX_COUNT, DEFAULT_MIN_COUNT


class ProfilerManager:
    """Collects current object count and referent memory snapshots."""

    def __init__(
        self,
        min_count: int = DEFAULT_MIN_COUNT,
        max_count: int = DEFAULT_MAX_COUNT,
    ) -> None:
        self.min_count = min_count
        self.max_count = max_count
        self.last_report: dict | None = None
        self._refresh_listeners: list[Callable[[], None]] = []

    def add_refresh_listener(self, listener: Callable[[], None]) -> None:
        """Register a callback notified after each snapshot."""
        self._refresh_listeners.append(listener)

    def notify_refresh_listeners(self) -> None:
        """Notify listeners after a snapshot on Home Assistant's event loop."""
        for listener in self._refresh_listeners:
            listener()

    def set_count_range(self, min_count: int, max_count: int) -> None:
        """Set the inclusive object-count range that supports sensors."""
        if min_count > max_count:
            raise ValueError("min_count must not exceed max_count")
        self.min_count = min_count
        self.max_count = max_count

    def set_min_count(self, min_count: int) -> None:
        """Set the lower bound, expanding the upper bound if needed."""
        self.min_count = min_count
        self.max_count = max(self.max_count, min_count)

    def set_max_count(self, max_count: int) -> None:
        """Set the upper bound, expanding the lower bound if needed."""
        self.max_count = max_count
        self.min_count = min(self.min_count, max_count)

    @property
    def class_names(self) -> list[str]:
        """Return the object classes available in the latest snapshot."""
        if not self.last_report:
            return []
        return self.supported_class_names

    @property
    def supported_class_names(self) -> list[str]:
        """Return classes whose current counts are within the configured range."""
        if not self.last_report:
            return []
        return [
            name
            for name, count in self.last_report["object_counts"].items()
            if self.min_count <= count <= self.max_count
        ]

    def refresh(self) -> dict:
        """Capture current object counts and referent memory estimates."""
        object_counts: dict[str, int] = {}
        memory_counts: dict[str, int] = {}
        for obj in gc.get_objects():
            class_name = type(obj).__name__
            object_counts[class_name] = object_counts.get(class_name, 0) + 1
            referents = gc.get_referents(obj)
            memory_counts[class_name] = memory_counts.get(class_name, 0) + (
                referents.__sizeof__() if hasattr(referents, "__sizeof__") else 0
            )

        object_counts = dict(sorted(object_counts.items()))
        memory_counts = dict(sorted(memory_counts.items()))
        report = {
            "refreshed_at": datetime.now(timezone.utc).isoformat(),
            "object_counts": object_counts,
            "memory_counts": memory_counts,
            "summary": {
                "object_count": sum(object_counts.values()),
                "memory": sum(memory_counts.values()),
                "object_type_count": len(object_counts),
            },
        }

        self.last_report = report
        return report

    def _parse_report(self, report: dict) -> list[dict]:
        """Convert a snapshot report into entity/value rows for test and UI display."""
        rows: list[dict] = []
        for name, value in report.get("object_counts", {}).items():
            rows.append({"entity": name, "value": value})
        return rows
