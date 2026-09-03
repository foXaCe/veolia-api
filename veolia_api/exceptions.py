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

    Adaptive authentication demands a second factor whenever it does not
    recognise the caller's context. Portals that migrated their accounts
    often carry an unverified placeholder phone number, in which case the
    SMS code never arrives and the challenge cannot be answered at all --
    hence its own error rather than a generic authentication failure.
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
