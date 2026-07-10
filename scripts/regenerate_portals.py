"""Regenerate the ``VEOLIA_PORTALS`` table from the national portal bundle.

Fetches https://eau.veolia.fr, locates its content-hashed JS bundle, extracts
the brand -> hostname and brand -> Cognito client id registries embedded in
it, and prints a candidate ``VEOLIA_PORTALS`` block plus a diff against the
current table. The script never writes to ``veolia_api/portals.py`` — review
the output and edit the file manually.

Usage: python scripts/regenerate_portals.py
"""

from __future__ import annotations

import asyncio
import re
import sys

import aiohttp

from veolia_api.portals import VEOLIA_PORTALS

PORTAL_HOME = "https://eau.veolia.fr"
BUNDLE_RE = re.compile(r"/assets/index-[\w-]+\.js")
CLIENT_ID_RE = re.compile(r'cognitoUserpool([A-Za-z]+)ClientId:"([^"]+)"')
HOSTNAME_RE = re.compile(r'enum:"([A-Za-z]+)",masterBrand:"[A-Z]+"[^}]*?prd:"([^"]+)"')
USERPOOL_RE = re.compile(r'cognitoUserpoolId:"([^"]+)"')

# The client-id registry names the national brand "VeoliaWaterp"; the
# hostname registry names the same brand "Veolia". Join keys are lowercased.
BRAND_ALIASES = {"veoliawaterp": "veolia"}


def _norm_host(hostname: str) -> str:
    """Strip a leading ``www.`` (registry says www.eau.veolia.fr; table says eau.veolia.fr)."""
    return hostname.removeprefix("www.")


async def _fetch(session: aiohttp.ClientSession, url: str) -> str:
    """Return the body of a public GET, raising on non-2xx."""
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


async def main() -> None:
    """Extract both registries, print the candidate table and the diff."""
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        home = await _fetch(session, PORTAL_HOME)
        match = BUNDLE_RE.search(home)
        if match is None:
            sys.exit(f"ERROR: no /assets/index-*.js bundle found on {PORTAL_HOME}")
        bundle_url = f"{PORTAL_HOME}{match.group(0)}"
        print(f"# Source bundle: {bundle_url}")
        bundle = await _fetch(session, bundle_url)

    client_ids = {
        BRAND_ALIASES.get(brand.lower(), brand.lower()): client_id
        for brand, client_id in CLIENT_ID_RE.findall(bundle)
    }
    brands = {
        brand.lower(): (brand, host) for brand, host in HOSTNAME_RE.findall(bundle)
    }
    userpools = sorted(set(USERPOOL_RE.findall(bundle)))
    if not client_ids or not brands:
        sys.exit("ERROR: registries not found in the bundle (app layout changed?)")

    print(f"# Userpool id(s) seen in the bundle: {', '.join(userpools)}")
    print("# Candidate table (paste into veolia_api/portals.py after review):")
    print("VEOLIA_PORTALS: dict[str, VeoliaPortal] = {")
    extracted: dict[str, str] = {}
    for key in sorted(brands, key=lambda k: _norm_host(brands[k][1])):
        brand, raw_host = brands[key]
        host = _norm_host(raw_host)
        client_id = client_ids.get(key)
        if client_id is None:
            print(f"    # {brand} ({host}): NO client id found — investigate")
            continue
        extracted[host] = client_id
        www_note = " (normalized from www.)" if raw_host != host else ""
        print(f'    "{host}": VeoliaPortal(')
        print(f'        client_id="{client_id}",  # {brand}{www_note}')
        print("    ),")
    print("}")

    print("\n# Diff against the current VEOLIA_PORTALS:")
    for host, portal in sorted(VEOLIA_PORTALS.items()):
        if host not in extracted:
            print(f"#   {host}: NOT in the bundle registry — independent deployment,")
            print("#     keep its manually maintained entry (e.g. www.ea-pm.fr).")
        elif extracted[host] == portal.client_id:
            print(f"#   {host}: unchanged")
        else:
            print(
                f"#   {host}: CHANGED {portal.client_id} -> {extracted[host]} "
                "— client id rotated, update the library!",
            )
    for host in sorted(set(extracted) - set(VEOLIA_PORTALS)):
        print(f"#   {host}: NEW (not in the current table)")

    print("\n# CAVEATS — human review required before editing portals.py:")
    print("#   - Backends are UNVERIFIED: the default backend is assumed for all")
    print("#     entries above; independent deployments have their own backend.")
    print("#   - Independent deployments (own bundle/userpool, e.g. www.ea-pm.fr)")
    print("#     are NOT covered by the national bundle registry.")
    print("#   - This script prints only; it never writes to portals.py.")


if __name__ == "__main__":
    asyncio.run(main())
