"""ESI OAuth2 authentication flow implementation.

This module handles the complete OAuth2 flow for EVE Online ESI authentication,
including authorization, token exchange, and token refresh operations.
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


# class AuthenticationSession:
#     def __init__(
#         self,
#         client_id: str,
#         scopes: list[str],
#         callback_url: CallbackUrl,
#         authorization_endpoint: str,
#         token_endpoint: str,
#         jwks_client: PyJWKClient,
#         client_session: aiohttp.ClientSession,
#         audience: str,
#         issuer: Sequence[str],
#     ):
#         self._client_id = client_id
#         self._scopes = scopes
#         self._callback_url = callback_url
#         self._authorization_endpoint = authorization_endpoint
#         self._client_session = client_session
#         self._code_verifier, self._code_challenge = AH.generate_code_challenge()
#         self._token_endpoint = token_endpoint
#         self._jwks_client = jwks_client
#         self._audience = audience
#         self._issuer = issuer
#         self._sso_url, self.state = AH.redirect_to_sso(
#             client_id=client_id,
#             redirect_uri=self._callback_url.url(),
#             scopes=scopes,
#             authorization_endpoint=authorization_endpoint,
#             challenge=self._code_challenge,
#         )
#         self._token: AH.OauthToken | None = None
#         self._validated_token: dict[str, Any] | None = None

#     def sso_url(self) -> str:
#         return self._sso_url

#     def character_token(self) -> Any:
#         if self._token is None or self._validated_token is None:
#             raise AuthenticationError("Authentication flow has not been executed.")
#         pass

#     # def execute(self) -> None:
#     #     """Execute the authentication flow synchronously."""
#     #     if self._token is None:
#     #         asyncio.run(self.execute_async())
#     #     else:
#     #         raise AuthenticationError("Authentication flow has already been executed.")

#     async def execute_async(self) -> None:
#         """Execute the authentication flow asynchronously."""
#         if not self._client_session:
#             raise AuthenticationError("Client session not initialized.")
#         if self._token is None:
#             logger.info(f"Starting authentication flow. Navigate to: {self._sso_url}")
#             logger.info(f"Listening on {self._callback_url.url()} for callback...")
#             authorization_code = await AH.run_callback_server(
#                 callback_host=self._callback_url.callback_host,
#                 callback_port=self._callback_url.callback_port,
#                 callback_route=self._callback_url.callback_route,
#                 expected_state=self.state,
#             )
#             logger.info(f"Received authorization code: {authorization_code}")
#             self._token = await AH.request_token(
#                 client_id=self._client_id,
#                 authorization_code=authorization_code,
#                 code_verifier=self._code_verifier,
#                 token_endpoint=self._token_endpoint,
#                 client_session=self._client_session,
#                 user_agent=USER_AGENT,
#             )
#             logger.info(f"Received token: {self._token}")
#             self._validated_token = AH.validate_jwt_token(
#                 access_token=self._token["access_token"],
#                 jwks_client=self._jwks_client,
#                 audience=self._audience,
#                 issuers=self._issuer,
#                 user_agent=USER_AGENT,
#             )
#             logger.info(f"Validated token: {self._validated_token}")
#         else:
#             raise AuthenticationError("Authentication flow has already been executed.")


# class RefreshTokenSession:
#     def __init__(self):
#         pass


# class EsiAuthenticator:
#     """Handles EVE Online ESI OAuth2 authentication flow.

#     This class manages the complete OAuth2 flow including:
#     - Generating authorization URLs
#     - Running callback server
#     - Exchanging authorization codes for tokens
#     - Refreshing access tokens
#     - Validating character information
#     """

#     def __init__(
#         self,
#         client_session: aiohttp.ClientSession,
#         jwks_client: PyJWKClient,
#         oauth_metadata: AH.OauthMetadata,
#         user_agent: str = USER_AGENT,
#     ):
#         """Initialize the ESI authenticator with current settings."""
#         self.settings = get_settings()

#         self.client_session: aiohttp.ClientSession = client_session
#         self.jwks_client: PyJWKClient = jwks_client
#         self.oauth_metadata: AH.OauthMetadata = oauth_metadata
#         self.user_agent = user_agent

#     def authentication_session(self, scopes: list[str]) -> AuthenticationSession:
#         """Create a new authentication session for the OAuth2 flow."""
#         if not self.client_session or not self.jwks_client or not self.oauth_metadata:
#             raise AuthenticationError("Authenticator not properly initialized")
#         return AuthenticationSession(
#             client_id=self.settings.client_id,
#             scopes=scopes,
#             callback_url=CallbackUrl(
#                 callback_host=self.settings.callback_host,
#                 callback_port=self.settings.callback_port,
#                 callback_route=self.settings.callback_route,
#             ),
#             authorization_endpoint=self.oauth_metadata.get("authorization_endpoint"),
#             token_endpoint=self.oauth_metadata.get("token_endpoint"),
#             jwks_client=self.jwks_client,
#             client_session=self.client_session,
#             audience=self.settings.oauth2_audience,
#             issuer=self.settings.oauth2_issuer,
#         )

