"""Listening to the house for Jarvis: what it watches, as it changes, sent in batches (batch.py)."""

from __future__ import annotations

import logging
import time
from datetime import timedelta

import aiohttp

from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval

from .api import JarvisAuthError, JarvisNoHouse, JarvisUnreachable, get_watch, post_events
from .batch import Batcher
from .const import REFRESH_SECONDS, TICK_SECONDS

_LOGGER = logging.getLogger(__name__)
# Home Assistant starting, or a device dropping off: not a change in the house.
NOISE = {"unavailable", "unknown"}


class Watcher:
    def __init__(self, hass: HomeAssistant, base: str, token: str, session: aiohttp.ClientSession) -> None:
        self._hass = hass
        self._base = base
        self._token = token
        self._session = session
        self._batch = Batcher()
        self._version = ""
        self._urgent: set[str] = set()
        self._entities: list[str] = []
        self._unsub_state = None
        self._unsub_tick = None
        self._refreshed = 0.0
        self._sending = False

    async def async_start(self) -> None:
        await self._refresh()
        self._unsub_tick = async_track_time_interval(self._hass, self._tick, timedelta(seconds=TICK_SECONDS))

    async def async_stop(self) -> None:
        if self._unsub_tick:
            self._unsub_tick()
        if self._unsub_state:
            self._unsub_state()
        # What is waiting goes now rather than never.
        if self._batch.waiting():
            await self._send()

    async def _refresh(self) -> None:
        """Ask Jarvis what to watch, and listen to exactly that."""
        try:
            w = await get_watch(self._session, self._base, self._token)
        except (JarvisAuthError, JarvisNoHouse, JarvisUnreachable) as e:
            _LOGGER.warning("Jarvis: could not get the watch list: %s", e)
            self._refreshed = time.monotonic() - REFRESH_SECONDS + 60  # try again in a minute
            return
        self._refreshed = time.monotonic()
        self._version = w.version
        self._urgent = w.urgent
        if w.entities != self._entities:
            self._entities = w.entities
            if self._unsub_state:
                self._unsub_state()
            self._unsub_state = async_track_state_change_event(self._hass, self._entities, self._on_change)
            _LOGGER.info("Jarvis: watching %d things, %d of them urgent", len(self._entities), len(self._urgent))

    @callback
    def _on_change(self, event: Event[EventStateChangedData]) -> None:
        old = event.data["old_state"]
        new = event.data["new_state"]
        # Added or removed, an attribute alone, or Home Assistant starting: nothing for Jarvis.
        if old is None or new is None or old.state == new.state or new.state in NOISE or old.state in NOISE:
            return
        entity = event.data["entity_id"]
        self._batch.add(entity, old.state, new.state, urgent=entity in self._urgent, now=time.monotonic())

    async def _tick(self, _now=None) -> None:
        if self._batch.due(time.monotonic()):
            await self._send()
        if time.monotonic() - self._refreshed >= REFRESH_SECONDS:
            await self._refresh()

    async def _send(self) -> None:
        if self._sending:
            return
        self._sending = True
        try:
            changes = self._batch.take(time.monotonic())
            if not changes:
                return
            try:
                version = await post_events(self._session, self._base, self._token, changes)
            except (JarvisAuthError, JarvisNoHouse, JarvisUnreachable) as e:
                self._batch.failed(changes, time.monotonic())
                _LOGGER.warning("Jarvis: %d changes not sent, will try again: %s", len(changes), e)
                return
            self._batch.succeeded()
            if version and version != self._version:
                await self._refresh()
        finally:
            self._sending = False
