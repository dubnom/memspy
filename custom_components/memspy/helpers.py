"""Shared Home Assistant helpers for the Memspy integration."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import SIGNAL_PROFILER_UPDATED
from .profiler import ProfilerManager


async def async_refresh_manager(hass: HomeAssistant, manager: ProfilerManager) -> None:
    """Refresh the manager and notify all Memspy entities."""
    await hass.async_add_executor_job(manager.refresh)
    manager.notify_refresh_listeners()
    async_dispatcher_send(hass, SIGNAL_PROFILER_UPDATED)
