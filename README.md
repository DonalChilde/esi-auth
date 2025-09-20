# ESI Auth - EVE Online Authentication Library

A simple and robust Python library for managing EVE Online ESI authentication tokens. This library handles the complete OAuth2 authentication flow, token storage, and refresh operations for EVE Online's ESI (EVE Swagger Interface) API.

## Features

- 🔐 **Complete OAuth2 Flow**: Handles authorization, token exchange, and refresh
- 💾 **Persistent Storage**: JSON-based token storage with backup/restore capabilities
- 🔄 **Automatic Token Refresh**: Smart token refresh with configurable timing
- ⚙️ **Environment Profiles**: Support for testing and production configurations
- 🖥️ **CLI Interface**: Full-featured command-line interface
- 🧪 **Well Tested**: Comprehensive test suite with pytest
- 📚 **Type Safe**: Full type hints and Pydantic models
- 🪵 **Logging Support**: Structured logging throughout

## Installation

Install with pip (once published):

```bash
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
2. Set callback URL to `http://localhost:8080/callback`
3. Note your Client ID and Client Secret

### 2. Configure Environment

Set your application credentials:

```bash
export ESI_AUTH_CLIENT_ID="your_client_id_here"
export ESI_AUTH_CLIENT_SECRET="your_client_secret_here"
```

Or create a `.env` file:

```env
ESI_AUTH_CLIENT_ID=your_client_id_here
ESI_AUTH_CLIENT_SECRET=your_client_secret_here
```

### 3. Authenticate Your First Character

```python
import asyncio
from esi_auth import authenticate_character

# Authenticate a character (opens browser)
async def main():
    token = await authenticate_character([
        "esi-characters.read_character.v1",
        "esi-assets.read_assets.v1"
    ])
    print(f"Authenticated: {token.character_name}")

asyncio.run(main())
```

### 4. Use the CLI

```bash
# Authenticate a character
esi-auth auth --scope esi-characters.read_character.v1

# List authenticated characters
esi-auth list

# Refresh expired tokens
esi-auth refresh

# Get character information
esi-auth info 12345678

# Remove a character
esi-auth remove 12345678
```

## API Reference

### Core Functions

#### `authenticate_character(scopes=None)`

Authenticate a new character using OAuth2 flow.

```python
import asyncio
from esi_auth import authenticate_character

async def main():
    token = await authenticate_character([
        "esi-characters.read_character.v1"
    ])
    print(f"Authenticated: {token.character_name}")

asyncio.run(main())
```

#### `load_characters()`

Load all authenticated characters from storage.

```python
from esi_auth import load_characters

characters = load_characters()
for character_id, token in characters.characters.items():
    print(f"Character: {token.character_name}")
```

#### `list_characters()`

Get a list of all character tokens.

```python
from esi_auth import list_characters

characters = list_characters()
for token in characters:
    print(f"Character: {token.character_name}")
```

#### `refresh_token(character_token)`

Refresh a character's access token.

```python
import asyncio
from esi_auth import get_character, refresh_token

async def main():
    token = get_character(12345678)
    if token and token.needs_refresh():
        refreshed_token = await refresh_token(token)
        print(f"Token refreshed for: {refreshed_token.character_name}")

asyncio.run(main())
```

#### `refresh_expired_tokens()`

Refresh all expired or soon-to-expire tokens.

```python
import asyncio
from esi_auth import refresh_expired_tokens

async def main():
    results = await refresh_expired_tokens()
    for char_id, result in results.items():
        if isinstance(result, Exception):
            print(f"Failed to refresh {char_id}: {result}")
        else:
            print(f"Refreshed: {result.character_name}")

asyncio.run(main())
```

### Models

#### `CharacterToken`

Represents an authenticated character's token data.

```python
from esi_auth import CharacterToken

# Properties
token.character_id       # Character ID
token.character_name     # Character name
token.access_token       # Current access token
token.refresh_token      # Refresh token
token.expires_at         # Expiration time
token.scopes            # List of authorized scopes

# Methods
token.is_expired()       # Check if token is expired
token.needs_refresh()    # Check if token needs refresh
```

