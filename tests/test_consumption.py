"""Tests for consumption fetching and full-range aggregation."""

from __future__ import annotations

import gc
from datetime import UTC, date, datetime

import pytest

from tests.conftest import COGNITO_OK, ESPACE_CLIENT_OK, FACTURATION_OK
from veolia_api.constants import ConsumptionType
from veolia_api.exceptions import VeoliaAPIGetDataError, VeoliaAPITokenError

JOURNALIERES_URL = r"/consommations/123/journalieres$"
MENSUELLES_URL = r"/consommations/123/mensuelles$"
ALERTES_URL = r"/alertes/PDS1$"
PLAN_URL = r"/facturation/mensualisation/plan$"
COGNITO_URL = r"cognito-idp\.eu-west-3\.amazonaws\.com"
ESPACE_CLIENT_URL = r"/espace-client"
FACTURATION_URL = r"/facturation$"


def add_reauth_mocks(mock_session):
    """Register the three requests a forced re-login replays."""
    mock_session.add("POST", COGNITO_URL, payload=COGNITO_OK, repeat=True)
    mock_session.add("GET", ESPACE_CLIENT_URL, payload=ESPACE_CLIENT_OK, repeat=True)
    mock_session.add("GET", FACTURATION_URL, payload=FACTURATION_OK, repeat=True)


async def test_daily_consumption_params(logged_in_api, mock_session):
    payload = [{"jour": "2025-01-01", "consommation": 120}]
    mock_session.add("GET", JOURNALIERES_URL, status=200, payload=payload)

    result = await logged_in_api._get_consumption_data(
        ConsumptionType.MONTHLY,
        2025,
        1,
    )

    assert result == payload
    params = mock_session.calls_matching("journalieres")[0][2]["params"]
    assert params["annee"] == 2025
    assert params["mois"] == 1
    assert params["numero-pds"] == "PDS1"
    assert params["date-debut-abonnement"] == "2020-01-15"


async def test_yearly_consumption_params(logged_in_api, mock_session):
    payload = [{"mois": "2025-01", "consommation": 3}]
    mock_session.add("GET", MENSUELLES_URL, status=200, payload=payload)

    result = await logged_in_api._get_consumption_data(ConsumptionType.YEARLY, 2025)

    assert result == payload
    params = mock_session.calls_matching("mensuelles")[0][2]["params"]
    assert params["annee"] == 2025
    assert "mois" not in params


async def test_request_before_subscription_start_returns_empty(
    logged_in_api,
    mock_session,
):
    result = await logged_in_api._get_consumption_data(
        ConsumptionType.MONTHLY,
        2019,
        6,
    )

    assert result == []
    assert mock_session.requests == []


async def test_first_month_of_subscription_is_fetched(logged_in_api, mock_session):
    payload = [{"d": 1}]
    mock_session.add("GET", JOURNALIERES_URL, status=200, payload=payload)

    result = await logged_in_api._get_consumption_data(
        ConsumptionType.MONTHLY,
        2020,
        1,
    )

    assert result == payload
    assert len(mock_session.requests) == 1


async def test_first_year_of_subscription_is_fetched(logged_in_api, mock_session):
    payload = [{"m": 1}]
    mock_session.add("GET", MENSUELLES_URL, status=200, payload=payload)

    result = await logged_in_api._get_consumption_data(ConsumptionType.YEARLY, 2020)

    assert result == payload


async def test_month_entirely_before_subscription_still_skipped(
    logged_in_api,
    mock_session,
):
    result = await logged_in_api._get_consumption_data(
        ConsumptionType.MONTHLY,
        2019,
        12,
    )

    assert result == []
    assert mock_session.requests == []


async def test_invalid_type_raises_value_error(logged_in_api):
    with pytest.raises(ValueError, match="Invalid data type"):
        await logged_in_api._get_consumption_data(ConsumptionType.MONTHLY, 2025)


async def test_non_200_raises_get_data_error(logged_in_api, mock_session):
    mock_session.add("GET", JOURNALIERES_URL, status=500)

    with pytest.raises(VeoliaAPIGetDataError):
        await logged_in_api._get_consumption_data(ConsumptionType.MONTHLY, 2025, 1)


async def test_fetch_all_data_aggregates(logged_in_api, mock_session):
    mock_session.add("GET", MENSUELLES_URL, payload=[{"m": 1}], repeat=True)
    mock_session.add("GET", JOURNALIERES_URL, payload=[{"d": 1}], repeat=True)
    mock_session.add("GET", ALERTES_URL, status=204, repeat=True)
    mock_session.add("GET", PLAN_URL, status=204, repeat=True)

    await logged_in_api.fetch_all_data(date(2024, 11, 1), date(2025, 2, 1))

    data = logged_in_api.account_data
    assert data.monthly_consumption == [{"m": 1}, {"m": 1}]
    assert data.daily_consumption == [{"d": 1}] * 4
    assert data.billing_plan == {}
    assert data.alert_settings.daily_enabled is False
    assert len(mock_session.calls_matching("mensuelles")) == 2
    assert len(mock_session.calls_matching("journalieres")) == 4


