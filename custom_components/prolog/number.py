"""Number entities controlling the supported object-count range."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    ATTR_MAX_COUNT,
    ATTR_MIN_COUNT,
    DOMAIN,
    SIGNAL_PROFILER_UPDATED,
)
from .profiler import ProfilerManager


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up count range controls."""
    manager: ProfilerManager = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            CountRangeNumber(manager, entry, ATTR_MIN_COUNT),
            CountRangeNumber(manager, entry, ATTR_MAX_COUNT),
        ]
    )


class CountRangeNumber(NumberEntity):
    """A number entity controlling one side of the count range."""

    _attr_native_min_value = 0
    _attr_native_max_value = 2**63 - 1
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX

    def __init__(self, manager: ProfilerManager, entry: ConfigEntry, bound: str) -> None:
        self._manager = manager
        self._bound = bound
        self._attr_name = f"prolog_{bound}"
        self._attr_unique_id = f"{entry.entry_id}_{bound}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)}, name="Prolog"
        )

    @property
    def native_value(self) -> int:
        return getattr(self._manager, self._bound)

    async def async_set_native_value(self, value: float) -> None:
        """Update the bound and refresh object sensors."""
        value = int(value)
        if self._bound == ATTR_MIN_COUNT:
            self._manager.set_min_count(value)
        else:
            self._manager.set_max_count(value)
        await self.hass.async_add_executor_job(self._manager.refresh)
        self._manager.notify_refresh_listeners()
        async_dispatcher_send(self.hass, SIGNAL_PROFILER_UPDATED)