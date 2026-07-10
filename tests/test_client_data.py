"""Tests for the parsing of account and billing data (_get_client_data)."""

from __future__ import annotations

import pytest

from tests.conftest import ESPACE_CLIENT_OK, FACTURATION_OK
from veolia_api.exceptions import VeoliaAPIGetDataError, VeoliaAPIResponseError

ESPACE_CLIENT_URL = r"/espace-client"
FACTURATION_URL = r"/facturation$"


async def test_get_client_data_happy_path(logged_in_api, mock_session):
    mock_session.add("GET", ESPACE_CLIENT_URL, status=200, payload=ESPACE_CLIENT_OK)
    mock_session.add("GET", FACTURATION_URL, status=200, payload=FACTURATION_OK)

    await logged_in_api._get_client_data()

    data = logged_in_api.account_data
    assert data.id_abonnement == "123"
    assert data.tiers_id == "T1"
    assert data.contact_id == "C1"
    assert data.numero_compteur == "M1"
    assert data.adresse_de_branchement == "1 rue de l'Eau"
    assert data.emplacement_compteur == "cave"
    assert data.libelle_contrat == "Contrat eau"
    assert data.statut == "actif"
    assert data.numero_pds == "PDS1"
    assert data.date_debut_abonnement == "2020-01-15"
    assert data.solde == 12.5
    assert data.dernier_index_releve == 1234.0
    assert data.date_index_releve == "2026-01-01"
    assert data.mode_releve == "TELERELEVE"
    assert data.mode_paiement == "PRELEVEMENT"
    assert data.numero_client == "NC1"
    assert data.titulaire == "Alice Example"
    assert data.marque == "VEOLIA"


async def test_get_client_data_non_200_raises(logged_in_api, mock_session):
    mock_session.add("GET", ESPACE_CLIENT_URL, status=500)

    with pytest.raises(VeoliaAPIGetDataError):
        await logged_in_api._get_client_data()


async def test_facturation_non_200_raises(logged_in_api, mock_session):
    mock_session.add("GET", ESPACE_CLIENT_URL, status=200, payload=ESPACE_CLIENT_OK)
    mock_session.add("GET", FACTURATION_URL, status=500)

    with pytest.raises(VeoliaAPIGetDataError):
        await logged_in_api._get_client_data()


async def test_missing_numero_pds_raises(logged_in_api, mock_session):
    facturation = {k: v for k, v in FACTURATION_OK.items() if k != "numero_pds"}
    mock_session.add("GET", ESPACE_CLIENT_URL, status=200, payload=ESPACE_CLIENT_OK)
    mock_session.add("GET", FACTURATION_URL, status=200, payload=facturation)

    with pytest.raises(VeoliaAPIResponseError):
        await logged_in_api._get_client_data()


async def test_missing_date_debut_raises(logged_in_api, mock_session):
    facturation = {
        k: v for k, v in FACTURATION_OK.items() if k != "date_debut_abonnement"
    }
    mock_session.add("GET", ESPACE_CLIENT_URL, status=200, payload=ESPACE_CLIENT_OK)
    mock_session.add("GET", FACTURATION_URL, status=200, payload=facturation)

    with pytest.raises(VeoliaAPIResponseError):
        await logged_in_api._get_client_data()
