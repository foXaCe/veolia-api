"""veolia_api package"""

from __future__ import annotations

from .discovery import resolve_portal_url
from .portals import VEOLIA_PORTAL_CLIENTS, VEOLIA_PORTALS, VeoliaPortal
from .veolia_api import VeoliaAPI

__all__ = [
    "VEOLIA_PORTALS",
    "VEOLIA_PORTAL_CLIENTS",
    "VeoliaAPI",
    "VeoliaPortal",
    "resolve_portal_url",
]

__version__ = "2.4.4"
