"""Shared fixtures for the HTTP-layer tests."""

from __future__ import annotations

import re
from datetime import UTC, datetime

import pytest
import tenacity

from veolia_api import VeoliaAPI

COGNITO_OK = {"AuthenticationResult": {"AccessToken": "test-token", "ExpiresIn": 3600}}
ESPACE_CLIENT_OK = {
    "contacts": [
        {
            "id_contact": "C1",
            "tiers": [
                {
                    "id": "T1",
                    "abonnements": [
                        {
                            "id_abonnement": "123",
                            "numero_compteur": "M1",
                            "adresse_de_branchement": "1 rue de l'Eau",
                            "emplacement_compteur": "cave",
                            "libelle_contrat": "Contrat eau",
                            "statut": "actif",
                        },
                    ],
                },
            ],
        },
    ],
}
FACTURATION_OK = {
    "numero_pds": "PDS1",
    "date_debut_abonnement": "2020-01-15",
    "solde": 12.5,
    "dernier_index_releve": 1234.0,
    "date_index_releve": "2026-01-01",
    "mode_releve": "TELERELEVE",
    "mode_paiement": "PRELEVEMENT",
    "numero_client": "NC1",
    "titulaire": "Alice Example",
    "marque": "VEOLIA",
}
ALERTS_OK = {
    "seuils": {
        "journalier": {
            "valeur": 100,
            "unite": "L",
            "moyen_contact": {"souscrit_par_email": True, "souscrit_par_mobile": True},
        },
        "mensuel": {
            "valeur": 5,
            "unite": "M3",
            "moyen_contact": {"souscrit_par_email": True, "souscrit_par_mobile": False},
        },
    },
}


class MockResponse:
    """Minimal stand-in for aiohttp.ClientResponse."""

    def __init__(self, status=200, payload=None):
        self.status = status
        self._payload = payload
        self.released = False

    def release(self):
        self.released = True

    async def json(self, content_type=None):  # noqa: ARG002
        return self._payload


class MockSession:
    """Route-based stand-in for aiohttp.ClientSession.

    Register expectations with add(); every request is recorded in
    self.requests as (METHOD, url, kwargs). A request matching no
    route raises AssertionError so a missing mock fails loudly.
    """

    def __init__(self):
        self._routes = []
        self.requests = []
        self.served = []
        self.closed = False

    def add(self, method, url_pattern, status=200, payload=None, repeat=False):
        self._routes.append(
            {
                "method": method.upper(),
                "pattern": re.compile(url_pattern),
                "status": status,
                "payload": payload,
                "repeat": repeat,
                "used": False,
            },
        )

    async def request(self, method, url, **kwargs):
        self.requests.append((method.upper(), str(url), kwargs))
        for route in self._routes:
            if route["method"] != method.upper():
                continue
            if not route["pattern"].search(str(url)):
                continue
            if route["used"] and not route["repeat"]:
                continue
            route["used"] = True
            response = MockResponse(status=route["status"], payload=route["payload"])
            self.served.append(response)
            return response
        raise AssertionError(f"Unexpected request: {method} {url}")

    async def close(self):
        self.closed = True

    def calls_matching(self, url_substring):
        """Recorded (METHOD, url, kwargs) tuples whose url contains the substring."""
        return [r for r in self.requests if url_substring in r[1]]


@pytest.fixture
def no_retry_wait():
    """Disable the exponential backoff between tenacity retries."""
    retrying = VeoliaAPI._send_request.retry
    original = retrying.wait
    retrying.wait = tenacity.wait_none()
    yield
    retrying.wait = original


@pytest.fixture
def mock_session():
    return MockSession()


@pytest.fixture
def api(mock_session):
    """A client wired to the mock transport (injected session, never closed by the client)."""
    return VeoliaAPI("alice@example.test", "pw", session=mock_session)


@pytest.fixture
def logged_in_api(api):
    """A client with account data pre-populated (skips the login flow)."""
    api.account_data.access_token = "test-token"
    api.account_data.token_expiration = datetime.now(UTC).timestamp() + 3600
    api.account_data.id_abonnement = "123"
    api.account_data.numero_pds = "PDS1"
    api.account_data.contact_id = "C1"
    api.account_data.tiers_id = "T1"
    api.account_data.numero_compteur = "M1"
    api.account_data.date_debut_abonnement = "2020-01-15"
    return api
