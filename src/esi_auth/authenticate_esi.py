"""Helper functions for OAuth2 authentication with EVE Online SSO.

These functions are broken down into discrete steps that can be used
individually or together to implement the OAuth2 authorization code flow with PKCE.
"""

import asyncio
import base64
import hashlib
import logging
import random
import secrets
import string
from collections.abc import Sequence
from typing import Any, TypedDict
from urllib.parse import urlencode, urlparse

import aiohttp
import jwt
from aiohttp import web
from jwt.jwks_client import PyJWKClient
from rich.console import Console
from rich.json import JSON
from rich.prompt import Prompt
from whenever import Instant

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------------
# Models
# ------------------------------------------------------------------------------------


class OauthSettings(TypedDict):
    """Settings for OAuth2 authentication flow."""

    audience: str
    metadata_endpoint: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str
    revocation_endpoint: str
    issuers: list[str]


# These settings are current as of 2026-03-04, and are not likely to change much.
# They are included here for convenience, but can also be fetched dynamically from the metadata endpoint if needed.
# The current settings can be found at https://login.eveonline.com/.well-known/oauth-authorization-server
OAUTH_SETTINGS = OauthSettings(
    audience="EVE Online",
    metadata_endpoint="https://login.eveonline.com/.well-known/oauth-authorization-server",
    authorization_endpoint="https://login.eveonline.com/v2/oauth/authorize",
    token_endpoint="https://login.eveonline.com/v2/oauth/token",
    jwks_uri="https://login.eveonline.com/oauth/jwks",
    revocation_endpoint="https://login.eveonline.com/v2/oauth/revoke",
    issuers=["https://login.eveonline.com"],
)


class JWK(TypedDict):
    """JSON Web Key structure for JWT signature verification."""

    kty: str
    use: str
    kid: str
    alg: str
    n: str
    e: str


class JWKS(TypedDict):
    """JSON Web Key Set containing multiple JWKs."""

    keys: list[JWK]


# type ValidatedToken = dict[str, Any]


class ValidatedToken(TypedDict):
    """Represents a validated/decoded character token.

    This information is extracted from the JWT access token after it has been validated.

    The sub field contains the character ID in `CHARACTER:EVE:<character_id>` format,
    the azp field contains the client ID, and the name field contains the character name.
    """

    scp: str
    jti: str
    kid: str
    sub: str
    azp: str
    tenant: str
    tier: str
    region: str
    aud: list[str]
    name: str
    owner: str
    exp: int
    iat: int
    iss: str


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


class OauthTokenDict(TypedDict):
    """OAuth2 token response structure."""

    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str


class PKCECodeChallenge(TypedDict):
    """PKCE code challenge and verifier pair."""

    code_verifier: str
    code_challenge: str


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


# ------------------------------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------------------------------


def generate_code_challenge() -> PKCECodeChallenge:
    """Generates a code challenge for PKCE using SHA-256.

    Returns:
        A CodeChallenge containing the code verifier and code challenge.
    """
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32))
    sha256 = hashlib.sha256()
    sha256.update(code_verifier)
    code_challenge = base64.urlsafe_b64encode(sha256.digest()).decode().rstrip("=")
    return PKCECodeChallenge(
        code_verifier=code_verifier.decode(), code_challenge=code_challenge
    )


def callback_uri(
    host: str = "localhost", port: int = 8080, route: str = "/callback"
) -> str:
    """Generate the OAuth callback URI.

    Args:
        host: The hostname for the callback (default: localhost).
        port: The port for the callback (default: 8080).
        route: The route for the callback (default: /callback).

    Returns:
        The full callback URI.
    """
    return f"http://{host}:{port}{route}"


# ------------------------------------------------------------------------------------
# Meat and Potatoes
# ------------------------------------------------------------------------------------


async def request_token(
    client_id: str,
    authorization_code: str,
    code_verifier: str,
    token_endpoint: str,
    user_agent: str,
    client_session: aiohttp.ClientSession,
) -> OauthTokenDict:
    """Takes an authorization code and code verifier and exchanges it for an access token and refresh token.

    Args:
        client_id: The client ID of the application.
        authorization_code: The authorization code received from the SSO.
        code_verifier: The code verifier used to generate the code challenge, as generated by `generate_code_challenge`.
        token_endpoint: The token endpoint URI for exchanging the authorization code.
        user_agent: The User-Agent string to use in the request.
        client_session: The aiohttp client session for making requests.

    Returns:
        A dictionary containing the access token and refresh token.

    Raises:
        ValueError: If client_session is not initialized.
        aiohttp.ClientResponseError: If the token request fails.
    """
    if not client_session:
        raise ValueError("client_session must be initialized to request token.")
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": user_agent,
    }
    payload: dict[str, str] = {
        "grant_type": "authorization_code",
        "code": authorization_code,
        "client_id": client_id,
        "code_verifier": code_verifier,
    }
    response = await client_session.post(token_endpoint, headers=headers, data=payload)
    response.raise_for_status()
    result = await response.json()

    return result


