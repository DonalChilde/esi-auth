# """Token storage implementations for esi-auth."""

# import asyncio
# import logging
# from pathlib import Path
# from typing import Protocol

# from pydantic import ValidationError

# from esi_auth.auth import (
#     TokenRefreshError,
#     get_oauth_params,
#     refresh_multiple_characters,
# )
# from esi_auth.models import AuthenticatedCharacters, CharacterToken, EveCredentials
# from esi_auth.settings import get_settings

# logger = logging.getLogger(__name__)


# class TokenStorageError(Exception):
#     """Exception raised during token storage operations.

#     This exception is raised when token storage or retrieval fails.
#     """

#     def __init__(self, message: str, path: Path | None = None):
#         """Initialize the token storage error.

#         Args:
#             message: Human-readable error message.
#             path: Optional file path related to the error.
#         """
#         super().__init__(message)
#         self.message = message
#         self.path = path


# class TokenStorageProtocol(Protocol):
#     def add_character(
#         self, credentials: EveCredentials, character_token: CharacterToken
#     ) -> None:
#         """Add or update a character's token data.

#         Args:
#             credentials: The EveCredentials associated with the character.
#             character_token: The CharacterToken to add or update.
#         """
#         ...

#     def remove_character(self, credentials: EveCredentials, character_id: int) -> bool:
#         """Remove a character from storage.

#         Args:
#             credentials: The EveCredentials associated with the character.
#             character_id: The character ID to remove.

#         Returns:
#             True if character was removed, False if not found.
#         """
#         ...

#     def get_character(
#         self, credentials: EveCredentials, character_id: int
#     ) -> CharacterToken | None:
#         """Get a specific character's token from storage.

#         Args:
#             credentials: The EveCredentials associated with the character.
#             character_id: The character ID to retrieve.

#         Returns:
#             The CharacterToken if found, None otherwise.
#         """
#         ...

#     def refresh_characters(
#         self, credentials: EveCredentials, characters: list[CharacterToken]
#     ) -> tuple[list[int], list[int]]:
#         """Refresh multiple characters' token data.

#         Args:
#             credentials: The EveCredentials associated with the characters.
#             characters: A list of CharacterToken instances to refresh.

#         Returns:
#             A tuple containing two lists:
#                 - List of character IDs successfully refreshed.
#                 - List of character IDs that failed to refresh.
#         """
#         ...

#     def list_characters(self, credentials: EveCredentials) -> list[CharacterToken]:
#         """List all stored characters.

#         Args:
#             credentials: The EveCredentials associated with the characters.

#         Returns:
#             A list of all CharacterToken instances in storage.
#         """
#         ...

#     def list_expired_characters(
#         self, credentials: EveCredentials
#     ) -> list[CharacterToken]:
#         """List all characters with expired tokens.

#         Args:
#             credentials: The EveCredentials associated with the characters.

#         Returns:
#             A list of CharacterToken instances whose access tokens have expired.
#         """
#         ...

#     def list_characters_needing_refresh(
#         self, credentials: EveCredentials, buffer_minutes: int = 5
#     ) -> list[CharacterToken]:
#         """List all characters whose tokens need refreshing.

#         This includes tokens that are about to expire within the specified buffer time.

#         Args:
#             credentials: The EveCredentials associated with the characters.
#             buffer_minutes: The buffer time in minutes before actual expiration to consider for refresh.

#         Returns:
#             A list of CharacterToken instances that need their access tokens refreshed.
#         """
#         ...


# class TokenStoreJson(TokenStorageProtocol):
#     """A simple JSON file-based implementation of TokenStorageProtocol.

#     This class provides methods to store and retrieve character tokens
#     using a JSON file as the backend storage.
#     """

#     def __init__(self, storage_path: Path | None = None):
#         """Initialize the token storage.

#         Args:
#             storage_path: Optional custom path for token storage.
#                          If None, uses path from application settings.
#         """
#         settings = get_settings()
#         self.storage_path = (
#             storage_path or settings.token_store_dir / settings.token_file_name
#         )
#         logger.info(f"TokenStorage initialized with path: {self.storage_path}")

#     def _load_characters(self) -> AuthenticatedCharacters:
#         """Load authenticated characters from storage.

#         Returns:
#             AuthenticatedCharacters instance with loaded data.
#             Returns empty collection if file doesn't exist.

