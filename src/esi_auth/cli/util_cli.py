"""Utility CLI commands for esi_auth."""

import json
from pathlib import Path
from typing import Annotated, TypedDict

import typer
from rich.console import Console

from esi_auth.auth_helpers import OauthMetadata, fetch_oauth_metadata_sync
from esi_auth.helpers import get_user_agent
from esi_auth.models import CallbackUrl
from esi_auth.settings import APPLICATION_NAME, DEFAULT_APP_DIR, get_settings

app = typer.Typer(no_args_is_help=True)


class EveDevAppConfig(TypedDict):
    name: str
    description: str
    clientId: str
    clientSecret: str
    callbackUrl: str
    scopes: list[str]


OAUTH_METADATA_URL = (
    "https://login.eveonline.com/.well-known/oauth-authorization-server"
)


# FROM https://login.eveonline.com/.well-known/oauth-authorization-server
# Current as of 2025-9-29
DEFAULT_METADATA: OauthMetadata = {
    "issuer": "https://login.eveonline.com",
    "authorization_endpoint": "https://login.eveonline.com/v2/oauth/authorize",
    "token_endpoint": "https://login.eveonline.com/v2/oauth/token",
    "response_types_supported": ["code", "token"],
    "jwks_uri": "https://login.eveonline.com/oauth/jwks",
    "revocation_endpoint": "https://login.eveonline.com/v2/oauth/revoke",
    "subject_types_supported": ["public"],
    "revocation_endpoint_auth_methods_supported": [
        "client_secret_basic",
        "client_secret_post",
        "client_secret_jwt",
    ],
    "token_endpoint_auth_methods_supported": [
        "client_secret_basic",
        "client_secret_post",
        "client_secret_jwt",
    ],
    "id_token_signing_alg_values_supported": ["HS256"],
    "token_endpoint_auth_signing_alg_values_supported": ["HS256"],
    "code_challenge_methods_supported": ["S256"],
}

DEFAULT_APP_CONFIG: EveDevAppConfig = {
    "name": "your_app_name_here",
    "description": "your_app_description_here",
    "clientId": "your_client_id_here",
    "clientSecret": "your_client_secret_here",
    "callbackUrl": "http://localhost:8080/callback",
    "scopes": ["publicData", "esi-characters.read_character_info.v1"],
}


def parse_eve_dev_app_config(eve_app_config: EveDevAppConfig) -> dict[str, str]:
    """Parse the Eve Online Developers app configuration into env file format."""
    result: dict[str, str] = {}
    callback_url = CallbackUrl.parse(eve_app_config["callbackUrl"])
    result["NAME"] = eve_app_config["name"]
    result["DESCRIPTION"] = eve_app_config["description"]
    result["CLIENT_ID"] = eve_app_config["clientId"]
    result["CLIENT_SECRET"] = eve_app_config["clientSecret"]
    result["CALLBACK_HOST"] = callback_url.callback_host
    result["CALLBACK_PORT"] = str(callback_url.callback_port)
    result["CALLBACK_ROUTE"] = callback_url.callback_route
    result["SCOPES"] = json.dumps(eve_app_config["scopes"])
    return result


