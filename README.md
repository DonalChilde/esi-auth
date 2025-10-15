# ESI Auth - EVE Online Authentication Library

A simple and robust Python library for managing EVE Online ESI app credentials and authentication tokens. This library handles the complete OAuth2 authentication flow, token storage, and refresh operations for EVE Online's ESI (EVE Swagger Interface) API.

## Features

- 🔐 **Complete PKCE OAuth2 Flow**: Handles authorization, token exchange, and refresh
- 💾 **Persistent Storage**: JSON-based credential and token storage in a single file.
- 🔄 **Automatic Token Refresh**: Smart token refresh with configurable timing.
- 🖥️ **CLI Interface**: Full-featured command-line interface

## TODO

- Testing
- pypi release

## Installation

Install with pip (once published):

```bash
# Not published to pypi yet...
pip install esi-auth
```

Install with uv:

```bash
# run esi-auth without installing to Path
uvx --from git+https://github.com/DonalChilde/esi-auth@main esi-auth

# OR

# Install to Path
uv tool install --from git+https://github.com/DonalChilde/esi-auth@main esi-auth
# and run
uvx esi-auth


```

Or for development:

```bash
git clone https://github.com/DonalChilde/esi-auth.git
cd esi-auth
uv sync
```

For use in a project:

```toml
# in your pyproject file, for a uv managed project
dependencies = ["esi-auth"]
[tool.uv.sources]
esi-auth = { git = "https://github.com/DonalChilde/esi-auth", branch = "main" }
```

## Quick Start

### 1. Set Up EVE Application

First, create an EVE Online application at [EVE Developers](https://developers.eveonline.com/):

1. Create a new application
2. After your application has been created, view your application settings.
3. In that settings view, copy your application settings as json, and save to file.
4. You can use this file later to import your credentials to esi-auth.

### 2. Setup the Environment

On first run, esi-auth will create a directory in the default application location as defined by Typer. This directory will contain the program logs, and the auth-store.json data file. There is an option to start the cli with a custom location for the auth store file. use the command `esi-auth version` to see the full path to the auth-store.json file.

### 3. Add your credentials to esi-auth

Add your credentials to esi-auth by running `esi-auth credentials add <path-to-credentials-file>`

For convenience, you can supply an alias for you credentials. If no alias is provided, one will be generated from your app name. Aliases and client_id's must be unique within each auth store file.

e.g. `esi-auth credentials add <path-to-credentials-file> -a <short-unique-name-for-your-app>`

Credentials can be retrieved later either by client_id, or alias.

### 4. Authenticate Your First Character

From the terminal, run `esi-auth tokens add -i <client_id>` or `esi-auth tokens add -a <your-app-alias>`

This should open your default browser to the Eve login page.

If it does not, you can either click on the link in the terminal, or see the logs for the url which you can copy and paste into your web browser. If you get a page noit found error for your callback page, try reloading the page. Sometimes the server takes a tick to load up.

## API Usage

The primary path for auth store modification should be through the esi-auth CLI. For access to the CharacterTokens from a third party app, that app can use the TokenManager object. This allows a third party app to get a copy of all the tokens for a particular client alias. Each time tokens are requested, the store file will be loaded, and the tokens checked for refresh.

## License

MIT License - see LICENSE file for details.

## Support

- [Issues](https://github.com/DonalChilde/esi-auth/issues)
- EVE Online Developers: [developers.eveonline.com](https://developers.eveonline.com/)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.