async def request_refreshed_token(
    refresh_token: str,
    client_id: str,
    token_endpoint: str,
    user_agent: str,
    client_session: aiohttp.ClientSession,
) -> OauthTokenDict:
    """Takes a refresh token and exchanges it for a new access token and refresh token.

    Args:
        refresh_token: The refresh token received from the SSO.
        client_id: The client ID of the application.
        token_endpoint: The token endpoint URI for refreshing tokens.
        user_agent: The User-Agent string to use in the request.
        client_session: The aiohttp client session for making requests.

    Returns:
        A dictionary containing the new access token and refresh token.

    Raises:
        ValueError: If client_session is not initialized.
        aiohttp.ClientResponseError: If the token request fails.
    """
    if not client_session:
        raise ValueError("client_session must be initialized to refresh token.")
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": user_agent,
    }
    payload: dict[str, str] = {
        "client_id": client_id,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    response = await client_session.post(token_endpoint, headers=headers, data=payload)
    response.raise_for_status()
    result = await response.json()
    return result


def redirect_to_sso(
    client_id: str,
    scopes: Sequence[str],
    redirect_uri: str,
    authorization_endpoint: str,
    challenge: str,
) -> tuple[str, str]:
    """Generates a URL to redirect the user to the SSO for authentication.

    Args:
        client_id: The client ID of the application.
        scopes: A list of scopes that the application is requesting access to.
        redirect_uri: The URL where the user will be redirected back to after the authorization flow is complete.
        authorization_endpoint: The authorization endpoint URI.
        challenge: A challenge as generated by `generate_code_challenge`.

    Returns:
        A tuple containing the URL and the state parameter that was used.
    """
    state = "".join(random.choices(string.ascii_letters + string.digits, k=16))
    query_params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes),
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    query_string = urlencode(query_params)
    return (f"{authorization_endpoint}?{query_string}", state)


async def fetch_oauth_metadata(
    client_session: aiohttp.ClientSession, oauth_metadata_url: str, user_agent: str
) -> OauthMetadata:
    """Fetches the OAuth metadata from the SSO server.

    Args:
        client_session: The aiohttp client session for making requests.
        oauth_metadata_url: The URL to fetch OAuth metadata from.
        user_agent: The User-Agent string to use in the request.

    Returns:
        The OAuth metadata.

    Raises:
        aiohttp.ClientResponseError: If the metadata request fails.
    """
    header = {"User-Agent": user_agent}
    logger.info(f"Fetching OAuth metadata from {oauth_metadata_url}")
    response = await client_session.get(oauth_metadata_url, headers=header)
    response.raise_for_status()
    result = await response.json()
    return result


async def fetch_jwks(
    client_session: aiohttp.ClientSession,
    user_agent: str,
    jwks_uri: str,
) -> JWKS:
    """Fetches the JWKS metadata from the SSO server.

    Args:
        client_session: The aiohttp client session for making requests.
        user_agent: The User-Agent string to use in the request.
        jwks_uri: The JWKS URI to fetch the keys from.

    Returns:
        The JWKS metadata.

    Raises:
        aiohttp.ClientResponseError: If the JWKS request fails.
    """
    header = {"User-Agent": user_agent}
    logger.info(f"Fetching JWKS from {jwks_uri}")
    response = await client_session.get(jwks_uri, headers=header)
    response.raise_for_status()
    result = await response.json()

    return result


