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
2. Set callback URL. esi-auth defaults to `http://localhost:8080/callback`
3. Note your Client ID and Client Secret
4. After your application has been created, view your application settings.
5. In that settings view, copy your application settings as json, and save to file.
6. You can use this file later to generate an .env file that stores the settings for esi-auth.

### 2. Configure Environment

Set your application credentials:

```bash
export ESI_AUTH_CLIENT_ID="your_client_id_here"
export ESI_AUTH_CLIENT_SECRET="your_client_secret_here"
export ESI_AUTH_CALLBACK_HOST="localhost"
export ESI_AUTH_CALLBACK_PORT=8080
export ESI_AUTH_CALLBACK_ROUTE="/callback"
export ESI_AUTH_CHARACTER_NAME="Unknown"
export ESI_AUTH_USER_EMAIL="Unknown"
export ESI_AUTH_USER_APP_NAME="Unknown"
export ESI_AUTH_USER_APP_VERSION="Unknown"
```

Or create a `.env` file:

```env
ESI_AUTH_CLIENT_ID=your_client_id_here
ESI_AUTH_CLIENT_SECRET=your_client_secret_here
ESI_AUTH_CALLBACK_HOST="localhost"
ESI_AUTH_CALLBACK_PORT=8080
ESI_AUTH_CALLBACK_ROUTE="/callback"
ESI_AUTH_CHARACTER_NAME="Unknown"
ESI_AUTH_USER_EMAIL="Unknown"
ESI_AUTH_USER_APP_NAME="Unknown"
ESI_AUTH_USER_APP_VERSION="Unknown"
```

The .env file can be located in the current working directory, or in the app directory.
You can see the app directory by running `esi-auth version`

You can generate an .env file with `esi-auth util`. NOTE this needs some polish.

### 3. Authenticate Your First Character

From the terminal, run `esi-auth store add`

This should open your default browser to the Eve login page.

If it does not, you can either click on the link in the terminal, or see the logs for the url which you can copy and paste into your web broswer.

## API Reference

### Core Functions

At present there is only one api function, one function meant to be used by other programs.

#### `get_authorized_characters`

This function will return a dict of CharacterTokens indexed by character id. CharacterToken contains the token needed to make authorization required calls to the Eve ESI.
The dict is created new with each call to `get_authorized_characters`
During the call, the characters are checked for expired, or soon to expire tokens, and those tokens are refreshed.
It is reasonable to call `get_authorized_characters` before each esi call, or group of calls, to ensure there are no problems with token timeout.
The default `buffer` is 5 minutes. Tokens thathave expired, or will expire in less than the `buffer` will be refreshed.

## License

MIT License - see LICENSE file for details.

## Support

- [Issues](https://github.com/DonalChilde/esi-auth/issues)
- EVE Online Developers: [developers.eveonline.com](https://developers.eveonline.com/)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.
