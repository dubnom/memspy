"""Button entities for MemSpy."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SERVICE_INSTALL_DASHBOARD


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the MemSpy dashboard install button."""
    async_add_entities([InstallDashboardButton(entry, DOMAIN)])


class InstallDashboardButton(ButtonEntity):
    """Expose a UI button that installs or refreshes the MemSpy dashboard view."""

    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, domain: str) -> None:
        self._attr_name = "Install or Upgrade"
        self._attr_unique_id = f"{entry.entry_id}_install_dashboard"
        self._attr_device_info = DeviceInfo(
            identifiers={(domain, entry.entry_id)}, name="Memspy"
        )

    async def async_press(self) -> None:
        """Install or upgrade the MemSpy view on its dedicated dashboard."""
        await self.hass.services.async_call(
            DOMAIN,
            SERVICE_INSTALL_DASHBOARD,
            blocking=True,
            return_response=True,
        )
