"""Constants for the Prolog integration."""
from __future__ import annotations

DOMAIN = "prolog"

SERVICE_REFRESH = "refresh"
SERVICE_SET_FREQUENCY = "set_frequency"
SERVICE_START_TRACEMALLOC = "start_tracemalloc"
SERVICE_SNAPSHOT_TRACEMALLOC = "snapshot_tracemalloc"
SERVICE_STOP_TRACEMALLOC = "stop_tracemalloc"

ATTR_FREQUENCY = "frequency"
ATTR_TOP_N = "top_n"
DEFAULT_TOP_N = 10

EVENT_TRACEMALLOC_SNAPSHOT = "prolog_tracemalloc_snapshot"
SIGNAL_PROFILER_UPDATED = f"{DOMAIN}_updated"

