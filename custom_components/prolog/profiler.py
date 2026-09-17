"""Garbage-collected object statistics for Prolog."""
from __future__ import annotations

import gc
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
