"""Text entities for tracemalloc path filters."""
from __future__ import annotations

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_PROFILER_UPDATED
from .profiler import ProfilerManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the tracemalloc snapshot directory filter."""
    manager: ProfilerManager = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [TracemallocIncludeText(manager, entry), TracemallocExcludeText(manager, entry)]
    )


class TracemallocIncludeText(TextEntity):
    """Controls which Python source directory is included in tracemalloc snapshots."""

    def __init__(self, manager: ProfilerManager, entry: ConfigEntry) -> None:
        self._manager = manager
        self._attr_name = "memspy_tracemalloc_include"
        self._attr_unique_id = f"{entry.entry_id}_tracemalloc_include"
        self._attr_native_value = manager.snapshot_filter
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)}, name="Memspy"
        )

    @property
    def native_value(self) -> str:
        return self._manager.snapshot_filter

    @property
    def icon(self) -> str:
        return "mdi:folder-search"

    async def async_set_value(self, value: str) -> None:
        """Persist the snapshot filter and refresh snapshots if needed."""
        self._manager.set_snapshot_filter(value)
        self._manager.notify_refresh_listeners()
        self.async_write_ha_state()


class TracemallocExcludeText(TextEntity):
    """Controls newline-separated native tracemalloc exclusion patterns."""

    _attr_native_max = 255

    def __init__(self, manager: ProfilerManager, entry: ConfigEntry) -> None:
        self._manager = manager
        self._attr_name = "memspy_tracemalloc_exclude"
        self._attr_unique_id = f"{entry.entry_id}_tracemalloc_exclude"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)}, name="Memspy"
        )

    @property
    def native_value(self) -> str:
        return "\n".join(self._manager.snapshot_exclusions)

    @property
    def icon(self) -> str:
        return "mdi:filter-off-outline"

    async def async_set_value(self, value: str) -> None:
        """Persist exclusion patterns for future tracemalloc snapshots."""
        self._manager.set_snapshot_exclusions(value)
        self.async_write_ha_state()
