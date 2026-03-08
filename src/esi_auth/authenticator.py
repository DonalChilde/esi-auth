import asyncio
import base64
import hashlib
import logging
import secrets
import string
from collections.abc import Sequence
from random import choices
from urllib.parse import urlencode, urlparse

import aiohttp
import jwt
from aiohttp import web
from jwt.jwks_client import PyJWKClient

from esi_auth.models import CharacterToken, OauthToken, RequestParams, ValidatedToken
from esi_auth.protocols import AuthenticatorProtocol
from esi_auth.settings import USER_AGENT

logger = logging.getLogger(__name__)


# TODO expand the docs. Emphasize launching the browser with sso url.
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


class Authenticator(AuthenticatorProtocol):
    """This class provides a simplified interface for retrieving authentication information for ESI API calls.

    It provides default urls for the ESI SSO and ESI API endpoints, but these can be overridden if needed.
    """

    def __init__(
        self,
        client_id: str,
        scopes: list[str],
        callback_url: str,
        audience: str = "EVE Online",
        metadata_endpoint: str = "https://login.eveonline.com/.well-known/oauth-authorization-server",
        authorization_endpoint: str = "https://login.eveonline.com/v2/oauth/authorize",
        token_endpoint: str = "https://login.eveonline.com/v2/oauth/token",
        jwks_uri: str = "https://login.eveonline.com/oauth/jwks",
        revocation_endpoint: str = "https://login.eveonline.com/v2/oauth/revoke",
        issuers: Sequence[str] = ("https://login.eveonline.com",),
    ) -> None:
        self.metadata_endpoint = metadata_endpoint
        self.authorization_endpoint = authorization_endpoint
        self.token_endpoint = token_endpoint
        self.jwks_uri = jwks_uri
        self.revocation_endpoint = revocation_endpoint
        self.audience = audience
        self.issuers = list(issuers)
        self.client_id = client_id
        self.scopes = scopes
        self.callback_url = callback_url
        self.jwks_client = None  # This will be initialized on the first token request

    async def request_character_token(self, params: RequestParams) -> CharacterToken:
        """Request a new ESI token.

        Runs the server, gets the token, validates it, and returns the character information.

        This method should be implemented by subclasses to provide the actual logic for requesting a new token.
        """
        authorization_code = await self._run_callback_server(params.state, timeout=300)
        async with aiohttp.ClientSession() as client_session:
            oauth_token = await self._request_token(
                authorization_code, params.code_verifier, client_session
            )
        validated_token = self._validate_jwt_token(oauth_token.access_token)
        return self._create_character_token(validated_token, oauth_token)

    async def refresh_character_token(
        self, token: CharacterToken, client_session: aiohttp.ClientSession
    ) -> CharacterToken:
        """Refresh an existing ESI token.

        Returns a new CharacterToken with updated auth token information.
        """
        if not client_session:
            raise ValueError("client_session must be initialized to refresh token.")
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": USER_AGENT,
        }
        payload: dict[str, str] = {
            "client_id": self.client_id,
            "grant_type": "refresh_token",
            "refresh_token": token.oauth_token.refresh_token,
        }
        response = await client_session.post(
            self.token_endpoint, headers=headers, data=payload
        )
        response.raise_for_status()
        result = await response.json()
        oauth_token = OauthToken(**result)
        validated_token = self._validate_jwt_token(oauth_token.access_token)
        return self._create_character_token(validated_token, oauth_token)

    async def revoke_character_token(
        self, token: CharacterToken, client_session: aiohttp.ClientSession
    ) -> None:
        """Revoke an existing ESI token.

        Raises:

        """
        if not client_session:
            raise ValueError("client_session must be initialized to revoke token.")
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": USER_AGENT,
        }
        payload: dict[str, str] = {
            "token": token.oauth_token.refresh_token,
            "token_type_hint": "refresh_token",
            "client_id": self.client_id,
        }

        response = await client_session.post(
            self.revocation_endpoint, headers=headers, data=payload
        )
        response.raise_for_status()
        if response.status == 200:
            logger.info("Token revoked successfully")

    def prepare_for_request(self, scopes: list[str] | None = None) -> RequestParams:
        """Prepare the authenticator for making requests.

        This method can be used to initialize any necessary state or perform any necessary setup before making requests.
        """
        code_challenge, code_verifier = self._generate_code_challenge_and_verifier()
        url, state = self._generate_url_and_state(code_challenge, scopes)
        return RequestParams(
            url=url,
            state=state,
            code_verifier=code_verifier,
            code_challenge=code_challenge,
        )

    def _create_character_token(
        self, validated_token: ValidatedToken, oauth_token: OauthToken
    ) -> CharacterToken:
        """Create a CharacterToken from a ValidatedToken and OauthToken."""
        return CharacterToken(
            character_id=validated_token.character_id,
            character_name=validated_token.character_name,
            oauth_token=oauth_token,
            created=validated_token.created_at,
            expires=validated_token.expires_at,
        )

    def _validate_jwt_token(self, access_token: str) -> ValidatedToken:
        """Validate a JWT token using the JWKs from the ESI SSO.

        This method should be implemented by subclasses to provide the actual logic for validating a JWT token.
        """
        if not self.jwks_client:
            self.jwks_client = PyJWKClient(
                self.jwks_uri, headers={"User-Agent": USER_AGENT}
            )

        unverified_header = jwt.get_unverified_header(access_token)
        kid = unverified_header["kid"]
        alg = unverified_header["alg"]
        signing_key = self.jwks_client.get_signing_key(kid).key
        try:
            # Decode and validate the token
            valid_decoded_token = jwt.decode(  # type: ignore
                jwt=access_token,
                key=signing_key,
                algorithms=[alg],
                audience=self.audience,
                issuer=self.issuers,
                options={"verify_aud": True, "verify_iss": True},
            )
            character_id = valid_decoded_token["sub"].split(":")[-1]
            character_name = valid_decoded_token["name"]

            return ValidatedToken(
                character_id=character_id,
                character_name=character_name,
                created_at=valid_decoded_token["iat"],
                expires_at=valid_decoded_token["exp"],
            )
        except jwt.ExpiredSignatureError as e:
            logger.error("Token has expired")
            raise e
        except Exception as e:
            logger.error(f"Invalid token or other error: {e}")
            raise e

    async def _request_token(
        self,
        authorization_code: str,
        code_verifier: str,
        client_session: aiohttp.ClientSession,
    ) -> OauthToken:
        """Request an OAuth token from the ESI SSO token endpoint using the authorization code and code verifier."""
        if not client_session:
            raise ValueError("client_session must be initialized to request token.")
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": USER_AGENT,
        }
        payload: dict[str, str] = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "client_id": self.client_id,
            "code_verifier": code_verifier,
        }
        response = await client_session.post(
            self.token_endpoint, headers=headers, data=payload
        )
        response.raise_for_status()
        result = await response.json()

        return OauthToken(**result)

    async def _run_callback_server(
        self, expected_state: str, timeout: int = 300
    ) -> str:
        """Run a temporary server to receive the OAuth callback and return the OAuth token.

        This method should be implemented by subclasses to provide the actual logic for running the callback server.
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
        parsed_url = urlparse(self.callback_url)
        app.router.add_get(parsed_url.path, callback_handler)

        runner = web.AppRunner(app)
        await runner.setup()

        site = web.TCPSite(runner, parsed_url.hostname, parsed_url.port)

        try:
            await site.start()
            logger.info(
                f"Callback server started on {self.callback_url}, waiting for authentication response..."
            )

            # Wait for callback or timeout
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

    def _generate_url_and_state(
        self, challenge: str, scopes: list[str] | None = None
    ) -> tuple[str, str]:
        """Generate the URL and state.

        The URL for the user to visit to authorize the application, along with the state
        value to use for CSRF protection.
        """
        state = "".join(choices(string.ascii_letters + string.digits, k=16))
        if scopes is None:
            scopes = self.scopes
        query_params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.callback_url,
            "scope": " ".join(scopes),
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        query_string = urlencode(query_params)
        return (f"{self.authorization_endpoint}?{query_string}", state)

    def _generate_code_challenge_and_verifier(self) -> tuple[str, str]:
        """Generate a code challenge and code verifier for PKCE."""
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32))
        sha256 = hashlib.sha256()
        sha256.update(code_verifier)
        code_challenge = base64.urlsafe_b64encode(sha256.digest()).decode().rstrip("=")
        return code_challenge, code_verifier.decode()
