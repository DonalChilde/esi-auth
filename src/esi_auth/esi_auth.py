"""EVE SSO Authentication and Token Management."""

import asyncio
import logging
from copy import deepcopy
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import aiohttp
from jwt import PyJWKClient
from pydantic import BaseModel, Field, RootModel
from whenever import Instant

from esi_auth import auth_helpers as AH
from esi_auth.helpers import get_author_email, get_package_url

OAUTH_METADATA_URL = (
    "https://login.eveonline.com/.well-known/oauth-authorization-server"
)
logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SplitURL:
    scheme: str
    host: str
    port: int
    route: str

    @classmethod
    def from_url(cls, url: str) -> "SplitURL":
        """Create a SplitURL from a full URL string.

        port defaults to 8080 if not specified in the URL.
        """
        parsed = urlparse(url)
        host = parsed.hostname or ""
        port = parsed.port
        route = parsed.path
        return SplitURL(
            scheme=parsed.scheme,
            host=host,
            port=port if port is not None else 8080,
            route=route,
        )

    def __repr__(self) -> str:
        """Represent the SplitURL as a string."""
        return (
            f"SplitURL(scheme={self.scheme!r}, host={self.host!r}, port={self.port!r}, "
            f"route={self.route!r})"
        )


@dataclass(slots=True)
class AuthRequest:
    code_verifier: str
    # code_challenge: str
    sso_url: str
    state: str
    callback_url: str


@dataclass(slots=True)
class AuthCode:
    authorization_code: str
    code_verifier: str


class AuthStoreException(Exception):
    def __init__(self, *args: object) -> None:
        """An exception relating to the auth store."""
        super().__init__(*args)


def _get_current_instant() -> Instant:
    """Factory function to get current instant for default values.

    This function is used as a default_factory to avoid circular dependencies
    that can occur when using Instant.now directly in field definitions.

    Returns:
        Current instant in time.
    """
    return Instant.now()


class CharacterToken(BaseModel):
    """Represents an authenticated character's token data.

    This model stores all necessary information for maintaining
    authentication with the EVE Online ESI API for a specific character.
    """

    character_id: int = Field(..., description="The EVE character ID")
    character_name: str = Field(..., description="The character's name")
    access_token: str = Field(..., description="Current access token")
    refresh_token: str = Field(..., description="Token used to refresh access token")
    expires_at: Instant = Field(..., description="When the access token expires")
    scopes: list[str] = Field(
        default_factory=list, description="List of authorized scopes"
    )
    token_type: str = Field(default="Bearer", description="Type of token")
    client_id: str = Field(..., description="The client ID associated with the token")
    created_at: Instant = Field(
        default_factory=_get_current_instant, description="When token was first created"
    )
    updated_at: Instant = Field(
        default_factory=_get_current_instant, description="When token was last updated"
    )

    def is_expired(self) -> bool:
        """Check if the access token has expired.

        Returns:
            True if the token has expired, False otherwise.
        """
        return Instant.now() >= self.expires_at

    def needs_refresh(self, buffer_minutes: int = 5) -> bool:
        """Check if the token needs refreshing.

        Args:
            buffer_minutes: Minutes before expiry to consider needing refresh.

        Returns:
            True if the token should be refreshed, False otherwise.
        """
        buffer_time = self.expires_at.subtract(minutes=buffer_minutes)
        return Instant.now() >= buffer_time

    def minutes_until_expiry(self) -> float:
        """Get the number of minutes until the token expires.

        Returns:
            Minutes until expiry as a float. Negative if already expired.
        """
        time_diff = self.expires_at.difference(Instant.now())
        return time_diff.in_minutes()


