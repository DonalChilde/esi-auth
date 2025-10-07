"""ESI OAuth2 authentication flow implementation.

This module handles the complete OAuth2 flow for EVE Online ESI authentication,
including authorization, token exchange, and token refresh operations. These functions
operate at a higher level than their auth_helper counterparts, orchestrating
the entire process in a more user-friendly manner, creating and consuming CharacterToken
objects.

"""

import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import aiohttp
from jwt.jwks_client import PyJWKClient
from whenever import Instant

from esi_auth.models import CallbackUrl

from . import auth_helpers as AH
from .helpers import get_user_agent
from .models import CharacterToken, EveCredentials
from .settings import EsiAuthSettings, get_settings

USER_AGENT = get_user_agent()


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


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


@dataclass(slots=True)
class AuthState:
    """State information for initial authentication and token exchange."""

    code_verifier: str
    code_challenge: str
    state: str
    sso_url: str
    authorization_code: str | None = None


@dataclass(slots=True)
class OauthParams:
    """OAuth2 parameters required for authentication and validation."""

    token_endpoint: str
    authorization_endpoint: str
    audience: str
    issuer: Sequence[str]
    jwks_uri: str


def get_oauth_params(settings: EsiAuthSettings | None = None) -> OauthParams:
    """Retrieve OAuth2 parameters from settings."""
    settings = get_settings() if settings is None else settings
    return OauthParams(
        token_endpoint=settings.token_endpoint,
        authorization_endpoint=settings.authorization_endpoint,
        audience=settings.oauth2_audience,
        issuer=settings.oauth2_issuer,
        jwks_uri=settings.jwks_uri,
    )


def get_auth_state(
    credentials: EveCredentials,
    oauth_params: OauthParams,
    scopes: Sequence[str] | None = None,
) -> AuthState:
    """Generate the AuthState for the initial authentication flow.

    Creates the code verifier, code challenge, state, and SSO URL.

    Args:
        credentials: The EveCredentials instance containing client info.
        oauth_params: The OauthParams instance containing OAuth2 parameters.
        scopes: Optional sequence of scopes to request. Must be a subset of credentials.scopes.
            If None, uses credentials.scopes.

    Returns:
        AuthState: The generated authentication state.
    """
    code_verifier, code_challenge = AH.generate_code_challenge()
    if scopes is None:
        scopes = credentials.scopes
    else:
        for scope in scopes:
            if scope not in credentials.scopes:
                raise ValueError(
                    f"Requested scope '{scope}' not in allowed scopes: {credentials.scopes}"
                )
    sso_url, state = AH.redirect_to_sso(
        client_id=credentials.client_id,
        redirect_uri=credentials.callback_url,
        scopes=scopes or [],
        authorization_endpoint=oauth_params.authorization_endpoint,
        challenge=code_challenge,
    )
    logger.info(f"Generated SSO URL: {sso_url} with state: {state}")

    return AuthState(
        code_verifier=code_verifier,
        code_challenge=code_challenge,
        state=state,
        sso_url=sso_url,
    )


async def request_authorization_code(
    credentials: EveCredentials, auth_state: AuthState
) -> str:
    """Run the callback server to receive the authorization code.

    In addtion to returning the authorization code, this function also updates
    the provided AuthState instance with the received code.

    Args:
        credentials: The EveCredentials instance containing client info.
        auth_state: The AuthState instance containing state for the auth flow.

    Returns:
        str: The received authorization code.
    """
    logger.info("Starting callback server to receive authorization code...")
    callback_url = CallbackUrl.parse(credentials.callback_url)
    authorization_code = await AH.run_callback_server(
        callback_host=callback_url.callback_host,
        callback_port=callback_url.callback_port,
        callback_route=callback_url.callback_route,
        expected_state=auth_state.state,
    )
    logger.info(f"Received authorization code: {authorization_code}")
    auth_state.authorization_code = authorization_code
    return authorization_code


async def request_token(
    credentials: EveCredentials,
    auth_state: AuthState,
    oauth_params: OauthParams,
    client_session: aiohttp.ClientSession,
    user_agent: str = USER_AGENT,
) -> AH.OauthToken:
    """Request an access token using the authorization code.

    Args:
        credentials: The EveCredentials instance containing client info.
        auth_state: The AuthState instance containing state for the auth flow.
        oauth_params: The OauthParams instance containing OAuth2 parameters.
        client_session: The aiohttp client session to use for HTTP requests.
        user_agent: The User-Agent string to use for HTTP requests.

    Returns:
        AH.OauthToken: The obtained OAuth token.

    Raises:
        ValueError: If the authorization code is not set in AuthState.
    """
    logger.info("Requesting access token...")
    if auth_state.authorization_code is None:
        raise ValueError("Authorization code is not set in AuthState.")
    token = await AH.request_token(
        client_id=credentials.client_id,
        authorization_code=auth_state.authorization_code,
        code_verifier=auth_state.code_verifier,
        token_endpoint=oauth_params.token_endpoint,
        client_session=client_session,
        user_agent=user_agent,
    )
    logger.info(f"Received token: {token}")
    return token


def validate_token(
    oauth_params: OauthParams,
    jwks_client: PyJWKClient | None,
    access_token: str,
    user_agent: str = USER_AGENT,
) -> dict[str, Any]:
    """Validate and decode the received JWT access token.

    Args:
        oauth_params: The OauthParams instance containing OAuth2 parameters.
        jwks_client: Optional PyJWKClient instance for token validation. If None, a new one will be created.
        access_token: The JWT access token to validate.
        user_agent: The User-Agent string to use for HTTP requests.

    Returns:
        dict: The validated and decodedJWT token payload.
    """
    logger.info("Validating access token...")
    if jwks_client is None:
        jwks_client = PyJWKClient(oauth_params.jwks_uri)
    validated_token = AH.validate_jwt_token(
        access_token=access_token,
        jwks_client=jwks_client,
        audience=oauth_params.audience,
        issuers=oauth_params.issuer,
        user_agent=user_agent,
    )
    logger.info(f"Validated token: {validated_token}")
    return validated_token


