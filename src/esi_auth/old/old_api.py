"""Core API functions for ESI authentication.

This module provides the main public API for the esi-auth library,
offering high-level functions for character authentication, token management,
and character operations.
"""

import logging
from typing import Any

from .old_auth import ESIAuthenticator
from .old_models import AuthenticatedCharacters, CharacterToken
from .old_storage import TokenStorage, get_token_storage

logger = logging.getLogger(__name__)


async def authenticate_character(
    scopes: list[str] | None = None,
    storage: TokenStorage | None = None,
    auto_save: bool = True,
) -> CharacterToken:
    """Authenticate a new character using OAuth2 flow.

    This function runs the complete OAuth2 authentication flow,
    including opening a browser for user authorization and storing
    the resulting token.

    Args:
        scopes: List of ESI scopes to request. If None, uses basic character access.
        storage: Optional custom TokenStorage instance. If None, uses default.
        auto_save: Whether to automatically save the token to storage.

    Returns:
        CharacterToken with authentication data.

    Raises:
        AuthenticationError: If authentication fails.
        TokenStorageError: If saving fails and auto_save is True.

    Example:
        >>> token = await authenticate_character(["esi-characters.read_character.v1"])
        >>> print(f"Authenticated: {token.character_name}")
    """
    logger.info("Starting character authentication")

    if storage is None:
        storage = get_token_storage()

    async with ESIAuthenticator() as authenticator:
        character_token = await authenticator.authenticate_character(scopes)

    if auto_save:
        logger.debug(f"Saving character token for {character_token.character_name}")
        storage.add_character(character_token)

    logger.info(
        f"Successfully authenticated character: {character_token.character_name}"
    )
    return character_token


def load_characters(storage: TokenStorage | None = None) -> AuthenticatedCharacters:
    """Load all authenticated characters from storage.

    Args:
        storage: Optional custom TokenStorage instance. If None, uses default.

    Returns:
        AuthenticatedCharacters instance with all stored character tokens.

    Raises:
        TokenStorageError: If loading from storage fails.

    Example:
        >>> characters = load_characters()
        >>> for token in characters.list_characters():
        ...     print(f"Character: {token.character_name}")
    """
    logger.debug("Loading characters from storage")

    if storage is None:
        storage = get_token_storage()

    return storage.load_characters()


def get_character(
    character_id: int, storage: TokenStorage | None = None
) -> CharacterToken | None:
    """Get a specific character's token from storage.

    Args:
        character_id: The character ID to retrieve.
        storage: Optional custom TokenStorage instance. If None, uses default.

    Returns:
        CharacterToken if found, None otherwise.

    Raises:
        TokenStorageError: If loading from storage fails.

    Example:
        >>> token = get_character(12345678)
        >>> if token:
        ...     print(f"Found: {token.character_name}")
    """
    logger.debug(f"Getting character {character_id} from storage")

    if storage is None:
        storage = get_token_storage()

    return storage.get_character(character_id)


def list_characters(storage: TokenStorage | None = None) -> list[CharacterToken]:
    """List all authenticated characters.

    Args:
        storage: Optional custom TokenStorage instance. If None, uses default.

    Returns:
        List of all CharacterToken objects.

    Raises:
        TokenStorageError: If loading from storage fails.

    Example:
        >>> characters = list_characters()
        >>> print(f"Found {len(characters)} characters")
    """
    logger.debug("Listing all characters from storage")

    if storage is None:
        storage = get_token_storage()

    return storage.list_characters()


async def refresh_token(
    character_token: CharacterToken,
    storage: TokenStorage | None = None,
    auto_save: bool = True,
) -> CharacterToken:
    """Refresh a character's access token.

    Args:
        character_token: The character token to refresh.
        storage: Optional custom TokenStorage instance. If None, uses default.
        auto_save: Whether to automatically save the refreshed token.

    Returns:
        Updated CharacterToken with new access token.

    Raises:
        TokenRefreshError: If token refresh fails.
        TokenStorageError: If saving fails and auto_save is True.

    Example:
        >>> token = get_character(12345678)
        >>> if token and token.needs_refresh():
        ...     token = await refresh_token(token)
    """
    logger.info(f"Refreshing token for character {character_token.character_name}")

    if storage is None:
        storage = get_token_storage()

    async with ESIAuthenticator() as authenticator:
        refreshed_token = await authenticator.refresh_character_token(character_token)

    if auto_save:
        logger.debug(f"Saving refreshed token for {refreshed_token.character_name}")
        storage.add_character(refreshed_token)

    logger.info(f"Successfully refreshed token for {refreshed_token.character_name}")
    return refreshed_token


