"""Token storage system for ESI authentication.

This module provides functionality for persisting and loading character
authentication tokens to/from JSON files in the application directory.
"""

import json
import logging
from pathlib import Path

from .models import AuthenticatedCharacters, CharacterToken
from .settings import get_settings

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


class TokenStorage:
    """Manages persistent storage of character authentication tokens.

    This class handles loading and saving character tokens to/from JSON files
    using Pydantic models for serialization and validation.
    """

    def __init__(self, storage_path: Path | None = None):
        """Initialize the token storage.

        Args:
            storage_path: Optional custom path for token storage.
                         If None, uses path from application settings.
        """
        self.storage_path = storage_path or get_settings().token_file_path
        logger.info(f"TokenStorage initialized with path: {self.storage_path}")

    def load_characters(self) -> AuthenticatedCharacters:
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
                data = json.load(f)

            characters = AuthenticatedCharacters.model_validate(data)
            logger.info(f"Loaded {len(characters.characters)} characters from storage")
            return characters

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in token file: {e}"
            logger.error(error_msg)
            raise TokenStorageError(error_msg, self.storage_path) from e
        except Exception as e:
            error_msg = f"Failed to load token file: {e}"
            logger.error(error_msg)
            raise TokenStorageError(error_msg, self.storage_path) from e

    def save_characters(self, characters: AuthenticatedCharacters) -> None:
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
                json.dump(
                    characters.model_dump(mode="json"), f, indent=2, ensure_ascii=False
                )

            # Atomic move to final location
            temp_path.replace(self.storage_path)

            logger.info(f"Successfully saved characters to storage")

        except Exception as e:
            # Clean up temp file if it exists
            if "temp_path" in locals() and temp_path.exists():
                temp_path.unlink(missing_ok=True)

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

        characters = self.load_characters()
        characters.add_character(token)
        self.save_characters(characters)

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

        characters = self.load_characters()
        removed = characters.remove_character(character_id)

        if removed:
            self.save_characters(characters)
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

        characters = self.load_characters()
        return characters.get_character(character_id)

    def list_characters(self) -> list[CharacterToken]:
        """List all characters in storage.

        Returns:
            List of all CharacterToken objects.

        Raises:
            TokenStorageError: If the operation fails.
        """
        logger.debug("Listing all characters")

        characters = self.load_characters()
        return characters.list_characters()

    def backup_storage(self, backup_path: Path | None = None) -> Path:
        """Create a backup of the current token storage.

        Args:
            backup_path: Optional custom backup path.
                        If None, creates backup in same directory with timestamp.

        Returns:
            Path to the created backup file.

        Raises:
            TokenStorageError: If backup creation fails.
        """
        if not self.storage_path.exists():
            raise TokenStorageError(
                "Cannot backup non-existent token file", self.storage_path
            )

        if backup_path is None:
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{self.storage_path.stem}_backup_{timestamp}.json"
            backup_path = self.storage_path.parent / backup_name

        try:
            logger.info(f"Creating backup: {backup_path}")

            # Ensure backup directory exists
            backup_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy the file
            import shutil

            shutil.copy2(self.storage_path, backup_path)

            logger.info(f"Backup created successfully: {backup_path}")
            return backup_path

        except Exception as e:
            error_msg = f"Failed to create backup: {e}"
            logger.error(error_msg)
            raise TokenStorageError(error_msg, backup_path) from e

    def restore_from_backup(self, backup_path: Path) -> None:
        """Restore token storage from a backup file.

        Args:
            backup_path: Path to the backup file to restore from.

        Raises:
            TokenStorageError: If restore operation fails.
        """
        if not backup_path.exists():
            raise TokenStorageError(
                f"Backup file does not exist: {backup_path}", backup_path
            )

        try:
            logger.info(f"Restoring from backup: {backup_path}")

            # First validate the backup file by loading it
            temp_storage = TokenStorage(backup_path)
            characters = temp_storage.load_characters()  # This validates the file

            # If validation passes, copy the backup to storage location
            import shutil

            shutil.copy2(backup_path, self.storage_path)

            logger.info(
                f"Successfully restored from backup with {len(characters.characters)} characters"
            )

        except Exception as e:
            error_msg = f"Failed to restore from backup: {e}"
            logger.error(error_msg)
            raise TokenStorageError(error_msg, backup_path) from e


def get_token_storage() -> TokenStorage:
    """Get the default token storage instance.

    This is a convenience function that creates a TokenStorage instance
    using the default settings.

    Returns:
        A TokenStorage instance configured with application settings.
    """
    return TokenStorage()


def load_characters() -> AuthenticatedCharacters:
    """Load authenticated characters using default storage.

    This is a convenience function for the common operation of loading
    all characters from the default storage location.

    Returns:
        AuthenticatedCharacters instance with loaded data.
    """
    storage = get_token_storage()
    return storage.load_characters()
