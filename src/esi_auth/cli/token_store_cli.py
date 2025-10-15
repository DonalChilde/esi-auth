"""CLI commands for managing the token store."""

import asyncio
import logging
import webbrowser
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text
from whenever import Instant

from esi_auth.cli import STYLE_ERROR, STYLE_SUCCESS, STYLE_WARNING
from esi_auth.esi_auth import CharacterToken, EsiAuth, EveCredentials

from .cli_helpers import check_user_agent_setup

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
    console = Console()
    console.rule("[bold blue]Add Authorized Character[/bold blue]")
    check_user_agent_setup(ctx)
    esi_auth: EsiAuth = ctx.obj.auth_store  # type: ignore
    if esi_auth is None:  # pyright: ignore[reportUnnecessaryComparison]
        console.print("[bold red]Auth store is not initialized.[/bold red]")
        raise typer.Exit(code=1)
    # Checks for client_id/client_alias presence and mutual exclusivity
    credentials = get_credentials_from_store(
        esi_auth=esi_auth,
        client_id=client_id,
        client_alias=client_alias,
    )
    auth_request = esi_auth.prepare_request(credentials=credentials)
    logger.info(f"Attempting to add character authorization using the following url.")
    logger.info(f"{auth_request.sso_url}")
    console.print()
    console.print(f"Your web browser should automatically open to the Eve login page.")
    console.print(f"If it does not, try clicking on the link below:")
    console.print(f"[blue]Click Here[/blue]", style=f"link {auth_request.sso_url}")
    console.print("See logs for full URL details.")
    webbrowser.open_new(auth_request.sso_url)
    character_token = asyncio.run(
        esi_auth.request_character_token(
            credentials=credentials, auth_request=auth_request
        )
    )
    console.print(
        f"Successfully authorized character: {character_token.character_name}",
        style="bold green",
    )
    esi_auth.store_token(token=character_token, credentials=credentials)
    console.print(
        f"Character {character_token.character_name} added to token store for client {credentials.client_alias}.",
        style="bold green",
    )