async def authenticate_character(
    credentials: EveCredentials,
    oauth_params: OauthParams,
    auth_state: AuthState,
) -> CharacterToken:
    """Run the full authentication flow for a character.

    This function orchestrates the complete OAuth2 flow including:
    - Generating the SSO URL
    - Running the callback server to get the authorization code
    - Exchanging the code for an access token
    - Validating the received token

    Args:
        credentials: The EveCredentials instance containing client info.
        oauth_params: The OauthParams instance containing OAuth2 parameters.
        auth_state: The AuthState instance containing state for the auth flow.

    Returns:
        CharacterToken: The authenticated character's token information.

    Raises:
        AuthenticationError: If any step in the authentication process fails.
    """
    logger.info(f"Starting authentication flow. Navigate to: {auth_state.sso_url}")
    logger.info(f"Listening on {credentials.callback_url} for callback...")
    async with aiohttp.ClientSession() as client_session:
        _authorization_code = await request_authorization_code(
            credentials=credentials, auth_state=auth_state
        )
        logger.info(f"Received authorization code: {_authorization_code}")
        token = await request_token(
            credentials=credentials,
            auth_state=auth_state,
            oauth_params=oauth_params,
            client_session=client_session,
        )
        logger.info(f"Received token: {token}")
        validated_token = validate_token(
            oauth_params, jwks_client=None, access_token=token["access_token"]
        )
        character_token = character_token_from_validated_token(validated_token, token)
        logger.info(f"Created CharacterToken: {character_token}")
    return character_token


def character_token_from_validated_token(
    validated_token: dict[str, Any], token: AH.OauthToken
) -> CharacterToken:
    """Create a CharacterToken from a validated JWT token and raw token data.

    Args:
        validated_token: The validated JWT token payload.
        token: The raw token data from the token endpoint.

    Returns:
        CharacterToken: The constructed CharacterToken instance.
    """
    return CharacterToken(
        character_id=validated_token.get("sub", "Unknown").split(":")[-1],
        character_name=validated_token.get("name", "Unknown"),
        access_token=token["access_token"],
        refresh_token=token["refresh_token"],
        expires_at=Instant.now().add(seconds=token["expires_in"]),
        scopes=validated_token.get("scp", []),
        token_type=token["token_type"],
        updated_at=Instant.now(),
    )


async def refresh_character(
    credentials: EveCredentials,
    oauth_params: OauthParams,
    character_token: CharacterToken,
    client_session: aiohttp.ClientSession,
    jwks_client: PyJWKClient | None = None,
    user_agent: str = USER_AGENT,
) -> CharacterToken:
    """Refresh an access token using the provided refresh token.

    Args:
        credentials: The EveCredentials instance containing client info.
        oauth_params: The OauthParams instance containing OAuth2 parameters.
        character_token: The CharacterToken instance to refresh.
        client_session: The aiohttp client session to use for HTTP requests.
        jwks_client: Optional PyJWKClient instance for token validation. If None, a new one will be created.
        user_agent: The User-Agent string to use for HTTP requests.

    Returns:
        CharacterToken: The refreshed character token.

    Raises:
        TokenRefreshError: If the token refresh fails.
    """
    try:
        refresh_token = await AH.request_refreshed_token(
            refresh_token=character_token.refresh_token,
            client_id=credentials.client_id,
            token_endpoint=oauth_params.token_endpoint,
            user_agent=user_agent,
            client_session=client_session,
        )
        validated_token = validate_token(
            oauth_params=oauth_params,
            jwks_client=jwks_client,
            access_token=refresh_token["access_token"],
        )
        new_character_token = character_token_from_validated_token(
            validated_token, refresh_token
        )
    except Exception as e:
        logger.error(
            f"Error refreshing token for character {character_token.character_id}: {e}"
        )
        raise TokenRefreshError(
            message=str(e),
            character_id=int(character_token.character_id),
            error_code=getattr(e, "error_code", None),
        ) from e

    return new_character_token


async def refresh_multiple_characters(
    credentials: EveCredentials,
    oauth_params: OauthParams,
    character_tokens: Sequence[CharacterToken],
) -> list[CharacterToken | Exception]:
    """Refresh multiple character tokens concurrently.

    Args:
        credentials: The EveCredentials instance containing client info.
        oauth_params: The OauthParams instance containing OAuth2 parameters.
        character_tokens: A sequence of CharacterToken instances to refresh.

    Returns:
        A dictionary mapping character IDs to their refreshed CharacterToken instances.

    Raises:
        TokenRefreshError: If any token refresh fails.
    """
    refreshed_tokens: list[CharacterToken | Exception] = []
    jwks_client = PyJWKClient(oauth_params.jwks_uri)
    async with aiohttp.ClientSession() as client_session:
        tasks = [
            refresh_character(
                credentials=credentials,
                oauth_params=oauth_params,
                character_token=token,
                client_session=client_session,
                jwks_client=jwks_client,
            )
            for token in character_tokens
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            refreshed_tokens.append(result)
        else:
            refreshed_tokens.append(result)  # pyright: ignore[reportArgumentType]

    return refreshed_tokens
