"""Simple implementation of AppCredentialManagerProtocol and CharacterTokenManagerProtocol.

Uses JSON files in a directory to store credentials and tokens.
"""

import asyncio
from pathlib import Path

import aiohttp
from whenever import Instant

from esi_auth.authenticate_esi import request_refreshed_token
from esi_auth.models import CharacterToken, OauthToken
from esi_auth.protocols import (
    CharacterTokenManagerProtocol,
    CharacterTokenProviderProtocol,
)
from esi_auth.settings import DEFAULT_OAUTH_SETTINGS, USER_AGENT


class CharacterTokenProvider(CharacterTokenProviderProtocol):
    """Simple implementation of CharacterTokenProviderProtocol that reads tokens from JSON files in a directory.

    The token files should be named in the format "{client_alias}-{character_id}-token.json"
    """

    def __init__(
        self,
        tokens_dir: Path,
        token_endpoint: str = DEFAULT_OAUTH_SETTINGS.token_endpoint,
        user_agent: str = USER_AGENT,
    ):
        """Initialize the CharacterTokenProvider with the given tokens directory and optional app credential provider.

        Args:
            tokens_dir: The directory where token JSON files are stored.
            token_endpoint: The OAuth token endpoint.
            user_agent: The user agent to use for HTTP requests.
        """
        self.tokens_dir = tokens_dir
        self.token_endpoint = token_endpoint
        self.user_agent = user_agent

    def _token_file_path(self, token: CharacterToken) -> Path:
        """Return the file path for the given token."""
        return self._token_file_path_by_id(token.character_id)

    def _token_file_path_by_id(self, character_id: int) -> Path:
        """Return the file path for the given character ID."""
        return self.tokens_dir / f"{character_id}-token.json"

    def _token_files(self) -> list[Path]:
        """Return a list of all token files in the tokens directory."""
        return list(self.tokens_dir.glob("*-token.json"))

    def _load_token(self, file_path: Path) -> CharacterToken:
        """Load a token from the given file path."""
        return CharacterToken.model_validate_json(file_path.read_text())

    def _load_all_tokens(self) -> list[CharacterToken]:
        """Load all tokens from the tokens directory."""
        token_files = self._token_files()
        return [self._load_token(file) for file in token_files]

    def _save_token(self, token: CharacterToken) -> None:
        """Save the given token to a JSON file in the tokens directory."""
        file_path = self._token_file_path(token)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(token.model_dump_json(indent=2))

    async def _refresh_token(
        self, token: CharacterToken, client_session: aiohttp.ClientSession
    ) -> CharacterToken:
        """Refresh the given token and return the new token."""
        json_oauth_token = await request_refreshed_token(
            refresh_token=token.oauth_token.refresh_token,
            client_id=token.client_id,
            token_endpoint=self.token_endpoint,
            user_agent=self.user_agent,
            client_session=client_session,
        )
        oauth_token = OauthToken.model_validate(json_oauth_token)
        new_token = CharacterToken(
            character_id=token.character_id,
            character_name=token.character_name,
            client_id=token.client_id,
            oauth_token=oauth_token,
            refreshed_at=Instant.now().timestamp(),
        )
        return new_token

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
        file_path = self._token_file_path_by_id(character_id)
        if file_path.exists():
            token = self._load_token(file_path)
        else:
            raise KeyError(f"No token found for character ID '{character_id}'")
        if min_seconds < 0:
            # Refresh disabled, return existing token
            return token
        if min_seconds >= 0 and token.expires_in < min_seconds:

            async def refresh(token: CharacterToken) -> CharacterToken:
                async with aiohttp.ClientSession() as session:
                    new_token = await self._refresh_token(token, session)
                return new_token

            new_token = await refresh(token)
            self._save_token(new_token)
            return new_token
        return token

    async def list_tokens(self, min_seconds: int = 300) -> list[CharacterToken]:
        """Return a list of all ESI tokens, optionally refreshing tokens that are about to expire.

        Args:
            min_seconds: The minimum number of seconds before a token expires to
                trigger a refresh. -1 to disable refresh. Default is 300 (5 minutes).

        Raises:
            KeyError: If no tokens exist.
        """
        token_files = self._token_files()
        if not token_files:
            raise KeyError("No tokens found.")
        tokens = self._load_all_tokens()
        if min_seconds < 0:
            # Refresh disabled, return existing tokens
            return tokens
        refresh_needed = [token for token in tokens if token.expires_in < min_seconds]

        async def refresh_all(tokens: list[CharacterToken]) -> list[CharacterToken]:
            async with aiohttp.ClientSession() as session:
                refreshed_tokens = await asyncio.gather(
                    *(self._refresh_token(token, session) for token in tokens)
                )
            return refreshed_tokens

        new_tokens = await refresh_all(refresh_needed)
        for token in new_tokens:
            self._save_token(token)
        # Return the updated list of tokens after refresh
        tokens = self._load_all_tokens()
        return tokens


class CharacterTokenManager(CharacterTokenProvider, CharacterTokenManagerProtocol):
    """Simple implementation of CharacterTokenManagerProtocol that manages tokens as JSON files in a directory."""

    def add_token(self, token: CharacterToken) -> None:
        """Add a new ESI token to the provider.

        Raises:
            ValueError: If a token for the same character ID already exists.
        """
        file_path = self._token_file_path(token)
        if file_path.exists():
            raise ValueError(
                f"Token for character ID '{token.character_id}' already exists. Remove it before adding a new token."
            )
        self._save_token(token)

    def remove_token(self, character_id: int) -> None:
        """Remove a token from the provider by character ID.

        Raises:
            KeyError: If no token for the given character ID exists.
        """
        file_path = self._token_file_path_by_id(character_id)
        if file_path.exists():
            file_path.unlink()
        else:
            raise KeyError(f"No token found for character ID '{character_id}'")
