# Security Policy

## Supported versions

Only the latest release published on the `main` branch is supported.
Please upgrade to the most recent version before reporting an issue.

| Version | Supported          |
| ------- | ------------------ |
| 2.3.x   | :white_check_mark: |
| < 2.3   | :x:                |

## Reporting a vulnerability

**Please do not open a public issue for security vulnerabilities.**

Report privately through GitHub's
[private vulnerability reporting](https://github.com/foXaCe/veolia-api/security/advisories/new).

Include, if possible:

- a description of the vulnerability and its impact,
- the affected version(s),
- steps to reproduce or a proof of concept.

Target response time: **7 days**.

## Handling of credentials

This client authenticates against Veolia's AWS Cognito endpoint. Account
credentials and bearer tokens are **never** written to logs: the request logger
redacts passwords (`AuthParameters.PASSWORD`) and `Authorization` headers. If you
find a code path that leaks a credential or token, treat it as a security issue
and report it privately as described above.
