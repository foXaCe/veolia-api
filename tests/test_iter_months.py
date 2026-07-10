"""Tests for the month-iteration helper."""

from __future__ import annotations

from datetime import date

from veolia_api.veolia_api import VeoliaAPI


def test_iter_months_within_single_year():
    result = list(VeoliaAPI._iter_months(date(2024, 1, 1), date(2024, 3, 15)))
    assert result == [(2024, 1), (2024, 2), (2024, 3)]


def test_iter_months_across_year_boundary():
    result = list(VeoliaAPI._iter_months(date(2023, 11, 1), date(2024, 2, 1)))
    assert result == [(2023, 11), (2023, 12), (2024, 1), (2024, 2)]


def test_iter_months_single_month():
    result = list(VeoliaAPI._iter_months(date(2024, 6, 10), date(2024, 6, 20)))
    assert result == [(2024, 6)]
