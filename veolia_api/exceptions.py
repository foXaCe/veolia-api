"""Custom exception classes for Veolia API errors."""

from __future__ import annotations


class VeoliaAPIError(Exception):
    """Base exception class for Veolia API errors."""


class VeoliaAPIInvalidCredentialsError(VeoliaAPIError):
    """Exception for missing or rejected credentials."""


class VeoliaAPITokenError(VeoliaAPIError):
    """Exception for access-token retrieval or validation failures."""


class VeoliaAPIChallengeError(VeoliaAPIError):
    """Cognito answered a sign-in with a challenge instead of tokens.

    Portals behind Cognito's adaptive authentication answer an unrecognised
    context with a challenge (``SMS_MFA`` in practice) rather than tokens.
    On accounts migrated to such a portal the pool's ``phone_number`` is an
    unverified placeholder, so the code never arrives and the challenge can
    never be answered: authenticating with a refresh token is the way in.
    """

    def __init__(self, challenge_name: str) -> None:
        """Record which challenge Cognito demanded."""
        self.challenge_name = challenge_name
        super().__init__(
            f"Cognito demanded the {challenge_name} challenge, "
            "which this client cannot answer",
        )


class VeoliaAPIConnectionError(VeoliaAPIError):
    """Exception for network-level failures (connection errors, timeouts)."""


class VeoliaAPIResponseError(VeoliaAPIError):
    """Exception for unexpected API response payloads."""


class VeoliaAPIGetDataError(VeoliaAPIError):
    """Exception for data-fetching failures."""


class VeoliaAPISetDataError(VeoliaAPIError):
    """Exception for data-writing failures."""


class VeoliaAPIRateLimitError(VeoliaAPIError):
    """Exception for HTTP 429 Too Many Requests."""