@app.command()
def generate_example_env(
    ctx: typer.Context,
    file_out: Annotated[
        Path, typer.Option("-o", "--output", help="Output file path")
    ] = Path(".example.env"),
    overwrite: Annotated[
        bool, typer.Option("--overwrite", help="Overwrite existing file")
    ] = False,
    character_name: Annotated[
        str, typer.Option("--character-name", help="Character name for User-Agent")
    ] = "Unknown",
    user_email: Annotated[
        str, typer.Option("--user-email", help="User email for User-Agent")
    ] = "Unknown",
    user_app_version: Annotated[
        str, typer.Option("--user-app-version", help="App version for User-Agent")
    ] = "Unknown",
    oauth_url: Annotated[
        str | None,
        typer.Option(
            "--oauth-url",
            help=f"OAuth2 metadata URL. If not set, uses {OAUTH_METADATA_URL}",
        ),
    ] = None,
    eve_dev_app_json: Annotated[
        Path | None,
        typer.Option(
            "--eve-dev-app-json",
            help="Path to Eve Online Developers app JSON file to parse",
            exists=True,
            dir_okay=False,
        ),
    ] = None,
    env_prefix: Annotated[
        str,
        typer.Option(
            "--env-prefix",
            help="Environment variable prefix to use in the .env file",
        ),
    ] = "ESI_AUTH_",
):
    """Generate an example .env file with placeholder values."""
    console = Console()
    console.rule("[bold green]Generate Example .env File")
    # Check if file exists and handle overwrite
    if file_out.exists() and not overwrite:
        console.print(
            f"File {file_out} already exists. Use --overwrite to replace it.",
            style="yellow",
        )
        raise typer.Exit(code=1)
    # TODO refine with current values from command?
    user_agent = get_user_agent()
    if oauth_url is None:
        oauth_url = OAUTH_METADATA_URL
    metadata = fetch_metadata(url=oauth_url, user_agent=user_agent)

    if eve_dev_app_json is not None:
        file_txt = eve_dev_app_json.read_text()
        app_config: EveDevAppConfig = json.loads(file_txt)
        parsed_app_config = parse_eve_dev_app_config(app_config)
    else:
        app_config = DEFAULT_APP_CONFIG
        parsed_app_config = parse_eve_dev_app_config(app_config)

    # Generate example content with comments and all available settings
    env_content = [
        "# ESI Auth Configuration File",
        "# This file contains all available settings for the ESI Auth application.",
        "# Copy this file to the APP_DIR and rename it to .env . Update the values as needed.",
        "",
        "# Application Configuration",
        "# ========================",
        f'# {env_prefix}APP_NAME="{APPLICATION_NAME}"',
        f'# {env_prefix}APP_DIR="{DEFAULT_APP_DIR}"',
        f'# {env_prefix}LOG_DIR="{DEFAULT_APP_DIR / "logs"}"',
        f'# {env_prefix}TOKEN_STORE_DIR="{DEFAULT_APP_DIR / "token-store"}"',
        f'# {env_prefix}TOKEN_FILE_NAME="character_tokens.json"',
        f"# {env_prefix}REQUEST_TIMEOUT=30",
        "",
        "# OAuth2 Credentials (REQUIRED)",
        "# ==============================",
        "# Get these from https://developers.eveonline.com/applications",
        "# You can also use the `esi-auth util parse-app-json` command",
        "# to parse the JSON file downloaded from the developer site,",
        "# and generate the relevant .env lines.",
        "# Note: CLIENT_ID must be set for the application to work, but CLIENT_SECRET",
        "# can be anything, as it is not used in the PKCE auth flow.",
        f"{env_prefix}CLIENT_ID={parsed_app_config['CLIENT_ID']}",
        f"{env_prefix}CLIENT_SECRET={parsed_app_config['CLIENT_SECRET']}",
        "",
        "# OAuth2 Scopes",
        "# =============",
        "# Must be a JSON array string. Common scopes:",
        "# - publicData: Basic character info",
        "# - esi-characters.read_character_info.v1: Character details",
        "# - esi-assets.read_assets.v1: Asset information",
        "# - esi-wallet.read_character_wallet.v1: Wallet information",
        "# You can use the `esi-auth util parse-app-json` command",
        "# to generate this line from your app configuration.",
        f"#{env_prefix}SCOPES='{parsed_app_config['SCOPES']}'",
        "",
        "# EVE Online API Endpoints",
        "# ========================",
        f'# {env_prefix}ESI_BASE_URL="https://esi.evetech.net"',
        f'# {env_prefix}SSO_BASE_URL="https://login.eveonline.com"',
        f"# {env_prefix}OAUTH2_AUTHORIZATION_METADATA_URL={OAUTH_METADATA_URL}",
        f"# {env_prefix}AUTHORIZATION_ENDPOINT={metadata['authorization_endpoint']}",
        f"# {env_prefix}TOKEN_ENDPOINT={metadata['token_endpoint']}",
        f"# {env_prefix}JWKS_URI={metadata['jwks_uri']}",
        "",
        "# OAuth2 Token Validation",
        "# =======================",
        f'# {env_prefix}OAUTH2_AUDIENCE="EVE Online"',
        f"# {env_prefix}OAUTH2_ISSUER='{json.dumps([f'{metadata["issuer"]}'])}'",
        "",
        "# Callback Server Configuration",
        "# =============================",
        "# These settings control the local server that receives OAuth callbacks, and ",
        "# are required for the application to function properly.",
        "# They must match the settings in your EVE Online developer application.",
        "# You can use the `esi-auth util parse-app-json` command",
        "# to generate these lines from your app configuration.",
        f"{env_prefix}CALLBACK_HOST={parsed_app_config['CALLBACK_HOST']}",
        f"{env_prefix}CALLBACK_PORT={parsed_app_config['CALLBACK_PORT']}",
        f"{env_prefix}CALLBACK_ROUTE={parsed_app_config['CALLBACK_ROUTE']}",
        "",
        "# User Agent Information",
        "# ======================",
        "# Used to identify your application in API requests",
        "# You must set at least CHARACTER_NAME and USER_EMAIL",
        f"{env_prefix}CHARACTER_NAME={character_name}",
        f"{env_prefix}USER_EMAIL={user_email}",
        f"{env_prefix}USER_APP_NAME={parsed_app_config['NAME']}",
        f"{env_prefix}USER_APP_VERSION={user_app_version}",
        "",
        "# Notes:",
        "# ------",
        "# - Lines starting with # are comments and will be ignored",
        "# - Remove the # prefix to enable a setting",
        "# - Settings with default values are commented out by default",
        "# - Required settings (CLIENT_ID, CLIENT_SECRET, etc.) are uncommented",
        "# - JSON values must be properly quoted and escaped",
    ]

    content = "\n".join(env_content) + "\n"

    # Write the file
    try:
        file_out.write_text(content, encoding="utf-8")
        console.print(
            f"✅ Example .env file generated: {file_out.absolute()}", style="green"
        )
        console.print()
        console.print("Next steps:", style="bold")
        console.print("1. Copy the example file to APP_DIR and rename it to .env:")
        console.print("2. Edit .env and add missing required values")
        console.print("3. Customize other settings as needed")
        console.print(
            "4. Run: esi-auth store add  # to authenticate your first character"
        )

    except Exception as e:
        console.print(f"❌ Failed to write file: {e}", style="red")
        raise typer.Exit(code=1) from e


