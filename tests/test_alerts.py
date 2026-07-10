"""Tests for reading and writing the consumption alert settings."""

from __future__ import annotations

import pytest

from tests.conftest import ALERTS_OK
from veolia_api.exceptions import VeoliaAPIGetDataError, VeoliaAPISetDataError
from veolia_api.model import AlertSettings

ALERTES_URL = r"/alertes/PDS1$"


async def test_get_alerts_settings_parses_response(logged_in_api, mock_session):
    mock_session.add("GET", ALERTES_URL, status=200, payload=ALERTS_OK)

    settings = await logged_in_api.get_alerts_settings()

    assert settings.daily_enabled is True
    assert settings.daily_threshold == 100
    assert settings.daily_notif_email is True
    assert settings.daily_notif_sms is True
    assert settings.monthly_enabled is True
    assert settings.monthly_threshold == 5
    assert settings.monthly_notif_email is True
    assert settings.monthly_notif_sms is False


async def test_get_alerts_settings_204_returns_disabled_defaults(
    logged_in_api,
    mock_session,
):
    mock_session.add("GET", ALERTES_URL, status=204)

    settings = await logged_in_api.get_alerts_settings()

    assert settings.daily_enabled is False
    assert settings.daily_threshold == 0
    assert settings.daily_notif_email is False
    assert settings.daily_notif_sms is False
    assert settings.monthly_enabled is False
    assert settings.monthly_threshold == 0
    assert settings.monthly_notif_email is False
    assert settings.monthly_notif_sms is False


async def test_get_alerts_settings_error_raises(logged_in_api, mock_session):
    mock_session.add("GET", ALERTES_URL, status=500)

    with pytest.raises(VeoliaAPIGetDataError):
        await logged_in_api.get_alerts_settings()


async def test_set_alerts_settings_success(logged_in_api, mock_session):
    mock_session.add("POST", ALERTES_URL, status=204)
    settings = AlertSettings(
        daily_enabled=True,
        daily_threshold=150,
        daily_notif_email=True,
        daily_notif_sms=False,
        monthly_enabled=False,
        monthly_threshold=0,
        monthly_notif_email=False,
        monthly_notif_sms=False,
    )

    result = await logged_in_api.set_alerts_settings(settings)

    assert result is True
    body = mock_session.calls_matching("/alertes/PDS1")[0][2]["json"]
    assert body["alerte_journaliere"]["seuil"] == 150
    assert "alerte_mensuelle" not in body
    assert body["abo_id"] == "123"


async def test_missing_moyen_contact_defaults_false(logged_in_api, mock_session):
    payload = {"seuils": {"journalier": {"valeur": 100, "unite": "L"}}}
    mock_session.add("GET", ALERTES_URL, status=200, payload=payload)

    settings = await logged_in_api.get_alerts_settings()

    assert settings.daily_enabled is True
    assert settings.daily_threshold == 100
    assert settings.daily_notif_email is False
    assert settings.daily_notif_sms is False


async def test_missing_valeur_defaults_zero(logged_in_api, mock_session):
    payload = {"seuils": {"journalier": {"moyen_contact": {}}}}
    mock_session.add("GET", ALERTES_URL, status=200, payload=payload)

    settings = await logged_in_api.get_alerts_settings()

    assert settings.daily_threshold == 0


async def test_set_alerts_settings_failure_raises(logged_in_api, mock_session):
    mock_session.add("POST", ALERTES_URL, status=400)
    settings = AlertSettings(
        daily_enabled=True,
        daily_threshold=150,
        daily_notif_email=True,
        daily_notif_sms=False,
        monthly_enabled=False,
        monthly_threshold=0,
        monthly_notif_email=False,
        monthly_notif_sms=False,
    )

    with pytest.raises(VeoliaAPISetDataError):
        await logged_in_api.set_alerts_settings(settings)
