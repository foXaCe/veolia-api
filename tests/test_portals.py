"""Tests for portal resolution."""

from __future__ import annotations

import pytest

from veolia_api.portals import (
    DEFAULT_BACKEND_URL,
    VEOLIA_PORTAL_CLIENTS,
    VEOLIA_PORTALS,
    VeoliaPortal,
    get_portal,
)


def test_default_portal_uses_default_backend():
    portal = get_portal(None)
    assert portal.backend_url == DEFAULT_BACKEND_URL
    assert portal.client_id == VEOLIA_PORTALS["eau.veolia.fr"].client_id


def test_get_portal_explicit_backend():
    portal = get_portal("www.ea-pm.fr")
    assert portal.backend_url == "https://prd-ael-sirius-pmm-backend.istefr.fr"


def test_get_portal_unknown_raises():
    with pytest.raises(ValueError, match="Unknown Veolia portal"):
        get_portal("nope.example")


def test_portal_clients_mapping_matches_portals():
    assert set(VEOLIA_PORTAL_CLIENTS) == set(VEOLIA_PORTALS)
    for host, client_id in VEOLIA_PORTAL_CLIENTS.items():
        assert client_id == VEOLIA_PORTALS[host].client_id


def test_portal_defaults_to_default_backend():
    portal = VeoliaPortal(client_id="abc")
    assert portal.backend_url == DEFAULT_BACKEND_URL
