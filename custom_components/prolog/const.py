"""Constants for the Prolog integration."""
from __future__ import annotations

DOMAIN = "prolog"

SERVICE_REFRESH = "refresh"
SERVICE_SET_FREQUENCY = "set_frequency"

ATTR_FREQUENCY = "frequency"
ATTR_MIN_MEMORY = "min_memory"
ATTR_MAX_MEMORY = "max_memory"
DEFAULT_MIN_MEMORY = 1000
DEFAULT_MAX_MEMORY = 2**63 - 1

SIGNAL_PROFILER_UPDATED = f"{DOMAIN}_updated"