def parse_oauth_metadata(metadata: OauthMetadata) -> dict[str, str]:
    result: dict[str, str] = {}
    result["AUTHORIZATION_ENDPOINT"] = metadata.get("authorization_endpoint", "Unknown")
    result["TOKEN_ENDPOINT"] = metadata.get("token_endpoint", "Unknown")
    result["JWKS_URI"] = metadata.get("jwks_uri", "Unknown")
    result["ISSUER"] = metadata.get("issuer", "Unknown")
    console = Console()
    for key, value in result.items():
        if value == "Unknown":
            console.print(
                f"Warning: {key} is missing in parsed metadata", style="bold yellow"
            )
    return result


def fetch_metadata(url: str = "", user_agent: str = "esi-auth") -> OauthMetadata:
    return fetch_oauth_metadata_sync(url=url, user_agent=user_agent)


@app.command()
def oauth_metadata_env(
    ctx: typer.Context,
    file_out: Annotated[
        Path, typer.Argument(..., dir_okay=False, writable=True)
    ] = Path(".oauth-example.env"),
    oauth_url: Annotated[
        str | None,
        typer.Option(
            "--oauth-url",
            help=f"OAuth2 metadata URL. If not set, uses {OAUTH_METADATA_URL}",
        ),
    ] = None,
    env_prefix: Annotated[
        str,
        typer.Option(
            "--env-prefix",
            help="Environment variable prefix to use in the .env file",
        ),
    ] = "ESI_AUTH_",
):
    """Fetch and display the OAuth2 metadata from EVE Online.

    Display the OAuth2 metadata from the EVE Online authorization server, and
    output the metadata fields in env file format.
    """
    console = Console()
    if oauth_url is None:
        oauth_url = OAUTH_METADATA_URL
    user_agent = get_user_agent()
    metadata = fetch_metadata(url=oauth_url, user_agent=user_agent)

    console.rule("[bold green]OAuth2 Metadata")
    console.print(metadata)
    console.print()
    console.rule("[bold green]Metadata as Environment Variables")
    console.print("# The following lines can be placed in the .env file:")
    env_lines = [
        f'{env_prefix}OAUTH2_AUTHORIZATION_ENDPOINT="{metadata.get("authorization_endpoint", "Unknown")}"',
        f'{env_prefix}OAUTH2_TOKEN_ENDPOINT="{metadata.get("token_endpoint", "Unknown")}"',
        f'{env_prefix}OAUTH2_JWKS_URI="{metadata.get("jwks_uri", "Unknown")}"',
        f'{env_prefix}OAUTH2_ISSUER="{metadata.get("issuer", "Unknown")}"',
    ]
    text_out = "\n".join(env_lines) + "\n"
    console.print(text_out, no_wrap=True, crop=False, overflow="ignore")


