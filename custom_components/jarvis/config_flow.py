"""Setting up Jarvis: its address, and a device token made in Jarvis with the home scope."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import JarvisAuthError, JarvisNoHouse, JarvisUnreachable, get_watch
from .const import CONF_TOKEN, CONF_URL, DOMAIN

SCHEMA = vol.Schema({vol.Required(CONF_URL): str, vol.Required(CONF_TOKEN): str})


class JarvisConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            base = user_input[CONF_URL].strip().rstrip("/")
            token = user_input[CONF_TOKEN].strip()
            try:
                # Tried before it is kept: a wrong token is better said now than found out never to send.
                await get_watch(async_get_clientsession(self.hass), base, token)
            except JarvisAuthError:
                errors["base"] = "invalid_auth"
            except JarvisNoHouse:
                errors["base"] = "no_house"
            except JarvisUnreachable:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(base)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Jarvis", data={CONF_URL: base, CONF_TOKEN: token})
        return self.async_show_form(step_id="user", data_schema=SCHEMA, errors=errors)
