from dataclasses import dataclass

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
