"""CLI commands for managing the token store."""

import asyncio
import logging
import webbrowser
from typing import Annotated

import typer
from jwt import PyJWKClient
from rich.console import Console
from rich.table import Table
from whenever import Instant

from esi_auth.auth import (
    authenticate_character,
    create_auth_params,
    get_sso_url,
)
from esi_auth.credential_storage import CredentialStoreJson
from esi_auth.settings import get_settings

logger = logging.getLogger(__name__)

app = typer.Typer(no_args_is_help=True)


@app.command()
def add(
    ctx: typer.Context,
    client_id: Annotated[
        str | None,
        typer.Option(
            "-i",
            "--client-id",
            help="Client ID to use for authorization. Either the client ID or client alias must be provided.",
        ),
    ] = None,
    client_alias: Annotated[
        str | None,
        typer.Option(
            "-a",
            "--client-alias",
            help="Alias for the client ID to use for authorization. Either the client ID or client alias must be provided.",
        ),
    ] = None,
):
    """Add an authorized character to the token store."""
    if all([client_id, client_alias]):
        typer.echo("Error: Specify either client ID or client alias, not both.")
        raise typer.Exit(code=1)
    if not any([client_id, client_alias]):
        typer.echo("Error: Either client ID or client alias must be specified.")
        raise typer.Exit(code=1)
    console = Console()
    console.rule("[bold blue]Add Authorized Character[/bold blue]")
    settings = get_settings()
    credential_store = get_credential_store()
    if client_alias:
        credentials = credential_store.get_credentials_by_alias(client_alias)
    elif client_id:
        credentials = credential_store.get_credentials(client_id)
    else:
        raise typer.Exit(code=1)  # This should never happen due to earlier checks
    if not credentials:
        console.print(
            f"Credentials not found for "
            f"{f'alias {client_alias}' if client_alias else f'client ID {client_id}'}.",
            style="bold red",
        )
        raise typer.Exit(code=1)

    jwks_client = PyJWKClient(settings.jwks_uri)
    auth_params = create_auth_params(credentials=credentials, jwks_client=jwks_client)
    console.print(credentials.scopes)
    sso_url, state = get_sso_url(auth_params=auth_params, scopes=credentials.scopes)
    logger.info(f"Attempting to add character authorization using the following url.")
    logger.info(f"{sso_url}")
    console.print()
    console.print(f"Your web browser should automatically open to the Eve login page.")
    console.print(f"If it does not, try clicking on the link below:")
    console.print(f"[blue]Click Here[/blue]", style=f"link {sso_url}")
    console.print("See logs for full URL details.")
    webbrowser.open_new(sso_url)
    character = asyncio.run(
        authenticate_character(auth_params=auth_params, sso_url=sso_url, state=state)
    )
    console.print(
        f"Successfully authorized character: {character.character_name}",
        style="bold green",
    )
    ctx.obj.token_store.add_character(character)
    console.print(
        f"Character {character.character_name} added to token store.",
        style="bold green",
    )


def get_credential_store():
    """Get the credential store instance."""
    settings = get_settings()
    return CredentialStoreJson(
        settings.credential_store_dir / settings.credential_file_name
    )


@app.command()
def remove(ctx: typer.Context, character_id: int):
    """Remove an authorized character."""
    console = Console()
    console.rule("[bold blue]Remove Authorized Character[/bold blue]")
    character = ctx.obj.token_store.get_character(character_id)
    if not character:
        console.print(
            f"Character with ID {character_id} not found.",
            style="bold red",
        )
        raise typer.Exit(code=1)

    ctx.obj.token_store.remove_character(character_id)
    console.print(
        f"Character {character.character_name} removed from token store.",
        style="bold green",
    )


@app.command()
def list(
    ctx: typer.Context,
    buffer_minutes: Annotated[
        int,
        typer.Option(
            "-b",
            "--buffer",
            help="Buffer time in minutes to consider a token as expiring.",
        ),
    ] = 5,
):
    """List authorized characters."""
    console = Console()
    console.rule("[bold blue]Authorized Characters[/bold blue]")

    characters = ctx.obj.token_store.list_characters()

    if not characters:
        console.print("No authorized characters found.", style="yellow")
        return

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Character ID", width=12)
    table.add_column("Character Name", style="cyan", no_wrap=True)
    table.add_column("Token Status", justify="center", width=12)
    table.add_column("Minutes Until Expiry", justify="center", width=20)

    current_time = Instant.now()

    for character in characters:
        # Calculate minutes until expiry
        if character.is_expired():
            status = "[red]EXPIRED[/red]"
            minutes_text = "[red]Expired[/red]"
        else:
            time_diff = character.expires_at.difference(current_time)
            minutes_until_expiry = time_diff.in_minutes()

            if minutes_until_expiry < buffer_minutes:  # Less than buffer time
                status = "[yellow]EXPIRING[/yellow]"
                minutes_text = f"[yellow]{minutes_until_expiry:.1f}[/yellow]"
            else:
                status = "[green]VALID[/green]"
                minutes_text = f"[green]{minutes_until_expiry:.1f}[/green]"

        table.add_row(
            str(character.character_id),
            character.character_name,
            status,
            minutes_text,
        )

    console.print(table)
    console.print(f"\nTotal characters: {len(characters)}")


