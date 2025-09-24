"""An example script demonstrating OAuth2 Authorization Code Flow with PKCE for EVE Online SSO.

To use this script, you must first register an application at
https://developers.eveonline.com/ to obtain a client ID and configure the
redirect URI.

You will need several pieces of information from your EVE SSO application:

- Client ID
- Redirect URI (must match the callback settings in this script)
- scopes (the scopes your application is requesting access to)

You should edit the script main function to set the callback host, port, and route
to match the redirect URI configured in your EVE SSO application. You must also
set the scopes to request access to. These can be a subset of the scopes defined
in your EVE SSO application.

You will be asked your client ID when you run the script, or you can set it
directly in the main function to skip the prompt.


Running the script will open a browser window to authenticate with EVE SSO,
and then start a temporary HTTP server to receive the OAuth callback with the
authorization code. The script will then exchange the authorization code for an
access token and refresh token, validate the JWT access token, and demonstrate
refreshing the tokens.

Many of the following functions are adapted from the example scripts provided in the
EVE ESI SSO documentation, but have been modified to work together in this
single script, using aiohttp for HTTP requests and server, and pyjwt for JWT
validation.



The easiest way to run this script is using uv:

    `uv run <path_to_script>/esi_pkce_auth_example.py`

uv will manage creating a virtual environment and installing the required
dependencies.

Instructions for installing uv can be found at https://docs.astral.sh/uv/

Resources:
- EVE SSO Documentation: https://developers.eveonline.com/docs/services/sso/
- Eve ESI docs on github: https://github.com/esi/esi-docs
- Esi Api explorer: https://developers.eveonline.com/api-explorer#/
- EVE Online Developer Portal: https://developers.eveonline.com/
- EVE oauth2 metadata: https://login.eveonline.com/.well-known/oauth-authorization-server

"""

# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "aiohttp",
#     "pyjwt[crypto]",
#     "rich",
# ]
# ///
import asyncio
import base64
import hashlib
import logging
import random
import secrets
import string
import webbrowser
from collections.abc import Sequence
from typing import Any, TypedDict
from urllib.parse import urlencode

import aiohttp
import jwt
from aiohttp import web
from jwt.jwks_client import PyJWKClient
from rich.console import Console

logger = logging.getLogger(__name__)

USER_AGENT = "Example auth script/1.0"


############################################################################
# These TypedDicts are used for type hinting the JSON responses from the SSO
# and token endpoints.
############################################################################
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


class OauthMetadata(TypedDict):
    """OAuth2 server metadata from well-known endpoint."""

    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    revocation_endpoint: str
    jwks_uri: str
    response_types_supported: list[str]
    subject_types_supported: list[str]
    id_token_signing_alg_values_supported: list[str]
    scopes_supported: list[str]
    token_endpoint_auth_methods_supported: list[str]
    claims_supported: list[str]


class OauthToken(TypedDict):
    """OAuth2 token response structure."""

    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str


#############################################################################
# end TypedDicts
#############################################################################


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


############################################################################
# from https://github.com/esi/esi-docs/blob/main/snippets/sso/authorization-code-pkce.py
############################################################################
def generate_code_challenge() -> tuple[bytes, str]:
    """Generates a code challenge for PKCE.

    Returns:
        A tuple containing the code verifier and code challenge.
    """
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32))
    sha256 = hashlib.sha256()
    sha256.update(code_verifier)
    code_challenge = base64.urlsafe_b64encode(sha256.digest()).decode().rstrip("=")
    return (code_verifier, code_challenge)


async def request_token(
    client_id: str,
    authorization_code: str,
    code_verifier: str,
    token_uri: str,
    client_session: aiohttp.ClientSession,
) -> OauthToken:
    """Takes an authorization code and code verifier and exchanges it for an access token and refresh token.

    Args:
        client_id: The client ID of the application.
        authorization_code: The authorization code received from the SSO.
        code_verifier: The code verifier used to generate the code challenge, as generated by `generate_code_challenge`.
        token_uri: The token endpoint URI for exchanging the authorization code.
        client_session: The aiohttp client session for making requests.

    Returns:
        A dictionary containing the access token and refresh token.

    Raises:
        ValueError: If client_session is not initialized.
        aiohttp.ClientResponseError: If the token request fails.
    """
    if not client_session:
        raise ValueError("client_session must be initialized")
    # if client_session is None:
    #     client_session = aiohttp.ClientSession()
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": USER_AGENT,
    }
    payload: dict[str, str] = {
        "grant_type": "authorization_code",
        "code": authorization_code,
        "client_id": client_id,
        "code_verifier": code_verifier,
    }
    response = await client_session.post(token_uri, headers=headers, data=payload)
    response.raise_for_status()
    result = await response.json()

    return result


