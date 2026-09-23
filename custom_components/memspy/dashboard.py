"""Dynamically register the MemSpy view on the dedicated dashboard."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

VIEW_PATH = "memspy"
DEDICATED_DASHBOARD_PATH = "memspy-dashboard"
_VIEW_FILE = Path(__file__).parent / "dashboard_view.yaml"
VIEW_VERSION_KEY = "memspy_view_version"
# Bump whenever the bundled dashboard changes so existing installs pick up the update.
VIEW_VERSION = 3


def _load_view_sync() -> dict[str, Any]:
    """Read the bundled MemSpy Lovelace view definition without blocking the event loop."""
    with _VIEW_FILE.open("r", encoding="utf-8") as handle:
        view = yaml.safe_load(handle)
    view[VIEW_VERSION_KEY] = VIEW_VERSION
    return view


async def _load_view(hass: HomeAssistant) -> dict[str, Any]:
    """Load the dashboard YAML via the executor so the event loop stays responsive."""
    return await hass.async_add_executor_job(_load_view_sync)


async def _ensure_dedicated_dashboard(hass: HomeAssistant) -> Any:
    """Create the dedicated MemSpy storage dashboard if it does not exist."""
    from homeassistant.components.lovelace import frontend
    from homeassistant.components.lovelace.const import (
        CONF_ICON,
        CONF_REQUIRE_ADMIN,
        CONF_SHOW_IN_SIDEBAR,
        CONF_TITLE,
        CONF_URL_PATH,
        LOVELACE_DATA,
        MODE_STORAGE,
    )
    from homeassistant.components.lovelace.dashboard import (
        DashboardsCollection,
        LovelaceStorage,
    )

    lovelace_data = hass.data[LOVELACE_DATA]
    existing = lovelace_data.dashboards.get(DEDICATED_DASHBOARD_PATH)
    if existing is not None:
        return existing

    collection = DashboardsCollection(hass)
    await collection.async_load()
    item = collection.data.get(DEDICATED_DASHBOARD_PATH)
    if item is None:
        item = await collection.async_create_item(
            {
                CONF_TITLE: "MemSpy",
                CONF_URL_PATH: DEDICATED_DASHBOARD_PATH,
                CONF_ICON: "mdi:incognito",
                CONF_SHOW_IN_SIDEBAR: True,
                CONF_REQUIRE_ADMIN: False,
                "mode": MODE_STORAGE,
                "allow_single_word": False,
            }
        )

    dashboard_config = LovelaceStorage(hass, item)
    lovelace_data.dashboards[DEDICATED_DASHBOARD_PATH] = dashboard_config
    frontend.async_register_built_in_panel(
        hass,
        "lovelace",
        frontend_url_path=DEDICATED_DASHBOARD_PATH,
        sidebar_title=item[CONF_TITLE],
        sidebar_icon=item[CONF_ICON],
        require_admin=item[CONF_REQUIRE_ADMIN],
        config={"mode": MODE_STORAGE},
        update=False,
    )
    return dashboard_config


async def async_register_dashboard_view(hass: HomeAssistant, *, force: bool = False) -> str:
    """Add or refresh the MemSpy view on its dedicated Lovelace dashboard.

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

    dashboard_config = await _ensure_dedicated_dashboard(hass)
    try:
        config = await dashboard_config.async_load(False)
    except ConfigNotFound:
        config = {"views": []}

    views = config.setdefault("views", [])
    existing_index = next(
        (index for index, view in enumerate(views) if view.get("path") == VIEW_PATH),
        None,
    )
    try:
        view = await _load_view(hass)
    except OSError:
        _LOGGER.warning("Unable to load bundled MemSpy dashboard view")
        return "view_file_missing"

    if (
        not force
        and existing_index is not None
        and views[existing_index].get(VIEW_VERSION_KEY) == VIEW_VERSION
    ):
        _LOGGER.debug(
            "MemSpy view already present at version %s; skipping", VIEW_VERSION
        )
        return "already_up_to_date"

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


async def async_dashboard_out_of_date(hass: HomeAssistant) -> bool:
    """Return whether the existing MemSpy dashboard needs installation or upgrade."""
    try:
        from homeassistant.components.lovelace.const import LOVELACE_DATA
        from homeassistant.components.lovelace.dashboard import ConfigNotFound
    except ImportError:
        return True

    lovelace_data = hass.data.get(LOVELACE_DATA)
    if lovelace_data is None:
        return True

    dashboard_config = lovelace_data.dashboards.get(DEDICATED_DASHBOARD_PATH)
    if dashboard_config is None:
        return True
    try:
        config = await dashboard_config.async_load(False)
    except ConfigNotFound:
        return True

    view = next(
        (
            candidate
            for candidate in config.get("views", [])
            if candidate.get("path") == VIEW_PATH
        ),
        None,
    )
    return view is None or view.get(VIEW_VERSION_KEY) != VIEW_VERSION
