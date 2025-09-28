import logging
from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

from esi_auth.models import AuthenticatedCharacters, CharacterToken
from esi_auth.settings import get_settings

logger = logging.getLogger(__name__)


class TokenStorageError(Exception):
    """Exception raised during token storage operations.

    This exception is raised when token storage or retrieval fails.
    """

    def __init__(self, message: str, path: Path | None = None):
        """Initialize the token storage error.

        Args:
            message: Human-readable error message.
            path: Optional file path related to the error.
        """
        super().__init__(message)
        self.message = message
        self.path = path


class TokenStorageProtocol(Protocol):
    def add_character(self, token: CharacterToken) -> None:
        """Add or update a character's token data.

        Args:
            token: The CharacterToken to add or update.
        """
        ...

    def remove_character(self, character_id: int) -> bool:
        """Remove a character from storage.

        Args:
            character_id: The character ID to remove.

        Returns:
            True if character was removed, False if not found.
        """
        ...

    def get_character(self, character_id: int) -> CharacterToken | None:
        """Get a specific character's token from storage.

        Args:
            character_id: The character ID to retrieve.

        Returns:
            The CharacterToken if found, None otherwise.
        """
        ...

    def list_characters(self) -> list[CharacterToken]:
        """List all stored characters.

        Returns:
            A list of all CharacterToken instances in storage.
        """
        ...

    def list_expired_characters(self) -> list[CharacterToken]:
        """List all characters with expired tokens.

        Returns:
            A list of CharacterToken instances whose access tokens have expired.
        """
        ...

    def list_characters_needing_refresh(
        self, buffer_minutes: int = 5
    ) -> list[CharacterToken]:
        """List all characters whose tokens need refreshing.

        Args:
            buffer_minutes: The buffer time in minutes before actual expiration to consider for refresh.

        Returns:
            A list of CharacterToken instances that need their access tokens refreshed.
        """
        ...


class TokenStoreJson(TokenStorageProtocol):
    """A simple JSON file-based implementation of TokenStorageProtocol.

    This class provides methods to store and retrieve character tokens
    using a JSON file as the backend storage.
    """

    def __init__(self, storage_path: Path | None = None):
        """Initialize the token storage.

        Args:
            storage_path: Optional custom path for token storage.
                         If None, uses path from application settings.
        """
        settings = get_settings()
        self.storage_path = (
            storage_path or settings.token_store_dir / settings.token_file_name
        )
        logger.info(f"TokenStorage initialized with path: {self.storage_path}")

    def _load_characters(self) -> AuthenticatedCharacters:
        """Load authenticated characters from storage.

        Returns:
            AuthenticatedCharacters instance with loaded data.
            Returns empty collection if file doesn't exist.

        Raises:
            TokenStorageError: If file exists but cannot be loaded or parsed.
        """
        if not self.storage_path.exists():
            logger.info(f"Token file does not exist: {self.storage_path}")
            return AuthenticatedCharacters()

        try:
            logger.debug(f"Loading characters from: {self.storage_path}")
            with open(self.storage_path, encoding="utf-8") as f:
                data = AuthenticatedCharacters.model_validate_json(f.read())

            characters = AuthenticatedCharacters.model_validate(data)
            logger.info(f"Loaded {len(characters.characters)} characters from storage")
            return characters

        except ValidationError as e:
            error_msg = f"Validation error in token file: {e}"
            logger.error(error_msg)
            raise TokenStorageError(error_msg, self.storage_path) from e
        except Exception as e:
            error_msg = f"Failed to load token file: {e}"
            logger.error(error_msg)
            raise TokenStorageError(error_msg, self.storage_path) from e

    def _save_characters(self, characters: AuthenticatedCharacters) -> None:
        """Save authenticated characters to storage.

        Args:
            characters: The AuthenticatedCharacters instance to save.

        Raises:
            TokenStorageError: If the data cannot be saved.
        """
        try:
            # Ensure the directory exists
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)

            logger.debug(
                f"Saving {len(characters.characters)} characters to: {self.storage_path}"
            )

            # Create a temporary file for atomic write
            temp_path = self.storage_path.with_suffix(".tmp")

            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(characters.model_dump_json(indent=2))

            # Atomic move to final location
            temp_path.replace(self.storage_path)

            logger.info(f"Successfully saved characters to storage")

        except Exception as e:
            # Clean up temp file if it exists
            if "temp_path" in locals() and temp_path.exists():  # type: ignore
                temp_path.unlink(missing_ok=True)  # type: ignore

            error_msg = f"Failed to save token file: {e}"
            logger.error(error_msg)
            raise TokenStorageError(error_msg, self.storage_path) from e

    def add_character(self, token: CharacterToken) -> None:
        """Add or update a character's token in storage.

        Args:
            token: The CharacterToken to add or update.

        Raises:
            TokenStorageError: If the operation fails.
        """
        logger.debug(
            f"Adding/updating character {token.character_id} ({token.character_name})"
        )

        characters = self._load_characters()
        characters.add_character(token)
        self._save_characters(characters)

    def remove_character(self, character_id: int) -> bool:
        """Remove a character from storage.

        Args:
            character_id: The character ID to remove.

        Returns:
            True if character was removed, False if not found.

        Raises:
            TokenStorageError: If the operation fails.
        """
        logger.debug(f"Removing character {character_id}")

        characters = self._load_characters()
        removed = characters.remove_character(character_id)

        if removed:
            self._save_characters(characters)
            logger.info(f"Successfully removed character {character_id}")
        else:
            logger.warning(f"Character {character_id} not found for removal")

        return removed

    def get_character(self, character_id: int) -> CharacterToken | None:
        """Get a specific character's token from storage.

        Args:
            character_id: The character ID to retrieve.

        Returns:
            The CharacterToken if found, None otherwise.

        Raises:
            TokenStorageError: If the operation fails.
        """
        logger.debug(f"Retrieving character {character_id}")

        characters = self._load_characters()
        return characters.get_character(character_id)

    def list_characters(self) -> list[CharacterToken]:
        """List all characters in storage.

        Returns:
            List of all CharacterToken objects.

        Raises:
            TokenStorageError: If the operation fails.
        """
        logger.debug("Listing all characters")

        characters = self._load_characters()
        return characters.list_characters()

    def list_expired_characters(self) -> list[CharacterToken]:
        """List all characters with expired tokens.

        Returns:
            A list of CharacterToken instances whose access tokens have expired.
        """
        logger.debug("Listing expired characters")

        characters = self._load_characters()
        return characters.get_expired_tokens()

    def list_characters_needing_refresh(
        self, buffer_minutes: int = 5
    ) -> list[CharacterToken]:
        """List all characters whose tokens need refreshing.

        Args:
            buffer_minutes: The buffer time in minutes before actual expiration to consider for refresh.

        Returns:
            A list of CharacterToken instances that need their access tokens refreshed.
        """
        logger.debug(
            f"Listing characters needing refresh with buffer {buffer_minutes}m"
        )
        characters = self._load_characters()
        return characters.get_tokens_needing_refresh(buffer_minutes)
