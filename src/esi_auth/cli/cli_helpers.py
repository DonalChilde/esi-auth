"""Helper functions for CLI commands."""

from pathlib import Path

import typer
from rich.console import Console
from rich.text import Text

from esi_auth.cli import STYLE_ERROR
from esi_auth.esi_auth import EsiAuth
from esi_auth.settings import env_example


def check_user_agent_setup(ctx: typer.Context) -> None:
    """Check that the application is properly set up.

    This function is called before executing commands that require
    user-agent information to be configured.
    """
    console = Console()
    esi_auth = esi_auth_getter(ctx)
    if any(
        [
            esi_auth.user_agent_settings.character_name == "Unknown",
            esi_auth.user_agent_settings.user_email == "Unknown",
            esi_auth.user_agent_settings.user_app_name == "Unknown",
            esi_auth.user_agent_settings.user_app_version == "Unknown",
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
            "[bold yellow]Configure your User-Agent settings in the .env file.[/bold yellow]"
        )
        raise typer.Exit(code=1)


def esi_auth_getter(ctx: typer.Context) -> EsiAuth:
    """Retrieve the EsiAuth instance from the CLI context.

    Args:
        ctx: The Typer context containing the EsiAuth instance.

    Returns:
        The EsiAuth instance.

    Raises:
        typer.Exit: If the EsiAuth instance is not initialized.
    """
    esi_auth: EsiAuth = ctx.obj.esi_auth
    if esi_auth is None:  # pyright: ignore[reportUnnecessaryComparison]
        console = Console()
        console.print(
            Text("[bold red]Auth store is not initialized.[/bold red]"),
            style=STYLE_ERROR,
        )
        raise typer.Exit(code=1)
    return esi_auth


def ensure_env_example(file_path: Path) -> bool:
    """Ensure that a file exists at the file_path.

    If no file exists, make an example .env file.

    Args:
        file_path: The path to the file to check or create.

    Returns:
        True if the file was created, False if it already existed.
    """
    if not file_path.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(env_example())
        return False
    return True
