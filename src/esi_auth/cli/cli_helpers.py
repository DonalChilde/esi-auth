"""Helper functions for CLI commands."""

import typer
from rich.console import Console
from rich.text import Text

from esi_auth.cli import STYLE_ERROR
from esi_auth.esi_auth import EsiAuth


def check_user_agent_setup(ctx: typer.Context) -> None:
    """Check that the application is properly set up.

    This function is called before executing commands that require
    user-agent information to be configured.
    """
    console = Console()
    auth_store: EsiAuth = ctx.obj.auth_store  # type: ignore
    if auth_store is None:  # pyright: ignore[reportUnnecessaryComparison]
        console.print("[bold red]Auth store is not initialized.[/bold red]")
        raise typer.Exit(code=1)
    if any(
        [
            auth_store.store.user_agent.character_name == "Unknown",
            auth_store.store.user_agent.user_email == "Unknown",
            auth_store.store.user_agent.user_app_name == "Unknown",
            auth_store.store.user_agent.user_app_version == "Unknown",
        ]
    ):
        console = Console()
        console.print(
            "[bold yellow]Warning: User-Agent information is not fully configured."
        )
        console.print(
            "[bold yellow]You must set character name, user email, your app name, and your app version."
        )
        console.print(f"[bold yellow]Before making network requests.")
        console.print(
            "[bold yellow]Use the 'esi-auth user-agent set' command to configure these fields.[/bold yellow]"
        )
        raise typer.Exit(code=1)


def get_auth_store(ctx: typer.Context) -> EsiAuth:
    """Retrieve the EsiAuth instance from the CLI context.

    Args:
        ctx: The Typer context containing the EsiAuth instance.

    Returns:
        The EsiAuth instance.

    Raises:
        typer.Exit: If the EsiAuth instance is not initialized.
    """
    auth_store: EsiAuth = ctx.obj.auth_store
    if auth_store is None:  # pyright: ignore[reportUnnecessaryComparison]
        console = Console()
        console.print(
            Text("[bold red]Auth store is not initialized.[/bold red]"),
            style=STYLE_ERROR,
        )
        raise typer.Exit(code=1)
    return auth_store
