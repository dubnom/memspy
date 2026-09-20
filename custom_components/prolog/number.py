"""Number entities controlling Prolog settings."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    ATTR_TOP_N,
    DOMAIN,
    SIGNAL_REFRESH_CONFIG,
    SIGNAL_PROFILER_UPDATED,
)
from .profiler import ProfilerManager


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the top-memory-user control."""
    manager: ProfilerManager = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            TopNNumber(manager, entry),
            RefreshFrequencyNumber(manager, entry),
        ]
    )


class TopNNumber(NumberEntity):
    """A number entity controlling how many memory users are supported."""

    _attr_native_min_value = 1
    _attr_native_max_value = 2**63 - 1
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX

    def __init__(self, manager: ProfilerManager, entry: ConfigEntry) -> None:
        self._manager = manager
        self._attr_name = "prolog_top_n"
        self._attr_unique_id = f"{entry.entry_id}_top_n"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)}, name="Prolog"
        )

    @property
    def native_value(self) -> int:
        return self._manager.top_n

    async def async_set_native_value(self, value: float) -> None:
        """Update the bound and refresh object sensors."""
        value = int(value)
        self._manager.set_top_n(value)
        await self.hass.async_add_executor_job(self._manager.refresh)
        self._manager.notify_refresh_listeners()
        async_dispatcher_send(self.hass, SIGNAL_PROFILER_UPDATED)


class RefreshFrequencyNumber(NumberEntity):
    """A number entity controlling automatic memory scan frequency."""

    _attr_native_min_value = 1
    _attr_native_max_value = 86400
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX

    def __init__(self, manager: ProfilerManager, entry: ConfigEntry) -> None:
        self._manager = manager
        self._attr_name = "prolog_memory_scan_frequency"
        self._attr_unique_id = f"{entry.entry_id}_memory_scan_frequency"
        self._attr_native_unit_of_measurement = "s"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)}, name="Prolog"
        )

    @property
    def native_value(self) -> int:
        return self._manager.refresh_frequency

    async def async_set_native_value(self, value: float) -> None:
        self._manager.refresh_frequency = max(1, int(value))
        async_dispatcher_send(self.hass, SIGNAL_REFRESH_CONFIG)