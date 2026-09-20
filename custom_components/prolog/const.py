"""Constants for the Prolog integration."""
from __future__ import annotations

DOMAIN = "prolog"

ATTR_FREQUENCY = "frequency"
ATTR_TOP_N = "top_n"
DEFAULT_TOP_N = 10
DEFAULT_REFRESH_FREQUENCY = 30

EVENT_TRACEMALLOC_SNAPSHOT = "prolog_tracemalloc_snapshot"
SIGNAL_REFRESH_CONFIG = f"{DOMAIN}_refresh_config"
SIGNAL_PROFILER_UPDATED = f"{DOMAIN}_updated"

