"""ESI OAuth2 authentication flow implementation.

This module handles the complete OAuth2 flow for EVE Online ESI authentication,
including authorization, token exchange, and token refresh operations.
"""

import asyncio
import base64
import logging
import secrets
import urllib.parse
from typing import Any

import aiohttp
from aiohttp import web
from whenever import Instant, PlainDateTime

from .models import (
    AuthenticationError,
    CharacterInfo,
    CharacterToken,
    ESIAuthenticationResponse,
    TokenRefreshError,
    VerifiedToken,
)
from .settings import get_settings

logger = logging.getLogger(__name__)

# TODO auth metadata retrieval and update settings.
# TODO make better user agent.


class ESIAuthenticator:
    """Handles EVE Online ESI OAuth2 authentication flow.

    This class manages the complete OAuth2 flow including:
    - Generating authorization URLs
    - Running callback server
    - Exchanging authorization codes for tokens
    - Refreshing access tokens
    - Validating character information
    """

    def __init__(self):
        """Initialize the ESI authenticator with current settings."""
        self.settings = get_settings()
        self.client_session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> "ESIAuthenticator":
        """Async context manager entry."""
        if self.client_session is None:
            self.client_session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.settings.request_timeout)
            )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        if self.client_session:
            await self.client_session.close()

    def generate_auth_url(
        self, scopes: list[str] | None = None, state: str | None = None
    ) -> tuple[str, str]:
        """Generate OAuth2 authorization URL.

        Args:
            scopes: List of ESI scopes to request. If None, uses basic scopes.
            state: Optional state parameter for CSRF protection.
                  If None, generates a random state.

        Returns:
            Tuple of (authorization_url, state_value)
        """
        if scopes is None:
            scopes = ["esi-skills.read_skills.v1"]

        if state is None:
            state = secrets.token_urlsafe(32)

        params = {
            "response_type": "code",
            "redirect_uri": self.settings.callback_url,
            "client_id": self.settings.client_id,
            "scope": " ".join(scopes),
            "state": state,
        }

        auth_url = f"{self.settings.authorize_url}?{urllib.parse.urlencode(params)}"
        logger.debug(f"Generated auth URL for scopes: {scopes}")

        return auth_url, state

    async def exchange_code_for_token(
        self, authorization_code: str
    ) -> ESIAuthenticationResponse:
        """Exchange authorization code for access token.

        Args:
            authorization_code: The authorization code from OAuth callback.

        Returns:
            ESIAuthenticationResponse with token data.

        Raises:
            AuthenticationError: If token exchange fails.
        """
        if not self.client_session:
            raise AuthenticationError("Client session not initialized")

        # Prepare Basic Auth header
        credentials = f"{self.settings.client_id}:{self.settings.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": f"{self.settings.app_name}/1.0",
        }

        data = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": self.settings.callback_url,
        }

        try:
            logger.debug("Exchanging authorization code for token")
            async with self.client_session.post(
                self.settings.token_url, headers=headers, data=data
            ) as response:
                response_data = await response.json()
                logger.info(f"Token exchange response: {response_data!r}")

                if response.status != 200:
                    error_msg = f"Token exchange failed: {response_data.get('error_description', 'Unknown error')}"
                    logger.error(f"{error_msg} (status: {response.status})")
                    raise AuthenticationError(error_msg, response_data.get("error"))

                logger.info("Successfully exchanged code for token")
                return ESIAuthenticationResponse.model_validate(response_data)

        except aiohttp.ClientError as e:
            error_msg = f"Network error during token exchange: {e}"
            logger.error(error_msg)
            raise AuthenticationError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error during token exchange: {e}"
            logger.error(error_msg)
            raise AuthenticationError(error_msg) from e

    async def refresh_token(self, refresh_token: str) -> ESIAuthenticationResponse:
        """Refresh an access token using refresh token.

        Args:
            refresh_token: The refresh token to use.

        Returns:
            ESIAuthenticationResponse with new token data.

        Raises:
            TokenRefreshError: If token refresh fails.
        """
        if not self.client_session:
            raise TokenRefreshError("Client session not initialized", 0)

        # Prepare Basic Auth header
        credentials = f"{self.settings.client_id}:{self.settings.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": f"{self.settings.app_name}/1.0",
        }

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }

        try:
            logger.debug("Refreshing access token")
            async with self.client_session.post(
                self.settings.token_url, headers=headers, data=data
            ) as response:
                response_data = await response.json()

                if response.status != 200:
                    error_msg = f"Token refresh failed: {response_data.get('error_description', 'Unknown error')}"
                    logger.error(f"{error_msg} (status: {response.status})")
                    raise TokenRefreshError(error_msg, 0, response_data.get("error"))
                logger.info(f"Token refresh response: {response_data!r}")
                logger.info("Successfully refreshed token")
                return ESIAuthenticationResponse.model_validate(response_data)

        except aiohttp.ClientError as e:
            error_msg = f"Network error during token refresh: {e}"
            logger.error(error_msg)
            raise TokenRefreshError(error_msg, 0) from e
        except Exception as e:
            error_msg = f"Unexpected error during token refresh: {e}"
            logger.error(error_msg)
            raise TokenRefreshError(error_msg, 0) from e

    async def verify_token(self, access_token: str) -> VerifiedToken:
        """Verify an access token using ESI /verify/ endpoint.

        Args:
            access_token: The access token to verify.

        Returns:
            Dictionary with verification data.
        """
        if not self.client_session:
            raise AuthenticationError("Client session not initialized")
        headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": f"{self.settings.app_name}/1.0",
        }
        try:
            verify_url = f"{self.settings.esi_base_url}/verify/"
            logger.debug("Verifying token")
            async with self.client_session.get(verify_url, headers=headers) as response:
                response_data = await response.json()
                if response.status != 200:
                    error_msg = f"Token verification failed: {response_data.get('error_description', 'Unknown error')}"
                    logger.error(f"{error_msg} (status: {response.status})")
                    raise AuthenticationError(error_msg)
                logger.info(f"Token verification response: {response_data!r}")
                logger.info("Successfully verified token")
                response_data["ExpiresOn"] = PlainDateTime.parse_common_iso(
                    response_data["ExpiresOn"]
                ).assume_utc()
                response_data["Scopes"] = response_data["Scopes"].split(" ")
                verified_token = VerifiedToken.model_validate(response_data)
                logger.info(f"Verified token: {verified_token!r}")
                return verified_token
        except Exception as e:
            error_msg = f"Unexpected error during token verification: {e}"
            logger.error(error_msg)
            raise AuthenticationError(error_msg) from e

    async def get_character_info(self, access_token: str) -> CharacterInfo:
        """Get character information from ESI using access token.

        Args:
            access_token: The access token for the character.

        Returns:
            CharacterInfo with character details.

        Raises:
            AuthenticationError: If character info retrieval fails.
        """
        if not self.client_session:
            raise AuthenticationError("Client session not initialized")

        try:
            # First, verify the token and get character ID
            verified_token = await self.verify_token(access_token)

            # Get detailed character information
            char_url = f"{self.settings.esi_base_url}/latest/characters/{verified_token.character_id}/"
            logger.debug(
                f"Getting character info for {verified_token.character_name} ({verified_token.character_id})"
            )

            async with self.client_session.get(char_url) as response:
                if response.status != 200:
                    error_msg = (
                        f"Character info retrieval failed (status: {response.status})"
                    )
                    logger.error(error_msg)
                    raise AuthenticationError(error_msg)

                char_data = await response.json()
                logger.info(f"Retrieved character info: {char_data!r}")
                char_data["character_id"] = (
                    verified_token.character_id  # Add the character_id to the data
                )

                logger.info(
                    f"Retrieved character info for {verified_token.character_name}"
                )
                return CharacterInfo.model_validate(char_data)

        except aiohttp.ClientError as e:
            error_msg = f"Network error retrieving character info: {e}"
            logger.error(error_msg)
            raise AuthenticationError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error retrieving character info: {e}"
            logger.error(error_msg)
            raise AuthenticationError(error_msg) from e

    async def authenticate_character(
        self, scopes: list[str] | None = None
    ) -> CharacterToken:
        """Complete OAuth2 authentication flow for a character.

        Args:
            scopes: List of ESI scopes to request.

        Returns:
            CharacterToken with authentication data.

        Raises:
            AuthenticationError: If authentication fails.
        """
        # Generate authorization URL
        auth_url, state = self.generate_auth_url(scopes)

        logger.info(f"Starting authentication flow")
        logger.info(f"Please open this URL in your browser: {auth_url}")

        # Start callback server and wait for authorization code
        authorization_code = await self._run_callback_server(state)

        # Exchange code for token
        token_response = await self.exchange_code_for_token(authorization_code)
        logger.info(f"Token exchange response: {token_response!r}")

        # Get character information
        character_info = await self.get_character_info(token_response.access_token)

        # Create CharacterToken
        # TODO change this to use token_response time plus expires_in? check returns for token_response
        expires_at = Instant.now().add(seconds=token_response.expires_in)

        character_token = CharacterToken(
            character_id=character_info.character_id,
            character_name=character_info.name,
            access_token=token_response.access_token,
            refresh_token=token_response.refresh_token,
            expires_at=expires_at,
            scopes=scopes or [],
            token_type=token_response.token_type,
        )

        logger.info(f"Successfully authenticated character: {character_info.name}")
        return character_token

    async def refresh_character_token(
        self, character_token: CharacterToken
    ) -> CharacterToken:
        """Refresh a character's access token.

        Args:
            character_token: The character token to refresh.

        Returns:
            Updated CharacterToken with new access token.

        Raises:
            TokenRefreshError: If refresh fails.
        """
        logger.debug(f"Refreshing token for character {character_token.character_name}")

        try:
            token_response = await self.refresh_token(character_token.refresh_token)

            # Update the character token with new data
            # TODO change this to use refresh time plus expires_in? check returns for refresh_token
            expires_at = Instant.now().add(seconds=token_response.expires_in)

            character_token.access_token = token_response.access_token
            character_token.expires_at = expires_at
            character_token.updated_at = Instant.now()

            # Update refresh token if provided (some implementations may rotate it)
            if (
                hasattr(token_response, "refresh_token")
                and token_response.refresh_token
            ):
                character_token.refresh_token = token_response.refresh_token

            logger.info(
                f"Successfully refreshed token for {character_token.character_name}"
            )
            return character_token

        except Exception as e:
            error_msg = f"Failed to refresh token for character {character_token.character_id}: {e}"
            logger.error(error_msg)
            raise TokenRefreshError(error_msg, character_token.character_id) from e

    async def _run_callback_server(self, expected_state: str) -> str:
        """Run temporary HTTP server to receive OAuth callback.

        Args:
            expected_state: The state parameter to validate.

        Returns:
            The authorization code from the callback.

        Raises:
            AuthenticationError: If callback handling fails.
        """
        authorization_code = None
        error_message = None

        async def callback_handler(request: web.Request) -> web.Response:
            nonlocal authorization_code, error_message

            # Check for error in callback
            if "error" in request.query:
                error_message = request.query.get(
                    "error_description", request.query["error"]
                )
                return web.Response(
                    text="<h1>Authentication Failed</h1>"
                    f"<p>Error: {error_message}</p>"
                    "<p>You can close this window.</p>",
                    content_type="text/html",
                )

            # Validate state parameter
            received_state = request.query.get("state")
            if received_state != expected_state:
                error_message = "Invalid state parameter (possible CSRF attack)"
                return web.Response(
                    text="<h1>Authentication Failed</h1>"
                    "<p>Security validation failed. Please try again.</p>"
                    "<p>You can close this window.</p>",
                    content_type="text/html",
                )

            # Get authorization code
            logger.info(f"Received OAuth callback: {request.query!r}")
            authorization_code = request.query.get("code")
            if not authorization_code:
                error_message = "No authorization code received"
                return web.Response(
                    text="<h1>Authentication Failed</h1>"
                    "<p>No authorization code received.</p>"
                    "<p>You can close this window.</p>",
                    content_type="text/html",
                )

            return web.Response(
                text="<h1>Authentication Successful</h1>"
                "<p>You can now close this window and return to the application.</p>",
                content_type="text/html",
            )

        # Create and start the server
        app = web.Application()
        app.router.add_get("/callback", callback_handler)

        runner = web.AppRunner(app)
        await runner.setup()

        site = web.TCPSite(
            runner, self.settings.callback_host, self.settings.callback_port
        )

        try:
            await site.start()
            logger.info(
                f"Callback server started on {self.settings.callback_host}:{self.settings.callback_port}"
            )

            # Wait for callback or timeout
            timeout = 300  # 5 minutes
            for _ in range(timeout):
                if authorization_code or error_message:
                    break
                await asyncio.sleep(1)

            if error_message:
                raise AuthenticationError(f"OAuth callback error: {error_message}")

            if not authorization_code:
                raise AuthenticationError("Timeout waiting for OAuth callback")

            return authorization_code

        finally:
            await runner.cleanup()
            logger.debug("Callback server stopped")


async def authenticate_character(scopes: list[str] | None = None) -> CharacterToken:
    """Authenticate a character using OAuth2 flow.

    This is a convenience function that creates an ESIAuthenticator
    and runs the complete authentication flow.

    Args:
        scopes: List of ESI scopes to request.

    Returns:
        CharacterToken with authentication data.
    """
    async with ESIAuthenticator() as authenticator:
        return await authenticator.authenticate_character(scopes)


async def refresh_character_token(character_token: CharacterToken) -> CharacterToken:
    """Refresh a character's access token.

    This is a convenience function that creates an ESIAuthenticator
    and refreshes the given character token.

    Args:
        character_token: The character token to refresh.

    Returns:
        Updated CharacterToken with new access token.
    """
    async with ESIAuthenticator() as authenticator:
        return await authenticator.refresh_character_token(character_token)
