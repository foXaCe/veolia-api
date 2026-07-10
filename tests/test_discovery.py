"""Tests for commune-based portal discovery (resolve_portal_url)."""

from __future__ import annotations

import aiohttp
import pytest

from veolia_api import resolve_portal_url
from veolia_api.exceptions import (
    VeoliaAPIConnectionError,
    VeoliaAPIGetDataError,
    VeoliaAPIResponseError,
)

COMMUNES_URL = r"/communes-nationales$"

PERPIGNAN_ENTRIES = [
    {
        "numero_commune": 38970,
        "numero_quartier": 0,
        "libelle": "PERPIGNAN",
        "code_insee": "66136",
        "code_postal": "66000",
        "url_redirection": "https://www.ea-pm.fr?numero_commune=38970&numero_quartier=0",
        "type_commune": "REDIRIGE",
    },
    {
        "numero_commune": 38970,
        "numero_quartier": 0,
        "libelle": "PERPIGNAN",
        "code_insee": "66136",
        "code_postal": "66100",
        "url_redirection": "https://www.ea-pm.fr?numero_commune=38970&numero_quartier=0",
        "type_commune": "REDIRIGE",
    },
]


class RaisingSession:
    """Session stand-in whose request() always raises the given exception."""

    closed = False

    def __init__(self, exc):
        self._exc = exc

    async def request(self, method, url, **kwargs):  # noqa: ARG002
        raise self._exc


async def test_redirige_resolves_to_portal_hostname(mock_session):
    mock_session.add("GET", COMMUNES_URL, status=200, payload=PERPIGNAN_ENTRIES)

    portal = await resolve_portal_url("Perpignan", session=mock_session)

    assert portal == "www.ea-pm.fr"


async def test_non_redirige_resolves_to_national_portal(mock_session):
    payload = [
        {
            "numero_commune": 26479,
            "numero_quartier": 0,
            "libelle": "DEVILLE LES ROUEN",
            "code_insee": "76216",
            "code_postal": "76250",
            "type_commune": "NON_REDIRIGE",
        },
    ]
    mock_session.add("GET", COMMUNES_URL, status=200, payload=payload)

    portal = await resolve_portal_url("Deville les Rouen", session=mock_session)

    assert portal == "eau.veolia.fr"


async def test_mixed_quartiers_raise_with_candidates(mock_session):
    payload = [
        {
            "libelle": "TOULOUSE",
            "type_commune": "REDIRIGE",
            "url_redirection": "https://eaudetm.monespace.eau.veolia.fr?numero_commune=26219",
        },
        {
            "libelle": "TOULOUSE (AVENUE DES ETATS UNIS)",
            "type_commune": "NON_REDIRIGE",
        },
    ]
    mock_session.add("GET", COMMUNES_URL, status=200, payload=payload)

    with pytest.raises(VeoliaAPIResponseError) as err:
        await resolve_portal_url("Toulouse", session=mock_session)

    assert "eaudetm.monespace.eau.veolia.fr" in str(err.value)
    assert "eau.veolia.fr" in str(err.value)


async def test_not_served_raises(mock_session):
    payload = [{"libelle": "ROUEN", "type_commune": "NON_DESSERVIE"}]
    mock_session.add("GET", COMMUNES_URL, status=200, payload=payload)

    with pytest.raises(VeoliaAPIResponseError, match="not served"):
        await resolve_portal_url("Rouen", session=mock_session)


async def test_maintenance_raises(mock_session):
    payload = [{"libelle": "SOMEWHERE", "type_commune": "EN_MAINTENANCE"}]
    mock_session.add("GET", COMMUNES_URL, status=200, payload=payload)

    with pytest.raises(VeoliaAPIResponseError, match="maintenance"):
        await resolve_portal_url("Somewhere", session=mock_session)


async def test_no_match_raises(mock_session):
    mock_session.add("GET", COMMUNES_URL, status=200, payload=[])

    with pytest.raises(VeoliaAPIResponseError):
        await resolve_portal_url("Nowhere", session=mock_session)


async def test_http_error_raises_get_data_error(mock_session):
    mock_session.add("GET", COMMUNES_URL, status=500)

    with pytest.raises(VeoliaAPIGetDataError):
        await resolve_portal_url("Perpignan", session=mock_session)

    assert mock_session.served[0].released is True


async def test_network_error_wrapped():
    session = RaisingSession(aiohttp.ClientConnectionError("boom"))

    with pytest.raises(VeoliaAPIConnectionError) as err:
        await resolve_portal_url("Perpignan", session=session)

    assert isinstance(err.value.__cause__, aiohttp.ClientConnectionError)
