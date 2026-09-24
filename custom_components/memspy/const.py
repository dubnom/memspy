"""Constants for the Memspy integration."""
from __future__ import annotations

DOMAIN = "memspy"

ATTR_FREQUENCY = "frequency"
ATTR_RESULTS_LIMIT = "results_limit"
DEFAULT_RESULTS_LIMIT = 10
DEFAULT_REFRESH_FREQUENCY = 30

EVENT_TRACEMALLOC_SNAPSHOT = "memspy_tracemalloc_snapshot"
SIGNAL_REFRESH_CONFIG = f"{DOMAIN}_refresh_config"
SIGNAL_PROFILER_UPDATED = f"{DOMAIN}_updated"
SIGNAL_DASHBOARD_UPDATED = f"{DOMAIN}_dashboard_updated"

SERVICE_INSTALL_DASHBOARD = "install_dashboard"
