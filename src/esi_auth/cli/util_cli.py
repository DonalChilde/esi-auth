"""Utility CLI commands for esi_auth."""

import json
from pathlib import Path
from typing import Annotated, TypedDict

import typer
from rich.console import Console

from esi_auth.auth_helpers import fetch_oauth_metadata_sync
from esi_auth.helpers import get_user_agent
from esi_auth.models import CallbackUrl
from esi_auth.settings import APPLICATION_NAME, DEFAULT_APP_DIR, get_settings

app = typer.Typer(no_args_is_help=True)


class AppConfig(TypedDict):
    name: str
    description: str
    clientId: str
    clientSecret: str
    callbackUrl: str
    scopes: list[str]


@app.command()
def parse_app_json(
    file_in: Annotated[Path, typer.Argument(..., exists=True, dir_okay=False)],
    file_out: Annotated[
        Path, typer.Argument(..., dir_okay=False, writable=True)
    ] = Path(".app-example.env"),
):
    """Parse the json representation of the app configuration from Eve Online Developers.

    You can manage your applications at https://developers.eveonline.com/applications,
    and you can download the app configuration as a JSON file.
    This command will parse the app configuration from the JSON file,
    and print the relevant settings to be placed in the .env file.
    """
    console = Console()
    file_txt = file_in.read_text()
    app_config: AppConfig = json.loads(file_txt)
    console.rule(f"[bold green]App Configuration: {app_config['name']}")
    console.print(app_config)
    console.print()
    console.rule("[bold green]Environment Variables")
    callback_url = CallbackUrl.parse(app_config["callbackUrl"])

    env_lines = [
        f'CLIENT_ID="{app_config["clientId"]}"',
        f'CLIENT_SECRET="{app_config["clientSecret"]}"',
        "# Note: The scopes must be a string representing a JSON array of strings.",
        f"SCOPES='{json.dumps(app_config['scopes'])}'",
        f'CALLBACK_HOST="{callback_url.callback_host}"',
        f'CALLBACK_PORT="{callback_url.callback_port}"',
        f'CALLBACK_ROUTE="{callback_url.callback_route}"',
    ]
    text_out = "\n".join(env_lines) + "\n"
    console.print("# The following lines can be placed in the .env file:")
    console.print(text_out, no_wrap=True, crop=False, overflow="ignore")
    file_out.write_text(text_out)
    console.print(f"Wrote settings to {file_out.absolute()}")


