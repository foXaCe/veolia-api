"""veolia_api package"""

from .portals import VEOLIA_PORTAL_CLIENTS, VEOLIA_PORTALS, VeoliaPortal
from .veolia_api import VeoliaAPI

__all__ = [
    "VEOLIA_PORTALS",
    "VEOLIA_PORTAL_CLIENTS",
    "VeoliaAPI",
    "VeoliaPortal",
]

__version__ = "2.2.3"