#         Raises:
#             TokenStorageError: If file exists but cannot be loaded or parsed.
#         """
#         if not self.storage_path.is_file():
#             logger.info(
#                 f"Token file does not exist: {self.storage_path}, creating empty store."
#             )
#             return AuthenticatedCharacters()

#         try:
#             logger.debug(f"Loading characters from: {self.storage_path}")
#             with open(self.storage_path, encoding="utf-8") as f:
#                 data = AuthenticatedCharacters.model_validate_json(f.read())
#             logger.info(f"Loaded {len(data.characters)} characters from storage")
#             return data

#         except ValidationError as e:
#             error_msg = f"Validation error in token file: {e}"
#             logger.error(error_msg)
#             raise TokenStorageError(error_msg, self.storage_path) from e
#         except Exception as e:
#             error_msg = f"Failed to load token file: {e}"
#             logger.error(error_msg)
#             raise TokenStorageError(error_msg, self.storage_path) from e

#     def _save_characters(self, characters: AuthenticatedCharacters) -> None:
#         """Save authenticated characters to storage.

#         Args:
#             characters: The AuthenticatedCharacters instance to save.

#         Raises:
#             TokenStorageError: If the data cannot be saved.
#         """
#         try:
#             # Ensure the directory exists
#             self.storage_path.parent.mkdir(parents=True, exist_ok=True)

#             logger.debug(
#                 f"Saving {len(characters.characters)} characters to: {self.storage_path}"
#             )

#             # Create a temporary file for atomic write
#             temp_path = self.storage_path.with_suffix(".tmp")

#             with open(temp_path, "w", encoding="utf-8") as f:
#                 f.write(characters.model_dump_json(indent=2))

#             # Atomic move to final location
#             temp_path.replace(self.storage_path)

#             logger.info(f"Successfully saved characters to storage")

#         except Exception as e:
#             # Clean up temp file if it exists
#             if "temp_path" in locals() and temp_path.exists():  # type: ignore
#                 temp_path.unlink(missing_ok=True)  # type: ignore

#             error_msg = f"Failed to save token file: {e}"
#             logger.error(error_msg)
#             raise TokenStorageError(error_msg, self.storage_path) from e

#     @classmethod
#     def init_store(cls, storage_path: Path) -> "TokenStoreJson":
#         """Initialize the token store, creating an empty file if needed.

#         Args:
#             storage_path: Optional custom path for token storage.

#         Returns:
#             An instance of TokenStoreJson.
#         """
#         if storage_path.is_file():
#             logger.info(f"File already exists at: {storage_path}")
#             raise TokenStorageError(
#                 f"File already exists at: {storage_path}", storage_path
#             )
#         store = cls(storage_path)
#         characters = AuthenticatedCharacters()
#         store._save_characters(characters)
#         logger.info(f"Initialized new token store at: {storage_path}")
#         return store

#     def add_character(
#         self, credentials: EveCredentials, character_token: CharacterToken
#     ) -> None:
#         """Add or update a character's token in storage.

#         Args:
#             credentials: The EveCredentials associated with the character.
#             character_token: The CharacterToken to add or update.

#         Raises:
#             TokenStorageError: If the operation fails.
#         """
#         logger.debug(
#             f"Adding/updating character {character_token.character_id} ({character_token.character_name})"
#         )

#         characters = self._load_characters()
#         characters.add_character(credentials.client_id, character_token)
#         self._save_characters(characters)

#     def remove_character(self, credentials: EveCredentials, character_id: int) -> bool:
#         """Remove a character from storage.

#         Args:
#             credentials: The EveCredentials associated with the character.
#             character_id: The character ID to remove.

#         Returns:
#             True if character was removed, False if not found.

#         Raises:
#             TokenStorageError: If the operation fails.
#         """
#         logger.debug(f"Removing character {character_id}")

#         characters = self._load_characters()
#         removed = characters.remove_character(credentials.client_id, character_id)

#         if removed:
#             self._save_characters(characters)
#             logger.info(f"Successfully removed character {character_id}")
#         else:
#             logger.warning(f"Character {character_id} not found for removal")

#         return removed

#     def get_character(
#         self, credentials: EveCredentials, character_id: int
#     ) -> CharacterToken | None:
#         """Get a specific character's token from storage.

#         Args:
#             credentials: The EveCredentials associated with the character.
#             character_id: The character ID to retrieve.

#         Returns:
#             The CharacterToken if found, None otherwise.

