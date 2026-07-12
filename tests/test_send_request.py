"""Tests for the retry, rate-limit, 401 and header behavior of _send_request."""

from __future__ import annotations

import aiohttp
import pytest

from tests.conftest import COGNITO_OK, ESPACE_CLIENT_OK, FACTURATION_OK
from veolia_api import VeoliaAPI
from veolia_api.exceptions import (
    VeoliaAPIConnectionError,
    VeoliaAPIGetDataError,
    VeoliaAPIRateLimitError,
    VeoliaAPITokenError,
)

COGNITO_URL = r"cognito-idp\.eu-west-3\.amazonaws\.com"
ESPACE_CLIENT_URL = r"/espace-client"
FACTURATION_URL = r"/facturation$"
PLAN_URL = r"/facturation/mensualisation/plan$"


class RaisingSession:
    """Session stand-in whose request() always raises the given exception."""

    closed = False

    def __init__(self, exc):
        self._exc = exc
        self.calls = 0

    async def request(self, method, url, **kwargs):  # noqa: ARG002
        self.calls += 1
        raise self._exc


@pytest.mark.usefixtures("no_retry_wait")
async def test_rate_limit_retries_then_succeeds(logged_in_api, mock_session):
    mock_session.add("GET", ESPACE_CLIENT_URL, status=429)
    mock_session.add("GET", ESPACE_CLIENT_URL, status=200, payload=ESPACE_CLIENT_OK)
    mock_session.add("GET", FACTURATION_URL, status=200, payload=FACTURATION_OK)

    await logged_in_api._get_client_data()

    assert logged_in_api.account_data.numero_pds == "PDS1"


@pytest.mark.usefixtures("no_retry_wait")
async def test_rate_limit_exhausts_after_five_attempts(logged_in_api, mock_session):
    mock_session.add("GET", ESPACE_CLIENT_URL, status=429, repeat=True)

    with pytest.raises(VeoliaAPIRateLimitError):
        await logged_in_api._get_client_data()

    assert len(mock_session.calls_matching("/espace-client")) == 5


async def test_unauthorized_raises_token_error(logged_in_api, mock_session):
    mock_session.add("GET", ESPACE_CLIENT_URL, status=401)

    with pytest.raises(VeoliaAPITokenError):
        await logged_in_api._send_request_with_retry(
            url="https://x.test/espace-client",
            method="GET",
        )

    assert len(mock_session.requests) == 1


async def test_forbidden_raises_token_error(logged_in_api, mock_session):
    # Veolia answers a stale bearer token with 403 as well as 401.
    mock_session.add("GET", ESPACE_CLIENT_URL, status=403)

    with pytest.raises(VeoliaAPITokenError):
        await logged_in_api._send_request_with_retry(
            url="https://x.test/espace-client",
            method="GET",
        )

    assert len(mock_session.requests) == 1
    assert mock_session.served[0].released is True


async def test_bearer_header_sent_when_token_present(logged_in_api, mock_session):
    mock_session.add("GET", ESPACE_CLIENT_URL, status=200, payload=ESPACE_CLIENT_OK)
    mock_session.add("GET", FACTURATION_URL, status=200, payload=FACTURATION_OK)

    await logged_in_api._get_client_data()

    headers = mock_session.calls_matching("/espace-client")[0][2]["headers"]
    assert headers["Authorization"] == "Bearer test-token"


async def test_login_request_uses_amz_content_type(api, mock_session):
    mock_session.add("POST", COGNITO_URL, payload=COGNITO_OK)
    mock_session.add("GET", ESPACE_CLIENT_URL, payload=ESPACE_CLIENT_OK)
    mock_session.add("GET", FACTURATION_URL, payload=FACTURATION_OK)

    await api.login()

    kwargs = mock_session.calls_matching("cognito-idp")[0][2]
    headers = kwargs["headers"]
    assert headers["x-amz-target"] == "AWSCognitoIdentityProviderService.InitiateAuth"
    assert headers["Content-Type"] == "application/x-amz-json-1.1"
    assert kwargs["json"]["AuthParameters"]["USERNAME"] == "alice@example.test"


@pytest.mark.usefixtures("no_retry_wait")
async def test_429_responses_are_released_before_retry(logged_in_api, mock_session):
    mock_session.add("GET", ESPACE_CLIENT_URL, status=429, repeat=True)

    with pytest.raises(VeoliaAPIRateLimitError):
        await logged_in_api._get_client_data()

    assert len(mock_session.served) == 5
    assert all(r.released for r in mock_session.served)


async def test_401_response_is_released(logged_in_api, mock_session):
    mock_session.add("GET", ESPACE_CLIENT_URL, status=401)

    with pytest.raises(VeoliaAPITokenError):
        await logged_in_api._send_request_with_retry(
            url="https://x.test/espace-client",
            method="GET",
        )

    assert mock_session.served[0].released is True


async def test_non_ok_client_data_response_is_released(logged_in_api, mock_session):
    mock_session.add("GET", ESPACE_CLIENT_URL, status=500)

    with pytest.raises(VeoliaAPIGetDataError):
        await logged_in_api._get_client_data()

    assert mock_session.served[0].released is True


async def test_mensualisation_plan_failure_response_is_released(
    logged_in_api,
    mock_session,
):
    mock_session.add("GET", r"/facturation/mensualisation/plan$", status=500)

    result = await logged_in_api._get_mensualisation_plan()

    assert result == {}
    assert mock_session.served[0].released is True


async def test_mensualisation_plan_persistent_403_is_skipped(
    logged_in_api,
    mock_session,
):
    # The optional plan keeps rejecting even after the re-login: it must be
    # skipped (return {}), never fail the whole refresh.
    mock_session.add("GET", PLAN_URL, status=403, repeat=True)
    mock_session.add("POST", COGNITO_URL, payload=COGNITO_OK, repeat=True)
    mock_session.add("GET", ESPACE_CLIENT_URL, payload=ESPACE_CLIENT_OK, repeat=True)
    mock_session.add("GET", FACTURATION_URL, payload=FACTURATION_OK, repeat=True)

    result = await logged_in_api._get_mensualisation_plan()

    assert result == {}
    # The 403 did trigger exactly one re-login before giving up.
    assert len(mock_session.calls_matching("cognito-idp")) == 1


@pytest.mark.usefixtures("no_retry_wait")
async def test_client_error_wrapped_after_retries():
    session = RaisingSession(aiohttp.ClientConnectionError("boom"))
    api = VeoliaAPI("alice@example.test", "pw", session=session)

    with pytest.raises(VeoliaAPIConnectionError) as err:
        await api._send_request(url="https://x.test", method="GET")

    assert session.calls == 5
    assert isinstance(err.value.__cause__, aiohttp.ClientConnectionError)


async def test_timeout_wrapped_without_retry():
    session = RaisingSession(TimeoutError())
    api = VeoliaAPI("alice@example.test", "pw", session=session)

    with pytest.raises(VeoliaAPIConnectionError) as err:
        await api._send_request(url="https://x.test", method="GET")

    assert session.calls == 1
    assert isinstance(err.value.__cause__, TimeoutError)


@pytest.mark.usefixtures("no_retry_wait")
async def test_rate_limit_error_not_wrapped(logged_in_api, mock_session):
    mock_session.add("GET", ESPACE_CLIENT_URL, status=429, repeat=True)

    with pytest.raises(VeoliaAPIRateLimitError) as err:
        await logged_in_api._get_client_data()

    assert type(err.value) is VeoliaAPIRateLimitError
