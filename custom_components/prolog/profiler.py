"""Garbage-collected object statistics for Prolog."""
from __future__ import annotations

import gc
from collections.abc import Callable
from datetime import datetime, timezone

from .const import DEFAULT_MAX_MEMORY, DEFAULT_MIN_MEMORY


class ProfilerManager:
    """Collects current object count and referent memory snapshots."""

    def __init__(
        self,
        min_memory: int = DEFAULT_MIN_MEMORY,
        max_memory: int = DEFAULT_MAX_MEMORY,
    ) -> None:
        self.min_memory = min_memory
        self.max_memory = max_memory
        self.last_report: dict | None = None
        self._refresh_listeners: list[Callable[[], None]] = []

    def add_refresh_listener(self, listener: Callable[[], None]) -> None:
        """Register a callback notified after each snapshot."""
        self._refresh_listeners.append(listener)

    def notify_refresh_listeners(self) -> None:
        """Notify listeners after a snapshot on Home Assistant's event loop."""
        for listener in self._refresh_listeners:
            listener()

    def set_memory_range(self, min_memory: int, max_memory: int) -> None:
        """Set the inclusive memory range that supports sensors."""
        if min_memory > max_memory:
            raise ValueError("min_memory must not exceed max_memory")
        self.min_memory = min_memory
        self.max_memory = max_memory

    def set_min_memory(self, min_memory: int) -> None:
        """Set the lower bound, expanding the upper bound if needed."""
        self.min_memory = min_memory
        self.max_memory = max(self.max_memory, min_memory)

    def set_max_memory(self, max_memory: int) -> None:
        """Set the upper bound, expanding the lower bound if needed."""
        self.max_memory = max_memory
        self.min_memory = min(self.min_memory, max_memory)

    @property
    def class_names(self) -> list[str]:
        """Return the object classes available in the latest snapshot."""
        if not self.last_report:
            return []
        return self.supported_class_names

    @property
    def supported_class_names(self) -> list[str]:
        """Return classes whose current memory is within the configured range."""
        if not self.last_report:
            return []
        return [
            name
            for name, memory in self.last_report["memory_counts"].items()
            if self.min_memory <= memory <= self.max_memory
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
        gc_stats = [dict(stats) for stats in gc.get_stats()]
        report = {
            "refreshed_at": datetime.now(timezone.utc).isoformat(),
            "object_counts": object_counts,
            "memory_counts": memory_counts,
            "gc_stats": gc_stats,
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
