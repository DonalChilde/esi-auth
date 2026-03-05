"""Models for ESI Auth."""

from pydantic import BaseModel, ConfigDict
from whenever import Instant


class OauthToken(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str

    model_config = ConfigDict(frozen=True)


class EveAppCredentials(BaseModel):
    """EVE application credentials.

    Field names match the JSON keys returned by the ESI app registration page.
    https://developers.eveonline.com/applications
    """

    name: str
    description: str
    clientId: str
    clientSecret: str
    callbackUrl: str
    scopes: list[str]

    model_config = ConfigDict(frozen=True)


class CharacterToken(BaseModel):
    character_id: int
    character_name: str
    app_alias: str
    refreshed_at: int
    oauth_token: OauthToken

    model_config = ConfigDict(frozen=True)

    @property
    def expires_at(self) -> int:
        """Return the timestamp when the token expires."""
        return self.refreshed_at + self.oauth_token.expires_in

    @property
    def expires_in(self) -> int:
        """Return the number of seconds until the token expires."""
        return self.expires_at - Instant.now().timestamp()


class AppCredentials(BaseModel):
    alias: str
    credentials: EveAppCredentials

    model_config = ConfigDict(frozen=True)
