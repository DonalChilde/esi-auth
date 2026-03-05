"""Simple implementation of AppCredentialManagerProtocol and CharacterTokenManagerProtocol.

Uses JSON files in a directory to store credentials and tokens.
"""

import asyncio
from pathlib import Path

import aiohttp
from whenever import Instant

from esi_auth.v2.authenticate_esi import request_refreshed_token
from esi_auth.v2.models import AppCredentials, CharacterToken, OauthToken
from esi_auth.v2.protocols import (
    AppCredentialManagerProtocol,
    AppCredentialProviderProtocol,
    CharacterTokenManagerProtocol,
    CharacterTokenProviderProtocol,
)
from esi_auth.v2.settings import OAUTH_SETTINGS, USER_AGENT


class AppCredentialProvider(AppCredentialProviderProtocol):
    """Simple implementation of AppCredentialProviderProtocol that reads credentials from JSON files in a directory.

    The credential files should be named in the format "{alias}-app-credential.json"
    """

    def __init__(self, credentials_dir: Path):
        """Initialize the AppCredentialProvider with the given credentials directory.

        Args:
            credentials_dir: The directory where credential JSON files are stored.
        """
        self.credentials_dir = credentials_dir

    def _credential_files(self) -> list[Path]:
        """Return a list of all credential files in the credentials directory."""
        return list(self.credentials_dir.glob("*-app-credential.json"))

    def by_alias(self, alias: str) -> AppCredentials:
        """Return the credentials for the given alias."""
        file_path = self.credentials_dir / f"{alias}-app-credential.json"
        if file_path.exists():
            return AppCredentials.model_validate_json(file_path.read_text())
        else:
            raise KeyError(f"No credentials found for alias '{alias}'")


class AppCredentialManager(AppCredentialProvider, AppCredentialManagerProtocol):
    """Simple implementation of AppCredentialManagerProtocol that manages credentials as JSON files in a directory."""

    def __init__(self, credentials_dir: Path):
        """Initialize the AppCredentialManager with the given credentials directory.

        Args:
            credentials_dir: The directory where credential JSON files are stored.
        """
        super().__init__(credentials_dir)

    def _credential_files(self) -> list[Path]:
        """Return a list of all credential files in the credentials directory."""
        return list(self.credentials_dir.glob("*-app-credential.json"))

    def _credential_objects(self) -> list[AppCredentials]:
        """Return a list of all credential objects in the credentials directory."""
        return [
            AppCredentials.model_validate_json(file.read_text())
            for file in self._credential_files()
        ]

    def by_client_id(self, client_id: str) -> AppCredentials:
        """Return the credentials for the given client ID."""
        for creds in self._credential_objects():
            if creds.credentials.clientId == client_id:
                return creds
        raise KeyError(f"No credentials found for client ID '{client_id}'")

    def add_credentials(self, credentials: AppCredentials) -> None:
        """Add new credentials to the provider.

        Raises:
            ValueError: If credentials with the same client ID or alias already exist.
        """
        existing_credentials = self._credential_objects()
        if any(
            creds.credentials.clientId == credentials.credentials.clientId
            for creds in existing_credentials
        ):
            raise ValueError(
                f"Credentials with client ID '{credentials.credentials.clientId}' already exist."
            )
        if any(creds.alias == credentials.alias for creds in existing_credentials):
            raise ValueError(
                f"Credentials with alias '{credentials.alias}' already exist."
            )
        file_path = self.credentials_dir / f"{credentials.alias}-app-credential.json"
        file_path.write_text(credentials.model_dump_json())

    def remove_credentials(self, client_id: str) -> None:
        """Remove credentials from the provider by client ID.

        Raises:
            KeyError: If no credentials with the given client ID exist.
        """
        for file in self._credential_files():
            creds = AppCredentials.model_validate_json(file.read_text())
            if creds.credentials.clientId == client_id:
                file.unlink()
                return
        raise KeyError(f"No credentials found for client ID '{client_id}'")

    def list_credentials(self) -> list[AppCredentials]:
        """Return a list of all credentials in the provider."""
        return self._credential_objects()


