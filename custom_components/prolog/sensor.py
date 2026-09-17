"""Sensors exposing garbage-collected object statistics."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
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
    entities: dict[str, ObjectSensor] = {}

    def add_supported_entities() -> None:
        new_entities = [
            ObjectSensor(manager, entry, class_name)
            for class_name in manager.class_names
            if class_name not in entities
        ]
        entities.update({entity.class_name: entity for entity in new_entities})
        if new_entities:
            async_add_entities(new_entities)

    manager.add_refresh_listener(add_supported_entities)
    async_add_entities(
        []
    )
    add_supported_entities()


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
    """Reports memory usage and object count for one Python object class."""

    _attr_device_class = SensorDeviceClass.DATA_SIZE
    _attr_icon = "mdi:memory"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "B"

    def __init__(
        self, manager: ProfilerManager, entry: ConfigEntry, class_name: str
    ) -> None:
        super().__init__(manager, entry)
        self._class_name = class_name
        self._attr_name = f"prolog_{class_name}"
        self._attr_unique_id = f"{entry.entry_id}_{class_name}"

    @property
    def class_name(self) -> str:
        """Return the Python class represented by this sensor."""
        return self._class_name

    @property
    def native_value(self) -> int | None:
        report = self._manager.last_report
        if not report or self._class_name not in self._manager.supported_class_names:
            return None
        return report["memory_counts"].get(self._class_name)

    @property
    def available(self) -> bool:
        """Only expose classes within the configured memory range."""
        return self._class_name in self._manager.supported_class_names

    @property
    def extra_state_attributes(self) -> dict:
        report = self._manager.last_report
        if not report:
            return {}
        return {
            "count": report["object_counts"].get(self._class_name, 0),
            "gc_stats": report["gc_stats"],
        }
