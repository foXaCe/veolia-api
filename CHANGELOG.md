# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Repository tooling: `SECURITY.md`, `CODE_OF_CONDUCT.md`, `.editorconfig`,
  `.gitattributes`, issue/PR templates.
- CI: CodeQL analysis, daily security audit (pip-audit, OSV-Scanner, Gitleaks,
  dependency review), stale-issue management, and a real `pytest` test suite.

### Changed

- `CODEOWNERS` now points to the fork maintainer (`@foXaCe`).
- CI actions bumped (`actions/checkout` v7, `actions/cache` v6).

### Fixed

- `bumpver` `current_version` realigned with the published package version.
- Atypical `espace-client` payloads (no contact/tiers/subscription) now raise
  `VeoliaAPIResponseError` instead of crashing with `TypeError`/`IndexError`.
- Alert settings with missing `moyen_contact`/`valeur` fields no longer raise
  `KeyError`; they fall back to disabled/zero defaults.
- A Cognito response without `ExpiresIn` no longer marks the token as
  immediately expired (defaults to 1 hour, with a warning).

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

[Unreleased]: https://github.com/foXaCe/veolia-api/compare/v2.3.0...HEAD
[2.3.0]: https://github.com/foXaCe/veolia-api/releases/tag/v2.3.0
