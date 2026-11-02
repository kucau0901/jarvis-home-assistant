"""Jarvis: tells Jarvis what changes in the house, as it happens.

Jarvis decides what is worth watching and what to do about it; this integration only listens and passes
changes on (watcher.py). It adds no entities.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_TOKEN, CONF_URL
from .watcher import Watcher

type JarvisConfigEntry = ConfigEntry[Watcher]


async def async_setup_entry(hass: HomeAssistant, entry: JarvisConfigEntry) -> bool:
    watcher = Watcher(hass, entry.data[CONF_URL], entry.data[CONF_TOKEN], async_get_clientsession(hass))
    await watcher.async_start()
    entry.runtime_data = watcher
    return True


async def async_unload_entry(hass: HomeAssistant, entry: JarvisConfigEntry) -> bool:
    await entry.runtime_data.async_stop()
    return True
