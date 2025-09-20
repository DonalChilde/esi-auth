"""ESI Authentication Library for EVE Online.

A simple library for managing EVE Online ESI authentication tokens.
"""

__version__ = "0.1.0"

# Public API exports
from .api import (
    authenticate_character,
    backup_characters,
    get_character,
    get_character_info,
    list_characters,
    load_characters,
    refresh_expired_tokens,
    refresh_token,
    remove_character,
    restore_characters,
    validate_token,
)
from .models import (
    AuthenticatedCharacters,
    AuthenticationError,
    CharacterInfo,
    CharacterToken,
    TokenRefreshError,
)
from .settings import (
    ESIAuthSettings,
    get_settings,
    set_production_profile,
    set_testing_profile,
)
from .storage import TokenStorage, TokenStorageError, get_token_storage

__all__ = [
    # Core API functions
    "authenticate_character",
    "load_characters",
    "list_characters",
    "get_character",
    "refresh_token",
    "refresh_expired_tokens",
    "remove_character",
    "validate_token",
    "get_character_info",
    "backup_characters",
    "restore_characters",
    # Models
    "CharacterToken",
    "AuthenticatedCharacters",
    "CharacterInfo",
    "AuthenticationError",
    "TokenRefreshError",
    "TokenStorageError",
    # Settings
    "ESIAuthSettings",
    "get_settings",
    "set_testing_profile",
    "set_production_profile",
    # Storage
    "TokenStorage",
    "get_token_storage",
]


def main() -> None:
    """Main entry point for the esi-auth CLI."""
    print("Hello from esi-auth!")
