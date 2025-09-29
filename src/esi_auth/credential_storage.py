"""Credential storage implementations and protocols."""

import logging
from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

from esi_auth.models import CredentialStore, EveCredentials
from esi_auth.settings import get_settings

logger = logging.getLogger(__name__)


class CredentialStorageError(Exception):
    """Exception raised during credential storage operations.

    This exception is raised when credential storage or retrieval fails.
    """

    def __init__(self, message: str, path: Path | None = None):
        """Initialize the credential storage error.

        Args:
            message: Human-readable error message.
            path: Optional file path related to the error.
        """
        super().__init__(message)
        self.message = message
        self.path = path


class CredentialStorageProtocol(Protocol):
    """Protocol for credential storage implementations.

    This protocol defines the methods that any credential storage
    implementation must provide.
    """

    def add_credentials(self, credentials: EveCredentials) -> None:
        """Save the given credentials to storage.

        Args:
            credentials: The EveCredentials instance to add.

        Raises:
            CredentialStorageError: If saving fails.
        """
        ...

    def remove_credentials(self, credentials: EveCredentials) -> None:
        """Remove the given credentials from storage.

        Args:
            credentials: The EveCredentials instance to remove.

        Raises:
            CredentialStorageError: If removal fails.
        """
        ...

    def get_credentials(self, client_id: str) -> EveCredentials | None:
        """Retrieve credentials by client_id.

        Args:
            client_id: The client_id of the application to retrieve.

        Returns:
            The EveCredentials instance if found, else None.

        Raises:
            CredentialStorageError: If retrieval fails.
        """
        ...

    def list_credentials(self) -> list[EveCredentials]:
        """List all stored credentials.

        Returns:
            A list of all EveCredentials instances in storage.

        Raises:
            CredentialStorageError: If listing fails.
        """
        ...


class CredentialStoreJson(CredentialStorageProtocol):
    """JSON file-based implementation of CredentialStorageProtocol.

    This class provides methods to store and retrieve EveCredentials
    using a JSON file as the backend storage.
    """

    def __init__(self, storage_path: Path | None = None) -> None:
        """Initialize the JSON credential store.

        Args:
            storage_path: The path to the JSON file for storing credentials.
        """
        settings = get_settings()
        self.storage_path = (
            storage_path
            or settings.credential_store_dir / settings.credential_file_name
        )
        # Load existing credentials from the file or initialize empty storage
        self._load_credentials()

    def _load_credentials(self) -> CredentialStore:
        """Load credentials from the JSON file.

        Raises:
            CredentialStorageError: If loading fails.
        """
        if not self.storage_path.is_file():
            logger.info(f"Credential file does not exist: {self.storage_path}")
            return CredentialStore()
        try:
            logger.info(f"Loading credentials from {self.storage_path}")
            with self.storage_path.open("r", encoding="utf-8") as f:
                data = CredentialStore.model_validate_json(f.read())
            logger.info(f"Loaded {len(data.credentials)} credentials from storage")
            return data
        except ValidationError as e:
            logger.error(f"Failed to load credentials: {e}")
            raise CredentialStorageError(f"Failed to load credentials: {e}") from e
        except Exception as e:
            logger.error(f"Error reading credential file: {e}")
            raise CredentialStorageError(f"Error reading credential file: {e}") from e

    def _save_credentials(self) -> None:
        """Save current credentials to the JSON file.

        Raises:
            CredentialStorageError: If saving fails.
        """
        # Implementation to save credentials to JSON file
        pass

    def add_credentials(self, credentials: EveCredentials) -> None:
        """Save the given credentials to storage.

        Args:
            credentials: The EveCredentials instance to add.

        Raises:
            CredentialStorageError: If saving fails.
        """
        # Implementation to add credentials
        pass

    def remove_credentials(self, credentials: EveCredentials) -> None:
        """Remove the given credentials from storage.

        Args:
            credentials: The EveCredentials instance to remove.

        Raises:
            CredentialStorageError: If removal fails.
        """
        # Implementation to remove credentials
        pass

    def get_credentials(self, client_id: str) -> EveCredentials | None:
        """Retrieve credentials by client_id.

        Args:
            client_id: The client_id of the application to retrieve.

        Returns:
            The EveCredentials instance if found, else None.

        Raises:
            CredentialStorageError: If retrieval fails.
        """
        # Implementation to get credentials by client_id
        pass

    def list_credentials(self) -> list[EveCredentials]:
        """List all stored credentials.

        Returns:
            A list of all EveCredentials instances in storage.

        Raises:
            CredentialStorageError: If listing fails.
        """
        # Implementation to list all credentials
        pass