@app.command()
def remove(
    ctx: typer.Context,
    character_id: int,
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
    """Remove an authorized character."""
    console = Console()
    console.rule("[bold blue]Remove Authorized Character[/bold blue]")

    esi_auth: EsiAuth = ctx.obj.auth_store  # type: ignore
    if esi_auth is None:  # pyright: ignore[reportUnnecessaryComparison]
        console.print("[bold red]Auth store is not initialized.[/red]")
        raise typer.Exit(code=1)
    # Checks for client_id/client_alias presence and mutual exclusivity
    credentials = get_credentials_from_store(
        esi_auth=esi_auth,
        client_id=client_id,
        client_alias=client_alias,
    )
    character_token = esi_auth.get_token_from_id(
        credentials=credentials, character_id=character_id
    )
    if not character_token:
        console.print(
            f"[bold red]Character with ID {character_id} not found.[/bold red]",
        )
        raise typer.Exit(code=1)
    esi_auth.remove_token(token=character_token, credentials=credentials)
    console.print(
        f"Character {character_token.character_name} removed from token store for client {credentials.client_alias}.",
        style="bold green",
    )


@app.command()
def list_characters(
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
    console.rule("[bold blue]List Authorized Characters[/bold blue]")

    esi_auth: EsiAuth = ctx.obj.auth_store  # type: ignore
    if esi_auth is None:  # pyright: ignore[reportUnnecessaryComparison]
        console.print("[bold red]Auth store is not initialized.[/red]")
        raise typer.Exit(code=1)
    # Checks for client_id/client_alias presence and mutual exclusivity
    credentials = get_credentials_from_store(
        esi_auth=esi_auth,
        client_id=client_id,
        client_alias=client_alias,
    )

    character_tokens = esi_auth.get_all_tokens(credentials=credentials)

    if not character_tokens:
        console.print("No authorized characters found.", style="yellow")
        return

    table = character_list_table(
        characters=character_tokens, buffer_minutes=buffer_minutes
    )

    console.print(table)
    console.print(f"\nTotal characters: {len(character_tokens)}")


def character_list_table(
    characters: list[CharacterToken], buffer_minutes: int
) -> Table:
    """Helper to create a rich Table of characters."""
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Character ID", width=12)
    table.add_column("Character Name", style="cyan", no_wrap=True)
    table.add_column("Token Status", justify="center", width=12)
    table.add_column("Minutes Until Expiry", justify="center", width=20)

    current_time = Instant.now()

    for character in characters:
        # Calculate minutes until expiry
        if character.is_expired():
            status = Text("EXPIRED", style=STYLE_ERROR)
            minutes_text = Text("Expired", style=STYLE_ERROR)
        else:
            time_diff = character.expires_at.difference(current_time)
            minutes_until_expiry = time_diff.in_minutes()

            if minutes_until_expiry < buffer_minutes:  # Less than buffer time
                status = Text("EXPIRING", style=STYLE_WARNING)
                minutes_text = Text(f"{minutes_until_expiry:.1f}", style=STYLE_WARNING)
            else:
                status = Text("VALID", style=STYLE_SUCCESS)
                minutes_text = Text(f"{minutes_until_expiry:.1f}", style=STYLE_SUCCESS)

        table.add_row(
            str(character.character_id),
            character.character_name,
            status,
            minutes_text,
        )
    return table


def get_credentials_from_store(
    esi_auth: EsiAuth,
    client_id: str | None,
    client_alias: str | None,
) -> EveCredentials:
    """Helper to get credential and token stores and validate client info."""
    # Note: duplicate argument verification code retained for better CLI error messages.
    console = Console()
    if all([client_id, client_alias]):
        console.print(
            "[bold red]Error: Specify either client ID or client alias, not both.[/bold red]",
        )
        raise typer.Exit(code=1)
    if not any([client_id, client_alias]):
        console.print(
            "[bold red]Error: Either client ID or client alias must be specified.[/bold red]",
        )
        raise typer.Exit(code=1)
    if client_alias:
        credentials = esi_auth.get_credentials_from_alias(client_alias)
    elif client_id:
        credentials = esi_auth.get_credentials_from_id(client_id)
    else:  # Should not be reachable
        credentials = None
    if not credentials:
        console.print(
            f"[bold red]Credentials not found for "
            f"{f'alias {client_alias}' if client_alias else f'client ID {client_id}'}.[/bold red]",
        )
        raise typer.Exit(code=1)
    return credentials


@app.command()
def refresh(
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
    character_id: Annotated[
        int | None,
        typer.Option(
            "-c",
            "--character",
            help="Refresh token for a specific character ID. If not provided, refreshes all characters needing refresh.",
        ),
    ] = None,
    buffer_minutes: Annotated[
        int,
        typer.Option(
            "-b",
            "--buffer",
            help="Buffer time in minutes to consider a token as expiring. 20 is the maximum value.",
        ),
    ] = 5,
):
    """Refresh tokens for authorized characters.

    By default, refreshes tokens for characters that need refreshing (expiring soon).
    Use options to control which characters to refresh.
    """
    console = Console()
    console.rule("[bold blue]Refresh Character Tokens[/bold blue]")
    check_user_agent_setup(ctx)
    if buffer_minutes < 0:
        console.print(
            "[bold red]Error: buffer_minutes must be non-negative.[/bold red]"
        )
        raise typer.Exit(code=1)
    if buffer_minutes > 20:
        buffer_minutes = 20

    esi_auth: EsiAuth = ctx.obj.auth_store  # type: ignore
    if esi_auth is None:  # pyright: ignore[reportUnnecessaryComparison]
        console.print(Text("Auth store is not initialized.", style=STYLE_ERROR))
        raise typer.Exit(code=1)
    # Checks for client_id/client_alias presence and mutual exclusivity
    credentials = get_credentials_from_store(
        esi_auth=esi_auth,
        client_id=client_id,
        client_alias=client_alias,
    )

    # Refresh one Character needing refresh
    if character_id:
        character = esi_auth.get_token_from_id(
            credentials=credentials, character_id=character_id, buffer=-1
        )
        if not character:
            console.print(
                f"[bold red]Character with ID {character_id} not found.[/bold red]",
            )
            raise typer.Exit(code=1)
        console.print(f"Before refresh:")
        table = character_list_table(
            characters=[character] if character else [], buffer_minutes=buffer_minutes
        )
        console.print(table)
        console.print(f"After refresh:")
        refreshed_character = esi_auth.get_token_from_id(
            credentials=credentials, character_id=character_id, buffer=buffer_minutes
        )
        table = character_list_table(
            characters=[refreshed_character] if refreshed_character else [],
            buffer_minutes=buffer_minutes,
        )
        console.print(table)
    else:
        # Refresh all Characters needing refresh
        console.print("Before refresh:")
        character_tokens = esi_auth.get_all_tokens(credentials=credentials, buffer=-1)
        table = character_list_table(
            characters=character_tokens,
            buffer_minutes=buffer_minutes,
        )
        console.print(table)
        console.print(f"After refresh:")
        refreshed_characters = esi_auth.get_all_tokens(
            credentials=credentials, buffer=buffer_minutes
        )
        table = character_list_table(
            characters=refreshed_characters, buffer_minutes=buffer_minutes
        )
        console.print(table)


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
