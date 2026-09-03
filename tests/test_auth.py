"""Tests for the login and token-refresh flows."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import Mock

import aiohttp
import pytest

from tests.conftest import COGNITO_OK, ESPACE_CLIENT_OK, FACTURATION_OK
from veolia_api.exceptions import (
    VeoliaAPIChallengeError,
    VeoliaAPIInvalidCredentialsError,
    VeoliaAPITokenError,
)

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


async def test_concurrent_check_token_single_login(logged_in_api, mock_session):
    logged_in_api.account_data.token_expiration = datetime.now(UTC).timestamp() - 10
    mock_session.add("POST", COGNITO_URL, payload=COGNITO_OK, repeat=True)

    await asyncio.gather(
        logged_in_api._check_token(),
        logged_in_api._check_token(),
    )

    assert len(mock_session.calls_matching("cognito-idp")) == 1
    assert logged_in_api.account_data.access_token == "test-token"
    assert logged_in_api.account_data.token_expiration > datetime.now(UTC).timestamp()


def cognito_payload(mock_session):
    """The JSON body of the single Cognito call recorded so far."""
    (call,) = mock_session.calls_matching("cognito-idp")
    return call[2]["json"]


async def test_login_with_refresh_token_uses_the_refresh_flow(
    token_api,
    mock_session,
):
    add_login_mocks(mock_session)

    assert await token_api.login() is True

    payload = cognito_payload(mock_session)
    assert payload["AuthFlow"] == "REFRESH_TOKEN_AUTH"
    assert payload["AuthParameters"] == {"REFRESH_TOKEN": "refresh-me"}
    assert token_api.account_data.access_token == "test-token"
    assert token_api.account_data.id_abonnement == "123"


async def test_login_with_refresh_token_skips_credential_validation(
    token_api,
    mock_session,
):
    """An empty username is not an error when a refresh token authenticates."""
    add_login_mocks(mock_session)

    assert await token_api.login() is True


async def test_password_login_still_uses_the_password_flow(api, mock_session):
    add_login_mocks(mock_session)

    await api.login()

    payload = cognito_payload(mock_session)
    assert payload["AuthFlow"] == "USER_PASSWORD_AUTH"
    assert payload["AuthParameters"]["USERNAME"] == "alice@example.test"


async def test_refresh_flow_drops_the_stale_bearer_header(token_api, mock_session):
    """Cognito is asked for a new token without being shown the expired one."""
    token_api.account_data.access_token = "expired-token"
    mock_session.add("POST", COGNITO_URL, payload=COGNITO_OK)

    await token_api._get_access_token()

    (call,) = mock_session.calls_matching("cognito-idp")
    assert "Authorization" not in call[2]["headers"]
    assert token_api.account_data.access_token == "test-token"


async def test_expired_token_renews_through_the_refresh_flow(
    token_api,
    mock_session,
):
    """A discovered account renews its token without a full login."""
    token_api.account_data.id_abonnement = "123"
    token_api.account_data.numero_pds = "PDS1"
    token_api.account_data.date_debut_abonnement = "2020-01-15"
    token_api.account_data.access_token = "expired-token"
    token_api.account_data.token_expiration = datetime.now(UTC).timestamp() - 10
    mock_session.add("POST", COGNITO_URL, payload=COGNITO_OK)

    await token_api._check_token()

    assert len(mock_session.requests) == 1
    assert cognito_payload(mock_session)["AuthFlow"] == "REFRESH_TOKEN_AUTH"


async def test_rejected_refresh_token_raises_invalid_credentials(
    token_api,
    mock_session,
):
    mock_session.add(
        "POST",
        COGNITO_URL,
        status=400,
        payload={
            "__type": "NotAuthorizedException",
            "message": "Refresh Token has expired.",
        },
    )

    with pytest.raises(VeoliaAPIInvalidCredentialsError):
        await token_api.login()


async def test_cognito_challenge_raises_challenge_error(api, mock_session):
    """A 200 carrying a challenge is not a plain authentication failure."""
    mock_session.add(
        "POST",
        COGNITO_URL,
        status=200,
        payload={"ChallengeName": "SMS_MFA", "Session": "s-1"},
    )

    with pytest.raises(VeoliaAPIChallengeError) as excinfo:
        await api.login()

    assert excinfo.value.challenge_name == "SMS_MFA"
