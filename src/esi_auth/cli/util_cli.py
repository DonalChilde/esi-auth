"""Utility CLI commands for esi_auth."""

import json
from pathlib import Path
from typing import Annotated, TypedDict

import typer
from rich.console import Console

from esi_auth.settings import (
    AUTHORIZATION_ENDPOINT,
    DEFAULT_APP_DIR,
    ESI_BASE_URL,
    JWKS_URI,
    OAUTH_AUDIENCE,
    OAUTH_ISSUER,
    OAUTH_METADATA_URL,
    SSO_BASE_URL,
    TOKEN_ENDPOINT,
)

app = typer.Typer(no_args_is_help=True)


class EveDevAppConfig(TypedDict):
    name: str
    description: str
    clientId: str
    clientSecret: str
    callbackUrl: str
    scopes: list[str]


@app.command()
def generate_example_env(
    ctx: typer.Context,
    path_out: Annotated[
        Path, typer.Argument(help="Path to save the generated env file")
    ],
    file_name: Annotated[
        Path, typer.Option("-f", "--file-name", help="Output file name")
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
    user_app_name: Annotated[
        str, typer.Option("--user-app-name", help="App name for User-Agent")
    ] = "Unknown",
    user_app_version: Annotated[
        str, typer.Option("--user-app-version", help="App version for User-Agent")
    ] = "Unknown",
    env_prefix: Annotated[
        str,
        typer.Option(
            "--env-prefix",
            help="Environment variable prefix to use in the .env file. For dev use only.",
        ),
    ] = "ESI_AUTH_",
):
    """Generate an example .env file with placeholder values."""
    console = Console()
    console.rule("[bold green]Generate Example .env File")
    # Check if file exists and handle overwrite
    if file_name.exists() and not overwrite:
        console.print(
            f"File {file_name} already exists. Use --overwrite to replace it.",
            style="yellow",
        )
        raise typer.Exit(code=1)

    # Generate example content with comments and all available settings
    content = example_env(
        env_prefix=env_prefix,
        character_name=character_name,
        user_email=user_email,
        user_app_name=user_app_name,
        user_app_version=user_app_version,
    )

    # Write the file
    try:
        file_out = path_out / file_name
        file_out.parent.mkdir(parents=True, exist_ok=True)
        file_out.write_text(content, encoding="utf-8")
        console.print(
            f"✅ Example .env file generated: {file_out.absolute()}", style="green"
        )
        console.print()
        console.print("Next steps:", style="bold")
        console.print(
            f"1. Copy the example file to {DEFAULT_APP_DIR} and rename it to .env:"
        )
        console.print("2. Edit .env and add missing required values")
        console.print("3. Customize other settings as needed")
        console.print(
            "4. Run: esi-auth store add  # to authenticate your first character"
        )

    except Exception as e:
        console.print(f"❌ Failed to write file: {e}", style="red")
        raise typer.Exit(code=1) from e


def example_env(
    env_prefix: str = "ESI_AUTH_",
    character_name: str = "Unknown",
    user_email: str = "Unknown",
    user_app_name: str = "Unknown",
    user_app_version: str = "Unknown",
) -> str:
    """Generate example .env content with placeholder values."""
    env_content = [
        "# ESI Auth Configuration File",
        "# This file contains all available settings for the ESI Auth application.",
        "# Copy this file to the APP_DIR and rename it to .env . Update the values as needed.",
        "",
        "# Application Configuration",
        "# ========================",
        f'# {env_prefix}APP_DIR="{DEFAULT_APP_DIR}"',
        f'# {env_prefix}LOG_DIR="{DEFAULT_APP_DIR / "logs"}"',
        f'# {env_prefix}TOKEN_STORE_DIR="{DEFAULT_APP_DIR / "token-store"}"',
        f'# {env_prefix}TOKEN_FILE_NAME="character_tokens.json"',
        f'# {env_prefix}CREDENTIAL_STORE_DIR="{DEFAULT_APP_DIR / "credential-store"}"',
        f'# {env_prefix}CREDENTIAL_FILE_NAME="app_credentials.json"',
        f"# {env_prefix}REQUEST_TIMEOUT=30",
        "",
        "# EVE Online API Endpoints",
        "# ========================",
        f"# {env_prefix}ESI_BASE_URL={ESI_BASE_URL}",
        f"# {env_prefix}SSO_BASE_URL={SSO_BASE_URL}",
        f"# {env_prefix}OAUTH2_AUTHORIZATION_METADATA_URL={OAUTH_METADATA_URL}",
        f"# {env_prefix}AUTHORIZATION_ENDPOINT={AUTHORIZATION_ENDPOINT}",
        f"# {env_prefix}TOKEN_ENDPOINT={TOKEN_ENDPOINT}",
        f"# {env_prefix}JWKS_URI={JWKS_URI}",
        "",
        "# OAuth2 Token Validation",
        "# =======================",
        f"# {env_prefix}OAUTH2_AUDIENCE={OAUTH_AUDIENCE}",
        f"# {env_prefix}OAUTH2_ISSUER='{json.dumps(OAUTH_ISSUER)}'",
        "",
        "# User Agent Information",
        "# ======================",
        "# Used to identify your application in API requests",
        "# This information is required by EVE Online's API guidelines,",
        "# and is used to contact you in case of issues.",
        f"{env_prefix}CHARACTER_NAME={character_name}",
        f"{env_prefix}USER_EMAIL={user_email}",
        f"{env_prefix}USER_APP_NAME={user_app_name}",
        f"{env_prefix}USER_APP_VERSION={user_app_version}",
        "",
        "# Notes:",
        "# ------",
        "# - Lines starting with # are comments and will be ignored",
        "# - Remove the # prefix to enable a setting",
        "# - Settings with default values are commented out by default",
        "# - Required settings (CHARACTER_NAME, USER_EMAIL, etc.) are uncommented",
        "# - JSON arrays and objects should be properly formatted as json.dumps() strings (e.g. OAUTH2_ISSUER)",
    ]

    content = "\n".join(env_content) + "\n"
    return content
