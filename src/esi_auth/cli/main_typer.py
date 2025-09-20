"""Typer-based CLI for ESI authentication.

This module provides a comprehensive command-line interface for managing
EVE Online character authentication tokens using the Typer library.
"""

import asyncio
import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from .. import api
from ..models import AuthenticationError, TokenRefreshError
from ..settings import get_settings, set_production_profile, set_testing_profile
from ..storage import TokenStorageError

# Create the main Typer application
app = typer.Typer(
    name="esi-auth",
    help="EVE Online ESI Authentication Manager",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# Create console for rich output
console = Console()


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for CLI operations.

    Args:
        verbose: Whether to enable verbose logging.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )


@app.callback()
def main(
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
    ] = False,
    test_mode: Annotated[
        bool, typer.Option("--test", help="Use testing configuration")
    ] = False,
) -> None:
    """EVE Online ESI Authentication Manager.

    Manage character authentication tokens for EVE Online ESI API access.
    """
    setup_logging(verbose)

    if test_mode:
        set_testing_profile()
        console.print("[yellow]Using testing configuration[/yellow]")
    else:
        set_production_profile()


@app.command()
def auth(
    scopes: Annotated[
        list[str],
        typer.Option(
            "--scope", "-s", help="ESI scope to request (can be used multiple times)"
        ),
    ] = None,
) -> None:
    """Authenticate a new character.

    Opens a web browser for OAuth2 authentication flow and saves the
    resulting token for future use.
    """
    if scopes is None:
        scopes = ["esi-characters.read_character.v1"]

    console.print(
        f"[blue]Starting authentication for scopes:[/blue] {', '.join(scopes)}"
    )

    try:
        # Run the authentication flow
        character_token = asyncio.run(api.authenticate_character(scopes))

        console.print(
            f"[green]✓[/green] Successfully authenticated character: [bold]{character_token.character_name}[/bold]"
        )
        console.print(f"Character ID: {character_token.character_id}")
        console.print(f"Expires: {character_token.expires_at}")

    except AuthenticationError as e:
        console.print(f"[red]Authentication failed:[/red] {e}")
        raise typer.Exit(1)
    except TokenStorageError as e:
        console.print(f"[red]Failed to save token:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def list() -> None:
    """List all authenticated characters."""
    try:
        characters = api.list_characters()

        if not characters:
            console.print("[yellow]No authenticated characters found.[/yellow]")
            console.print(
                "Use '[bold]esi-auth auth[/bold]' to authenticate a character."
            )
            return

        # Create a rich table
        table = Table(title="Authenticated Characters")
        table.add_column("Character ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="magenta")
        table.add_column("Status", justify="center")
        table.add_column("Expires", style="yellow")
        table.add_column("Scopes", style="blue")

        for token in characters:
            # Determine status
            if token.is_expired():
                status = "[red]Expired[/red]"
            elif token.needs_refresh():
                status = "[yellow]Needs Refresh[/yellow]"
            else:
                status = "[green]Valid[/green]"

            # Format expiry time
            expires_str = token.expires_at.format_common_iso()

            # Format scopes
            scopes_str = ", ".join(token.scopes) if token.scopes else "None"
            if len(scopes_str) > 40:
                scopes_str = scopes_str[:37] + "..."

            table.add_row(
                str(token.character_id),
                token.character_name,
                status,
                expires_str,
                scopes_str,
            )

        console.print(table)

    except TokenStorageError as e:
        console.print(f"[red]Failed to load characters:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def refresh(
    character_id: Annotated[
        int | None, typer.Argument(help="Character ID to refresh (optional)")
    ] = None,
    all_expired: Annotated[
        bool, typer.Option("--all", help="Refresh all expired tokens")
    ] = False,
) -> None:
    """Refresh character access tokens.

    If no character ID is specified and --all is not used, refreshes all
    tokens that are expired or close to expiring.
    """
    try:
        if character_id:
            # Refresh specific character
            token = api.get_character(character_id)
            if not token:
                console.print(f"[red]Character {character_id} not found.[/red]")
                raise typer.Exit(1)

            console.print(f"[blue]Refreshing token for:[/blue] {token.character_name}")

            refreshed_token = asyncio.run(api.refresh_token(token))
            console.print(f"[green]✓[/green] Token refreshed successfully")
            console.print(f"New expiry: {refreshed_token.expires_at}")

        elif all_expired:
            # Refresh all expired tokens
            console.print("[blue]Refreshing all expired tokens...[/blue]")
            results = asyncio.run(api.refresh_expired_tokens())

            if not results:
                console.print("[green]No tokens needed refreshing.[/green]")
                return

            successful = 0
            for char_id, result in results.items():
                if isinstance(result, Exception):
                    console.print(f"[red]✗[/red] Failed to refresh {char_id}: {result}")
                else:
                    console.print(
                        f"[green]✓[/green] Refreshed: {result.character_name}"
                    )
                    successful += 1

            console.print(
                f"[blue]Refreshed {successful}/{len(results)} tokens successfully.[/blue]"
            )

        else:
            # Default: refresh tokens that need it (with buffer)
            console.print("[blue]Refreshing tokens that need it...[/blue]")
            results = asyncio.run(api.refresh_expired_tokens(buffer_minutes=5))

            if not results:
                console.print("[green]No tokens need refreshing.[/green]")
                return

            successful = 0
            for char_id, result in results.items():
                if isinstance(result, Exception):
                    console.print(f"[red]✗[/red] Failed to refresh {char_id}: {result}")
                else:
                    console.print(
                        f"[green]✓[/green] Refreshed: {result.character_name}"
                    )
                    successful += 1

            console.print(
                f"[blue]Refreshed {successful}/{len(results)} tokens successfully.[/blue]"
            )

    except TokenRefreshError as e:
        console.print(f"[red]Token refresh failed:[/red] {e}")
        raise typer.Exit(1)
    except TokenStorageError as e:
        console.print(f"[red]Storage error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def remove(
    character_id: Annotated[int, typer.Argument(help="Character ID to remove")],
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Skip confirmation")
    ] = False,
) -> None:
    """Remove a character from authentication storage."""
    try:
        # Check if character exists
        token = api.get_character(character_id)
        if not token:
            console.print(f"[red]Character {character_id} not found.[/red]")
            raise typer.Exit(1)

        # Confirm removal unless forced
        if not force:
            confirm = typer.confirm(
                f"Remove character '{token.character_name}' ({character_id})?"
            )
            if not confirm:
                console.print("[yellow]Operation cancelled.[/yellow]")
                return

        # Remove the character
        removed = api.remove_character(character_id)

        if removed:
            console.print(f"[green]✓[/green] Removed character: {token.character_name}")
        else:
            console.print(f"[red]Failed to remove character {character_id}[/red]")
            raise typer.Exit(1)

    except TokenStorageError as e:
        console.print(f"[red]Storage error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def validate(
    character_id: Annotated[
        int | None, typer.Argument(help="Character ID to validate (optional)")
    ] = None,
) -> None:
    """Validate character tokens by testing API access."""
    try:
        if character_id:
            # Validate specific character
            token = api.get_character(character_id)
            if not token:
                console.print(f"[red]Character {character_id} not found.[/red]")
                raise typer.Exit(1)

            console.print(f"[blue]Validating token for:[/blue] {token.character_name}")

            is_valid = asyncio.run(api.validate_token(token))
            if is_valid:
                console.print(f"[green]✓[/green] Token is valid")
            else:
                console.print(f"[red]✗[/red] Token is invalid")
                raise typer.Exit(1)

        else:
            # Validate all characters
            characters = api.list_characters()
            if not characters:
                console.print("[yellow]No characters to validate.[/yellow]")
                return

            console.print("[blue]Validating all character tokens...[/blue]")

            valid_count = 0
            for token in characters:
                is_valid = asyncio.run(api.validate_token(token))
                if is_valid:
                    console.print(f"[green]✓[/green] {token.character_name}: Valid")
                    valid_count += 1
                else:
                    console.print(f"[red]✗[/red] {token.character_name}: Invalid")

            console.print(
                f"[blue]{valid_count}/{len(characters)} tokens are valid.[/blue]"
            )

    except TokenStorageError as e:
        console.print(f"[red]Storage error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def info(
    character_id: Annotated[int, typer.Argument(help="Character ID to get info for")],
) -> None:
    """Get detailed character information from ESI."""
    try:
        token = api.get_character(character_id)
        if not token:
            console.print(f"[red]Character {character_id} not found.[/red]")
            raise typer.Exit(1)

        console.print(
            f"[blue]Getting character info for:[/blue] {token.character_name}"
        )

        char_info = asyncio.run(api.get_character_info(token))

        # Create info table
        table = Table(title=f"Character Information: {char_info.name}")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Character ID", str(char_info.character_id))
        table.add_row("Name", char_info.name)
        table.add_row("Description", char_info.description or "None")
        table.add_row("Corporation ID", str(char_info.corporation_id))
        table.add_row(
            "Alliance ID",
            str(char_info.alliance_id) if char_info.alliance_id else "None",
        )
        table.add_row("Birthday", char_info.birthday.strftime("%Y-%m-%d"))
        table.add_row("Gender", char_info.gender)
        table.add_row("Race ID", str(char_info.race_id))
        table.add_row("Bloodline ID", str(char_info.bloodline_id))
        table.add_row("Ancestry ID", str(char_info.ancestry_id))
        table.add_row(
            "Security Status",
            f"{char_info.security_status:.2f}" if char_info.security_status else "None",
        )

        console.print(table)

    except AuthenticationError as e:
        console.print(f"[red]Authentication error:[/red] {e}")
        console.print(
            "[yellow]Tip:[/yellow] Try refreshing the token with '[bold]esi-auth refresh {character_id}[/bold]'"
        )
        raise typer.Exit(1)
    except TokenStorageError as e:
        console.print(f"[red]Storage error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def backup(
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Backup file path")
    ] = None,
) -> None:
    """Create a backup of all character tokens."""
    try:
        backup_path = api.backup_characters(output)
        console.print(f"[green]✓[/green] Backup created: [bold]{backup_path}[/bold]")

    except TokenStorageError as e:
        console.print(f"[red]Backup failed:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def restore(
    backup_file: Annotated[Path, typer.Argument(help="Path to backup file")],
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Skip confirmation")
    ] = False,
) -> None:
    """Restore character tokens from a backup file."""
    try:
        if not backup_file.exists():
            console.print(f"[red]Backup file does not exist:[/red] {backup_file}")
            raise typer.Exit(1)

        # Confirm restoration unless forced
        if not force:
            current_chars = api.list_characters()
            if current_chars:
                console.print(
                    f"[yellow]Warning:[/yellow] This will replace {len(current_chars)} existing characters."
                )

            confirm = typer.confirm(f"Restore from backup '{backup_file}'?")
            if not confirm:
                console.print("[yellow]Operation cancelled.[/yellow]")
                return

        api.restore_characters(backup_file)
        console.print(
            f"[green]✓[/green] Successfully restored from backup: [bold]{backup_file}[/bold]"
        )

        # Show restored characters
        characters = api.list_characters()
        console.print(f"[blue]Restored {len(characters)} characters.[/blue]")

    except TokenStorageError as e:
        console.print(f"[red]Restore failed:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def config() -> None:
    """Show current configuration settings."""
    settings = get_settings()

    table = Table(title="ESI Auth Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="white")

    table.add_row(
        "Client ID",
        settings.client_id[:8] + "..."
        if len(settings.client_id) > 8
        else settings.client_id,
    )
    table.add_row("App Name", settings.app_name)
    table.add_row("App Directory", str(settings.app_dir))
    table.add_row("Token File", str(settings.token_file_path))
    table.add_row("Callback URL", settings.callback_url)
    table.add_row("ESI Base URL", settings.esi_base_url)
    table.add_row("SSO Base URL", settings.sso_base_url)

    console.print(table)


if __name__ == "__main__":
    app()
