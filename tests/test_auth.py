"""Tests for the login and token-refresh flows."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import Mock

import aiohttp
import pytest

from tests.conftest import COGNITO_OK, ESPACE_CLIENT_OK, FACTURATION_OK
from veolia_api.exceptions import VeoliaAPIInvalidCredentialsError, VeoliaAPITokenError

COGNITO_URL = r"cognito-idp\.eu-west-3\.amazonaws\.com"
ESPACE_CLIENT_URL = r"/espace-client"
FACTURATION_URL = r"/facturation$"


def add_login_mocks(mock_session):
    mock_session.add("POST", COGNITO_URL, payload=COGNITO_OK)
    mock_session.add("GET", ESPACE_CLIENT_URL, payload=ESPACE_CLIENT_OK)
    mock_session.add("GET", FACTURATION_URL, payload=FACTURATION_OK)


async def test_login_success_populates_account_data(api, mock_session):
    add_login_mocks(mock_session)

    result = await api.login()

    assert result is True
    assert api.account_data.access_token == "test-token"
    assert api.account_data.id_abonnement == "123"
    assert api.account_data.numero_pds == "PDS1"
    assert api.account_data.contact_id == "C1"
    assert api.account_data.tiers_id == "T1"
    assert api.account_data.numero_compteur == "M1"
    assert api.account_data.date_debut_abonnement == "2020-01-15"
    assert api.account_data.solde == 12.5
    assert api.account_data.titulaire == "Alice Example"
    assert api.account_data.token_expiration > datetime.now(UTC).timestamp() + 3500


async def test_login_rejected_credentials_raises(api, mock_session):
    mock_session.add(
        "POST",
        COGNITO_URL,
        status=400,
        payload={
            "__type": "NotAuthorizedException",
            "message": "Incorrect username or password.",
        },
    )

    with pytest.raises(VeoliaAPIInvalidCredentialsError):
        await api.login()


async def test_login_unknown_user_raises(api, mock_session):
    mock_session.add(
        "POST",
        COGNITO_URL,
        status=400,
        payload={
            "__type": "UserNotFoundException",
            "message": "User does not exist.",
        },
    )

    with pytest.raises(VeoliaAPIInvalidCredentialsError):
        await api.login()


async def test_login_other_cognito_error_raises_token_error(api, mock_session):
    mock_session.add(
        "POST",
        COGNITO_URL,
        status=400,
        payload={
            "__type": "TooManyRequestsException",
            "message": "Too many requests.",
        },
    )

    with pytest.raises(VeoliaAPITokenError):
        await api.login()


async def test_token_empty_body_raises_token_error(api, mock_session):
    mock_session.add("POST", COGNITO_URL, status=502, payload=None)

    with pytest.raises(VeoliaAPITokenError):
        await api._get_access_token()


async def test_token_non_json_body_raises_token_error(api, mock_session):
    mock_session.add(
        "POST",
        COGNITO_URL,
        json_exc=aiohttp.ContentTypeError(request_info=Mock(), history=()),
    )

    with pytest.raises(VeoliaAPITokenError):
        await api._get_access_token()

    assert mock_session.served[-1].released is True


async def test_login_missing_authentication_result_raises(api, mock_session):
    mock_session.add("POST", COGNITO_URL, status=200, payload={})

    with pytest.raises(VeoliaAPITokenError):
        await api.login()


async def test_login_missing_access_token_raises(api, mock_session):
    mock_session.add(
        "POST",
        COGNITO_URL,
        status=200,
        payload={"AuthenticationResult": {"ExpiresIn": 3600}},
    )

    with pytest.raises(VeoliaAPITokenError):
        await api.login()


async def test_missing_expires_in_defaults_to_one_hour(api, mock_session):
    mock_session.add(
        "POST",
        COGNITO_URL,
        status=200,
        payload={"AuthenticationResult": {"AccessToken": "t"}},
    )
    mock_session.add("GET", ESPACE_CLIENT_URL, payload=ESPACE_CLIENT_OK)
    mock_session.add("GET", FACTURATION_URL, payload=FACTURATION_OK)

    await api.login()

    assert api.account_data.token_expiration > datetime.now(UTC).timestamp() + 3000


async def test_check_token_valid_token_skips_login(logged_in_api, mock_session):
    await logged_in_api._check_token()

    assert mock_session.requests == []


async def test_check_token_expired_triggers_login(logged_in_api, mock_session):
    logged_in_api.account_data.token_expiration = datetime.now(UTC).timestamp() - 10
    add_login_mocks(mock_session)

    await logged_in_api._check_token()

    assert len(mock_session.calls_matching("cognito-idp")) == 1


async def test_expired_token_with_discovered_account_refreshes_token_only(
    logged_in_api,
    mock_session,
):
    logged_in_api.account_data.token_expiration = datetime.now(UTC).timestamp() - 10
    mock_session.add("POST", COGNITO_URL, payload=COGNITO_OK)

    await logged_in_api._check_token()

    assert logged_in_api.account_data.access_token == "test-token"
    assert len(mock_session.requests) == 1


async def test_expired_token_without_discovery_does_full_login(api, mock_session):
    add_login_mocks(mock_session)

    await api._check_token()

    assert api.account_data.numero_pds == "PDS1"
