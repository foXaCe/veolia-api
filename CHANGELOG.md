# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.4.3] - 2026-07-12

### Fixed

- Self-heal on a rejected bearer token: the Veolia data backend answers a
  stale or server-invalidated token with `403` as often as `401`. Both now
  surface as a token error that triggers a single-flight re-authentication
  and one request retry, so a session that goes stale between two refresh
  cycles recovers on its own instead of failing every cycle (previously the
  `403` was fatal until the integration restarted).
- No more leaked coroutines: `fetch_all_data` now gathers with
  `return_exceptions=True` and surfaces the first failure only after every
  request has settled. A single failing request (e.g. the `403` above) no
  longer aborts the gather early and discards the semaphore-queued
  coroutines un-awaited, which emitted `coroutine ... was never awaited`
  `RuntimeWarning`s.

## [2.4.2] - 2026-07-10

### Added

- PEP 561 `py.typed` marker: consumers' type checkers now see the package's
  full type annotations instead of treating everything as `Any`.

### Changed

- Single-flight token refresh: an instance lock serializes `_check_token`,
  so concurrent calls hitting an expired token no longer each run their own
  Cognito login.
- `fetch_all_data` revalidates the token inside each batched task (long
  backfills with retries can outlive the 60 s expiry margin checked upfront)
  and now runs in 2 HTTP waves instead of 4 (monthly+daily share one gather;
  billing plan and alert settings are fetched concurrently).

### Fixed

- A closed client can be reused: `close()` resets the owned session so the
  next request lazily creates a fresh one (previously
  `RuntimeError: Session is closed`).
- Defensive Cognito response parsing: an empty body (gateway 502/504) or a
  non-JSON body (WAF/CDN error page) now raises `VeoliaAPITokenError` instead
  of leaking `AttributeError` / `aiohttp.ContentTypeError`.
- Devbox onboarding repaired: the `init_hook` installs the local package
  (editable) instead of the upstream `veolia-api` PyPI package, Python floor
  aligned to 3.11, and `run_test` points at `pytest` instead of a
  nonexistent `main.py`.

### Security

- `_redact()` now recurses into lists of dicts, closing a latent redaction
  bypass for payload shapes the API demonstrably uses.
- The `get_alerts_settings` response body is redacted before being debug
  logged (the last unredacted response log in the client).
- `resolve_portal_url` requests now set a per-request timeout and refuse
  redirects, mirroring the main client's hardening.

## [2.4.1] - 2026-07-10

### Security

- The Cognito login body (including the account e-mail) can no longer reach
  debug logs: credentials travel through a dedicated `login_json` parameter
  that is never passed to the request logger.
- Redaction is applied recursively to nested keys, and `username` is
  redacted alongside the other identifiers.

### Fixed

- CI: `pip-audit` audits the requirements only, skipping the local editable
  package (version-bump race with the PyPI index).

## [2.4.0] - 2026-07-10

### Added

- Repository tooling: `SECURITY.md`, `CODE_OF_CONDUCT.md`, `.editorconfig`,
  `.gitattributes`, issue/PR templates.
- CI: CodeQL analysis, daily security audit (pip-audit, OSV-Scanner, Gitleaks,
  dependency review), stale-issue management, and a real `pytest` test suite.
- New exception `VeoliaAPIConnectionError` raised for network-level failures
  (connection errors, timeouts).
- Strict mypy typechecking (`[tool.mypy]` config + CI job).
- `resolve_portal_url(commune)`: resolve a commune name to its portal
  hostname via Veolia's public commune-reference API (see the plan-011
  spike report).
- Maintainer script `scripts/regenerate_portals.py`: prints a regenerated
  `VEOLIA_PORTALS` table (13 portals) extracted from the national portal
  bundle, with a diff against the current table.

### Changed

- `CODEOWNERS` now points to the fork maintainer (`@foXaCe`).
- CI actions bumped (`actions/checkout` v7, `actions/cache` v6).
- Raw `aiohttp.ClientError` / `TimeoutError` no longer escape the client; they
  are wrapped in `VeoliaAPIConnectionError` (the original exception is kept as
  `__cause__`).
- `VeoliaAPI.session` is now a read-only property (assigning to it is no
  longer supported).
- Token refresh no longer re-fetches account/billing data on every expiry;
  only the Cognito authentication is repeated once the account is known.
- Debug logs now redact account identifiers (`numero_pds`, `contact_id`,
  `tiers_id`, `numero_compteur`, `abo_id`, `numero_client`, `titulaire`) in
  addition to the password and bearer token.

### Fixed

- `bumpver` `current_version` realigned with the published package version.
- Atypical `espace-client` payloads (no contact/tiers/subscription) now raise
  `VeoliaAPIResponseError` instead of crashing with `TypeError`/`IndexError`.
- Alert settings with missing `moyen_contact`/`valeur` fields no longer raise
  `KeyError`; they fall back to disabled/zero defaults.
- A Cognito response without `ExpiresIn` no longer marks the token as
  immediately expired (defaults to 1 hour, with a warning).
- HTTP responses are now released on every error path (429 retries, 401,
  non-OK statuses), preventing pooled-connection leaks in shared sessions.
- `VeoliaAPI(...)` no longer raises `RuntimeError: no running event loop` when
  constructed outside async code without an injected session; the session is
  created lazily on first request.
- Consumption requests covering the subscription's first month or first
  year are no longer silently skipped when the subscription started
  mid-period (ports upstream PR Jezza34000/veolia-api#33 by @casi-3).

### Removed

- Dead code from the pre-Cognito flow: `VeoliaAccountData.code`/`.verifier`,
  `CALLBACK_ENDPOINT`, `VeoliaAPIUnknownError`, and the unreachable
  POST-with-form-params branch in the request helper.

## [2.3.0] - 2026-07-10

### Added

- Multi-portal support: per-portal Cognito `client_id` and data backend
  (national portal, Eau de Toulouse Métropole, Eau de Perpignan Méditerranée
  Métropole).
- Expose account balance (`solde`), latest meter index and reading date.
- Expose contract details (connection address, meter location, contract label,
  status).
- Published on PyPI as `veolia-api-foxace` via trusted publishing (OIDC).

### Changed

- Client robustness: per-request timeouts, configurable token-expiry margin,
  stricter typing throughout.

### Security

- Redact the password from the Cognito login body and the bearer token from the
  `Authorization` header in debug logs.

---

Releases prior to the `veolia-api-foxace` fork are tracked in the git tags of
this repository and in the upstream project
[`Jezza34000/veolia-api`](https://github.com/Jezza34000/veolia-api).

[Unreleased]: https://github.com/foXaCe/veolia-api/compare/v2.4.2...HEAD
[2.4.2]: https://github.com/foXaCe/veolia-api/compare/v2.4.1...v2.4.2
[2.4.1]: https://github.com/foXaCe/veolia-api/compare/v2.4.0...v2.4.1
[2.4.0]: https://github.com/foXaCe/veolia-api/compare/v2.3.0...v2.4.0
[2.3.0]: https://github.com/foXaCe/veolia-api/releases/tag/v2.3.0
