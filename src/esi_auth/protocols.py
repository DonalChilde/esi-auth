"""Protocols for ESI Authentication storage and access."""

from typing import Protocol

from esi_auth.models import CharacterAuth, CharacterToken


class CharacterTokenProviderProtocol(Protocol):
    """Protocol for providing ESI tokens."""

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
