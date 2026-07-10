"""Tests for module-level constants."""

from __future__ import annotations

from veolia_api.constants import (
    BACKEND_ISTEFR,
    LOGIN_CLIENT_ID,
    TOKEN_EXPIRY_MARGIN,
    ConsumptionType,
)
from veolia_api.portals import DEFAULT_BACKEND_URL, VEOLIA_PORTALS


def test_consumption_type_values():
    assert ConsumptionType.MONTHLY.value == "monthly"
    assert ConsumptionType.YEARLY.value == "yearly"


def test_backend_istefr_is_default_backend():
    assert BACKEND_ISTEFR == DEFAULT_BACKEND_URL


def test_login_client_id_matches_default_portal():
    assert VEOLIA_PORTALS["eau.veolia.fr"].client_id == LOGIN_CLIENT_ID


def test_token_expiry_margin_is_positive():
    assert TOKEN_EXPIRY_MARGIN > 0
