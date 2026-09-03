"""Tests for the exception hierarchy."""

from __future__ import annotations

import pytest

from veolia_api import exceptions

_SUBCLASSES = [
    "VeoliaAPIInvalidCredentialsError",
    "VeoliaAPITokenError",
    "VeoliaAPIChallengeError",
    "VeoliaAPIConnectionError",
    "VeoliaAPIResponseError",
    "VeoliaAPIGetDataError",
    "VeoliaAPISetDataError",
    "VeoliaAPIRateLimitError",
]


def test_base_is_an_exception():
    assert issubclass(exceptions.VeoliaAPIError, Exception)


@pytest.mark.parametrize("name", _SUBCLASSES)
def test_subclass_derives_from_base(name):
    exc = getattr(exceptions, name)
    assert issubclass(exc, exceptions.VeoliaAPIError)


def test_subclasses_are_raisable():
    with pytest.raises(exceptions.VeoliaAPIError):
        raise exceptions.VeoliaAPIRateLimitError("boom")


def test_challenge_error_carries_the_challenge_name():
    exc = exceptions.VeoliaAPIChallengeError("SMS_MFA")

    assert exc.challenge_name == "SMS_MFA"
    assert "SMS_MFA" in str(exc)