def validate_jwt_token(
    access_token: str,
    jwks_client: PyJWKClient | None,
    audience: str,
    issuers: Sequence[str],
    user_agent: str,
    jwks_uri: str = "",
) -> ValidatedToken:
    """Validates and decodes a JWT Token.

    Args:
        access_token: The JWT token to validate.
        jwks_uri: The JWKS URI to fetch signing keys from.
        jwks_client: An optional PyJWKClient instance to use for fetching keys.
            If None, a new client will be created.
        audience: Expected audience for the token.
        issuers: Valid issuers for the token.
        user_agent: The User-Agent string to use in requests.

    Returns:
        The content of the validated JWT access token.

    Raises:
        ValueError: If jwks_uri is not provided when jwks_client is None.
        jwt.ExpiredSignatureError: If the token has expired.
        jwt.InvalidTokenError: If the token is invalid.
        Exception: If any other error occurs.
    """
    headers = {"User-Agent": user_agent}
    # NOTE the jwks_client can cache the keys, so we dont have to fetch them every time.
    # Pass in a jwks_client if you have one.
    if jwks_client is None:
        if not jwks_uri:
            raise ValueError("jwks_uri must be provided if jwks_client is None")
        jwks_client = PyJWKClient(jwks_uri, headers=headers)
    unverified_header = jwt.get_unverified_header(access_token)
    kid = unverified_header["kid"]
    alg = unverified_header["alg"]
    signing_key = jwks_client.get_signing_key(kid).key
    try:
        # Decode and validate the token
        valid_decoded_token = jwt.decode(  # type: ignore
            jwt=access_token,
            key=signing_key,
            algorithms=[alg],
            audience=audience,
            issuer=issuers,
            options={"verify_aud": True, "verify_iss": True},
        )

        return ValidatedToken(**valid_decoded_token)
    except jwt.ExpiredSignatureError as e:
        logger.error("Token has expired")
        raise e
    except Exception as e:
        logger.error(f"Invalid token or other error: {e}")
        raise e


async def revoke_refresh_token(
    refresh_token: str,
    revocation_endpoint: str,
    client_id: str,
    user_agent: str,
    client_session: aiohttp.ClientSession,
) -> Any:
    """Revoke a refresh token.

    Im not sure how to tell for sure if the refresh token got revoked, except to test a
    refresh after revocation and see if it fails. The SSO returns a 200 OK response even
    if the token is invalid or already revoked, so we have to rely on testing the token
    after revocation to confirm it worked.

    Args:
        refresh_token: The refresh token to revoke.
        revocation_endpoint: The revocation endpoint URI.
        client_id: The client ID of the application.
        user_agent: The User-Agent string to use in the request.
        client_session: The aiohttp client session for making requests.

    Raises:
        aiohttp.ClientResponseError: If the revocation request fails.
    """
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": user_agent,
    }
    payload: dict[str, str] = {
        "token": refresh_token,
        "token_type_hint": "refresh_token",
        "client_id": client_id,
    }

    response = await client_session.post(
        revocation_endpoint, headers=headers, data=payload
    )
    response.raise_for_status()
    if response.status == 200:
        logger.info("Token revoked successfully")