class EveCredentials(BaseModel):
    """EVE SSO application credentials.

    This model holds the client ID and secret required for OAuth2 authentication
    with the EVE Online SSO service.
    """

    name: str = Field(..., description="The name of the application")
    client_alias: str | None = Field(
        None, description="Unique alias for the client/application"
    )
    client_id: str = Field(
        ...,
        description="The OAuth2 client ID",
    )
    client_secret: str = Field(
        ...,
        description="The OAuth2 client secret",
    )
    callback_url: str = Field(
        ...,
        description="The full callback URL",
    )
    scopes: list[str] = Field(
        default_factory=lambda: ["publicData"],
        description="Default OAuth2 scopes for authentication",
    )


class CredentialStore(RootModel[dict[str, EveCredentials]]):
    pass


class TokenStore(RootModel[dict[str, dict[int, CharacterToken]]]):
    pass


class OauthSettings(BaseModel):
    audience: str = Field(
        default="EVE Online",
        description="Used in Token validation, not derived from oauth metadata.",
    )
    metadata_endpoint: str = Field(
        default="https://login.eveonline.com/.well-known/oauth-authorization-server"
    )
    issuers: list[str] = Field(default=["https://login.eveonline.com"])
    authorization_endpoint: str = Field(
        default="https://login.eveonline.com/v2/oauth/authorize"
    )
    token_endpoint: str = Field(default="https://login.eveonline.com/v2/oauth/token")
    jwks_uri: str = Field(default="https://login.eveonline.com/oauth/jwks")
    revocation_endpoint: str = Field(
        default="https://login.eveonline.com/v2/oauth/revoke"
    )
    downloaded_at: Instant | None = Field(
        default=None,
        description="Date the oath metadata was downloaded. None means default values used.",
    )
    raw_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="The oauth metadata downloaded from the metadata endpoint. Empty if never downloaded.",
    )


class UserAgentSettings(BaseModel):
    character_name: str = Field(
        default="Unknown", description="Character name for User-Agent header"
    )

    user_email: str = Field(
        default="Unknown", description="User email for User-Agent header"
    )
    user_app_name: str = Field(
        default="Unknown", description="App name for User-Agent header"
    )
    user_app_version: str = Field(
        default="Unknown", description="App version for User-Agent header"
    )


class EsiAuthStore(BaseModel):
    credentials: dict[str, EveCredentials]
    tokens: dict[str, dict[int, CharacterToken]]
    oauth_metadata: OauthSettings
    user_agent: UserAgentSettings

    def save_to_disk(self, file_path: Path | None) -> None:
        """Save the current store to disk atomically.

        Args:
            file_path: Path to the file where the store should be saved. If None, raises ValueError.
        """
        # Atomic save
        if file_path is None:
            raise ValueError("file_path must be set before saving to disk.")
        try:
            temp_file = file_path.with_suffix(".tmp")
            with temp_file.open("w", encoding="utf-8") as f:
                f.write(self.model_dump_json(indent=2))
            temp_file.replace(file_path)
        except Exception as e:
            raise OSError(f"Failed to save store to disk: {e}") from e

    @classmethod
    def load_from_disk(cls, file_path: Path) -> "EsiAuthStore":
        """Load the store from disk.

        Args:
            file_path: Path to the file where the store is saved.
        """
        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = f.read()
            return cls.model_validate_json(data)
        except Exception as e:
            raise OSError(f"Failed to load store from disk: {e}") from e


