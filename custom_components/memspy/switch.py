"""Switch controlling whether tracemalloc is active."""
from __future__ import annotations

import json

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect, async_dispatcher_send
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    EVENT_TRACEMALLOC_SNAPSHOT,
    SIGNAL_PROFILER_UPDATED,
    SIGNAL_REFRESH_CONFIG,
)
from .helpers import async_refresh_manager
from .profiler import ProfilerManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the tracemalloc activity switch."""
    manager: ProfilerManager = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [MemoryScanningSwitch(manager, entry), TracemallocSwitch(manager, entry)]
    )


class MemoryScanningSwitch(SwitchEntity):
    """Controls periodic object-memory scanning."""

    _attr_should_poll = False
    _attr_icon = "mdi:database-search"

    def __init__(self, manager: ProfilerManager, entry: ConfigEntry) -> None:
        self._manager = manager
        self._attr_name = "memspy_memory_scanning"
        self._attr_unique_id = f"{entry.entry_id}_memory_scanning"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)}, name="Memspy"
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_REFRESH_CONFIG, self._handle_update
            )
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        return self._manager.memory_scanning

    async def async_turn_on(self, **kwargs) -> None:
        self._manager.memory_scanning = True
        async_dispatcher_send(self.hass, SIGNAL_REFRESH_CONFIG)
        await async_refresh_manager(self.hass, self._manager)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        self._manager.memory_scanning = False
        async_dispatcher_send(self.hass, SIGNAL_REFRESH_CONFIG)
        self.async_write_ha_state()


class TracemallocSwitch(SwitchEntity):
    """Reports whether the tracemalloc session is currently active."""

    _attr_should_poll = False
    _attr_icon = "mdi:memory"

    def __init__(self, manager: ProfilerManager, entry: ConfigEntry) -> None:
        self._manager = manager
        self._attr_name = "memspy_tracemalloc_active"
        self._attr_unique_id = f"{entry.entry_id}_tracemalloc_active"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)}, name="Memspy"
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
        return self._manager.tracemalloc_active

    async def async_turn_on(self, **kwargs) -> None:
        await self.hass.async_add_executor_job(self._manager.start_tracemalloc)
        async_dispatcher_send(self.hass, SIGNAL_PROFILER_UPDATED)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        try:
            if self._manager.tracemalloc_active:
                snapshot = await self.hass.async_add_executor_job(
                    self._manager.snapshot_tracemalloc
                )
                self.hass.bus.async_fire(
                    EVENT_TRACEMALLOC_SNAPSHOT,
                    {"json": len(snapshot), "snapshot": json.dumps(snapshot)},
                )
        finally:
            await self.hass.async_add_executor_job(self._manager.stop_tracemalloc)
        async_dispatcher_send(self.hass, SIGNAL_PROFILER_UPDATED)
        self.async_write_ha_state()
