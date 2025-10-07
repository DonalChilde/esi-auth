"""Credential storage implementations and protocols.

Credentials for Eve ESI apps are downloaded by the user as json files, and are
stored locally. This module defines a protocol for credential storage and
provides a JSON file-based implementation.

"""

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

    def remove_credentials(self, client_id: str) -> bool:
        """Remove the given credentials from storage.

        Args:
            client_id: The client_id of the EveCredentials instance to remove.

        Raises:
            CredentialStorageError: If saving after removal fails.

        Returns:
            True if the credentials were removed, False otherwise.
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

    def get_credentials_by_alias(self, client_alias: str) -> EveCredentials | None:
        """Retrieve credentials by alias.

        Args:
            client_alias: The alias of the application to retrieve.

        Returns:
            The EveCredentials instance if found, else None.

        Raises:
            CredentialStorageError: If retrieval fails.
        """
        ...

    def get_credentials_by_alias_or_id(
        self, client_id: str | None = None, client_alias: str | None = None
    ) -> EveCredentials | None:
        """Retrieve credentials by client_id or alias.

        Args:
            client_id: The client ID for which to retrieve authorized characters.
                If provided, client_alias must be None.
            client_alias: The client alias for which to retrieve authorized characters.
                If provided, client_id must be None.

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

    def _save_credentials(self, credential_store: CredentialStore) -> None:
        """Save current credentials to the JSON file.

        Raises:
            CredentialStorageError: If saving fails.
        """
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            # Create a temporary file for atomic write
            temp_path = self.storage_path.with_suffix(".tmp")

            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(credential_store.model_dump_json(indent=2))

            # Atomic move to final location
            temp_path.replace(self.storage_path)

            logger.info(f"Successfully saved credentials to storage")
        except Exception as e:
            # Clean up temp file if it exists
            if "temp_path" in locals() and temp_path.exists():  # type: ignore
                temp_path.unlink(missing_ok=True)  # type: ignore

            error_msg = f"Failed to save credentials file: {e}"
            logger.error(error_msg)
            raise CredentialStorageError(error_msg, self.storage_path) from e

    def add_credentials(self, credentials: EveCredentials) -> None:
        """Save the given credentials to storage.

        Args:
            credentials: The EveCredentials instance to add.

        Raises:
            CredentialStorageError: If saving fails.
        """
        logger.debug(f"Adding credentials for client_id: {credentials.client_id}")
        existing_store = self._load_credentials()
        existing_store.credentials[credentials.client_id] = credentials
        self._save_credentials(existing_store)

    def remove_credentials(self, client_id: str) -> bool:
        """Remove the given credentials from storage.

        Args:
            client_id: The client_id of the EveCredentials instance to remove.

        Raises:
            CredentialStorageError: If saving after removal fails.

        Returns:
            True if the credentials were removed, False otherwise.
        """
        logger.debug(f"Removing credentials for client_id: {client_id}")
        existing_store = self._load_credentials()
        removed = existing_store.remove_credential(client_id)
        if removed:
            self._save_credentials(existing_store)
        else:
            logger.warning(f"Credentials for client_id {client_id} not found")
        return removed

    def get_credentials(self, client_id: str) -> EveCredentials | None:
        """Retrieve credentials by client_id.

        Args:
            client_id: The client_id of the application to retrieve.

        Returns:
            The EveCredentials instance if found, else None.

        Raises:
            CredentialStorageError: If retrieval fails.
        """
        logger.debug(f"Retrieving credentials for client_id: {client_id}")
        existing_store = self._load_credentials()
        return existing_store.credentials.get(client_id)

    def get_credentials_by_alias(self, client_alias: str) -> EveCredentials | None:
        """Retrieve credentials by alias.

        Args:
            client_alias: The alias of the application to retrieve.

        Returns:
            The EveCredentials instance if found, else None.

        Raises:
            CredentialStorageError: If retrieval fails.
        """
        logger.debug(f"Retrieving credentials for alias: {client_alias}")
        existing_store = self._load_credentials()
        for cred in existing_store.credentials.values():
            if cred.alias == client_alias:
                return cred
        return None

    def get_credentials_by_alias_or_id(
        self, client_id: str | None = None, client_alias: str | None = None
    ) -> EveCredentials | None:
        """Retrieve credentials by client_id or alias.

        Args:
            client_id: The client ID for which to retrieve authorized characters.
                If provided, client_alias must be None.
            client_alias: The client alias for which to retrieve authorized characters.
                If provided, client_id must be None.

        Returns:
            The EveCredentials instance if found, else None.
        """
        if client_id and client_alias:
            raise ValueError("Specify either client_id or client_alias, not both.")
        if not any([client_id, client_alias]):
            raise ValueError("Either client_id or client_alias must be specified.")
        if client_id:
            return self.get_credentials(client_id)
        if client_alias:
            return self.get_credentials_by_alias(client_alias)

    def list_credentials(self) -> list[EveCredentials]:
        """List all stored credentials.

        Returns:
            A list of all EveCredentials instances in storage.

        Raises:
            CredentialStorageError: If listing fails.
        """
        logger.debug("Listing all stored credentials")
        existing_store = self._load_credentials()
        return list(existing_store.credentials.values())


def get_credential_store():
    """Get the credential store instance."""
    settings = get_settings()
    return CredentialStoreJson(
        settings.credential_store_dir / settings.credential_file_name
    )
