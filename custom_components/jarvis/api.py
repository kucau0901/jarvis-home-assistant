"""Jarvis's two endpoints for this integration (Jarvis's docs/api.md, "The house")."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import aiohttp

from .const import TIMEOUT_SECONDS


class JarvisAuthError(Exception):
    """The token was refused: wrong, revoked, without the home scope, or not the owner's."""


class JarvisNoHouse(Exception):
    """Jarvis has no Home Assistant set up to watch."""


class JarvisUnreachable(Exception):
    """Jarvis could not be reached, or answered with an error."""


@dataclass
class WatchList:
    version: str
    entities: list[str]
    urgent: set[str]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


async def _call(session: aiohttp.ClientSession, method: str, url: str, token: str, body: dict | None = None) -> dict:
    try:
        async with session.request(method, url, headers=_headers(token), json=body, timeout=aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)) as res:
            if res.status in (401, 403):
                raise JarvisAuthError(await res.text())
            if res.status == 404:
                raise JarvisNoHouse(await res.text())
            if res.status >= 400:
                raise JarvisUnreachable(f"{res.status}: {(await res.text())[:200]}")
            return await res.json()
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        raise JarvisUnreachable(str(e)) from e


async def get_watch(session: aiohttp.ClientSession, base: str, token: str) -> WatchList:
    """What Jarvis watches, and which of it to send at once."""
    data = await _call(session, "GET", f"{base}/api/v1/house/watch", token)
    return WatchList(
        version=str(data.get("version", "")),
        entities=[e for e in data.get("entities", []) if isinstance(e, str)],
        urgent={e for e in data.get("urgent", []) if isinstance(e, str)},
    )


async def post_events(session: aiohttp.ClientSession, base: str, token: str, changes: list[dict[str, str]]) -> str:
    """Send a batch; the watch list's version, to ask again when it moved."""
    data = await _call(session, "POST", f"{base}/api/v1/house/events", token, {"changes": changes})
    return str(data.get("version", ""))