async def refresh_token(
    refresh_token: str,
    client_id: str,
    refresh_uri: str,
    client_session: aiohttp.ClientSession,
) -> OauthToken:
    """Takes a refresh token and exchanges it for a new access token and refresh token.

    Args:
        refresh_token: The refresh token received from the SSO.
        client_id: The client ID of the application.
        refresh_uri: The token endpoint URI for refreshing tokens.
        client_session: The aiohttp client session for making requests.

    Returns:
        A dictionary containing the new access token and refresh token.

    Raises:
        ValueError: If client_session is not initialized.
        aiohttp.ClientResponseError: If the token request fails.
    """
    if not client_session:
        raise ValueError("client_session must be initialized")
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": USER_AGENT,
    }
    payload: dict[str, str] = {
        "client_id": client_id,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    response = await client_session.post(refresh_uri, headers=headers, data=payload)
    response.raise_for_status()
    result = await response.json()

    return result


def redirect_to_sso(
    client_id: str, scopes: Sequence[str], redirect_uri: str, challenge: str
) -> tuple[str, str]:
    """Generates a URL to redirect the user to the SSO for authentication.

    Args:
        client_id: The client ID of the application.
        scopes: A list of scopes that the application is requesting access to.
        redirect_uri: The URL where the user will be redirected back to after the authorization flow is complete.
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
    return (f"https://login.eveonline.com/v2/oauth/authorize?{query_string}", state)


#############################################################################
# end
#############################################################################

#############################################################################
# from vhttps://github.com/esi/esi-docs/blob/main/snippets/sso/validate-jwt-token.py
#############################################################################


async def fetch_oauth_metadata(
    client_session: aiohttp.ClientSession, oauth_metadata_url: str
) -> OauthMetadata:
    """Fetches the OAuth metadata from the SSO server.

    Args:
        client_session: The aiohttp client session for making requests.
        oauth_metadata_url: The URL to fetch OAuth metadata from.

    Returns:
        The OAuth metadata.

    Raises:
        aiohttp.ClientResponseError: If the metadata request fails.
    """
    header = {"User-Agent": USER_AGENT}
    logger.info(f"Fetching OAuth metadata from {oauth_metadata_url}")
    response = await client_session.get(oauth_metadata_url, headers=header)
    response.raise_for_status()
    result = await response.json()

    return result


async def fetch_jwks(
    client_session: aiohttp.ClientSession,
    jwks_uri: str,
) -> JWKS:
    """Fetches the JWKS metadata from the SSO server.

    Args:
        client_session: The aiohttp client session for making requests.
        jwks_uri: The JWKS URI to fetch the keys from.

    Returns:
        The JWKS metadata.

    Raises:
        aiohttp.ClientResponseError: If the JWKS request fails.
    """
    header = {"User-Agent": USER_AGENT}
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
    jwks_uri: str = "",
) -> dict[str, Any]:
    """Validates and decodes a JWT Token.

    Args:
        access_token: The JWT token to validate.
        jwks_uri: The JWKS URI to fetch signing keys from.
        jwks_client: An optional PyJWKClient instance to use for fetching keys.
            If None, a new client will be created.
        audience: Expected audience for the token.
        issuers: Valid issuers for the token.

    Returns:
        The content of the validated JWT access token.

    Raises:
        ValueError: If jwks_uri is not provided when jwks_client is None.
        jwt.ExpiredSignatureError: If the token has expired.
        jwt.InvalidTokenError: If the token is invalid.
        Exception: If any other error occurs.
    """
    headers = {"User-Agent": USER_AGENT}
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
        data = jwt.decode(
            jwt=access_token,
            key=signing_key,
            algorithms=[alg],
            audience=audience,
            issuer=issuers,
            options={"verify_aud": True, "verify_iss": True},
        )
    except jwt.ExpiredSignatureError as e:
        logger.error("Token has expired")
        raise e
    except Exception as e:
        logger.error(f"Invalid token or other error: {e}")
        raise e
    # If we get here, the token is valid
    logger.info(f"Token is valid. {data=}")
    # Return the decoded token data

    return data


#############################################################################
# end
#############################################################################


async def revoke_refresh_token(
    access_token: str,
    revocation_uri: str,
    client_id: str,
    client_session: aiohttp.ClientSession,
) -> None:
    """Revoke a token.

    Args:
        access_token: The access token to revoke.
        revocation_uri: The revocation endpoint URI.
        client_id: The client ID of the application.
        client_session: The aiohttp client session for making requests.

    Raises:
        aiohttp.ClientResponseError: If the revocation request fails.
    """
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": USER_AGENT,
    }
    payload: dict[str, str] = {
        "token": access_token,
        "token_type_hint": "refresh_token",
        "client_id": client_id,
    }
    response = await client_session.post(revocation_uri, headers=headers, data=payload)
    response.raise_for_status()
    logger.info("Token revoked successfully")


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


def get_authorization_code(
    expected_state: str,
    callback_host: str = "localhost",
    callback_port: int = 8080,
    callback_route: str = "/callback",
) -> str:
    """Run temporary HTTP server to receive OAuth callback.

    Convenience wrapper to run the async server in a blocking manner, suitable
    for use in synchronous code.

    Args:
        expected_state: The state parameter to validate.
        callback_host: The hostname for the callback server (default: localhost).
        callback_port: The port for the callback server (default: 8080).
        callback_route: The route for the callback (default: /callback).

    Returns:
        The authorization code from the callback.

    Raises:
        AuthenticationError: If callback handling fails.
    """
    return asyncio.run(
        run_callback_server(
            callback_host=callback_host,
            callback_port=callback_port,
            expected_state=expected_state,
            callback_route=callback_route,
        )
    )


async def run_callback_server(
    expected_state: str,
    callback_host: str = "localhost",
    callback_port: int = 8080,
    callback_route: str = "/callback",
) -> str:
    """Run temporary HTTP server to receive OAuth callback.

    Args:
        expected_state: The state parameter to validate.
        callback_host: The hostname for the callback server (default: localhost).
        callback_port: The port for the callback server (default: 8080).
        callback_route: The route for the callback (default: /callback).

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
    app.router.add_get(callback_route, callback_handler)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, callback_host, callback_port)

    try:
        await site.start()
        logger.info(f"Callback server started on {callback_host}:{callback_port}")

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


