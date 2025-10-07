# ESI Auth - EVE Online Authentication Library

A simple and robust Python library for managing EVE Online ESI authentication tokens. This library handles the complete OAuth2 authentication flow, token storage, and refresh operations for EVE Online's ESI (EVE Swagger Interface) API.

## Features

- 🔐 **Complete OAuth2 Flow**: Handles authorization, token exchange, and refresh
- 💾 **Persistent Storage**: JSON-based token storage with backup/restore capabilities
- 🔄 **Automatic Token Refresh**: Smart token refresh with configurable timing
- ⚙️ **Environment Profiles**: Support for configuration through .env files.
- 🖥️ **CLI Interface**: Full-featured command-line interface
- 🧪 **Well Tested**: Comprehensive test suite with pytest - WIP

## Installation

Install with pip (once published):

```bash
# Not published to pypi yet...
pip install esi-auth
```

Or for development:

```bash
git clone https://github.com/DonalChilde/esi-auth.git
cd esi-auth
uv sync
```

## Quick Start

### 1. Set Up EVE Application

First, create an EVE Online application at [EVE Developers](https://developers.eveonline.com/):

1. Create a new application
2. After your application has been created, view your application settings.
3. In that settings view, copy your application settings as json, and save to file.
4. You can use this file later to import your credentials to esi-auth.

### 2. Configure Environment

On first run, esi-auth will generate an .env file in the application directory.
You must set some of the env variables in order to use esi-auth.

Open the .env file in a text editor and set the following values:

```bash
ESI_AUTH_CHARACTER_NAME=Unknown
ESI_AUTH_USER_EMAIL=Unknown
ESI_AUTH_USER_APP_NAME=Unknown
ESI_AUTH_USER_APP_VERSION=Unknown

```

The .env file must be located in the application directory.
You can see the app directory by running `esi-auth version`

You can also generate an .example.env file with `esi-auth util generate-example-env`.

### 3. Add your credentials to esi-auth

Add your credentials to esi-auth by running `esi-auth credentials add <path-to-credentials-file>`

For convenience, you can supply an alias for you credentials. If no alias is provided, one will be generated from your app name.

e.g. `esi-auth credentials add <path-to-credentials-file> -a <short-unique-name-for-your-app>`

Credentials can be retrieved later either by client_id, or alias.

### 4. Authenticate Your First Character

From the terminal, run `esi-auth tokens add -i <client_id>` or `esi-auth tokens add -a <your-app-alias>`

This should open your default browser to the Eve login page.

If it does not, you can either click on the link in the terminal, or see the logs for the url which you can copy and paste into your web browser.

## API Reference

### Core Functions

At present there is only one api function, one function meant to be used by other programs.

#### `get_authorized_characters`

This function will return a dict of CharacterTokens indexed by character id for a specific set of credentials. CharacterToken contains the token needed to make authorization required calls to the Eve ESI.
The dict is created new with each call to `get_authorized_characters`, changes to the dict will not affect the underlying data store.
During the call, the characters are checked for expired, or soon to expire tokens, and those tokens are refreshed.
It is reasonable to call `get_authorized_characters` before each esi call, or group of calls, to ensure there are no problems with token timeout.
The default `buffer` is 5 minutes. Tokens that have expired, or will expire in less than the `buffer` will be refreshed.

## License

MIT License - see LICENSE file for details.

## Support

- [Issues](https://github.com/DonalChilde/esi-auth/issues)
- EVE Online Developers: [developers.eveonline.com](https://developers.eveonline.com/)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.