async def test_fetch_all_data_stores_mensualisation_plan(logged_in_api, mock_session):
    mock_session.add("GET", MENSUELLES_URL, payload=[{"m": 1}], repeat=True)
    mock_session.add("GET", JOURNALIERES_URL, payload=[{"d": 1}], repeat=True)
    mock_session.add("GET", ALERTES_URL, status=204, repeat=True)
    mock_session.add(
        "GET",
        PLAN_URL,
        payload={"prelevements_echeancier": [{"montant": 42}]},
        repeat=True,
    )

    await logged_in_api.fetch_all_data(date(2025, 1, 1), date(2025, 1, 1))

    assert logged_in_api.account_data.billing_plan == {
        "prelevements_echeancier": [{"montant": 42}],
    }


async def test_fetch_all_data_expired_token_single_refresh(
    logged_in_api,
    mock_session,
):
    logged_in_api.account_data.token_expiration = datetime.now(UTC).timestamp() - 10
    mock_session.add("POST", COGNITO_URL, payload=COGNITO_OK, repeat=True)
    mock_session.add("GET", MENSUELLES_URL, payload=[{"m": 1}], repeat=True)
    mock_session.add("GET", JOURNALIERES_URL, payload=[{"d": 1}], repeat=True)
    mock_session.add("GET", ALERTES_URL, status=204, repeat=True)
    mock_session.add("GET", PLAN_URL, status=204, repeat=True)

    await logged_in_api.fetch_all_data(date(2025, 1, 1), date(2025, 1, 1))

    data = logged_in_api.account_data
    assert len(mock_session.calls_matching("cognito-idp")) == 1
    assert data.monthly_consumption == [{"m": 1}]
    assert data.daily_consumption == [{"d": 1}]


async def test_fetch_all_data_recovers_from_403_after_reauth(
    logged_in_api,
    mock_session,
):
    """A stale-token 403 on a data call re-authenticates once and retries."""
    # First journalieres call is rejected with 403, the rest succeed.
    mock_session.add("GET", JOURNALIERES_URL, status=403)
    mock_session.add("GET", JOURNALIERES_URL, payload=[{"d": 1}], repeat=True)
    mock_session.add("GET", MENSUELLES_URL, payload=[{"m": 1}], repeat=True)
    mock_session.add("GET", ALERTES_URL, status=204, repeat=True)
    mock_session.add("GET", PLAN_URL, status=204, repeat=True)
    add_reauth_mocks(mock_session)

    await logged_in_api.fetch_all_data(date(2025, 1, 1), date(2025, 1, 1))

    data = logged_in_api.account_data
    assert data.daily_consumption == [{"d": 1}]
    assert data.monthly_consumption == [{"m": 1}]
    # Exactly one re-login was triggered by the 403 (single-flight).
    assert len(mock_session.calls_matching("cognito-idp")) == 1


async def test_fetch_all_data_persistent_403_raises_token_error(
    logged_in_api,
    mock_session,
):
    """A 403 that survives the re-login fails the refresh as a token error."""
    mock_session.add("GET", MENSUELLES_URL, payload=[{"m": 1}], repeat=True)
    mock_session.add("GET", JOURNALIERES_URL, status=403, repeat=True)
    mock_session.add("GET", ALERTES_URL, status=204, repeat=True)
    mock_session.add("GET", PLAN_URL, status=204, repeat=True)
    add_reauth_mocks(mock_session)

    with pytest.raises(VeoliaAPITokenError):
        await logged_in_api.fetch_all_data(date(2025, 1, 1), date(2025, 1, 1))


async def test_fetch_all_data_awaits_every_task_on_failure(
    logged_in_api,
    mock_session,
    recwarn,
):
    """A failing refresh awaits every queued request — no coroutine is leaked.

    A server error (not an auth rejection, so no re-login kicks in) aborts the
    refresh over a wide window where most requests are queued behind the
    concurrency semaphore. Every request must still be issued, and no "coroutine
    was never awaited" RuntimeWarning may be emitted.
    """
    mock_session.add("GET", MENSUELLES_URL, status=500, repeat=True)
    mock_session.add("GET", JOURNALIERES_URL, status=500, repeat=True)

    with pytest.raises(VeoliaAPIGetDataError):
        await logged_in_api.fetch_all_data(date(2024, 1, 1), date(2024, 12, 1))

    # 1 yearly + 12 monthly requests were all issued (none abandoned).
    assert len(mock_session.calls_matching("mensuelles")) == 1
    assert len(mock_session.calls_matching("journalieres")) == 12

    gc.collect()
    assert not [w for w in recwarn.list if "never awaited" in str(w.message)]


async def test_fetch_all_data_merges_waves(logged_in_api, mock_session):
    mock_session.add("GET", MENSUELLES_URL, payload=[{"m": 1}], repeat=True)
    mock_session.add("GET", JOURNALIERES_URL, payload=[{"d": 1}], repeat=True)
    mock_session.add("GET", ALERTES_URL, status=204, repeat=True)
    mock_session.add("GET", PLAN_URL, status=204, repeat=True)

    await logged_in_api.fetch_all_data(date(2025, 1, 1), date(2025, 2, 1))

    data = logged_in_api.account_data
    assert data.monthly_consumption == [{"m": 1}]
    assert data.daily_consumption == [{"d": 1}, {"d": 1}]
    assert len(mock_session.calls_matching("mensuelles")) == 1
    assert len(mock_session.calls_matching("journalieres")) == 2
