"""Constants for the Veolia API."""

from __future__ import annotations

from enum import Enum
from typing import Final

from .portals import DEFAULT_BACKEND_URL, DEFAULT_PORTAL_URL, VEOLIA_PORTALS

# URLS
# Cognito authentication endpoint (region eu-west-3).
LOGIN_URL: Final = "https://cognito-idp.eu-west-3.amazonaws.com"
# Default data backend (national portal). Kept for backward compatibility;
# the effective backend is resolved per portal (see portals.py).
BACKEND_ISTEFR: Final = DEFAULT_BACKEND_URL

# AUTH — default Cognito client id (national portal), for backward compatibility.
LOGIN_CLIENT_ID: Final = VEOLIA_PORTALS[DEFAULT_PORTAL_URL].client_id

# API Flow Endpoints
CALLBACK_ENDPOINT: Final = "/callback"

TYPE_FRONT: Final = "WEB_ORDINATEUR"

# HTTP Methods
GET: Final = "GET"
POST: Final = "POST"

# AsyncIO HTTP/Session
TIMEOUT: Final = 15
CONCURRENTS_TASKS: Final = 3
# Re-login this many seconds before the token actually expires.
TOKEN_EXPIRY_MARGIN: Final = 60


class ConsumptionType(Enum):
    """Consumption type."""

    MONTHLY = "monthly"
    YEARLY = "yearly"
