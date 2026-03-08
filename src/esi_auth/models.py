"""Models for ESI Auth."""

from dataclasses import dataclass
from typing import TypedDict

from pydantic import BaseModel, ConfigDict
from whenever import Instant


@dataclass(slots=True, frozen=True)
class CharacterAuth:
    """The return from the `AuthProviderProtocol.character_auth` method."""

    character_id: int
    character_name: str
    auth_headers: dict[str, str]
    expires_at: int


@dataclass(slots=True, frozen=True)
class OauthToken:
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str


class OauthMetadata(TypedDict):
    """OAuth2 server metadata from well-known endpoint."""

    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    response_types_supported: list[str]
    jwks_uri: str
    revocation_endpoint: str
    subject_types_supported: list[str]
    revocation_endpoint_auth_methods_supported: list[str]
    token_endpoint_auth_methods_supported: list[str]
    id_token_signing_alg_values_supported: list[str]
    token_endpoint_auth_signing_alg_values_supported: list[str]
    code_challenge_methods_supported: list[str]


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
    created: int
    expires: int
    oauth_token: OauthToken

    model_config = ConfigDict(frozen=True)

    @property
    def expires_in(self) -> int:
        """Return the number of seconds until the token expires."""
        return self.expires - Instant.now().timestamp()


@dataclass(slots=True, frozen=True)
class RequestParams:
    url: str
    state: str
    code_verifier: str
    code_challenge: str


@dataclass(slots=True, frozen=True)
class ValidatedToken:
    character_id: int
    character_name: str
    created_at: int
    expires_at: int


# class AppCredentials(BaseModel):
#     alias: str
#     credentials: EveAppCredentials

#     model_config = ConfigDict(frozen=True)
