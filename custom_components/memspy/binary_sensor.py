"""Binary sensors for MemSpy."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_DASHBOARD_UPDATED
from .dashboard import async_dashboard_out_of_date


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the dashboard status binary sensor."""
    async_add_entities([DashboardOutOfDateBinarySensor(entry)])


class DashboardOutOfDateBinarySensor(BinarySensorEntity):
    """Indicate that the dedicated MemSpy dashboard needs installation or upgrade."""

    _attr_should_poll = False
    _attr_device_class = BinarySensorDeviceClass.UPDATE

    def __init__(self, entry: ConfigEntry) -> None:
        self._attr_name = "dashboard_out_of_date"
        self._attr_unique_id = f"{entry.entry_id}_dashboard_out_of_date"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)}, name="Memspy"
        )
        self._is_on = True

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_DASHBOARD_UPDATED, self._handle_dashboard_update
            )
        )
        await self._async_update_state()

    async def _async_update_state(self) -> None:
        self._is_on = await async_dashboard_out_of_date(self.hass)
        self.async_write_ha_state()

    @callback
    def _handle_dashboard_update(self, _data: dict[str, str]) -> None:
        self.hass.async_create_task(self._async_update_state())

    @property
    def is_on(self) -> bool:
        return self._is_on