### Configuration

#### Environment Variables

| Variable                 | Description                   | Default            |
| ------------------------ | ----------------------------- | ------------------ |
| `ESI_AUTH_CLIENT_ID`     | EVE application client ID     | Required           |
| `ESI_AUTH_CLIENT_SECRET` | EVE application client secret | Required           |
| `ESI_AUTH_APP_NAME`      | Application name              | `pfmsoft-esi-auth` |
| `ESI_AUTH_CALLBACK_HOST` | OAuth callback host           | `localhost`        |
| `ESI_AUTH_CALLBACK_PORT` | OAuth callback port           | `8080`             |

#### Testing Profile

For testing, use the `ESI_AUTH_TEST_` prefix:

```bash
export ESI_AUTH_TEST_CLIENT_ID="test_client_id"
export ESI_AUTH_TEST_CLIENT_SECRET="test_client_secret"
```

Or programmatically:

```python
from esi_auth import set_testing_profile

set_testing_profile()
```

## CLI Usage

The CLI provides a complete interface for managing character authentication:

### Authentication

```bash
# Authenticate with basic character access
esi-auth auth

# Authenticate with specific scopes
esi-auth auth -s esi-characters.read_character.v1 -s esi-assets.read_assets.v1

# Use testing configuration
esi-auth --test auth
```

### Character Management

```bash
# List all characters
esi-auth list

# Get character information
esi-auth info 12345678

# Remove a character
esi-auth remove 12345678

# Remove without confirmation
esi-auth remove 12345678 --force
```

### Token Management

```bash
# Refresh specific character
esi-auth refresh 12345678

# Refresh all expired tokens
esi-auth refresh --all

# Validate tokens
esi-auth validate

# Validate specific character
esi-auth validate 12345678
```

### Backup and Restore

```bash
# Create backup
esi-auth backup

# Create backup to specific file
esi-auth backup -o my_backup.json

# Restore from backup
esi-auth restore backup.json

# Restore without confirmation
esi-auth restore backup.json --force
```

### Configuration

```bash
# Show current configuration
esi-auth config
```

## Advanced Usage

### Custom Storage Location

```python
from esi_auth.storage import TokenStorage
from pathlib import Path

# Use custom storage location
storage = TokenStorage(Path("/custom/path/tokens.json"))
characters = storage.load_characters()
```

### Error Handling

```python
import asyncio
from esi_auth import authenticate_character, AuthenticationError

async def main():
    try:
        token = await authenticate_character()
    except AuthenticationError as e:
        print(f"Authentication failed: {e}")

asyncio.run(main())
```

### Logging

```python
import logging
from esi_auth import authenticate_character

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# The library uses structured logging
logger = logging.getLogger("esi_auth")
```

## Development

### Setup

```bash
git clone https://github.com/DonalChilde/esi-auth.git
cd esi-auth
uv sync
```

### Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=esi_auth

# Run specific test file
uv run pytest tests/test_models.py
```

### Linting

```bash
# Run ruff linting
uv run ruff check

# Auto-fix issues
uv run ruff check --fix

# Format code
uv run ruff format
```

## API Scopes

Common EVE Online ESI scopes you might need:

| Scope                                 | Description                 |
| ------------------------------------- | --------------------------- |
| `esi-characters.read_character.v1`    | Basic character information |
| `esi-assets.read_assets.v1`           | Character assets            |
| `esi-wallet.read_character_wallet.v1` | Character wallet            |
| `esi-skills.read_skills.v1`           | Character skills            |
| `esi-clones.read_clones.v1`           | Character clones            |

See the [EVE ESI Documentation](https://esi.evetech.net/) for a complete list.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run linting and tests
6. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

- [Issues](https://github.com/DonalChilde/esi-auth/issues)
- [Discussions](https://github.com/DonalChilde/esi-auth/discussions)
- EVE Online Developers: [developers.eveonline.com](https://developers.eveonline.com/)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.
