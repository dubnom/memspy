"""The Prolog integration."""
from __future__ import annotations

from datetime import timedelta
import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    ATTR_FREQUENCY,
    DOMAIN,
    EVENT_TRACEMALLOC_SNAPSHOT,
    SERVICE_REFRESH,
    SERVICE_SET_FREQUENCY,
    SERVICE_SNAPSHOT_TRACEMALLOC,
    SERVICE_START_TRACEMALLOC,
    SERVICE_STOP_TRACEMALLOC,
    SIGNAL_PROFILER_UPDATED,
)
from .profiler import ProfilerManager

PLATFORMS = ["sensor", "number"]
_LOGGER = logging.getLogger(__name__)

FREQUENCY_SERVICE_SCHEMA = vol.Schema(
    {vol.Required(ATTR_FREQUENCY): vol.All(vol.Coerce(int), vol.Range(min=0))}
)
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

    async def handle_refresh(call: ServiceCall) -> None:
        await refresh()

    async def handle_set_frequency(call: ServiceCall) -> None:
        nonlocal refresh_unsub
        if refresh_unsub:
            refresh_unsub()
            refresh_unsub = None
        frequency = call.data[ATTR_FREQUENCY]
        if frequency:
            refresh_unsub = async_track_time_interval(
                hass, handle_interval, timedelta(seconds=frequency)
            )
            _LOGGER.debug("Configured Prolog sensor refresh every %s seconds", frequency)
        manager._refresh_unsub = refresh_unsub  # noqa: SLF001
        await refresh()

    async def handle_start_tracemalloc(call: ServiceCall) -> None:
        await hass.async_add_executor_job(manager.start_tracemalloc)

    async def handle_snapshot_tracemalloc(call: ServiceCall) -> dict[str, list[dict[str, object]]]:
        snapshot = await hass.async_add_executor_job(manager.snapshot_tracemalloc)
        hass.bus.async_fire(EVENT_TRACEMALLOC_SNAPSHOT, {"results": snapshot})
        async_dispatcher_send(hass, SIGNAL_PROFILER_UPDATED)
        return {"results": snapshot}

    async def handle_stop_tracemalloc(call: ServiceCall) -> None:
        await hass.async_add_executor_job(manager.stop_tracemalloc)

    hass.services.async_register(DOMAIN, SERVICE_REFRESH, handle_refresh)
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_FREQUENCY,
        handle_set_frequency,
        schema=FREQUENCY_SERVICE_SCHEMA,
    )
    hass.services.async_register(DOMAIN, SERVICE_START_TRACEMALLOC, handle_start_tracemalloc)
    hass.services.async_register(
        DOMAIN,
        SERVICE_SNAPSHOT_TRACEMALLOC,
        handle_snapshot_tracemalloc,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(DOMAIN, SERVICE_STOP_TRACEMALLOC, handle_stop_tracemalloc)
    await refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        manager = hass.data[DOMAIN].pop(entry.entry_id, None)
        refresh_unsub = getattr(manager, "_refresh_unsub", None)
        if refresh_unsub:
            refresh_unsub()
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_REFRESH)
            hass.services.async_remove(DOMAIN, SERVICE_SET_FREQUENCY)
            hass.services.async_remove(DOMAIN, SERVICE_START_TRACEMALLOC)
            hass.services.async_remove(DOMAIN, SERVICE_SNAPSHOT_TRACEMALLOC)
            hass.services.async_remove(DOMAIN, SERVICE_STOP_TRACEMALLOC)
    return unload_ok