def signing_algos_supported(jkws: JWKS) -> list[str]:
    """Extracts the signing algorithms supported from the JWKS.

    Args:
        jkws: The JSON Web Key Set containing the signing keys.

    Returns:
        A list of supported signing algorithms.
    """
    supported_algos: list[str] = []
    for key in jkws.get("keys", []):
        alg = key.get("alg")
        if alg and alg not in supported_algos:
            supported_algos.append(alg)
    return supported_algos


async def make_authenticated_api_call(url: str, access_token: str) -> dict[str, Any]:
    """Make an authenticated API call using the provided access token.

    Args:
        url: The API endpoint URL to call.
        access_token: The access token for authentication.

    Returns:
        The JSON response from the API call.

    Raises:
        aiohttp.ClientResponseError: If the API request fails.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": USER_AGENT,
    }
    async with aiohttp.ClientSession() as client_session:
        response = await client_session.get(url, headers=headers)
        response.raise_for_status()
        result = await response.json()
    return result


async def main() -> None:
    """Main function to run the OAuth PKCE flow example.

    Demonstrates the complete OAuth2 Authorization Code Flow with PKCE for EVE Online SSO,
    including authorization, token exchange, JWT validation, and token refresh.
    """
    ############################################################################
    # auth settings
    ############################################################################

    oauth_metadata_url = (
        "https://login.eveonline.com/.well-known/oauth-authorization-server"
    )
    accepted_issuers = ("logineveonline.com", "https://login.eveonline.com")
    expected_audience = "EVE Online"

    ############################################################################
    # Make sure these match your EVE SSO application settings
    ############################################################################

    #  The callback host, port, and route must match the redirect URI configured
    #  in your EVE SSO application.
    callback_host = "localhost"
    callback_port = 8080
    callback_route = "/callback"
    # You will be prompted to enter the client_id when you run the script,
    # or you can set the client_id here and skip the prompt
    client_id = ""

    # Define the scopes to request authorization for in the token. Can be a subset
    # of the scopes defined in your EVE SSO application.
    scopes = ["publicData", "esi-skills.read_skills.v1"]

    ############################################################################
    # Start of script
    ############################################################################

    console = Console()
    console.print()
    console.rule("[bold red]EVE SSO Authentication Example Script")
    console.print()
    console.print(
        "[bold]NOTE:[/bold] You must first register an application at [blue]https://developers.eveonline.com/[/blue]"
    )
    console.print()
    console.print(
        "This script demonstrates the OAuth2 Authorization Code Flow with PKCE for the EVE Online ESI."
    )
    console.print(
        "It will provide examples of obtaining an authorization code, exchanging it for tokens, and validating the JWT access token, and refreshing the tokens."
    )
    console.print()
    console.print(
        "[bold]NOTE: Make sure to configure the callback settings in this script to match your EVE SSO application redirect URI."
    )
    console.print()

    ############################################################################
    # Prompt for client ID if not set
    ############################################################################

    if not client_id:
        client_id = console.input("Enter your EVE SSO Client ID: ").strip()

    ############################################################################
    # Get authorization code
    ############################################################################
    console.print()
    console.rule("[bold red]Step 1: Get Authorization Code")
    console.print()

    code_verifier, code_challenge = generate_code_challenge()
    redirect_uri_str = callback_uri(
        host=callback_host, port=callback_port, route=callback_route
    )
    auth_url, state = redirect_to_sso(
        client_id=client_id,
        scopes=scopes,
        redirect_uri=redirect_uri_str,
        challenge=code_challenge,
    )

    console.print("Opening browser for authentication...")
    webbrowser.open(auth_url)
    console.print(
        "Please visit the following URL to authorize the application if the browser does not open automatically:"
    )
    console.print()
    console.print(f"[blue]{auth_url}[/blue]")
    console.print()

    # Wait for the OAuth callback
    try:
        console.print(f"Starting http server...")
        console.print(
            f"Listening on http://{callback_host}:{callback_port}{callback_route}..."
        )
        console.print("Waiting for OAuth callback...")
        console.print("Press Ctrl-C to cancel.")
        authorization_code = await run_callback_server(
            expected_state=state,
            callback_host=callback_host,
            callback_port=callback_port,
            callback_route=callback_route,
        )
        console.print("Server stopped.")
        console.print(f"Authorization code received: {authorization_code}")
    except AuthenticationError as e:
        console.print(f"Error during authentication: {e}")
        raise SystemExit(1) from e

    ############################################################################
    # Create aiohttp client session and make requests
    ############################################################################

    async with aiohttp.ClientSession() as client_session:
        ############################################################################
        # Get oauth metadata
        ############################################################################
        console.print()
        console.rule("[bold red]Step 2: Get OAuth Metadata")
        console.print()
        console.print("Fetching OAuth metadata...")
        try:
            auth_metadata = await fetch_oauth_metadata(
                client_session=client_session, oauth_metadata_url=oauth_metadata_url
            )
        except aiohttp.ClientResponseError as e:
            console.print(f"Error fetching OAuth metadata: {e}")
            raise SystemExit(1) from e

        console.print("Oauth metadata received:")
        console.print(auth_metadata)

        ############################################################################
        # Exchange authorization code for tokens
        ############################################################################
        console.print()
        console.rule("[bold red]Step 3: Exchange Authorization Code for Tokens")
        console.print()
        console.print("Requesting access token...")
        # token_uri = "https://login.eveonline.com/v2/oauth/token"
        token_uri = auth_metadata.get("token_endpoint")
        try:
            esi_token = await request_token(
                client_id=client_id,
                authorization_code=authorization_code,
                code_verifier=code_verifier.decode(),
                token_uri=token_uri,
                client_session=client_session,
            )
        except aiohttp.ClientResponseError as e:
            console.print(f"Error requesting token: {e}")
            raise SystemExit(1) from e
        console.print("Access token and refresh token received:")
        console.print(esi_token)

        ############################################################################
        # Get the Json Web Key Set (JWKS)
        ############################################################################
        console.print()
        console.rule("[bold red]Step X: Fetch JWKS")
        console.print()
        console.print("Fetching Json Web Key Set (JWKS)...")
        console.print(
            "This is fetched just to show an example of the output, the JWKS URI will "
            "be used later to validate the JWT token."
        )
        # jwks_uri = "https://login.eveonline.com/oauth/jwks"
        jwks_uri = auth_metadata.get("jwks_uri")
        try:
            json_web_key_set = await fetch_jwks(
                client_session=client_session, jwks_uri=jwks_uri
            )
        except aiohttp.ClientResponseError as e:
            console.print(f"Error fetching JWKS: {e}")
            raise SystemExit(1) from e
        console.print("Json Web Key Set (JWKS) received:")
        console.print(json_web_key_set)

        ################################################################################
        # Validate the JWT token
        ################################################################################
        console.print()
        console.rule("[bold red]Step 4: Validate JWT Access Token")
        console.print()
        console.print(f"Validating JWT token, using {jwks_uri} for the JWKS URI...")
        console.print(
            "The validated and decoded token is where you will find the character name and ID."
        )
        try:
            validated_token = validate_jwt_token(
                esi_token["access_token"],
                jwks_uri=jwks_uri,
                jwks_client=None,
                audience=expected_audience,
                issuers=accepted_issuers,
            )
            character_name = validated_token.get("name", "Unknown")
            character_id = validated_token.get("sub", "Unknown").split(":")[-1]
            console.print(
                f"Validated and decoded JWT Token for {character_name} (ID: {character_id}):"
            )
            console.print(validated_token)
        except Exception as e:
            console.print(f"Error validating JWT token: {e}")
            raise SystemExit(1) from e

        ########################################################################
        # Refresh the tokens
        ########################################################################
        console.print()
        console.rule("[bold red]Step 5: Refresh Tokens")
        console.print()
        console.print(
            "Esi tokens are usually good for 20 minutes, but you will need to "
            "refresh them periodically."
        )
        console.print("Refreshing token...")
        # This url is found in the oauth metadata, hardcoded here for simplicity.
        esi_refresh_token = esi_token.get("refresh_token")
        # refresh_uri = "https://login.eveonline.com/v2/oauth/token"
        refresh_uri = auth_metadata.get("token_endpoint")
        try:
            refreshed_token = await refresh_token(
                refresh_token=esi_refresh_token,
                client_id=client_id,
                refresh_uri=refresh_uri,
                client_session=client_session,
            )
        except aiohttp.ClientResponseError as e:
            console.print(f"Error refreshing token: {e}")
            raise SystemExit(1) from e
        console.print(
            "New Access token and refresh token received. Note that it is possible "
            "for the refresh token to be rotated, so be sure to store the new "
            "refresh token."
        )
        console.print("Refreshed token:")
        console.print(refreshed_token)

        ########################################################################
        # Show an example of API access using the access token
        ########################################################################
        console.print()
        console.rule("[bold red]Step 6: Example API Access with Access Token")
        console.print()
        console.print(
            "Now that we have an access token, we can make an example API call to "
            "the EVE Online API."
        )
        root_url = "https://esi.evetech.net/latest"
        api_path = f"/characters/{character_id}/skills"
        request_url = f"{root_url}{api_path}"
        console.print(f"Making API call to {request_url}...")
        try:
            character_data = await make_authenticated_api_call(
                url=request_url, access_token=esi_token["access_token"]
            )
        except aiohttp.ClientResponseError as e:
            console.print(f"Error making API call: {e}")
            raise SystemExit(1) from e

        console.print("API call successful, response data:")
        console.print(character_data)

        ########################################################################
        # Revoke the refresh token
        ########################################################################
        console.print()
        console.rule("[bold red]Step 7: Revoke Refresh Token")
        console.print()
        console.print("You can revoke a refresh token if you feel the need...")
        console.print("Revoking refresh token...")
        # revocation_uri = "https://login.eveonline.com/v2/oauth/revoke"
        revocation_uri = auth_metadata.get("revocation_endpoint")
        try:
            await revoke_refresh_token(
                access_token=refreshed_token["refresh_token"],
                revocation_uri=revocation_uri,
                client_id=client_id,
                client_session=client_session,
            )
        except Exception as e:
            console.print(f"Error revoking token: {e}")
            raise SystemExit(1) from e
        console.print("Access token revoked successfully.")
        console.print("Esi PKCE auth example completed.")

        ############################################################################
        # Show failed attempt to refresh access token with revoked refresh token
        ############################################################################
        console.print()
        console.rule(
            "[bold red]Step 8: Attempt to refresh access token with revoked refresh token"
        )
        console.print()
        console.print(
            "Now that we have revoked the refresh token, let's demonstrate that it "
            "can no longer be used to refresh the access token."
        )
        console.print(f"Attempting to refresh token...")
        try:
            failed_request = await refresh_token(
                refresh_token=refreshed_token["refresh_token"],
                client_id=client_id,
                refresh_uri=refresh_uri,
                client_session=client_session,
            )
            console.print("Refresh token call unexpectedly succeeded, token data:")
            console.print(failed_request)
        except aiohttp.ClientResponseError as e:
            console.print(f"Refresh token call failed as expected: {e}")


if __name__ == "__main__":
    asyncio.run(main())
