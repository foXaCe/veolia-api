"""Commune-based portal discovery for the Veolia water portals."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any
from urllib.parse import urlsplit

import aiohttp

from .constants import REFCOMMUNES_URL, TIMEOUT
from .exceptions import (
    VeoliaAPIConnectionError,
    VeoliaAPIGetDataError,
    VeoliaAPIResponseError,
)
from .portals import DEFAULT_PORTAL_URL


def _select_portal(commune: str, entries: list[dict[str, Any]]) -> str:
    """Pick the single portal hostname the commune entries resolve to.

    Raises:
        VeoliaAPIResponseError: commune not served, portal under
            maintenance, or several distinct portals match.

    """
    candidates: set[str] = set()
    statuses: set[str | None] = set()
    for entry in entries:
        status = entry.get("type_commune")
        statuses.add(status)
        if status == "REDIRIGE":
            hostname = urlsplit(entry.get("url_redirection") or "").hostname
            if hostname:
                candidates.add(hostname)
        elif status == "NON_REDIRIGE":
            candidates.add(DEFAULT_PORTAL_URL)

    if not candidates:
        if "EN_MAINTENANCE" in statuses:
            raise VeoliaAPIResponseError(
                f"Portal for {commune!r} is under maintenance",
            )
        raise VeoliaAPIResponseError(f"Commune {commune!r} is not served by Veolia")
    if len(candidates) > 1:
        raise VeoliaAPIResponseError(
            f"Several portals match {commune!r}: {sorted(candidates)}. "
            "Pick one and pass it as portal_url.",
        )
    return candidates.pop()


async def resolve_portal_url(
    commune: str,
    session: aiohttp.ClientSession | None = None,
) -> str:
    """Resolve a commune name to its Veolia portal hostname.

    Queries the public commune-reference API. ``REDIRIGE`` entries resolve
    to the hostname of their ``url_redirection``; ``NON_REDIRIGE`` entries
    resolve to the national portal. The returned hostname plugs directly
    into ``VeoliaAPI(portal_url=...)``.

    Raises:
        VeoliaAPIResponseError: no match, commune not served by Veolia,
            portal under maintenance, or several distinct portals match
            (candidates are listed in the message).
        VeoliaAPIGetDataError: the reference API answered a non-200 status.
        VeoliaAPIConnectionError: network-level failure.

    """
    if session is None:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=TIMEOUT),
        ) as own_session:
            return await resolve_portal_url(commune, own_session)

    url = f"{REFCOMMUNES_URL}/communes-nationales"
    try:
        response = await session.request("GET", url, params={"q": commune})
    except (aiohttp.ClientError, TimeoutError) as err:
        raise VeoliaAPIConnectionError(
            f"Network error calling {url}: {err}",
        ) from err

    if response.status != HTTPStatus.OK:
        response.release()
        raise VeoliaAPIGetDataError(
            f"call to= communes-nationales failed with http status= {response.status}",
        )

    entries = await response.json(content_type=None)
    if not entries:
        raise VeoliaAPIResponseError(f"No commune matching {commune!r}")

    return _select_portal(commune, entries)