#         Raises:
#             TokenStorageError: If the operation fails.
#         """
#         logger.debug(f"Retrieving character {character_id}")

#         characters = self._load_characters()
#         return characters.get_character(credentials.client_id, character_id)

#     def list_characters(self, credentials: EveCredentials) -> list[CharacterToken]:
#         """List all characters in storage.

#         Args:
#             credentials: The EveCredentials associated with the characters.

#         Returns:
#             List of all CharacterToken objects.

#         Raises:
#             TokenStorageError: If the operation fails.
#         """
#         logger.debug("Listing all characters")

#         characters = self._load_characters()
#         return characters.list_characters(credentials.client_id)

#     def refresh_characters(
#         self, credentials: EveCredentials, characters: list[CharacterToken]
#     ) -> tuple[list[int], list[int]]:
#         """Refresh multiple characters' token data.

#         Args:
#             credentials: The EveCredentials associated with the characters.
#             characters: A list of CharacterToken instances to refresh.

#         Returns:
#             A tuple containing two lists:
#                 - List of character IDs successfully refreshed.
#                 - List of character IDs that failed to refresh.

#         Raises:
#             TokenStorageError: If the operation fails.
#         """
#         success: list[CharacterToken] = []
#         failure: list[Exception] = []
#         logger.debug(f"Refreshing {len(characters)} characters")
#         oauth_params = get_oauth_params()
#         refreshed_tokens = asyncio.run(
#             refresh_multiple_characters(
#                 credentials=credentials,
#                 oauth_params=oauth_params,
#                 character_tokens=characters,
#             )
#         )
#         for token in refreshed_tokens:
#             if isinstance(token, Exception):
#                 logger.error(f"Failed to refresh token: {token}")
#                 failure.append(token)
#             elif isinstance(token, CharacterToken):  # pyright: ignore[reportUnnecessaryIsInstance]
#                 logger.debug(
#                     f"Refreshed character {token.character_id} ({token.character_name})"
#                 )
#                 success.append(token)
#             else:
#                 raise ValueError(f"Unexpected type in refreshed tokens: {type(token)}")
#         for token in success:
#             # Update storage with refreshed token
#             self.add_character(credentials=credentials, character_token=token)

#         for token in refreshed_tokens:
#             if isinstance(token, TokenRefreshError):
#                 logger.error(
#                     f"Failed to refresh token: {token.character_id} - {token.message}"
#                 )

#         if len(success) < len(characters):
#             logger.warning(
#                 f"Refreshed {len(success)}/{len(characters)} characters successfully"
#             )
#         success_ids = [t.character_id for t in success]
#         failure_ids = [
#             t.character_id for t in failure if isinstance(t, TokenRefreshError)
#         ]
#         return (success_ids, failure_ids)

#     def list_expired_characters(
#         self, credentials: EveCredentials
#     ) -> list[CharacterToken]:
#         """List all characters with expired tokens.

#         Args:
#             credentials: The EveCredentials associated with the characters.

#         Returns:
#             A list of CharacterToken instances whose access tokens have expired.
#         """
#         logger.debug("Listing expired characters")

#         characters = self._load_characters()
#         return characters.get_expired_tokens(client_id=credentials.client_id)

#     def list_characters_needing_refresh(
#         self, credentials: EveCredentials, buffer_minutes: int = 5
#     ) -> list[CharacterToken]:
#         """List all characters whose tokens need refreshing.

#         Args:
#             credentials: The EveCredentials associated with the characters.
#             buffer_minutes: Minutes before actual expiration to consider a token as needing refresh.
#                 Should not exceed 15 minutes, as the starting lifetime for a refreshed token is 20 minutes.

#         Returns:
#             A list of CharacterToken instances that need their access tokens refreshed.
#         """
#         if buffer_minutes < 0:
#             raise ValueError("buffer_minutes must be non-negative")
#         if buffer_minutes > 15:
#             raise ValueError("buffer_minutes should not exceed 15 minutes")
#         logger.debug(
#             f"Listing characters needing refresh with buffer {buffer_minutes}m"
#         )
#         characters = self._load_characters()
#         return characters.get_tokens_needing_refresh(
#             client_id=credentials.client_id, buffer_minutes=buffer_minutes
#         )


# def get_token_store():
#     """Get the token store instance."""
#     settings = get_settings()
#     return TokenStoreJson(settings.token_store_dir / settings.token_file_name)
