"""Tests for client construction and pre-network credential validation."""

from __future__ import annotations

import pytest

from veolia_api import VeoliaAPI
from veolia_api.exceptions import VeoliaAPIInvalidCredentialsError
from veolia_api.portals import VEOLIA_PORTALS


def test_constructor_unknown_portal_raises():
    with pytest.raises(ValueError, match="Unknown Veolia portal"):
        VeoliaAPI("alice@example.test", "pw", portal_url="nope.example")


async def test_constructor_resolves_default_portal():
    api = VeoliaAPI("alice@example.test", "pw")
    try:
        assert api._client_id == VEOLIA_PORTALS["eau.veolia.fr"].client_id
    finally:
        await api.close()


async def test_login_missing_password_raises():
    api = VeoliaAPI("alice@example.test", "")
    try:
        with pytest.raises(VeoliaAPIInvalidCredentialsError):
            await api.login()
    finally:
        await api.close()


async def test_login_invalid_email_raises():
    api = VeoliaAPI("not-an-email", "pw")
    try:
        with pytest.raises(VeoliaAPIInvalidCredentialsError):
            await api.login()
    finally:
        await api.close()


def test_constructor_works_outside_event_loop():
    api = VeoliaAPI("alice@example.test", "pw")
    assert api._session is None


async def test_close_is_idempotent():
    api = VeoliaAPI("alice@example.test", "pw")
    await api.close()
    await api.close()
    assert api._session is None


async def test_close_closes_owned_session():
    api = VeoliaAPI("alice@example.test", "pw")
    session = api.session  # triggers lazy creation inside the running loop
    await api.close()
    assert session.closed


async def test_close_does_not_close_injected_session(mock_session):
    api = VeoliaAPI("alice@example.test", "pw", session=mock_session)
    await api.close()
    assert mock_session.closed is False


async def test_close_then_reuse_creates_fresh_session():
    api = VeoliaAPI("alice@example.test", "pw")
    api.session  # noqa: B018 - triggers lazy creation inside the running loop
    await api.close()
    assert api._session is None

    new_session = api.session  # triggers a fresh lazy creation
    assert new_session.closed is False

    await api.close()