async def refresh_expired_tokens(
    storage: TokenStorage | None = None, buffer_minutes: int = 5, auto_save: bool = True
) -> dict[int, CharacterToken | Exception]:
    """Refresh all expired or soon-to-expire tokens.

    Args:
        storage: Optional custom TokenStorage instance. If None, uses default.
        buffer_minutes: Minutes before expiry to consider needing refresh.
        auto_save: Whether to automatically save refreshed tokens.

    Returns:
        Dictionary mapping character_id to either refreshed CharacterToken
        or Exception if refresh failed.

    Example:
        >>> results = await refresh_expired_tokens()
        >>> for char_id, result in results.items():
        ...     if isinstance(result, Exception):
        ...         print(f"Failed to refresh {char_id}: {result}")
        ...     else:
        ...         print(f"Refreshed: {result.character_name}")
    """
    logger.info(f"Refreshing expired tokens (buffer: {buffer_minutes} minutes)")

    if storage is None:
        storage = get_token_storage()

    characters = storage.load_characters()
    tokens_to_refresh = characters.get_tokens_needing_refresh(buffer_minutes)

    if not tokens_to_refresh:
        logger.info("No tokens need refreshing")
        return {}

    logger.info(f"Found {len(tokens_to_refresh)} tokens to refresh")
    results: dict[int, CharacterToken | Exception] = {}

    async with ESIAuthenticator() as authenticator:
        for token in tokens_to_refresh:
            try:
                logger.debug(f"Refreshing token for {token.character_name}")
                refreshed_token = await authenticator.refresh_character_token(token)
                results[token.character_id] = refreshed_token

                if auto_save:
                    storage.add_character(refreshed_token)

            except Exception as e:
                logger.error(f"Failed to refresh token for {token.character_name}: {e}")
                results[token.character_id] = e

    successful_refreshes = sum(
        1 for result in results.values() if not isinstance(result, Exception)
    )
    logger.info(
        f"Refreshed {successful_refreshes}/{len(tokens_to_refresh)} tokens successfully"
    )

    return results


def remove_character(character_id: int, storage: TokenStorage | None = None) -> bool:
    """Remove a character from storage.

    Args:
        character_id: The character ID to remove.
        storage: Optional custom TokenStorage instance. If None, uses default.

    Returns:
        True if character was removed, False if not found.

    Raises:
        TokenStorageError: If storage operation fails.

    Example:
        >>> removed = remove_character(12345678)
        >>> if removed:
        ...     print("Character removed successfully")
    """
    logger.info(f"Removing character {character_id}")

    if storage is None:
        storage = get_token_storage()

    return storage.remove_character(character_id)


async def validate_token(character_token: CharacterToken) -> bool:
    """Validate that a character token is still valid.

    This function checks if the token can still be used to make
    authenticated requests to the ESI API.

    Args:
        character_token: The character token to validate.

    Returns:
        True if token is valid, False otherwise.

    Example:
        >>> token = get_character(12345678)
        >>> if token and await validate_token(token):
        ...     print("Token is valid")
        >>> else:
        ...     print("Token needs refresh or re-authentication")
    """
    logger.debug(f"Validating token for {character_token.character_name}")

    try:
        async with ESIAuthenticator() as authenticator:
            await authenticator.get_character_info(character_token.access_token)

        logger.debug(
            f"Token validation successful for {character_token.character_name}"
        )
        return True

    except Exception as e:
        logger.debug(
            f"Token validation failed for {character_token.character_name}: {e}"
        )
        return False


async def get_character_info(character_token: CharacterToken) -> Any:
    """Get current character information from ESI.

    Args:
        character_token: The character token to use for API access.

    Returns:
        CharacterInfo with current character data from ESI.

    Raises:
        AuthenticationError: If the request fails.

    Example:
        >>> token = get_character(12345678)
        >>> if token:
        ...     info = await get_character_info(token)
        ...     print(f"Character: {info.name} in corp {info.corporation_id}")
    """
    logger.debug(f"Getting character info for {character_token.character_name}")

    async with ESIAuthenticator() as authenticator:
        return await authenticator.get_character_info(character_token.access_token)


def backup_characters(
    backup_path: Any | None = None, storage: TokenStorage | None = None
) -> Any:
    """Create a backup of all character tokens.

    Args:
        backup_path: Optional custom backup path. If None, uses timestamped name.
        storage: Optional custom TokenStorage instance. If None, uses default.

    Returns:
        Path to the created backup file.

    Raises:
        TokenStorageError: If backup creation fails.

    Example:
        >>> backup_file = backup_characters()
        >>> print(f"Backup created: {backup_file}")
    """
    logger.info("Creating character tokens backup")

    if storage is None:
        storage = get_token_storage()

    return storage.backup_storage(backup_path)


def restore_characters(backup_path: Any, storage: TokenStorage | None = None) -> None:
    """Restore character tokens from a backup file.

    Args:
        backup_path: Path to the backup file to restore from.
        storage: Optional custom TokenStorage instance. If None, uses default.

    Raises:
        TokenStorageError: If restore operation fails.

    Example:
        >>> restore_characters("/path/to/backup.json")
        >>> print("Characters restored from backup")
    """
    logger.info(f"Restoring characters from backup: {backup_path}")

    if storage is None:
        storage = get_token_storage()

    storage.restore_from_backup(backup_path)
