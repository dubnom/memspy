"""Dynamically register the MemSpy view on the default Lovelace dashboard."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

VIEW_PATH = "memspy"
_VIEW_FILE = Path(__file__).parent / "dashboard_view.yaml"
VIEW_VERSION_KEY = "memspy_view_version"
# Bump whenever dashboard_view.yaml changes so existing installs pick up the update.
VIEW_VERSION = 1


def _load_view_sync() -> dict[str, Any]:
    """Read the bundled MemSpy Lovelace view definition without blocking the event loop."""
    with _VIEW_FILE.open("r", encoding="utf-8") as handle:
        view = yaml.safe_load(handle)
    view[VIEW_VERSION_KEY] = VIEW_VERSION
    return view


async def _load_view(hass: HomeAssistant) -> dict[str, Any]:
    """Load the dashboard YAML via the executor so the event loop stays responsive."""
    return await hass.async_add_executor_job(_load_view_sync)


async def async_register_dashboard_view(hass: HomeAssistant, *, force: bool = False) -> str:
    """Add or refresh the MemSpy view on the default storage-mode Lovelace dashboard.

    This is best-effort: any failure (unsupported Lovelace version, YAML-mode
    dashboard, missing lovelace integration, etc.) is logged and ignored so it
    never prevents the config entry from loading. Returns a short machine-readable
    reason string describing what happened, which is also logged.
    """
    try:
        from homeassistant.components.lovelace.const import LOVELACE_DATA
        from homeassistant.components.lovelace.dashboard import ConfigNotFound
    except ImportError:
        _LOGGER.debug("Lovelace integration not available; skipping view registration")
        return "lovelace_unavailable"

    lovelace_data = hass.data.get(LOVELACE_DATA)
    if lovelace_data is None:
        _LOGGER.debug("Lovelace has not been set up yet; skipping view registration")
        return "lovelace_not_ready"

    dashboard_config = lovelace_data.dashboards.get(None)
    if dashboard_config is None or dashboard_config.mode != "storage":
        _LOGGER.debug(
            "Default dashboard is not storage-managed; skipping view registration"
        )
        return "dashboard_not_storage_mode"

    try:
        config = await dashboard_config.async_load(False)
    except ConfigNotFound:
        config = {"views": []}

    views = config.setdefault("views", [])
    existing_index = next(
        (index for index, view in enumerate(views) if view.get("path") == VIEW_PATH),
        None,
    )
    if (
        not force
        and existing_index is not None
        and views[existing_index].get(VIEW_VERSION_KEY) == VIEW_VERSION
    ):
        _LOGGER.debug(
            "MemSpy view already present at version %s; skipping", VIEW_VERSION
        )
        return "already_up_to_date"

    try:
        view = await _load_view(hass)
    except OSError:
        _LOGGER.warning("Unable to load bundled MemSpy dashboard view")
        return "view_file_missing"

    if existing_index is None:
        views.append(view)
        reason = "added"
    else:
        views[existing_index] = view
        reason = "updated"
    try:
        await dashboard_config.async_save(config)
    except Exception:  # noqa: BLE001 - never break setup over a dashboard tweak
        _LOGGER.exception("Failed to add MemSpy view to the default dashboard")
        return "save_failed"

    _LOGGER.info("MemSpy dashboard view %s on the default Lovelace dashboard", reason)
    return reason
