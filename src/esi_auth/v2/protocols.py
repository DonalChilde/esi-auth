from typing import Protocol

import aiohttp

from esi_auth.v2.models import AppCredentials, CharacterToken


class AppCredentialProviderProtocol(Protocol):
    """Protocol for providing application credentials.

    Credential aliases are used to reference credentials in the token provider and
    manager protocols, and should be unique across all credentials in the provider.

    aliases should only contain A-Z, a-z, 0-9, hyphens, and underscores, and should not
    contain spaces or other special characters.
    """

    def by_alias(self, alias: str) -> AppCredentials:
        """Return the credentials for the given alias.

        Raises:
            KeyError: If no credentials with the given alias exist.
        """
        ...


class AppCredentialManagerProtocol(AppCredentialProviderProtocol, Protocol):
    """Protocol for managing application credentials."""

    def by_client_id(self, client_id: str) -> AppCredentials:
        """Return the credentials for the given client ID.

        Raises:
            KeyError: If no credentials with the given client ID exist.
        """
        ...

    def add_credentials(self, credentials: AppCredentials) -> None:
        """Add new credentials to the provider.

        Raises:
            ValueError: If credentials with the same client ID or alias already exist.
        """
        ...

    def remove_credentials(self, client_id: str) -> None:
        """Remove credentials from the provider by client ID.

        Raises:
            KeyError: If no credentials with the given client ID exist.
        """
        ...

    def list_credentials(self) -> list[AppCredentials]:
        """Return a list of all credentials in the provider."""
        ...


class CharacterTokenProviderProtocol(Protocol):
    """Protocol for providing ESI tokens."""

    app_credential_provider: AppCredentialProviderProtocol | None

    def get_token(self, client_alias: str, character_id: int) -> CharacterToken:
        """Return the ESI token for the given client_alias and character ID.

        Raises:
            KeyError: If no token for the given character ID exists.
        """
        ...

    def refresh_token(
        self,
        client_alias: str,
        character_id: int,
    ) -> CharacterToken:
        """Refresh the ESI token for the given character ID and return the new token.

        Raises:
            KeyError: If no token for the given character ID exists.
            ValueError: If the token cannot be refreshed (e.g. invalid refresh token).
        """
        ...

    def refresh_tokens(
        self, client_alias: str, min_seconds: int = 300
    ) -> list[CharacterToken]:
        """Refresh all tokens for the given client alias and return the new tokens.

        Args:
            client_alias: The client alias for which to refresh tokens.
            min_seconds: The minimum number of seconds before a token expires to
                trigger a refresh. -1 to disable refresh. Default is 300 (5 minutes).

        Raises:
            KeyError: If no tokens for the given client alias exist.
            ValueError: If any token cannot be refreshed (e.g. invalid refresh token).
        """
        ...


class CharacterTokenManagerProtocol(CharacterTokenProviderProtocol, Protocol):
    """Protocol for managing ESI tokens."""

    def add_token(self, token: CharacterToken) -> None:
        """Add a new ESI token to the provider.

        Raises:
            ValueError: If a token for the same client_alias and character ID already exists.
        """
        ...

    def remove_token(self, client_alias: str, character_id: int) -> None:
        """Remove the ESI token for the given client_alias and character ID.

        Raises:
            KeyError: If no token for the given client_alias and character ID exists.
        """
        ...

    def list_tokens(self, client_alias: str) -> list[CharacterToken]:
        """Return a list of all ESI tokens for the given client alias.

        Raises:
            KeyError: If no credentials with the given client alias exist.
        """
        ...

    def list_all_tokens(self) -> list[CharacterToken]:
        """Return a list of all ESI tokens in the provider."""
        ...
