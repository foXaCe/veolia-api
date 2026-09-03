<p align=center>
    <img src="https://upload.wikimedia.org/wikipedia/fi/thumb/2/2a/Veolia-logo.svg/250px-Veolia-logo.svg.png"/>
</p>

<p>
    <a href="https://pypi.org/project/veolia-api-foxace/"><img src="https://img.shields.io/pypi/v/veolia-api-foxace.svg"/></a>
    <a href="https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white"><img src="https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white" /></a>
    <a href="https://github.com/psf/black"><img src="https://img.shields.io/badge/code%20style-black-000000.svg" /></a>
    <a href="https://github.com/foXaCe/veolia-api/actions"><img src="https://github.com/foXaCe/veolia-api/workflows/CI/badge.svg"/></a>
</p>

Async Python client for the Veolia water portal API (`eau.veolia.fr`).

## Table of contents

- [Installation](#installation)
- [Usage](#usage)
- [Contributing](#contributing)
- [Credits](#credits)
- [License](#license)

## Installation

First of all, you need to install [devbox](https://www.jetify.com/docs/devbox/installing-devbox) **if you don't have a python environment**

Once the previous step is done, simply run

```bash
devbox shell
cp .env.example .env   # fill in your credentials
python usage_example.py
```

That's it !

If you already have a python environment just run

```bash
pip install veolia-api-foxace
```

## Usage

```python
"""Example of usage of the Veolia API"""

import asyncio
from datetime import date

import aiohttp

from veolia_api.veolia_api import VeoliaAPI


async def main() -> None:
    """Main function."""

    async with aiohttp.ClientSession() as session:
        client_api = VeoliaAPI("your@email.com", "password", session)

        await client_api.fetch_all_data(date(2025, 1, 1), date(2025, 9, 1))

        # Display fetched data
        print(client_api.account_data.daily_consumption)
        print(client_api.account_data.monthly_consumption)
        print(client_api.account_data.alert_settings.daily_enabled)


if __name__ == "__main__":
    asyncio.run(main())

```

You can use usage_example.py

### Portals

Veolia operates several portals. They share the same Cognito authentication flow
but each has its own `client_id`, and some run on a dedicated data backend. Select
a portal with the `portal_url` argument (defaults to the national portal):

```python
client_api = VeoliaAPI("your@email.com", "password", session, portal_url="www.ea-pm.fr")
```

| `portal_url`                      | Description                             | Backend  |
| --------------------------------- | --------------------------------------- | -------- |
| `eau.veolia.fr` (default)         | Veolia France (national)                | default  |
| `eaudetm.monespace.eau.veolia.fr` | Eau de Toulouse Métropole               | default  |
| `www.ea-pm.fr`                    | Eau de Perpignan Méditerranée Métropole | dedicated |

You can resolve a commune name to its portal at setup time:

```python
from veolia_api import resolve_portal_url

portal = await resolve_portal_url("Toulouse")   # "eaudetm.monespace.eau.veolia.fr"
client_api = VeoliaAPI("your@email.com", "password", session, portal_url=portal)
```

To add a portal, add an entry to `VEOLIA_PORTALS` in
[`veolia_api/portals.py`](veolia_api/portals.py) with its `client_id` (found in
the portal's JavaScript bundle as `ClientId:"..."`) and, if different from the
default, its `backend_url`.

### Refresh-token authentication

Some portals put password sign-ins behind Cognito's adaptive authentication:
whenever it does not recognise the caller's context, Cognito answers a challenge
(`SMS_MFA` in practice) instead of tokens. On accounts migrated to such a portal
the pool's `phone_number` is an unverified placeholder, so the code never arrives
and the challenge can never be answered. The client reports that case as
`VeoliaAPIChallengeError` rather than a generic authentication failure.

`REFRESH_TOKEN_AUTH` is not a sign-in flow, so Cognito never risk-scores it: a
refresh token obtained once from a context it already trusts authenticates from
any address. Pass it instead of the credentials, which may then be empty:

```python
client_api = VeoliaAPI("", "", session, refresh_token="ey...")
```

Obtain the token from a machine the portal is used from, with an
`InitiateAuth` call carrying the portal's `client_id`:

```bash
curl -s https://cognito-idp.eu-west-3.amazonaws.com/ \
  -H 'Content-Type: application/x-amz-json-1.1' \
  -H 'X-Amz-Target: AWSCognitoIdentityProviderService.InitiateAuth' \
  -d '{"ClientId":"<client_id>","AuthFlow":"USER_PASSWORD_AUTH",
       "AuthParameters":{"USERNAME":"your@email.com","PASSWORD":"..."}}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["AuthenticationResult"]["RefreshToken"])'
```

A refresh token is a credential in its own right: store it as you would the
password, and keep it out of logs and diagnostics.

It is also short-lived: its validity is set on the Cognito app client, measured
at one hour on the Toulouse Métropole pool, and `REFRESH_TOKEN_AUTH` returns no
new one — there is no rotation. Treat it as a way to reach an account whose
password sign-in is challenged, not as a lasting alternative to the password.
Cognito's risk score warms up as an address keeps presenting valid tokens, so
the password sign-in is usually accepted again afterwards.

Maintainers can regenerate the portal table from Veolia's national bundle:

```bash
python scripts/regenerate_portals.py
```

The script prints a candidate `VEOLIA_PORTALS` block and a diff against the
current table — review and edit `veolia_api/portals.py` manually.

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on reporting bugs, suggesting features, and submitting pull requests.

## Credits

This repository is inspired by the work done by @CorentinGrard. Thanks to him for his work.
It is a fork of [`Jezza34000/veolia-api`](https://github.com/Jezza34000/veolia-api).

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