class EsiAuth:
    def __init__(self, store_path: Path | None, auth_server_timeout: int = 300) -> None:
        """Initialize the EsiAuth instance.

        Pass None to store_path to create a new in-memory store.
        Set store_path later to save/load from disk.

        Args:
            store_path: Path to the file where the store is saved. If None, an in-memory store is used.
            auth_server_timeout: Seconds to wait for a reply.
        """
        self.store_path = store_path
        if self.store_path is None:
            store = EsiAuthStore(
                credentials={},
                tokens={},
                oauth_metadata=OauthSettings(),
                user_agent=UserAgentSettings(),
            )
            self.store = store
        elif self.store_path.is_dir():
            raise AuthStoreException(f"store_path {store_path} is a directory.")
        elif not self.store_path.is_file():
            store = EsiAuthStore(
                credentials={},
                tokens={},
                oauth_metadata=OauthSettings(),
                user_agent=UserAgentSettings(),
            )
            self.store = store
            self._save_store()  # Create new store file
        else:
            self.store = EsiAuthStore.load_from_disk(self.store_path)
        self._jwks_client: PyJWKClient | None = None
        self._server_timeout = auth_server_timeout

    #############################################################################
    # Authentication Flow Methods
    #############################################################################
    def prepare_request(self, credentials: EveCredentials) -> AuthRequest:
        """Prepare a request for an authorization code."""
        code_verifier, code_challenge = AH.generate_code_challenge()
        sso_url, state = AH.redirect_to_sso(
            client_id=credentials.client_id,
            redirect_uri=credentials.callback_url,
            scopes=credentials.scopes,
            authorization_endpoint=self.store.oauth_metadata.authorization_endpoint,
            challenge=code_challenge,
        )
        auth_request = AuthRequest(
            code_verifier=code_verifier,
            sso_url=sso_url,
            state=state,
            callback_url=credentials.callback_url,
        )
        return auth_request

    async def request_character_token(
        self, credentials: EveCredentials, auth_request: AuthRequest
    ) -> CharacterToken:
        """Request a CharacterToken.

        Run a callback server to get the auth code.
        Request the token from the token endpoint.
        Validate the JWT token.
        Create and return a CharacterToken.

        Args:
            credentials: The application credentials to use.
            auth_request: The prepared AuthRequest containing the code verifier and state.
        """
        split_url = SplitURL.from_url(credentials.callback_url)
        code = await AH.run_callback_server(
            expected_state=auth_request.state,
            callback_host=split_url.host,
            callback_route=split_url.route,
            callback_port=split_url.port,
            timeout=self._server_timeout,
        )
        async with aiohttp.ClientSession() as session:
            oauth_token = await AH.request_token(
                client_id=credentials.client_id,
                authorization_code=code,
                code_verifier=auth_request.code_verifier,
                token_endpoint=self.store.oauth_metadata.token_endpoint,
                user_agent=self.user_agent(),
                client_session=session,
            )
            validated_token = AH.validate_jwt_token(
                access_token=oauth_token["access_token"],
                jwks_client=self.jwks_client,
                audience=self.store.oauth_metadata.audience,
                issuers=self.store.oauth_metadata.issuers,
                user_agent=self.user_agent(),
            )
            character_token = make_character_token(
                validated_token=validated_token,
                token=oauth_token,
                client_id=credentials.client_id,
            )
            return character_token

    @property
    def jwks_client(self) -> PyJWKClient:
        """Lazy init jwks client."""
        header = {"User-Agent": self.user_agent()}
        logger.info(f"Fetching JWKS from {self.store.oauth_metadata.jwks_uri}")
        if self._jwks_client is None:
            self._jwks_client = PyJWKClient(
                self.store.oauth_metadata.jwks_uri, headers=header
            )
        return self._jwks_client

    #############################################################################
    # Credential Storage Methods
    #############################################################################
    def store_credentials(self, credentials: EveCredentials) -> None:
        """Store new application credentials.

        Args:
            credentials: The EveCredentials to store.
        """
        if self.is_credentials_in_store(credentials):
            raise AuthStoreException(
                f"Client_id {credentials.client_id} already exists in store. Remove "
                "credentials first. Note: this will remove associated tokens."
            )
        self.store.credentials[credentials.client_id] = credentials
        self._save_store()

    def remove_credentials(self, credentials: EveCredentials) -> bool:
        """Remove application credentials and associated tokens.

        Args:
            credentials: The EveCredentials to remove.

        Returns:
            True if credentials were removed, False if they were not found.
        """
        if self.is_credentials_in_store(credentials):
            self.store.credentials.pop(credentials.client_id, None)
            self.store.tokens.pop(credentials.client_id, None)
            self._save_store()
            return True
        return False

    def list_credentials(self) -> list[EveCredentials]:
        """List all stored application credentials."""
        creds = deepcopy(list(self.store.credentials.values()))
        return creds

    def get_credentials_from_id(self, client_id: str) -> EveCredentials | None:
        """Get credentials by client ID.

        Args:
            client_id: The client ID of the credentials to retrieve.
        """
        if client_id in self.store.credentials:
            return deepcopy(self.store.credentials[client_id])
        return None

    def get_credentials_from_alias(self, client_alias: str) -> EveCredentials | None:
        """Get credentials by client alias.

        Args:
            client_alias: The client alias of the credentials to retrieve.
        """
        for creds in self.store.credentials.values():
            if creds.client_alias == client_alias:
                return deepcopy(creds)
        return None

    #############################################################################
    # Token Storage Methods
    #############################################################################
    def store_token(self, token: CharacterToken, credentials: EveCredentials) -> None:
        """Store a character token.

        Args:
            token: The CharacterToken to store.
            credentials: The EveCredentials associated with the token.
        """
        if token.client_id != credentials.client_id:
            raise AuthStoreException(
                "Tried to store a token with incorrect credentials."
            )
        if not self.is_credentials_in_store(credentials):
            raise AuthStoreException(
                "Tried to store a token with credientials that are not in the store."
            )
        if credentials.client_id not in self.store.tokens:
            self.store.tokens[credentials.client_id] = {}
        self.store.tokens[credentials.client_id][token.character_id] = token
        self._save_store()

    def remove_token(self, token: CharacterToken, credentials: EveCredentials) -> bool:
        """Remove a character token.

        Args:
            token: The CharacterToken to remove.
            credentials: The EveCredentials associated with the token.

        Returns:
            True if the token was removed, False if it was not found.
        """
        if self.is_token_in_store(token=token, credentials=credentials):
            self.store.tokens.get(credentials.client_id, {}).pop(
                token.character_id, None
            )
            self._save_store()
            return True
        return False

    def list_tokens(self, credentials: EveCredentials) -> list[CharacterToken]:
        """List all stored character tokens for given credentials.

        Args:
            credentials: The EveCredentials associated with the tokens.

        Returns:
            List of CharacterToken instances.
        """
        if credentials.client_id not in self.store.credentials:
            raise AuthStoreException(
                "Tried to list tokens before adding credentials to store."
            )
        tokens = self.store.tokens.get(credentials.client_id, {})
        return deepcopy(list(tokens.values()))

    def get_token_from_id(
        self, character_id: int, credentials: EveCredentials, buffer: int = 5
    ) -> CharacterToken | None:
        """Get a character token by character ID.

        Args:
            character_id: The character ID of the token to retrieve.
            credentials: The EveCredentials associated with the token.
            buffer: Minutes before expiry to consider needing refresh. -1 to skip refresh.

        Returns:
            The CharacterToken if found, None otherwise.
        """
        if credentials.client_id not in self.store.credentials:
            raise AuthStoreException(
                "Tried to get token before adding credentials to store."
            )
        char_token = self.store.tokens.get(credentials.client_id, {}).get(
            character_id, None
        )
        if char_token is not None:
            if buffer == -1:
                return deepcopy(char_token)
            if char_token.needs_refresh(buffer):
                try:
                    updated = asyncio.run(self._refresh_token(token=char_token))
                except Exception as e:
                    raise AuthStoreException(f"Failed to refresh token {e}") from e
                self.store_token(token=updated, credentials=credentials)
                # return refreshed token
                return updated
            # Return copy of still current token
            return deepcopy(char_token)
        # Return None
        return char_token

    async def _refresh_all_tokens(
        self, tokens: list[CharacterToken]
    ) -> list[CharacterToken | BaseException]:
        """Refresh tokens.

        Gathers exceptions so that successful refreshes can still be used.
        """
        async with aiohttp.ClientSession() as session:
            tasks = [self._refresh_token(t, session) for t in tokens]
            refreshed_tokens = await asyncio.gather(*tasks, return_exceptions=True)
            return refreshed_tokens

    async def _refresh_token(
        self, token: CharacterToken, session: aiohttp.ClientSession | None = None
    ) -> CharacterToken:
        """Refresh a single token."""
        if session is None:
            session = aiohttp.ClientSession()

        try:
            async with session:
                refreshed_token = await AH.request_refreshed_token(
                    refresh_token=token.refresh_token,
                    client_id=token.client_id,
                    token_endpoint=self.store.oauth_metadata.token_endpoint,
                    user_agent=self.user_agent(),
                    client_session=session,
                )
                validated_token = AH.validate_jwt_token(
                    access_token=refreshed_token["access_token"],
                    jwks_client=self.jwks_client,
                    audience=self.store.oauth_metadata.audience,
                    issuers=self.store.oauth_metadata.issuers,
                    user_agent=self.user_agent(),
                )
                updated = make_character_token(
                    validated_token=validated_token,
                    token=refreshed_token,
                    client_id=token.client_id,
                )
                return updated
        except Exception as e:
            raise AuthStoreException(
                f"There was an error while trying to refresh the token {e}"
            ) from e

    def get_all_tokens(
        self, credentials: EveCredentials, buffer: int = 5
    ) -> list[CharacterToken]:
        """Get all character tokens for given credentials.

        Args:
            credentials: The EveCredentials associated with the tokens.
            buffer: Minutes before expiry to consider needing refresh. -1 to skip refresh.

        Returns:
            List of CharacterToken instances.
        """
        if self.is_credentials_in_store(credentials):
            tokens = self.store.tokens.get(credentials.client_id, {})
            copied_tokens = deepcopy(list(tokens.values()))
            if buffer == -1:
                # Don't try to refresh
                return copied_tokens
            dirty = False
            needs_refresh = [x for x in copied_tokens if x.needs_refresh(buffer)]
            ready_tokens = [x for x in copied_tokens if not x.needs_refresh(buffer)]
            refreshed_tokens = asyncio.run(self._refresh_all_tokens(needs_refresh))
            failed: list[BaseException] = []
            for token in refreshed_tokens:
                if isinstance(token, BaseException):
                    failed.append(token)
                else:
                    self.store.tokens[credentials.client_id][token.character_id] = token
                    dirty = True
                    ready_tokens.append(token)
            if dirty:
                self._save_store()
            if failed:
                msg = f"{len(failed)} tokens failed to refresh."
                logger.error(f"{msg} {failed}")
                raise AuthStoreException(msg)
            return ready_tokens
        # No credentials in store, so no tokens.
        return []

    ###############################################################################
    # Helper Methods
    ###############################################################################

    def update_user_agent(
        self,
        character_name: str,
        user_email: str,
        user_app_name: str,
        user_app_version: str,
    ) -> None:
        """Update the user agent settings."""
        self.store.user_agent.character_name = character_name
        self.store.user_agent.user_email = user_email
        self.store.user_agent.user_app_name = user_app_name
        self.store.user_agent.user_app_version = user_app_version
        self._save_store()

    def user_agent(self) -> str:
        """Construct the User-Agent header string."""
        user_portion = (
            f"{self.store.user_agent.user_app_name}/{self.store.user_agent.user_app_version} "
            f"(eve:{self.store.user_agent.character_name}; {self.store.user_agent.user_email})"
        )
        app_metadata = metadata.metadata("esi-auth")
        app_name = app_metadata["name"]
        app_version = app_metadata["version"]
        app_source_url = get_package_url("esi-auth", "Source")
        _, author_email = get_author_email("esi-auth")
        esi_auth_portion = (
            f"{app_name}/{app_version} ({author_email}; +{app_source_url})"
        )
        return f"{user_portion} {esi_auth_portion}"

    def is_credentials_in_store(self, credentials: EveCredentials) -> bool:
        """Check if credentials are in the store."""
        result = self.store.credentials.get(credentials.client_id, None)
        if result is None:
            return False
        return True

    def is_token_in_store(
        self, token: CharacterToken, credentials: EveCredentials
    ) -> bool:
        """Check if a character token is in the store."""
        if not self.is_credentials_in_store(credentials):
            raise AuthStoreException(
                "Tried to use credentials that were not in the store."
            )
        tokens = self.store.tokens.get(credentials.client_id, {})
        return token.character_id in tokens

    def update_oauth_metadata(
        self, metadata_url: str = OAUTH_METADATA_URL, audience: str = "Eve Online"
    ) -> None:
        """Update the oauth settings."""
        metadata = AH.fetch_oauth_metadata_sync(
            url=metadata_url, user_agent=self.user_agent()
        )
        try:
            oauth_settings = OauthSettings(
                audience=audience,
                metadata_endpoint=metadata_url,
                issuers=[metadata["issuer"]],
                authorization_endpoint=metadata["authorization_endpoint"],
                token_endpoint=metadata["token_endpoint"],
                jwks_uri=metadata["jwks_uri"],
                revocation_endpoint=metadata["revocation_endpoint"],
                downloaded_at=Instant.now(),
                raw_metadata=metadata,  # pyright: ignore[reportArgumentType]
            )
            self.store.oauth_metadata = oauth_settings
            self._save_store()
        except Exception as e:
            raise AuthStoreException(
                "Failed to update oauth settings due to {e}"
            ) from e

    def _save_store(self) -> None:
        # Save the current store to disk if a path is set
        if self.store_path is not None:
            self.store.save_to_disk(self.store_path)
        else:
            pass
            # If no path is set, do nothing, using in-memory store only


