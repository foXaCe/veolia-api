"""Tests for the dataclass models."""

from __future__ import annotations

from veolia_api.model import AlertSettings, VeoliaAccountData


def test_account_data_defaults():
    data = VeoliaAccountData()
    assert data.access_token is None
    assert data.token_expiration == 0
    assert data.monthly_consumption is None
    assert data.daily_consumption is None
    assert data.alert_settings is None
    assert data.billing_plan is None


def test_alert_settings_fields():
    settings = AlertSettings(
        daily_enabled=True,
        daily_threshold=100,
        daily_notif_email=True,
        daily_notif_sms=False,
        monthly_enabled=False,
        monthly_threshold=5,
        monthly_notif_email=True,
        monthly_notif_sms=False,
    )
    assert settings.daily_enabled is True
    assert settings.daily_threshold == 100
    assert settings.monthly_threshold == 5
    assert settings.monthly_notif_sms is False
