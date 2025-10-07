"""Helper functions for CLI commands."""

import typer
from rich.console import Console

from esi_auth.settings import get_settings


def check_user_agent_setup(ctx: typer.Context) -> None:
    """Check that the application is properly set up.

    This function is called before executing commands that require
    user-agent information to be configured.
    """
    settings = get_settings()
    if any(
        [
            settings.character_name == "Unknown",
            settings.user_email == "Unknown",
            settings.user_app_name == "Unknown",
            settings.user_app_version == "Unknown",
        ]
    ):
        console = Console()
        console.print(
            "[bold yellow]Warning: User-Agent information is not fully configured."
        )
        console.print(
            "[bold yellow]Please update your .env file with character name, email, app name, and app version."
        )
        console.print(f"[bold yellow]App directory: {settings.app_dir}")
        raise typer.Exit(code=1)
