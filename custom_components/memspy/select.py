"""Select entity for the tracemalloc include filter."""
from __future__ import annotations

from pathlib import Path

from homeassistant import loader
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .profiler import ProfilerManager

OPTION_ALL = "all"
OPTION_CUSTOM = "custom"
CUSTOM_COMPONENTS_PATH = "/config/custom_components"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the tracemalloc include selector."""
    manager: ProfilerManager = hass.data[DOMAIN][entry.entry_id]
    options: list[str] = [OPTION_ALL, OPTION_CUSTOM]
    locations: dict[str, str] = {
        OPTION_ALL: "*",
        OPTION_CUSTOM: CUSTOM_COMPONENTS_PATH,
    }
    config_entries: list[dict[str, object]] = []

    domains = sorted(
        {config_entry.domain for config_entry in hass.config_entries.async_entries()}
    )
    for domain in domains:
        try:
            integration = await loader.async_get_integration(hass, domain)
        except Exception:
            continue
        options.append(domain)
        locations[domain] = str(Path(integration.file_path))
        config_entries.extend(
            {
                "domain": domain,
                "title": config_entry.title,
                "code_location": locations[domain],
            }
            for config_entry in hass.config_entries.async_entries(domain)
        )

    async_add_entities(
        [TracemallocIncludeSelect(manager, entry, options, locations, config_entries)]
    )


class TracemallocIncludeSelect(SelectEntity):
    """Select which integration source directory tracemalloc includes."""

    _attr_icon = "mdi:folder-search"

    def __init__(
        self,
        manager: ProfilerManager,
        entry: ConfigEntry,
        options: list[str],
        locations: dict[str, str],
        config_entries: list[dict[str, object]],
    ) -> None:
        self._manager = manager
        self._locations = locations
        self._attr_options = options
        self._attr_current_option = self._option_for_filter(manager.snapshot_filter)
        self._config_entries = config_entries
        self._attr_name = "memspy_tracemalloc_include"
        self._attr_unique_id = f"{entry.entry_id}_tracemalloc_include_select"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)}, name="Memspy"
        )

    def _option_for_filter(self, snapshot_filter: str) -> str:
        for option, location in self._locations.items():
            if location == snapshot_filter:
                return option
        return OPTION_CUSTOM

    @property
    def current_option(self) -> str:
        return self._attr_current_option

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Expose configured entries and their resolved source directories."""
        return {
            "config_entries": self._config_entries,
            "code_locations": self._locations,
        }

    async def async_select_option(self, option: str) -> None:
        """Apply the selected include location."""
        self._manager.set_snapshot_filter(self._locations[option])
        self._attr_current_option = option
        self._manager.notify_refresh_listeners()
        self.async_write_ha_state()