@app.command()
def generate_example_env(
    file_out: Annotated[
        Path, typer.Option("-o", "--output", help="Output file path")
    ] = Path(".env.example"),
    overwrite: Annotated[
        bool, typer.Option("--overwrite", help="Overwrite existing file")
    ] = False,
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

    # Generate example content with comments and all available settings
    env_content = [
        "# ESI Auth Configuration File",
        "# This file contains all available settings for the ESI Auth application.",
        "# Copy this file to .env and update the values as needed.",
        "",
        "# Application Configuration",
        "# ========================",
        f'# ESI_AUTH_APP_NAME="{APPLICATION_NAME}"',
        f'# ESI_AUTH_APP_DIR="{DEFAULT_APP_DIR}"',
        f'# ESI_AUTH_LOG_DIR="{DEFAULT_APP_DIR / "logs"}"',
        f'# ESI_AUTH_TOKEN_STORE_DIR="{DEFAULT_APP_DIR / "token-store"}"',
        f'# ESI_AUTH_TOKEN_FILE_NAME="character_tokens.json"',
        f"# ESI_AUTH_REQUEST_TIMEOUT=30",
        "",
        "# OAuth2 Credentials (REQUIRED)",
        "# ==============================",
        "# Get these from https://developers.eveonline.com/applications",
        "# You can also use the `esi-auth util parse-app-json` command",
        "# to parse the JSON file downloaded from the developer site,",
        "# and generate the relevant .env lines.",
        "# Note: CLIENT_ID must be set for the application to work, but CLIENT_SECRET",
        "# can be anything, as it is not used in the PKCE auth flow.",
        'ESI_AUTH_CLIENT_ID="your_client_id_here"',
        'ESI_AUTH_CLIENT_SECRET="your_client_secret_here"',
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
        f"#ESI_AUTH_SCOPES='{json.dumps(['publicData', 'esi-characters.read_character_info.v1'])}'",
        "",
        "# EVE Online API Endpoints",
        "# ========================",
        f'# ESI_AUTH_ESI_BASE_URL="https://esi.evetech.net"',
        f'# ESI_AUTH_SSO_BASE_URL="https://login.eveonline.com"',
        f'# ESI_AUTH_OAUTH2_AUTHORIZATION_METADATA_URL="https://login.eveonline.com/.well-known/oauth-authorization-server"',
        f'# ESI_AUTH_AUTHORIZATION_ENDPOINT="https://login.eveonline.com/v2/oauth/authorize"',
        f'# ESI_AUTH_TOKEN_ENDPOINT="https://login.eveonline.com/v2/oauth/token"',
        f'# ESI_AUTH_JWKS_URI="https://login.eveonline.com/oauth/jwks"',
        "",
        "# OAuth2 Token Validation",
        "# =======================",
        f'# ESI_AUTH_OAUTH2_AUDIENCE="EVE Online"',
        f"# ESI_AUTH_OAUTH2_ISSUER='{json.dumps(['https://login.eveonline.com'])}'",
        "",
        "# Callback Server Configuration",
        "# =============================",
        "# These settings control the local server that receives OAuth callbacks, and ",
        "# are required for the application to function properly.",
        "# They must match the settings in your EVE Online developer application.",
        "# You can use the `esi-auth util parse-app-json` command",
        "# to generate these lines from your app configuration.",
        f'ESI_AUTH_CALLBACK_HOST="localhost"',
        f"ESI_AUTH_CALLBACK_PORT=8080",
        f'ESI_AUTH_CALLBACK_ROUTE="/callback"',
        "",
        "# User Agent Information",
        "# ======================",
        "# Used to identify your application in API requests",
        "# You must set at least CHARACTER_NAME and USER_EMAIL",
        'ESI_AUTH_CHARACTER_NAME="Unknown"',
        'ESI_AUTH_USER_EMAIL="Unknown"',
        'ESI_AUTH_USER_APP_NAME="Unknown"',
        'ESI_AUTH_USER_APP_VERSION="Unknown"',
        "",
        "# Notes:",
        "# ------",
        "# - Lines starting with # are comments and will be ignored",
        "# - Remove the # prefix to enable a setting",
        "# - Settings with default values are commented out by default",
        "# - Required settings (CLIENT_ID, CLIENT_SECRET) are uncommented",
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
        console.print("1. Copy the example file to .env:")
        console.print(f"   cp {file_out} .env")
        console.print("2. Edit .env and add your CLIENT_ID and CLIENT_SECRET")
        console.print("3. Customize other settings as needed")
        console.print(
            "4. Run: esi-auth store add  # to authenticate your first character"
        )

    except Exception as e:
        console.print(f"❌ Failed to write file: {e}", style="red")
        raise typer.Exit(code=1) from e


@app.command()
def parse_oauth_metadata():
    """Fetch and display the OAuth2 metadata from EVE Online.

    Display the OAuth2 metadata from the EVE Online authorization server, and
    output the metadata fields in env file format.
    """
    console = Console()
    settings = get_settings()
    oauth_metadata = fetch_oauth_metadata_sync(
        url=settings.oauth2_authorization_metadata_url,
        user_agent=get_user_agent(),
    )
    console.rule("[bold green]OAuth2 Metadata")
    console.print(oauth_metadata)
    console.print()
    console.rule("[bold green]Environment Variables")
    console.print("# The following lines can be placed in the .env file:")
    env_lines = [
        f'OAUTH2_AUTHORIZATION_ENDPOINT="{oauth_metadata.get("authorization_endpoint", "Unknown")}"',
        f'OAUTH2_TOKEN_ENDPOINT="{oauth_metadata.get("token_endpoint", "Unknown")}"',
        f'OAUTH2_JWKS_URI="{oauth_metadata.get("jwks_uri", "Unknown")}"',
        f'OAUTH2_ISSUER="{oauth_metadata.get("issuer", "Unknown")}"',
    ]
    text_out = "\n".join(env_lines) + "\n"
    console.print(text_out, no_wrap=True, crop=False, overflow="ignore")