#     async def refresh_character_token(
#         self, character_token: CharacterToken
#     ) -> CharacterToken:
#         """Refresh an access token using the provided refresh token."""
#         token_endpoint = self.oauth_metadata.get("token_endpoint")
#         refresh_token = await AH.do_refresh_token(
#             refresh_token=character_token.refresh_token,
#             client_id=self.settings.client_id,
#             token_endpoint=token_endpoint,
#             user_agent=self.user_agent,
#             client_session=self.client_session,
#         )
#         validated_token = AH.validate_jwt_token(
#             access_token=refresh_token["access_token"],
#             jwks_client=self.jwks_client,
#             audience=self.settings.oauth2_audience,
#             issuers=self.settings.oauth2_issuer,
#             user_agent=self.user_agent,
#         )


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
    jwks_client: PyJWKClient, oauth_metadata: AH.OauthMetadata
) -> AuthParams:
    """Create authentication parameters from current settings."""
    settings = get_settings()
    code_verifier, code_challenge = AH.generate_code_challenge()
    return AuthParams(
        client_id=settings.client_id,
        token_endpoint=oauth_metadata.get("token_endpoint"),
        authorization_endpoint=oauth_metadata.get("authorization_endpoint"),
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


def get_sso_url(auth_params: AuthParams, scopes: list[str]) -> tuple[str, str]:
    """Generate the SSO URL for user authorization."""
    sso_url, state = AH.redirect_to_sso(
        client_id=auth_params.client_id,
        redirect_uri=auth_params.callback_url.url(),
        scopes=scopes,
        authorization_endpoint=auth_params.authorization_endpoint,
        challenge=auth_params.code_challenge,
    )
    return sso_url, state


async def request_authorization_code(
    auth_params: AuthParams, expected_state: str
) -> str:
    """Run the callback server to receive the authorization code."""
    authorization_code = await AH.run_callback_server(
        callback_host=auth_params.callback_url.callback_host,
        callback_port=auth_params.callback_url.callback_port,
        callback_route=auth_params.callback_url.callback_route,
        expected_state=expected_state,
    )
    return authorization_code


async def request_token(
    auth_params: AuthParams,
    authorization_code: str,
    client_session: aiohttp.ClientSession,
) -> AH.OauthToken:
    """Request an access token using the authorization code."""
    token = await AH.request_token(
        client_id=auth_params.client_id,
        authorization_code=authorization_code,
        code_verifier=auth_params.code_verifier,
        token_endpoint=auth_params.token_endpoint,
        client_session=client_session,
        user_agent=auth_params.user_agent,
    )
    return token


async def validate_token(auth_params: AuthParams, access_token: str) -> dict[str, Any]:
    """Validate the received JWT access token."""
    validated_token = AH.validate_jwt_token(
        access_token=access_token,
        jwks_client=auth_params.jwks_client,
        audience=auth_params.audience,
        issuers=auth_params.issuer,
        user_agent=auth_params.user_agent,
    )
    return validated_token


async def authenticate_character(
    auth_params: AuthParams,
    sso_url: str,
    state: str,
    client_session: aiohttp.ClientSession,
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
    _authorization_code = await request_authorization_code(auth_params, state)
    logger.info(f"Received authorization code: {_authorization_code}")
    token = await request_token(auth_params, _authorization_code, client_session)
    logger.info(f"Received token: {token}")
    validated_token = await validate_token(auth_params, token["access_token"])
    logger.info(f"Validated token: {validated_token}")
    character_token = CharacterToken(
        character_id=validated_token["CharacterID"],
        character_name=validated_token["CharacterName"],
        access_token=token["access_token"],
        refresh_token=token["refresh_token"],
        expires_at=Instant.now().add(seconds=token["expires_in"]),
        scopes=validated_token.get("Scopes", []),
        token_type=token["token_type"],
        updated_at=Instant.now(),
    )
    return character_token


async def refresh_character_token(
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
    validated_token = await validate_token(auth_params, refresh_token["access_token"])
    new_character_token = CharacterToken(
        character_id=validated_token["CharacterID"],
        character_name=validated_token["CharacterName"],
        access_token=refresh_token["access_token"],
        refresh_token=refresh_token["refresh_token"],
        expires_at=Instant.now().add(seconds=refresh_token["expires_in"]),
        scopes=validated_token.get("Scopes", []),
        token_type=refresh_token["token_type"],
        updated_at=Instant.now(),
    )
    return new_character_token
