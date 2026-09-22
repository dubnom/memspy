"""The Memspy integration."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    DOMAIN,
    SERVICE_INSTALL_DASHBOARD,
    SIGNAL_REFRESH_CONFIG,
)
from .dashboard import async_register_dashboard_view
from .helpers import async_refresh_manager
from .profiler import ProfilerManager

PLATFORMS = ["sensor", "number", "text", "select", "switch", "button"]
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Memspy from a config entry."""
    manager = ProfilerManager()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = manager
    refresh_unsub = None

    async def refresh() -> None:
        await async_refresh_manager(hass, manager)

    async def handle_interval(_now) -> None:
        """Refresh sensors when the configured interval elapses."""
        _LOGGER.debug("Refreshing Memspy sensors on the configured interval")
        await refresh()

    @callback
    def configure_refresh() -> None:
        nonlocal refresh_unsub
        if refresh_unsub:
            refresh_unsub()
            refresh_unsub = None
        if manager.memory_scanning:
            refresh_unsub = async_track_time_interval(
                hass,
                handle_interval,
                timedelta(seconds=manager.refresh_frequency),
            )
        manager._refresh_unsub = refresh_unsub

    config_unsub = async_dispatcher_connect(
        hass, SIGNAL_REFRESH_CONFIG, configure_refresh
    )
    manager._config_unsub = config_unsub
    configure_refresh()
    await refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_register_dashboard_view(hass)

    async def handle_install_dashboard(_call: ServiceCall) -> dict[str, str]:
        """Force-(re)install the MemSpy Lovelace view, bypassing the version check."""
        result = await async_register_dashboard_view(hass, force=True)
        return {"result": result}

    if not hass.services.has_service(DOMAIN, SERVICE_INSTALL_DASHBOARD):
        hass.services.async_register(
            DOMAIN,
            SERVICE_INSTALL_DASHBOARD,
            handle_install_dashboard,
            supports_response=SupportsResponse.OPTIONAL,
        )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        manager = hass.data[DOMAIN].pop(entry.entry_id, None)
        config_unsub = getattr(manager, "_config_unsub", None)
        if config_unsub:
            config_unsub()
        refresh_unsub = getattr(manager, "_refresh_unsub", None)
        if refresh_unsub:
            refresh_unsub()
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_INSTALL_DASHBOARD)
    return unload_ok
