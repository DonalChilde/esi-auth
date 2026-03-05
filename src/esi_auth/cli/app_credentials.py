"""CLI commands for managing app credentials."""

from pathlib import Path
from typing import Annotated, cast

import typer
from rich.console import Console
from rich.json import JSON
from rich.prompt import Confirm

from esi_auth.cli.helpers import EsiAuthSettings, load_credentials
from esi_auth.models import EveAppCredentials

app = typer.Typer(no_args_is_help=True)


@app.command()
def show(ctx: typer.Context):
    """Show the stored app credentials."""
    settings = ctx.obj["esi-auth-settings"]
    settings = cast(EsiAuthSettings, settings)
    console = Console()
    credentials = load_credentials(settings, console)
    console.print(JSON.from_data(credentials.model_dump(mode="json")))


@app.command()
def add(
    ctx: typer.Context,
    file_path: Annotated[
        Path, typer.Argument(help="Path to the app credential JSON file to add.")
    ],
):
    """Add a new app credential.

    Expects a JSON file in the format of EveAppCredentials. The file is read
    and validated, and then stored in the app.
    """
    settings = ctx.obj["esi-auth-settings"]
    settings = cast(EsiAuthSettings, settings)
    console = Console()
    if settings.credentials_file.exists():
        console.print(
            f"[red]Warning: App credentials file already exists at {settings.credentials_file}. "
            "It must be removed first.[/red]"
        )
        raise typer.Exit(code=1)
    if not file_path.is_file():
        console.print(f"[red]File not found: {file_path}[/red]")
        raise typer.Exit(code=1)
    try:
        credential = EveAppCredentials.model_validate_json(file_path.read_text())
    except Exception as e:
        console.print(f"[red]Error reading credential file: {e}[/red]")
        raise typer.Exit(code=1) from e
    settings.credentials_file.parent.mkdir(parents=True, exist_ok=True)
    settings.credentials_file.write_text(credential.model_dump_json(indent=2))
    console.print(f"App credentials added to {settings.credentials_file}")


@app.command()
def remove(ctx: typer.Context):
    """Remove the stored app credentialsand associated token files."""
    settings = ctx.obj["esi-auth-settings"]
    settings = cast(EsiAuthSettings, settings)
    console = Console()
    if not settings.credentials_file.exists():
        console.print(
            f"[red]App credentials file not found at {settings.credentials_file}[/red]"
        )
        raise typer.Exit(code=1)
    is_confirmed = Confirm.ask(
        f"Are you sure you want to remove the app credentials at {settings.credentials_file}?\n"
        f"This will also remove any associated token files in {settings.tokens_dir}."
    )
    if not is_confirmed:
        console.print("Aborting app credential removal.")
        raise typer.Exit()
    try:
        settings.credentials_file.unlink()
        console.print(f"App credentials removed from {settings.credentials_file}")
    except Exception as e:
        console.print(f"[red]Error removing app credentials: {e}[/red]")
        raise typer.Exit(code=1) from e
    # Remove associated token files
    token_files = list(settings.tokens_dir.glob("*-token.json"))
    for token_file in token_files:
        try:
            token_file.unlink()
            console.print(f"Associated token file removed: {token_file}")
        except Exception as e:
            console.print(f"[red]Error removing token file {token_file}: {e}[/red]")
