"""Data models for ESI authentication.

This module contains Pydantic models for managing Eve Online ESI authentication
tokens, character data, and related metadata.
"""

from datetime import datetime

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


class ESIAuthenticationResponse(BaseModel):
    """Response from ESI OAuth authentication.

    This model represents the response received from the EVE Online
    SSO OAuth authentication process.
    """

    access_token: str = Field(..., description="The access token")
    refresh_token: str = Field(..., description="The refresh token")
    expires_in: int = Field(..., description="Token lifetime in seconds")
    token_type: str = Field(default="Bearer", description="Type of token")


class CharacterInfo(BaseModel):
    """Basic character information from ESI.

    This model represents character data retrieved from the ESI API
    for verification and display purposes.
    """

    character_id: int = Field(..., description="The character ID")
    name: str = Field(..., description="The character's name")
    description: str | None = Field(None, description="Character description")
    corporation_id: int = Field(..., description="Character's corporation ID")
    alliance_id: int | None = Field(None, description="Character's alliance ID")
    birthday: datetime = Field(..., description="Character creation date")
    gender: str = Field(..., description="Character gender")
    race_id: int = Field(..., description="Character's race ID")
    bloodline_id: int = Field(..., description="Character's bloodline ID")
    security_status: float | None = Field(
        None, description="Character's security status"
    )


class AuthenticationError(Exception):
    """Exception raised during authentication process.

    This exception is raised when authentication fails or encounters
    an error during the OAuth flow or token operations.
    """

    def __init__(self, message: str, error_code: str | None = None):
        """Initialize the authentication error.

        Args:
            message: Human-readable error message.
            error_code: Optional error code for programmatic handling.
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class TokenRefreshError(Exception):
    """Exception raised when token refresh fails.

    This exception is raised when attempting to refresh an access token
    fails for any reason.
    """

    def __init__(self, message: str, character_id: int, error_code: str | None = None):
        """Initialize the token refresh error.

        Args:
            message: Human-readable error message.
            character_id: The character ID whose token refresh failed.
            error_code: Optional error code for programmatic handling.
        """
        super().__init__(message)
        self.message = message
        self.character_id = character_id
        self.error_code = error_code
