"""Sensors exposing garbage-collected object statistics."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_PROFILER_UPDATED
from .profiler import ProfilerManager


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Prolog sensors from a config entry."""
    manager: ProfilerManager = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [ObjectSensor(manager, entry, class_name) for class_name in manager.class_names]
    )


class _PrologEntity(SensorEntity):
    """Base entity that refreshes whenever a snapshot is collected."""

    _attr_should_poll = False

    def __init__(self, manager: ProfilerManager, entry: ConfigEntry) -> None:
        self._manager = manager
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


class ObjectSensor(_PrologEntity):
    """Reports the count and memory estimate for one Python object class."""

    _attr_icon = "mdi:counter"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "objects"

    def __init__(
        self, manager: ProfilerManager, entry: ConfigEntry, class_name: str
    ) -> None:
        super().__init__(manager, entry)
        self._class_name = class_name
        self._attr_name = f"prolog_{class_name}"
        self._attr_unique_id = f"{entry.entry_id}_{class_name}"

    @property
    def native_value(self) -> int | None:
        report = self._manager.last_report
        return report["object_counts"].get(self._class_name) if report else None

    @property
    def extra_state_attributes(self) -> dict:
        report = self._manager.last_report
        if not report:
            return {}
        return {"memory": report["memory_counts"].get(self._class_name, 0)}
