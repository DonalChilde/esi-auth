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

On first run (try `esi-auth version`), esi-auth will create a directory in the default application location as defined by Typer. This directory will contain the program logs and data files.
### 3. Add your app credentials to esi-auth

Add your credentials to esi-auth by running `esi-auth creds add <path-to-credentials-file>`

Credentials must be in json format. 



### 4. Authenticate Your First Character

From the terminal, run `esi-auth tokens add` 

Click on the link in the terminal window, or copy and paste the url into your web browser.

Log into EVE Online, select your character, and approve the list of scopes.

You can use the `-t` flag to make a test request to the EVE Esi, assuming your app includes the `esi-skills.read_skills.v1` scope.



## API Usage

This app will normally be used from inside another app, such as esi-link, which will make use of the authenticated tokens. The cli is designed such that the commands should be easy to add on to another typer based project if desired.

TODO more explicit integration examples.

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

See the pyproject.toml file

## Contributing

## License

MIT License - see LICENSE file for details.

## Support

- [Issues](https://github.com/DonalChilde/esi-auth/issues)
- EVE Online Developers: [developers.eveonline.com](https://developers.eveonline.com/)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.
