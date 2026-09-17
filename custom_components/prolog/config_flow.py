"""Config flow for Prolog (single-instance, no user input required)."""
from __future__ import annotations

from homeassistant import config_entries

from .const import DOMAIN


class PrologConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Prolog."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None):
        """Handle the initial step."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(title="Prolog", data={})

        return self.async_show_form(step_id="user")
