"""Tests that credentials never leak into debug logs."""

from __future__ import annotations

import copy
import logging

from tests.conftest import ALERTS_OK
from veolia_api.veolia_api import VeoliaAPI, _redact


def test_password_param_is_redacted(caplog):
    with caplog.at_level(logging.DEBUG):
        VeoliaAPI._log_request(
            "https://example.test",
            "POST",
            {"password": "s3cret-value", "user": "alice"},
            None,
            {},
        )
    assert "s3cret-value" not in caplog.text
    assert "REDACTED" in caplog.text


def test_cognito_password_and_bearer_are_redacted(caplog):
    with caplog.at_level(logging.DEBUG):
        VeoliaAPI._log_request(
            "https://example.test",
            "POST",
            None,
            {"AuthParameters": {"USERNAME": "alice", "PASSWORD": "top-secret"}},
            {"Authorization": "Bearer abc123"},
        )
    assert "top-secret" not in caplog.text
    assert "alice" not in caplog.text
    assert "abc123" not in caplog.text
    assert "REDACTED" in caplog.text


async def test_login_body_is_never_logged(caplog, api, mock_session):
    mock_session.add("POST", r"login$", status=200, payload={})
    with caplog.at_level(logging.DEBUG):
        await api._send_request_with_retry(
            url="https://example.test/login",
            method="POST",
            login_json={
                "AuthParameters": {
                    "USERNAME": "alice@example.test",
                    "PASSWORD": "top-secret",
                },
            },
        )
    assert "top-secret" not in caplog.text
    assert "alice@example.test" not in caplog.text
    # The body still reaches the HTTP layer.
    assert mock_session.requests[0][2]["json"]["AuthParameters"]["PASSWORD"] == (
        "top-secret"
    )


def test_account_identifiers_in_params_are_redacted(caplog):
    with caplog.at_level(logging.DEBUG):
        VeoliaAPI._log_request(
            "https://example.test",
            "GET",
            {"numero-pds": "PDS-SECRET-1", "annee": 2025},
            None,
            {},
        )
    assert "PDS-SECRET-1" not in caplog.text
    assert "2025" in caplog.text


def test_account_identifiers_in_json_are_redacted(caplog):
    with caplog.at_level(logging.DEBUG):
        VeoliaAPI._log_request(
            "https://example.test",
            "POST",
            None,
            {
                "contact_id": "CID-1",
                "tiers_id": "TID-1",
                "numero_compteur": "MTR-1",
                "abo_id": "ABO-1",
                "type_front": "WEB_ORDINATEUR",
            },
            {},
        )
    assert "CID-1" not in caplog.text
    assert "TID-1" not in caplog.text
    assert "MTR-1" not in caplog.text
    assert "ABO-1" not in caplog.text
    assert "WEB_ORDINATEUR" in caplog.text


def test_sensitive_keys_inside_lists_are_redacted():
    original = {
        "contacts": [{"titulaire": "Alice", "solde": 1.0}],
        "seuils": [{"numero_client": "NC1"}],
    }
    payload = copy.deepcopy(original)

    redacted = _redact(payload)

    assert redacted["contacts"][0]["titulaire"] == "REDACTED"
    assert redacted["contacts"][0]["solde"] == 1.0
    assert redacted["seuils"][0]["numero_client"] == "REDACTED"
    assert payload == original


async def test_alerts_response_log_is_redacted(caplog, logged_in_api, mock_session):
    payload = copy.deepcopy(ALERTS_OK)
    payload["seuils"]["journalier"]["numero_client"] = "NC-SECRET"
    mock_session.add("GET", r"/alertes/PDS1$", status=200, payload=payload)

    with caplog.at_level(logging.DEBUG):
        await logged_in_api.get_alerts_settings()

    assert "NC-SECRET" not in caplog.text
    assert "REDACTED" in caplog.text
