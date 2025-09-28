"""Command line interface for managing EVE SSO authorized characters."""

import asyncio
import logging
import webbrowser

import typer
from jwt import PyJWKClient
from rich.console import Console

from esi_auth.auth import (
    AuthParams,
    authenticate_character,
    create_auth_params,
    get_sso_url,
)
from esi_auth.models import CharacterToken
from esi_auth.settings import get_settings

logger = logging.getLogger(__name__)

app = typer.Typer(no_args_is_help=True)


@app.command()
def add(ctx: typer.Context):
    """Add an authorized character."""
    console = Console()
    console.rule("[bold blue]Add Authorized Character[/bold blue]")
    settings = get_settings()
    if settings.client_id == "Unknown":
        console.print(
            f"Client ID must be set in settings. You can place it in the .env file "
            f"located in the project data directory: {settings.app_dir}.",
            style="bold red",
        )
        raise typer.Exit(code=1)

    jwks_client = PyJWKClient(settings.jwks_uri)
    auth_params = create_auth_params(jwks_client=jwks_client)
    sso_url, state = get_sso_url(auth_params=auth_params, scopes=settings.scopes)
    logger.info(f"Attempting to add character authorization using the following url.")
    logger.info(f"{sso_url}")
    console.print()
    console.print(f"Your web browser should automatically open to the Eve login page.")
    console.print(f"If it does not, try clicking on the link below:")
    console.print(f"[blue]Click Here[/blue]", style=f"link {sso_url}")
    console.print("See logs for full URL details.")
    webbrowser.open_new(sso_url)
    character = _authenticate_character(
        auth_params=auth_params, sso_url=sso_url, state=state
    )
    console.print(
        f"Successfully authorized character: {character.character_name}",
        style="bold green",
    )
    ctx.obj.token_store.add_character(character)


def _authenticate_character(
    auth_params: AuthParams, sso_url: str, state: str
) -> CharacterToken:
    character = asyncio.run(
        authenticate_character(auth_params=auth_params, sso_url=sso_url, state=state)
    )
    return character


@app.command()
def remove():
    """Remove an authorized character."""
    pass
    # TODO implement remove


@app.command()
def list():
    """List authorized characters."""
    pass
    # TODO implement list


@app.command()
def refresh():
    """Refresh tokens for authorized characters."""
    pass
    # TODO implement refresh


@app.command()
def backup():
    """Backup the database of authorized characters."""
    pass
    # TODO implement backup


@app.command()
def restore():
    """Restore the database of authorized characters from a backup."""
    pass
    # TODO implement restore