class CharacterTokenProvider(CharacterTokenProviderProtocol):
    """Simple implementation of CharacterTokenProviderProtocol that reads tokens from JSON files in a directory.

    The token files should be named in the format "{client_alias}-{character_id}-token.json"
    """

    def __init__(
        self,
        tokens_dir: Path,
        app_credential_provider: AppCredentialProviderProtocol | None,
        token_endpoint: str = OAUTH_SETTINGS.token_endpoint,
        user_agent: str = USER_AGENT,
    ):
        """Initialize the CharacterTokenProvider with the given tokens directory and optional app credential provider.

        Args:
            tokens_dir: The directory where token JSON files are stored.
            app_credential_provider: An optional app credential provider for refreshing tokens.
            token_endpoint: The OAuth token endpoint.
            user_agent: The user agent to use for HTTP requests.
        """
        self.tokens_dir = tokens_dir
        self.app_credential_provider = app_credential_provider
        self.token_endpoint = token_endpoint
        self.user_agent = user_agent

    def _token_file_path(self, token: CharacterToken) -> Path:
        """Return the file path for the given token."""
        return self.tokens_dir / f"{token.app_alias}-{token.character_id}-token.json"

    def _token_file_path_by_alias_and_id(
        self, client_alias: str, character_id: int
    ) -> Path:
        """Return the file path for the given client alias and character ID."""
        return self.tokens_dir / f"{client_alias}-{character_id}-token.json"

    def _token_files(self) -> list[Path]:
        """Return a list of all token files in the tokens directory."""
        return list(self.tokens_dir.glob("*-token.json"))

    def _list_aliases(self) -> list[str]:
        """Return a list of all client aliases for which tokens exist."""
        aliases: set[str] = set()
        for file in self._token_files():
            parts = file.stem.split("-")
            if len(parts) >= 3 and parts[-1] == "token":
                alias = "-".join(parts[:-2])
                aliases.add(alias)
        return list(aliases)

    def get_token(self, client_alias: str, character_id: int) -> CharacterToken:
        """Return the token for the given client alias and character ID."""
        file_path = self._token_file_path_by_alias_and_id(client_alias, character_id)
        if file_path.exists():
            return CharacterToken.model_validate_json(file_path.read_text())
        else:
            raise KeyError(
                f"No token found for client alias '{client_alias}' and character ID '{character_id}'"
            )

    def _save_token(self, token: CharacterToken) -> None:
        """Save the given token to a JSON file in the tokens directory."""
        file_path = self._token_file_path(token)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(token.model_dump_json(indent=2))

    def _list_tokens_by_alias(self, client_alias: str) -> list[CharacterToken]:
        """Return a list of all tokens for the given client alias."""
        token_files = self.tokens_dir.glob(f"{client_alias}-*-token.json")
        tokens: list[CharacterToken] = []
        for file_path in token_files:
            tokens.append(CharacterToken.model_validate_json(file_path.read_text()))
        if not tokens:
            raise KeyError(f"No tokens found for client alias '{client_alias}'")
        return tokens

    async def _refresh_token(
        self, token: CharacterToken, client_session: aiohttp.ClientSession
    ) -> CharacterToken:
        """Refresh the given token using the app credentials and return the new token."""
        if self.app_credential_provider is None:
            raise ValueError(
                "App credential provider is not set, Unable to refresh token."
            )
        app_credentials = self.app_credential_provider.by_alias(token.app_alias)
        new_oauth_token = await request_refreshed_token(
            refresh_token=token.oauth_token.refresh_token,
            client_id=app_credentials.credentials.clientId,
            token_endpoint=self.token_endpoint,
            user_agent=self.user_agent,
            client_session=client_session,
        )
        new_token = CharacterToken(
            app_alias=token.app_alias,
            character_id=token.character_id,
            character_name=token.character_name,
            oauth_token=OauthToken.model_validate(new_oauth_token),
            refreshed_at=Instant.now().timestamp(),
        )
        return new_token

    def refresh_token(
        self,
        client_alias: str,
        character_id: int,
    ) -> CharacterToken:
        """Refresh the token for the given client alias and character ID.

        Raises:
            KeyError: If no token for the given client alias and character ID exist.
            ValueError: If the token cannot be refreshed (e.g. invalid refresh token).
        """
        if self.app_credential_provider is None:
            raise ValueError(
                "App credential provider is not set, Unable to refresh token."
            )
        character_token = self.get_token(client_alias, character_id)

        async def refresh(character_token: CharacterToken) -> CharacterToken:
            async with aiohttp.ClientSession() as session:
                return await self._refresh_token(character_token, session)

        new_token = asyncio.run(refresh(character_token))
        self._save_token(new_token)
        return new_token

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
        tokens = self._list_tokens_by_alias(client_alias)
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

        new_tokens = asyncio.run(refresh_all(refresh_needed))
        for token in new_tokens:
            self._save_token(token)
        # Return the updated list of tokens for the client alias after refresh
        tokens = self._list_tokens_by_alias(client_alias)
        return tokens


class CharacterTokenManager(CharacterTokenProvider, CharacterTokenManagerProtocol):
    """Simple implementation of CharacterTokenManagerProtocol that manages tokens as JSON files in a directory."""

    def add_token(self, token: CharacterToken) -> None:
        """Add a new ESI token to the provider.

        Raises:
            ValueError: If a token for the same client_alias and character ID already exists.
        """
        file_path = self._token_file_path(token)
        if file_path.exists():
            raise ValueError(
                f"Token for client alias '{token.app_alias}' and character ID '{token.character_id}' already exists."
            )
        self._save_token(token)

    def remove_token(self, client_alias: str, character_id: int) -> None:
        """Remove a token from the provider by client alias and character ID.

        Raises:
            KeyError: If no token for the given client alias and character ID exist.
        """
        file_path = self._token_file_path_by_alias_and_id(client_alias, character_id)
        if file_path.exists():
            file_path.unlink()
        else:
            raise KeyError(
                f"No token found for client alias '{client_alias}' and character ID '{character_id}'"
            )

    def list_tokens(self, client_alias: str) -> list[CharacterToken]:
        """Return a list of all ESI tokens for the given client alias.

        Raises:
            KeyError: If no credentials with the given client alias exist.
        """
        return self._list_tokens_by_alias(client_alias)

    def list_all_tokens(self) -> list[CharacterToken]:
        """Return a list of all ESI tokens in the provider."""
        token_files = self._token_files()
        tokens: list[CharacterToken] = []
        for file_path in token_files:
            tokens.append(CharacterToken.model_validate_json(file_path.read_text()))
        return tokens
