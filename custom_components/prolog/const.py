"""Constants for the Prolog integration."""
from __future__ import annotations

DOMAIN = "prolog"

SERVICE_REFRESH = "refresh"
SERVICE_SET_FREQUENCY = "set_frequency"

ATTR_FREQUENCY = "frequency"
ATTR_MIN_COUNT = "min_count"
ATTR_MAX_COUNT = "max_count"
DEFAULT_MIN_COUNT = 1000
DEFAULT_MAX_COUNT = 2**63 - 1

SIGNAL_PROFILER_UPDATED = f"{DOMAIN}_updated"

