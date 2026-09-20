"""Sensors exposing the highest-memory garbage-collected object classes."""
from __future__ import annotations

import json

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
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
    entities: dict[int, ObjectSensor] = {}
    registry = er.async_get(hass)
    current_class_count = len(manager.class_names)

    for rank, class_name in enumerate(manager.class_names, start=1):
        old_unique_id = f"{entry.entry_id}_{class_name}"
        new_unique_id = f"{entry.entry_id}_class_{rank:03d}"
        entity_id = registry.async_get_entity_id("sensor", DOMAIN, old_unique_id)
        if entity_id:
            target_entity_id = f"sensor.class_{rank:03d}"
            target_unique_id = registry.async_get_entity_id(
                "sensor", DOMAIN, new_unique_id
            )
            if target_unique_id is None or target_unique_id == entity_id:
                registry.async_update_entity(
                    entity_id,
                    new_entity_id=target_entity_id,
                    new_unique_id=new_unique_id,
                )

    for entity in list(registry.entities.values()):
        if entity.config_entry_id != entry.entry_id or entity.domain != "sensor":
            continue
        if entity.unique_id.startswith(f"{entry.entry_id}_class_"):
            try:
                rank = int(entity.unique_id.rsplit("_", 1)[-1])
            except ValueError:
                continue
            if rank > current_class_count:
                registry.async_remove(entity.entity_id)
        elif entity.unique_id.startswith(f"{entry.entry_id}_") and entity.unique_id not in {
            f"{entry.entry_id}_summary",
            f"{entry.entry_id}_tracemalloc",
        }:
            registry.async_remove(entity.entity_id)

    def add_supported_entities() -> None:
        new_entities = [
            ObjectSensor(manager, entry, rank)
            for rank in range(1, len(manager.class_names) + 1)
            if rank not in entities
        ]
        entities.update({entity.rank: entity for entity in new_entities})
        for entity in entities.values():
            class_name = entity.class_name
            if class_name is None:
                continue
            entity_id = registry.async_get_entity_id(
                "sensor", DOMAIN, entity.unique_id
            )
            if entity_id is not None:
                registry.async_update_entity(entity_id, name=class_name)
        if new_entities:
            async_add_entities(new_entities)

    manager.add_refresh_listener(add_supported_entities)
    async_add_entities([])
    add_supported_entities()
    async_add_entities(
        [
            SummarySensor(manager, entry),
            TracemallocSensor(manager, entry),
            TracemallocDurationSensor(manager, entry),
        ]
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


class SummarySensor(_PrologEntity):
    """Reports global GC statistics independent of any one object class."""

    _attr_icon = "mdi:chart-box-outline"
    _attr_should_poll = False

    def __init__(self, manager: ProfilerManager, entry: ConfigEntry) -> None:
        super().__init__(manager, entry)
        self._attr_name = "prolog"
        self._attr_unique_id = f"{entry.entry_id}_summary"

    @property
    def native_value(self) -> int | None:
        report = self._manager.last_report
        if not report:
            return None
        return report["summary"]["object_count"]

    @property
    def extra_state_attributes(self) -> dict:
        report = self._manager.last_report
        if not report:
            return {}
        return {
            "memory": report["summary"]["memory"],
            "object_count": report["summary"]["object_count"],
            "garbage": report.get("garbage", 0),
            "collections": report.get("collections", 0),
            "collected": report.get("collected", 0),
            "uncollectable": report.get("uncollectable", 0),
            "gc_stats": report["gc_stats"],
        }


class TracemallocSensor(_PrologEntity):
    """Stores the most recent tracemalloc snapshot result."""

    _attr_icon = "mdi:memory"

    def __init__(self, manager: ProfilerManager, entry: ConfigEntry) -> None:
        super().__init__(manager, entry)
        self._attr_name = "prolog_tracemalloc"
        self._attr_unique_id = f"{entry.entry_id}_tracemalloc"

    @property
    def native_value(self) -> int | None:
        snapshot = self._manager.last_tracemalloc_snapshot
        if not snapshot:
            return None
        return len(snapshot)

    @property
    def extra_state_attributes(self) -> dict:
        snapshot = self._manager.last_tracemalloc_snapshot
        if not snapshot:
            return {"json": 0, "snapshot": "[]"}
        return {"json": len(snapshot), "snapshot": json.dumps(snapshot)}


class TracemallocDurationSensor(_PrologEntity):
    """Reports the duration of the current or most recent tracemalloc session."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_icon = "mdi:timer-outline"
    _attr_native_unit_of_measurement = "s"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, manager: ProfilerManager, entry: ConfigEntry) -> None:
        super().__init__(manager, entry)
        self._attr_name = "prolog_tracemalloc_duration"
        self._attr_unique_id = f"{entry.entry_id}_tracemalloc_duration"

    @property
    def native_value(self) -> float:
        return self._manager.tracemalloc_elapsed


class ObjectSensor(_PrologEntity):
    """Reports memory usage and object count for one Python object class."""

    _attr_has_entity_name = False
    _attr_device_class = SensorDeviceClass.DATA_SIZE
    _attr_icon = "mdi:memory"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "B"

    def __init__(self, manager: ProfilerManager, entry: ConfigEntry, rank: int) -> None:
        super().__init__(manager, entry)
        self._rank = rank
        self._attr_unique_id = f"{entry.entry_id}_class_{rank:03d}"

    @property
    def suggested_object_id(self) -> str:
        """Return the stable object ID prefix for this class sensor."""
        return f"class_{self._rank:03d}"

    @property
    def name(self) -> str:
        """Return the user-facing class name without the prefix."""
        return self.class_name or f"class_{self._rank:03d}"

    @property
    def class_name(self) -> str | None:
        """Return the Python class represented by this sensor."""
        class_names = self._manager.class_names
        if self._rank > len(class_names):
            return None
        return class_names[self._rank - 1]

    @property
    def rank(self) -> int:
        """Return the memory ranking represented by this sensor."""
        return self._rank

    @property
    def native_value(self) -> int | None:
        report = self._manager.last_report
        class_name = self.class_name
        if not report or class_name is None:
            return None
        return report["memory_counts"].get(class_name)

    @property
    def available(self) -> bool:
        """Only expose ranks within the configured top-N range."""
        return self.class_name is not None

    @property
    def extra_state_attributes(self) -> dict:
        report = self._manager.last_report
        class_name = self.class_name
        if not report or class_name is None:
            return {}
        return {
            "count": report["object_counts"].get(class_name, 0),
            "memory": report["memory_counts"].get(class_name, 0),
        }