@app.command()
def eve_app_json_env(
    ctx: typer.Context,
    file_in: Annotated[Path, typer.Argument(..., exists=True, dir_okay=False)],
    file_out: Annotated[
        Path, typer.Argument(..., dir_okay=False, writable=True)
    ] = Path(".eve-app-example.env"),
    env_prefix: Annotated[
        str,
        typer.Option(
            "--env-prefix",
            help="Environment variable prefix to use in the .env file",
        ),
    ] = "ESI_AUTH_",
):
    """Parse the json representation of the app configuration from Eve Online Developers to .env format.

    You can manage your applications at https://developers.eveonline.com/applications,
    and you can download the app configuration as a JSON file.
    This command will parse the app configuration from the JSON file,
    and print the relevant settings to be placed in the .env file.
    """
    console = Console()
    file_txt = file_in.read_text()
    app_config: EveDevAppConfig = json.loads(file_txt)
    console.rule(f"[bold green]Eve App Configuration:")
    console.print(app_config)
    console.print()
    console.rule("[bold green]Eve App Config as Environment Variables")
    parsed_app_config = parse_eve_dev_app_config(app_config)

    env_lines = [
        f'{env_prefix}CLIENT_ID="{parsed_app_config["CLIENT_ID"]}"',
        f'{env_prefix}CLIENT_SECRET="{parsed_app_config["CLIENT_SECRET"]}"',
        "# Note: The scopes must be a string representing a JSON array of strings.",
        f"{env_prefix}SCOPES='{parsed_app_config['SCOPES']}'",
        f'{env_prefix}CALLBACK_HOST="{parsed_app_config["CALLBACK_HOST"]}"',
        f'{env_prefix}CALLBACK_PORT="{parsed_app_config["CALLBACK_PORT"]}"',
        f'{env_prefix}CALLBACK_ROUTE="{parsed_app_config["CALLBACK_ROUTE"]}"',
    ]
    text_out = "\n".join(env_lines) + "\n"
    console.print("# The following lines can be placed in the .env file:")
    console.print(text_out, no_wrap=True, crop=False, overflow="ignore")
    file_out.write_text(text_out)
    console.print(f"Wrote settings to {file_out.absolute()}")
