# ESI Auth - An EVE Online Authentication Library

[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## Project Description

esi-auth is a library and cli for managing EVE Online ESI app credentials and authentication tokens. This library handles the complete OAuth2 PKCE authentication flow, token storage, and refresh operations for EVE Online's ESI API.

## Quick Start

### 1. Set Up EVE Application

First, create an EVE Online application at [EVE Developers](https://developers.eveonline.com/):

1. Create a new application
2. After your application has been created, view your application settings.
3. In that settings view, copy your application settings as json, and save to file.
4. You can use this file later to import your credentials to esi-auth.

### 2. Setup the Environment

On first run (try `esi-auth version`), esi-auth will create a directory in the default application location as defined by Typer. This directory will contain the program logs, the .env configuation file, and the auth store data file.

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

## Installation

This project uses uv for development, and uv is also the easiest way to run the project.

> uv docs:  
> [Astral - uv](https://docs.astral.sh/uv/)  
> [https://docs.astral.sh/uv/concepts/tools/](https://docs.astral.sh/uv/concepts/tools/)  
> [https://docs.astral.sh/uv/reference/cli/#uv-tool](https://docs.astral.sh/uv/reference/cli/#uv-tool)  
> [https://docs.astral.sh/uv/pip/packages/#installing-a-package](https://docs.astral.sh/uv/pip/packages/#installing-a-package)  
> [https://docs.astral.sh/uv/concepts/projects/dependencies/#dependency-sources](https://docs.astral.sh/uv/concepts/projects/dependencies/#dependency-sources)

To run with uv:

> Note the url format for tool install is the same as that for uv pip install:

```bash
# run esi-auth without installing
uvx --from git+https://github.com/DonalChilde/esi-auth@main esi-auth

# OR

# Install to Path
uv tool install --from git+https://github.com/DonalChilde/esi-auth@main esi-auth
# and run
esi-auth ARGS
```

## Development

### Download the source code:

```bash
git clone https://github.com/DonalChilde/esi-auth.git
cd esi-auth
uv sync
# activate the venv if desired
source ./.venv/bin/activate
```

### Use as a dependency in another project:

```toml
# in your pyproject.toml file, for a uv managed project
dependencies = ["esi-auth"]
[tool.uv.sources]
esi-auth = { git = "https://github.com/DonalChilde/esi-auth", branch = "main" }
```

### ruff settings for formatting and linting

```toml
[tool.ruff.lint]
select = ["B", "UP", "D", "DOC", "FIX", "I", "F401"]
# non-imperative-mood (D401)
ignore = ["D401", "D101"]
# extend-select = ["I"]

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.format]
docstring-code-format = true
docstring-code-line-length = 88
```

## Contributing

## License

MIT License - see LICENSE file for details.

## Support

- [Issues](https://github.com/DonalChilde/esi-auth/issues)
- EVE Online Developers: [developers.eveonline.com](https://developers.eveonline.com/)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.