class TokenManager:
    def __init__(self, store_path: Path) -> None:
        """Initialize the TokenManager with a store path.

        Args:
            store_path: Path to the file where the store is saved.

        """
        self.store_path = store_path

    def _load_esi_auth(self) -> EsiAuth:
        """Load the EsiAuth instance."""
        esi_auth = EsiAuth(store_path=self.store_path)
        return esi_auth

    def get_character_tokens(
        self, credential_alias: str, buffer: int = 5
    ) -> list[CharacterToken]:
        """Get all character tokens from the store.

        Args:
            credential_alias: The alias of the credentials to use.
            buffer: Minutes before expiry to consider needing refresh. -1 to skip refresh.

        Returns:
            List of CharacterToken instances.
        """
        esi_auth = self._load_esi_auth()
        credentials = esi_auth.get_credentials_from_alias(credential_alias)
        if credentials is None:
            return []
        tokens = esi_auth.get_all_tokens(credentials, buffer=buffer)
        return tokens


def make_character_token(
    validated_token: AH.ValidatedToken, token: AH.OauthToken, client_id: str
) -> CharacterToken:
    """Create a CharacterToken from a validated JWT token and raw token data.

    Args:
        validated_token: The validated JWT token payload.
        token: The raw token data from the token endpoint.
        client_id: The client ID associated with the token.

    Returns:
        CharacterToken: The constructed CharacterToken instance.
    """
    return CharacterToken(
        character_id=validated_token.get("sub", "Unknown").split(":")[-1],
        character_name=validated_token.get("name", "Unknown"),
        access_token=token["access_token"],
        refresh_token=token["refresh_token"],
        client_id=client_id,
        expires_at=Instant.now().add(seconds=token["expires_in"]),
        scopes=validated_token.get("scp", []),
        token_type=token["token_type"],
        updated_at=Instant.now(),
    )
