"""The Prolog integration."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    DOMAIN,
    SIGNAL_REFRESH_CONFIG,
)
from .helpers import async_refresh_manager
from .profiler import ProfilerManager

PLATFORMS = ["sensor", "number", "text", "switch"]
_LOGGER = logging.getLogger(__name__)


def _cleanup_legacy_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Migrate renamed text entities and remove obsolete binary sensors."""
    registry = er.async_get(hass)
    legacy_text_entities = {
        "snapshot_filter": "tracemalloc_include",
        "snapshot_exclusions": "tracemalloc_exclude",
    }
    for old_name, new_name in legacy_text_entities.items():
        old_unique_id = f"{entry.entry_id}_{old_name}"
        old_entity_id = registry.async_get_entity_id("text", DOMAIN, old_unique_id)
        if old_entity_id is None:
            continue
        new_unique_id = f"{entry.entry_id}_{new_name}"
        new_entity_id = registry.async_get_entity_id("text", DOMAIN, new_unique_id)
        target_entity_id = f"text.prolog_{new_name}"
        if new_entity_id is None and registry.async_get(target_entity_id) is None:
            registry.async_update_entity(
                old_entity_id,
                new_entity_id=target_entity_id,
                new_unique_id=new_unique_id,
            )
        else:
            registry.async_remove(old_entity_id)

    old_binary_unique_id = f"{entry.entry_id}_tracemalloc_active"
    old_binary_entity_id = registry.async_get_entity_id(
        "binary_sensor", DOMAIN, old_binary_unique_id
    )
    if old_binary_entity_id is not None:
        registry.async_remove(old_binary_entity_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Prolog from a config entry."""
    manager = ProfilerManager()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = manager
    refresh_unsub = None

    async def refresh() -> None:
        await async_refresh_manager(hass, manager)

    async def handle_interval(_now) -> None:
        """Refresh sensors when the configured interval elapses."""
        _LOGGER.debug("Refreshing Prolog sensors on the configured interval")
        await refresh()

    @callback
    def configure_refresh() -> None:
        nonlocal refresh_unsub
        if refresh_unsub:
            refresh_unsub()
            refresh_unsub = None
        if manager.memory_scanning:
            refresh_unsub = async_track_time_interval(
                hass,
                handle_interval,
                timedelta(seconds=manager.refresh_frequency),
            )
        manager._refresh_unsub = refresh_unsub

    config_unsub = async_dispatcher_connect(
        hass, SIGNAL_REFRESH_CONFIG, configure_refresh
    )
    manager._config_unsub = config_unsub
    configure_refresh()
    _cleanup_legacy_entities(hass, entry)
    await refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        manager = hass.data[DOMAIN].pop(entry.entry_id, None)
        config_unsub = getattr(manager, "_config_unsub", None)
        if config_unsub:
            config_unsub()
        refresh_unsub = getattr(manager, "_refresh_unsub", None)
        if refresh_unsub:
            refresh_unsub()
    return unload_ok
