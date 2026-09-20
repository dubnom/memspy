"""The Prolog integration."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    DOMAIN,
    SIGNAL_REFRESH_CONFIG,
    SIGNAL_PROFILER_UPDATED,
)
from .profiler import ProfilerManager

PLATFORMS = ["sensor", "number", "text", "switch"]
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Prolog from a config entry."""
    manager = ProfilerManager()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = manager
    refresh_unsub = None

    async def refresh() -> None:
        await hass.async_add_executor_job(manager.refresh)
        manager.notify_refresh_listeners()
        async_dispatcher_send(hass, SIGNAL_PROFILER_UPDATED)

    async def handle_interval(_now) -> None:
        """Refresh sensors when the configured interval elapses."""
        _LOGGER.debug("Refreshing Prolog sensors on the configured interval")
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
        manager._refresh_unsub = refresh_unsub  # noqa: SLF001

    config_unsub = async_dispatcher_connect(
        hass, SIGNAL_REFRESH_CONFIG, configure_refresh
    )
    manager._config_unsub = config_unsub  # noqa: SLF001
    configure_refresh()
    await refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
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
    return unload_ok