async def run_callback_server(
    expected_state: str,
    callback_url: str,
    timeout: int = 300,
) -> str:
    """Run temporary HTTP server to receive OAuth callback.

    Args:
        expected_state: The state parameter to validate.
        callback_url: The full URL for the callback server.
        timeout: Time in seconds to wait for the callback before timing out (default: 300).

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
    parsed_url = urlparse(callback_url)
    app.router.add_get(parsed_url.path, callback_handler)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, parsed_url.hostname, parsed_url.port)

    try:
        await site.start()
        logger.info(
            f"Callback server started on {callback_url}, waiting for authentication response..."
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


async def get_token_flow(
    client_id: str,
    sso_url: str,
    state: str,
    code_verifier: str,
    token_endpoint: str,
    client_session: aiohttp.ClientSession,
    user_agent: str,
    callback_url: str,
) -> OauthTokenDict:
    """Run the full OAuth2 authorization code flow to get an access token.

    Shown as an example of how to use the helper functions together.
    """
    logger.info(f"Starting authentication flow. Navigate to:")
    logger.info(sso_url)
    logger.info(f"Listening on {callback_url} for callback...")
    authorization_code = await run_callback_server(
        expected_state=state,
        callback_url=callback_url,
    )
    logger.info(f"Received authorization code: {authorization_code}")
    token = await request_token(
        client_id=client_id,
        authorization_code=authorization_code,
        code_verifier=code_verifier,
        token_endpoint=token_endpoint,
        user_agent=user_agent,
        client_session=client_session,
    )
    logger.info(f"Received token: {token}")

    return token


# ---------------------------------------------------------------------------------------
# NOTE the following code is a working example of how to use the above functions together
# to run through the full authentication flow, including refreshing and revoking tokens.
# You can run this function to test the flow, or use it as a reference for how to
# implement the flow in your own application.
# ---------------------------------------------------------------------------------------


async def main():
    """Example usage of the authentication functions."""
    console = Console()
    console.print("[bold green]Welcome to the ESI Authentication Example![/bold green]")
    # Always provide a user agent when making requests to the SSO, as it is required
    # and helps with debugging and support. Ideally, the user agent should include your
    # application name and version, and website or contact information.
    user_agent = "authenticate-esi.py/1.0 (eve:Donal Childe; Github:DonalChilde)"

    console.print(
        "To authenticate with EVE Online SSO, you will need to provide the following information:"
    )
    console.print(
        "- Client ID: The client ID of your application registered with the EVE Online SSO."
    )
    console.print(
        "- Callback URI: The URL where the SSO will redirect you after authentication. "
        "e.g http://localhost:8080/callback. "
        "This should match the callback URI registered with your application."
    )
    console.print(
        "- Scopes: The permissions you want to request access to. These should be all or "
        "some of the scopes you registered for your application."
    )
    console.print("")
    console.print(
        "You can register your application and get a client ID and set up a callback URI "
        "at https://developers.eveonline.com/applications"
    )
    console.print("")

    # ------------------------------------------------------------------------------------

    client_id = Prompt.ask("Enter your client ID")
    console.print("")
    default_callback_uri = "http://localhost:8080/callback"
    entered_callback_uri = Prompt.ask(
        "Enter your callback URI", default=default_callback_uri
    )
    console.print("")
    console.print(
        "The scopes you want to request access to. These should be registered "
        "with the SSO and should be a all of or a subset of the scopes you registered for your application."
    )
    console.print("")
    scopes_set: set[str] = set()
    scopes: list[str] = []
    while True:
        scope = Prompt.ask(
            "Enter a scope to request (or at least one space to finish)",
            default="esi-skills.read_skills.v1",
        )
        if not scope:
            break
        scopes_set.add(scope)
    scopes = list(scopes_set)
    console.print("")

    console.print(f"Client ID: {client_id}")
    console.print(f"Callback URI: {entered_callback_uri}")
    console.print(f"Requested scopes:")
    console.print(JSON.from_data(scopes))
    console.print("")

    # ------------------------------------------------------------------------------------

    console.print("Generating code challenge for PKCE...")
    code_challenge = generate_code_challenge()
    console.print(JSON.from_data(code_challenge))
    console.print("")

    console.print(
        "Generate the SSO URL. This is the URL you will navigate to in order to authenticate."
    )
    sso_url, state = redirect_to_sso(
        client_id=client_id,
        scopes=scopes,
        redirect_uri=entered_callback_uri,
        authorization_endpoint=OAUTH_SETTINGS["authorization_endpoint"],
        challenge=code_challenge["code_challenge"],
    )
    console.print(f"Navigate to the following URL to authenticate:")
    console.print(f"[link={sso_url}]Click ME[/link]")
    console.print(
        f"Or copy and paste the URL into your browser if your terminal does not support clickable links."
    )
    console.print(f"{sso_url}")
    console.print("")

    console.print(f"Listening on {entered_callback_uri} for callback...")
    console.print(
        "The local server can take a second to start. If the link gives an error, try reloading the page after a moment."
    )
    # Launch a web server to listen for the callback and get the authorization code.
    authorization_code = await run_callback_server(
        expected_state=state, callback_url=entered_callback_uri
    )
    console.print(f"Received authorization code: {authorization_code}")
    console.print("")

    # -------------------------------------------------------------------------------------

    # We will need a client session for the following requests.
    async with aiohttp.ClientSession() as client_session:
        token = await request_token(
            client_id=client_id,
            authorization_code=authorization_code,
            code_verifier=code_challenge["code_verifier"],
            token_endpoint=OAUTH_SETTINGS["token_endpoint"],
            user_agent=user_agent,
            client_session=client_session,
        )
        console.print(f"Received authentication token:")
        console.print(JSON.from_data(token))
        console.print("")

        console.print(
            "You can now use the access token to make authenticated requests to ESI, "
            "and use the refresh token to get new access tokens when needed. You can also "
            "get the character name and ID from the access token by validating and decoding "
            "it. You will need the character id and the access token to make requests to "
            "ESI on behalf of the character."
        )
        console.print("")

        validated_token = validate_jwt_token(
            access_token=token["access_token"],
            jwks_client=None,
            audience=OAUTH_SETTINGS["audience"],
            issuers=OAUTH_SETTINGS["issuers"],
            user_agent=user_agent,
            jwks_uri=OAUTH_SETTINGS["jwks_uri"],
        )
        console.print("Validated token content:")
        console.print(JSON.from_data(validated_token))
        console.print("")

        # -------------------------------------------------------------------------------------

        console.print(
            "From this, we can extract the character ID and name, and expiration time."
        )
        character_id = validated_token["sub"].split(":")[-1]
        character_name = validated_token["name"]
        expiration_time = Instant.from_timestamp(validated_token["exp"])
        console.print(f"Character ID: {character_id}")
        console.print(f"Character Name: {character_name}")
        console.print(f"Token Expiration Time: {expiration_time}")
        console.print(
            f"Token expires in {(expiration_time - Instant.now()).in_seconds():2f} seconds"
        )
        console.print("")

        # --------------------------------------------------------------------------------------

        console.print(
            "You can also use the access token to make authenticated requests to ESI. "
            "Here is an example of making a request to the character attributes endpoint."
        )
        console.print(
            "This assumes that the access token has the necessary scopes to "
            "access this endpoint, the esi-skills.read_skills.v1 scope in this case."
        )
        url = f"https://esi.evetech.net/characters/{character_id}/attributes"
        headers = {
            "User-Agent": user_agent,
            "Authorization": f"Bearer {token['access_token']}",
        }
        response = await client_session.get(url, headers=headers)
        if response.status == 200:
            character_attributes = await response.json()
            console.print(
                f"Successfully made authenticated request to ESI using access token:"
            )
            console.print(JSON.from_data(character_attributes))
        else:
            console.print(
                f"Failed to make authenticated request to ESI: {response.status} {response.reason}"
            )
        console.print("")

        # --------------------------------------------------------------------------------------

        console.print(
            "You can also refresh the token when it is close to expiring, using the refresh token."
        )
        new_token = await request_refreshed_token(
            refresh_token=token["refresh_token"],
            client_id=client_id,
            token_endpoint=OAUTH_SETTINGS["token_endpoint"],
            user_agent=user_agent,
            client_session=client_session,
        )
        console.print(f"Refreshed token:")
        console.print(JSON.from_data(new_token))
        console.print("")

        validated_new_token = validate_jwt_token(
            access_token=new_token["access_token"],
            jwks_client=None,
            audience=OAUTH_SETTINGS["audience"],
            issuers=OAUTH_SETTINGS["issuers"],
            user_agent=user_agent,
            jwks_uri=OAUTH_SETTINGS["jwks_uri"],
        )
        console.print(f"Validated refreshed token content:")
        console.print(JSON.from_data(validated_new_token))
        console.print("")

        character_id = validated_new_token["sub"].split(":")[-1]
        character_name = validated_new_token["name"]
        expiration_time = Instant.from_timestamp(validated_new_token["exp"])
        console.print(f"Character ID: {character_id}")
        console.print(f"Character Name: {character_name}")
        console.print(f"Token Expiration Time: {expiration_time}")
        console.print(
            f"Token expires in {(expiration_time - Instant.now()).in_seconds():2f} seconds"
        )
        console.print("")

        # --------------------------------------------------------------------------------------

        console.print(
            "You can also revoke the refresh token when you no longer need it,  e.g. "
            "if the character is unsubscribing from your application, "
            "or if you want to force the user to re-authenticate.\n"
        )
        console.print("Revoking the refresh token...\n")
        await revoke_refresh_token(
            refresh_token=new_token["refresh_token"],
            revocation_endpoint=OAUTH_SETTINGS["revocation_endpoint"],
            client_id=client_id,
            user_agent=user_agent,
            client_session=client_session,
        )
        await asyncio.sleep(
            1
        )  # Wait a moment to ensure revocation is processed before testing the token
        try:
            await request_refreshed_token(
                refresh_token=new_token["refresh_token"],
                client_id=client_id,
                token_endpoint=OAUTH_SETTINGS["token_endpoint"],
                user_agent=user_agent,
                client_session=client_session,
            )
        except aiohttp.ClientResponseError as e:
            if e.status == 400:
                console.print(
                    "Refresh token revoked successfully. Attempting to use it resulted in expected error."
                )
            else:
                console.print(
                    f"Unexpected error when testing revoked token: {e.status} {e.message}"
                )


if __name__ == "__main__":
    asyncio.run(main())
