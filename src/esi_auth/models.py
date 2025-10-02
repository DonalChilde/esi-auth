from dataclasses import dataclass
from typing import Self

from pydantic import BaseModel, Field
from whenever import Instant


def _get_current_instant() -> Instant:
    """Factory function to get current instant for default values.

    This function is used as a default_factory to avoid circular dependencies
    that can occur when using Instant.now directly in field definitions.

    Returns:
        Current instant in time.
    """
    return Instant.now()


@dataclass
class CallbackUrl:
    callback_host: str = "localhost"
    callback_port: int = 8080
    callback_route: str = "/callback"

    def url(self) -> str:
        """Construct the full callback URL.

        Returns:
            The complete callback URL.
        """
        return f"http://{self.callback_host}:{self.callback_port}{self.callback_route}"

    @classmethod
    def parse(cls, url: str) -> Self:
        """Parse a full URL into its components.

        Args:
            url: The full callback URL to parse.

        Returns:
            An instance of CallbackUrl with parsed components.
        """
        from urllib.parse import urlparse

        parsed = urlparse(url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 8080
        route = parsed.path or "/callback"
        return cls(callback_host=host, callback_port=port, callback_route=route)


class VerifiedToken(BaseModel):
    """Represents a verified character token.

    This model stores information about a character token that has been
    verified for validity and scope.
    """

    character_id: int = Field(
        ..., description="The EVE character ID", alias="CharacterID"
    )
    character_name: str = Field(
        ..., description="The character's name", alias="CharacterName"
    )
    expires_on: Instant = Field(
        ..., description="When the token expires", alias="ExpiresOn"
    )
    scopes: list[str] = Field(
        default_factory=list, description="List of authorized scopes", alias="Scopes"
    )
    token_type: str = Field(..., description="Type of token", alias="TokenType")
    character_owner_hash: str = Field(
        ..., description="Hash of the token owner", alias="CharacterOwnerHash"
    )
    # TODO drop this field?
    client_id: str = Field(
        ..., description="Client ID associated with the token", alias="ClientID"
    )
    verified_at: Instant = Field(
        default_factory=_get_current_instant, description="When the token was verified"
    )


class EveCredentials(BaseModel):
    """EVE SSO application credentials.

    This model holds the client ID and secret required for OAuth2 authentication
    with the EVE Online SSO service.
    """

    name: str = Field(..., description="The name of the application")
    alias: str | None = Field(None, description="Unique alias for the application")
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


class CredentialStore(BaseModel):
    """Container for multiple EVE application credentials.

    This model manages a collection of EVE application credentials, allowing
    for easy access and modification of stored credentials.
    """

    credentials: dict[str, EveCredentials] = Field(
        default_factory=dict,
        description="Dictionary mapping client_id to EveCredentials",
    )
    last_updated: Instant = Field(
        default_factory=_get_current_instant,
        description="When this collection was last modified",
    )

    def add_credential(self, cred: EveCredentials) -> None:
        """Add or update an application's credentials.

        Updates the last_updated timestamp to reflect the modification.

        Args:
            cred: The EveCredentials to add or update.
        """
        self.credentials[cred.client_id] = cred
        self.last_updated = Instant.now()

    def remove_credential(self, client_id: str) -> bool:
        """Remove an application's credentials by client_id.

        Updates the last_updated timestamp if a credential was removed.

        Args:
            client_id: The client_id of the application to remove.

        Returns:
            True if credential was removed, False if not found.
        """
        if client_id in self.credentials:
            del self.credentials[client_id]
            self.last_updated = Instant.now()
            return True
        return False

    def get_credential(self, client_id: str) -> EveCredentials | None:
        """Retrieve an application's credentials by client_id.

        Args:
            client_id: The client_id of the application to retrieve.

        Returns:
            EveCredentials if found, None otherwise.
        """
        return self.credentials.get(client_id)

    def list_credentials(self) -> list[EveCredentials]:
        """Get a list of all stored application credentials.

        Returns:
            List of all EveCredentials instances in the collection.
        """
        return list(self.credentials.values())

    def has_credential(self, client_id: str) -> bool:
        """Check if an application's credentials exist in the collection.

        Args:
            client_id: The client_id of the application to check.

        Returns:
            True if credentials exist, False otherwise.
        """
        return client_id in self.credentials


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


class AuthenticatedCharacters(BaseModel):
    """Container for all authenticated characters' tokens.

    This model manages the collection of authenticated characters and provides
    methods for accessing and modifying the token data.
    """

    characters: dict[int, CharacterToken] = Field(
        default_factory=dict[int, CharacterToken],
        description="Dictionary mapping character_id to CharacterToken",
    )
    last_updated: Instant = Field(
        default_factory=_get_current_instant,
        description="When this collection was last modified",
    )

    def add_character(self, token: CharacterToken) -> None:
        """Add or update a character's token data.

        Updates the last_updated timestamp to reflect the modification.

        Args:
            token: The CharacterToken to add or update.
        """
        self.characters[token.character_id] = token
        self.last_updated = Instant.now()

    def remove_character(self, character_id: int) -> bool:
        """Remove a character from the collection.

        Updates the last_updated timestamp if a character was removed.

        Args:
            character_id: The character ID to remove.

        Returns:
            True if character was removed, False if not found.
        """
        if character_id in self.characters:
            del self.characters[character_id]
            self.last_updated = Instant.now()
            return True
        return False

    def get_character(self, character_id: int) -> CharacterToken | None:
        """Retrieve a character's token data.

        Args:
            character_id: The character ID to retrieve.

        Returns:
            CharacterToken if found, None otherwise.
        """
        return self.characters.get(character_id)

    def list_characters(self) -> list[CharacterToken]:
        """Get a list of all authenticated characters.

        Returns:
            List of all CharacterToken instances in the collection.
        """
        return list(self.characters.values())

    def has_character(self, character_id: int) -> bool:
        """Check if a character exists in the collection.

        Args:
            character_id: The character ID to check.

        Returns:
            True if character exists, False otherwise.
        """
        return character_id in self.characters

    def get_expired_tokens(self) -> list[CharacterToken]:
        """Get list of characters with expired tokens.

        Returns:
            List of CharacterToken objects with expired access tokens.
        """
        return [token for token in self.characters.values() if token.is_expired()]

    def get_tokens_needing_refresh(
        self, buffer_minutes: int = 5
    ) -> list[CharacterToken]:
        """Get list of characters whose tokens need refreshing.

        Args:
            buffer_minutes: Minutes before expiry to consider needing refresh.

        Returns:
            List of CharacterToken objects that should be refreshed.
        """
        return [
            token
            for token in self.characters.values()
            if token.needs_refresh(buffer_minutes)
        ]
