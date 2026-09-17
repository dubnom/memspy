"""Garbage-collected object statistics for Prolog."""
from __future__ import annotations

import gc
from datetime import datetime, timezone


class ProfilerManager:
    """Collects current object count and referent memory snapshots."""

    def __init__(self) -> None:
        self.last_report: dict | None = None

    @property
    def class_names(self) -> list[str]:
        """Return the object classes available in the latest snapshot."""
        if not self.last_report:
            return []
        return list(self.last_report["object_counts"])

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
