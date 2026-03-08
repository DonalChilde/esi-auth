"""Protocols for ESI Authentication storage and access."""

from typing import Protocol

import aiohttp

from esi_auth.models import CharacterAuth, CharacterToken, RequestParams


class AuthenticatorProtocol(Protocol):
    """Protocol for authenticating ESI tokens."""

    async def request_character_token(
        self, params: RequestParams, timeout: int = 300
    ) -> CharacterToken:
        """Request a new ESI token.

        Runs the server, gets the token, validates it, and returns the character information.

        This method should be implemented by subclasses to provide the actual logic for requesting a new token.
        """
        ...

    async def refresh_character_token(
        self, token: CharacterToken, client_session: aiohttp.ClientSession
    ) -> CharacterToken:
        """Refresh an existing ESI token.

        Returns a new CharacterToken with updated auth token information.
        """
        ...

    async def revoke_character_token(
        self, token: CharacterToken, client_session: aiohttp.ClientSession
    ) -> None:
        """Revoke an existing ESI token.

        Raises:

        """
        ...

    def prepare_for_request(self, scopes: list[str] | None = None) -> RequestParams:
        """Prepare the authenticator for making requests.

        This method can be used to initialize any necessary state or perform any necessary setup before making requests.
        """
        ...


class CharacterTokenProviderProtocol(Protocol):
    """Protocol for providing ESI tokens."""

    authenticator: AuthenticatorProtocol

    async def get_token(
        self, character_id: int, min_seconds: int = 300
    ) -> CharacterToken:
        """Return the ESI token for the given character ID, optionally refreshing the token if it is about to expire.

        Args:
            character_id: The ID of the character for which to retrieve the token.
            min_seconds: The minimum number of seconds before a token expires to
                trigger a refresh. -1 to disable refresh. Default is 300 (5 minutes).

        Raises:
            KeyError: If no token for the given character ID exists.
        """
        ...

    async def list_tokens(self, min_seconds: int = 300) -> list[CharacterToken]:
        """Return a list of all ESI tokens, optionally refreshing tokens that are about to expire.

        Args:
            min_seconds: The minimum number of seconds before a token expires to
                trigger a refresh. -1 to disable refresh. Default is 300 (5 minutes).

        Raises:
            KeyError: If no tokens exist.
        """
        ...


class CharacterTokenManagerProtocol(CharacterTokenProviderProtocol, Protocol):
    """Protocol for managing ESI tokens."""

    def add_token(self, token: CharacterToken) -> None:
        """Add a new ESI token to the provider.

        Raises:
            ValueError: If a token for the same character ID already exists.
        """
        ...

    def remove_token(self, character_id: int) -> None:
        """Remove the ESI token for the given character ID.

        Raises:
            KeyError: If no token for the given character ID exists.
        """
        ...


class AuthProviderProtocol(Protocol):
    """Protocol for providing authentication information."""

    async def character_auth(self, character_id: int) -> CharacterAuth:
        """Return the authentication information for the given character ID.

        Args:
            character_id: The ID of the character for which to retrieve the authentication information.

        Returns:
            The authentication information for the given character ID.

        Raises:
            KeyError: If no authentication information for the given character ID exists.
        """
        ...

    async def available_characters(self) -> list[int]:
        """Return a list of character IDs for which authentication information is available."""
        ...
