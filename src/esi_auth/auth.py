"""ESI OAuth2 authentication flow implementation.

This module handles the complete OAuth2 flow for EVE Online ESI authentication,
including authorization, token exchange, and token refresh operations. These functions
operate at a higher level than their auth_helper counterparts, orchestrating
the entire process in a more user-friendly manner, creating and consuming CharacterToken
objects.

"""

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
from .models import CharacterToken
from .settings import get_settings

USER_AGENT = get_user_agent()


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


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


@dataclass
class AuthParams:
    client_id: str
    token_endpoint: str
    authorization_endpoint: str
    callback_url: CallbackUrl
    jwks_client: PyJWKClient
    audience: str
    issuer: Sequence[str]
    user_agent: str
    code_verifier: str
    code_challenge: str


def create_auth_params(
    jwks_client: PyJWKClient | None = None,
) -> AuthParams:
    """Create authentication parameters from current settings.

    Args:
        jwks_client: Optional PyJWKClient instance. If None, a new one will be created.

    Returns:
        AuthParams: The authentication parameters.
    """
    settings = get_settings()
    if jwks_client is None:
        jwks_client = PyJWKClient(settings.jwks_uri)
    code_verifier, code_challenge = AH.generate_code_challenge()
    return AuthParams(
        client_id=settings.client_id,
        token_endpoint=settings.token_endpoint,
        authorization_endpoint=settings.authorization_endpoint,
        callback_url=CallbackUrl(
            callback_host=settings.callback_host,
            callback_port=settings.callback_port,
            callback_route=settings.callback_route,
        ),
        jwks_client=jwks_client,
        audience=settings.oauth2_audience,
        issuer=settings.oauth2_issuer,
        user_agent=USER_AGENT,
        code_verifier=code_verifier,
        code_challenge=code_challenge,
    )


def get_sso_url(auth_params: AuthParams, scopes: Sequence[str]) -> tuple[str, str]:
    """Generate the SSO URL for user authorization."""
    sso_url, state = AH.redirect_to_sso(
        client_id=auth_params.client_id,
        redirect_uri=auth_params.callback_url.url(),
        scopes=scopes,
        authorization_endpoint=auth_params.authorization_endpoint,
        challenge=auth_params.code_challenge,
    )
    logger.info(f"Generated SSO URL: {sso_url} with state: {state}")
    return sso_url, state


async def request_authorization_code(
    auth_params: AuthParams, expected_state: str
) -> str:
    """Run the callback server to receive the authorization code."""
    logger.info("Starting callback server to receive authorization code...")
    authorization_code = await AH.run_callback_server(
        callback_host=auth_params.callback_url.callback_host,
        callback_port=auth_params.callback_url.callback_port,
        callback_route=auth_params.callback_url.callback_route,
        expected_state=expected_state,
    )
    logger.info(f"Received authorization code: {authorization_code}")
    return authorization_code


async def request_token(
    auth_params: AuthParams,
    authorization_code: str,
    client_session: aiohttp.ClientSession,
) -> AH.OauthToken:
    """Request an access token using the authorization code."""
    logger.info("Requesting access token...")
    token = await AH.request_token(
        client_id=auth_params.client_id,
        authorization_code=authorization_code,
        code_verifier=auth_params.code_verifier,
        token_endpoint=auth_params.token_endpoint,
        client_session=client_session,
        user_agent=auth_params.user_agent,
    )
    logger.info(f"Received token: {token}")
    return token


def validate_token(auth_params: AuthParams, access_token: str) -> dict[str, Any]:
    """Validate the received JWT access token."""
    logger.info("Validating access token...")
    validated_token = AH.validate_jwt_token(
        access_token=access_token,
        jwks_client=auth_params.jwks_client,
        audience=auth_params.audience,
        issuers=auth_params.issuer,
        user_agent=auth_params.user_agent,
    )
    logger.info(f"Validated token: {validated_token}")
    return validated_token


async def authenticate_character(
    auth_params: AuthParams,
    sso_url: str,
    state: str,
) -> CharacterToken:
    """Run the full authentication flow for a character.

    This function orchestrates the complete OAuth2 flow including:
    - Generating the SSO URL
    - Running the callback server to get the authorization code
    - Exchanging the code for an access token
    - Validating the received token

    Args:
        auth_params: The authentication parameters.
        sso_url: The SSO URL to direct the user to.
        state: The expected state value for CSRF protection.
        client_session: The aiohttp client session to use for HTTP requests.

    Returns:
        CharacterToken: The authenticated character's token information.
    """
    logger.info(f"Starting authentication flow. Navigate to: {sso_url}")
    logger.info(
        f"Listening on http://{auth_params.callback_url.callback_host}:{auth_params.callback_url.callback_port}{auth_params.callback_url.callback_route} for callback..."
    )
    async with aiohttp.ClientSession() as client_session:
        _authorization_code = await request_authorization_code(auth_params, state)
        logger.info(f"Received authorization code: {_authorization_code}")
        token = await request_token(auth_params, _authorization_code, client_session)
        logger.info(f"Received token: {token}")
        validated_token = validate_token(auth_params, token["access_token"])
        character_token = character_token_from_validated_token(validated_token, token)
        logger.info(f"Created CharacterToken: {character_token}")
    return character_token


def character_token_from_validated_token(
    validated_token: dict[str, Any], token: AH.OauthToken
) -> CharacterToken:
    """Create a CharacterToken from a validated JWT token and raw token data."""
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
    auth_params: AuthParams,
    character_token: CharacterToken,
    client_session: aiohttp.ClientSession,
) -> CharacterToken:
    """Refresh an access token using the provided refresh token."""
    refresh_token = await AH.do_refresh_token(
        refresh_token=character_token.refresh_token,
        client_id=auth_params.client_id,
        token_endpoint=auth_params.token_endpoint,
        user_agent=auth_params.user_agent,
        client_session=client_session,
    )
    validated_token = validate_token(auth_params, refresh_token["access_token"])
    new_character_token = character_token_from_validated_token(
        validated_token, refresh_token
    )

    return new_character_token
