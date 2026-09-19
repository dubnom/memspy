"""Binary sensor showing whether tracemalloc is active."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect, async_dispatcher_send
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_PROFILER_UPDATED
from .profiler import ProfilerManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the tracemalloc activity binary sensor."""
    manager: ProfilerManager = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([TracemallocBinarySensor(manager, entry)])


class TracemallocBinarySensor(BinarySensorEntity):
    """Reports whether the tracemalloc session is currently active."""

    _attr_should_poll = False
    _attr_icon = "mdi:memory"

    def __init__(self, manager: ProfilerManager, entry: ConfigEntry) -> None:
        self._manager = manager
        self._attr_name = "prolog_tracemalloc_active"
        self._attr_unique_id = f"{entry.entry_id}_tracemalloc_active"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)}, name="Prolog"
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_PROFILER_UPDATED, self._handle_update)
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        return self._manager._tracemalloc_started  # noqa: SLF001

    async def async_turn_on(self, **kwargs) -> None:
        await self.hass.async_add_executor_job(self._manager.start_tracemalloc)
        async_dispatcher_send(self.hass, SIGNAL_PROFILER_UPDATED)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        await self.hass.async_add_executor_job(self._manager.stop_tracemalloc)
        async_dispatcher_send(self.hass, SIGNAL_PROFILER_UPDATED)
        self.async_write_ha_state()
