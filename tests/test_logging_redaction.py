"""Tests that credentials never leak into debug logs."""

from __future__ import annotations

import logging

from veolia_api.veolia_api import VeoliaAPI


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
    assert "abc123" not in caplog.text
    assert "REDACTED" in caplog.text


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
