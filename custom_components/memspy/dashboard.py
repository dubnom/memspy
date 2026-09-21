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


def _load_view() -> dict[str, Any]:
    """Load the bundled MemSpy Lovelace view definition."""
    with _VIEW_FILE.open("r", encoding="utf-8") as handle:
        view = yaml.safe_load(handle)
    view[VIEW_VERSION_KEY] = VIEW_VERSION
    return view


async def async_register_dashboard_view(hass: HomeAssistant) -> None:
    """Add the MemSpy view to the default storage-mode Lovelace dashboard.

    This is best-effort: any failure (unsupported Lovelace version, YAML-mode
    dashboard, missing lovelace integration, etc.) is logged and ignored so it
    never prevents the config entry from loading.
    """
    try:
        from homeassistant.components.lovelace.const import LOVELACE_DATA
        from homeassistant.components.lovelace.dashboard import ConfigNotFound
    except ImportError:
        _LOGGER.debug("Lovelace integration not available; skipping view registration")
        return

    lovelace_data = hass.data.get(LOVELACE_DATA)
    if lovelace_data is None:
        _LOGGER.debug("Lovelace has not been set up yet; skipping view registration")
        return

    dashboard_config = lovelace_data.dashboards.get(None)
    if dashboard_config is None or dashboard_config.mode != "storage":
        _LOGGER.debug(
            "Default dashboard is not storage-managed; skipping view registration"
        )
        return

    try:
        config = await dashboard_config.async_load(False)
    except ConfigNotFound:
        config = {"views": []}

    views = config.setdefault("views", [])
    existing_index = next(
        (index for index, view in enumerate(views) if view.get("path") == VIEW_PATH),
        None,
    )
    if existing_index is not None and views[existing_index].get(VIEW_VERSION_KEY) == VIEW_VERSION:
        return

    try:
        view = _load_view()
    except OSError:
        _LOGGER.warning("Unable to load bundled MemSpy dashboard view")
        return

    if existing_index is None:
        views.append(view)
    else:
        views[existing_index] = view
    try:
        await dashboard_config.async_save(config)
    except Exception:  # noqa: BLE001 - never break setup over a dashboard tweak
        _LOGGER.exception("Failed to add MemSpy view to the default dashboard")
        return

    if existing_index is None:
        _LOGGER.info("Added MemSpy view to the default Lovelace dashboard")
    else:
        _LOGGER.info("Updated MemSpy view on the default Lovelace dashboard")