@app.command()
def refresh(
    ctx: typer.Context,
    character_id: Annotated[
        int | None,
        typer.Option(
            "-c", "--character", help="Refresh token for a specific character ID."
        ),
    ] = None,
    all_characters: Annotated[
        bool,
        typer.Option("-a", "--all", help="Refresh tokens for all characters."),
    ] = False,
    expired_only: Annotated[
        bool,
        typer.Option(
            "-e", "--expired", help="Refresh tokens only for expired characters."
        ),
    ] = False,
    expiring_only: Annotated[
        bool,
        typer.Option(
            "-x", "--expiring", help="Refresh tokens only for expiring characters."
        ),
    ] = False,
    buffer_minutes: Annotated[
        int,
        typer.Option(
            "-b",
            "--buffer",
            help="Buffer time in minutes to consider a token as expiring. Notr to exceed 15 minutes.",
        ),
    ] = 5,
):
    """Refresh tokens for authorized characters.

    By default, refreshes tokens for characters that need refreshing (expiring soon).
    Use options to control which characters to refresh.
    """
    console = Console()
    console.rule("[bold blue]Refresh Character Tokens[/bold blue]")
    if buffer_minutes < 0:
        console.print("Error: buffer_minutes must be non-negative.", style="bold red")
        raise typer.Exit(code=1)
    if buffer_minutes > 15:
        console.print(
            "Error: buffer_minutes should not exceed 15 minutes.", style="bold red"
        )
        raise typer.Exit(code=1)

    # Validate mutually exclusive options
    option_count = sum(
        [bool(character_id), all_characters, expired_only, expiring_only]
    )
    if option_count > 1:
        console.print(
            "Error: Only one refresh option can be specified at a time.",
            style="bold red",
        )
        raise typer.Exit(code=1)

    # Determine which characters to refresh
    if character_id:
        character = ctx.obj.token_store.get_character(character_id)
        if not character:
            console.print(
                f"Character with ID {character_id} not found.",
                style="bold red",
            )
            raise typer.Exit(code=1)
        characters_to_refresh = [character]
        refresh_type = f"character {character_id}"
    elif all_characters:
        characters_to_refresh = ctx.obj.token_store.list_characters()
        refresh_type = "all characters"
    elif expired_only:
        characters_to_refresh = ctx.obj.token_store.list_expired_characters()
        refresh_type = "expired characters"
    elif expiring_only:
        characters_to_refresh = ctx.obj.token_store.list_characters_needing_refresh(
            buffer_minutes
        )
        refresh_type = f"characters expiring within {buffer_minutes} minutes"
    else:
        # Default: refresh characters needing refresh
        characters_to_refresh = ctx.obj.token_store.list_characters_needing_refresh(
            buffer_minutes
        )
        refresh_type = f"characters needing refresh (within {buffer_minutes} minutes)"

    if not characters_to_refresh:
        console.print(f"No {refresh_type} found.", style="yellow")
        return

    console.print(f"Found {len(characters_to_refresh)} {refresh_type} to refresh.")

    # Ask for confirmation if refreshing multiple characters
    if len(characters_to_refresh) > 1:
        confirm = typer.confirm(
            f"Do you want to refresh {len(characters_to_refresh)} characters?"
        )
        if not confirm:
            console.print("Operation cancelled.", style="yellow")
            return
    success_ids, failure_ids = ctx.obj.token_store.refresh_characters(
        characters_to_refresh
    )
    if failure_ids:
        console.print(
            f"Refresh completed: {len(success_ids)} successful, {len(failure_ids)} failed.",
            style="bold yellow",
        )
        console.print(f"Failed character IDs: {', '.join(map(str, failure_ids))}")
        console.print("See logs for details.", style="yellow")


# @app.command()
# def backup():
#     """Backup the database of authorized characters."""
#     pass
#     # TODO implement backup


# @app.command()
# def restore():
#     """Restore the database of authorized characters from a backup."""
#     pass
#     # TODO implement restore
