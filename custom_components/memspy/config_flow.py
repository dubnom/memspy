"""Config flow for Memspy."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
    CONF_DASHBOARD_AUTO_INSTALL,
    CONF_MACHINE_MEMORY_GB,
    DOMAIN,
)
from .profiler import detect_machine_memory_gb


class MemspyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Memspy."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry):
        return MemspyOptionsFlow()

    async def async_step_user(self, user_input: dict | None = None):
        """Handle the initial step."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(title="Memspy", data={})

        return self.async_show_form(step_id="user")


class MemspyOptionsFlow(config_entries.OptionsFlow):
    """Configure MemSpy runtime and dashboard behavior."""

    async def async_step_init(self, user_input: dict | None = None):
        """Handle options form submission."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_MACHINE_MEMORY_GB,
                    default=current.get(
                        CONF_MACHINE_MEMORY_GB, detect_machine_memory_gb()
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.1,
                        max=2**20,
                        step=0.1,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_DASHBOARD_AUTO_INSTALL,
                    default=current.get(CONF_DASHBOARD_AUTO_INSTALL, False),
                ): selector.BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
