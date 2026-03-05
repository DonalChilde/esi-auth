"""CLI commands for managing app credentials."""

from pathlib import Path
from typing import Annotated, cast

import typer
from rich.console import Console
from rich.json import JSON

from esi_auth.v2.cli.helpers import EsiAuthSettings
from esi_auth.v2.models import AppCredentials, EveAppCredentials
from esi_auth.v2.simple_json_store import AppCredentialManager

app = typer.Typer(no_args_is_help=True)


@app.command()
def show(ctx: typer.Context):
    """Show the stored app credentials."""
    settings = ctx.obj["esi-auth-settings"]
    settings = cast(EsiAuthSettings, settings)
    console = Console()
    app_credentials_path = settings.credentials_dir
    manager = AppCredentialManager(app_credentials_path)
    credentials = manager.list_credentials()
    if not credentials:
        console.print(f"No app credentials found in {app_credentials_path}")
        return

    console.print(
        f"{len(credentials)} App credentials found in {app_credentials_path}:"
    )
    for credential in credentials:
        console.print(JSON.from_data(credential.model_dump(mode="json")))


@app.command()
def add(
    ctx: typer.Context,
    alias: Annotated[str, typer.Argument(help="Alias for the new app credential.")],
    file_path: Annotated[
        Path, typer.Argument(help="Path to the app credential JSON file to add.")
    ],
):
    """Add a new app credential.

    Expects a JSON file in the format of EveAppCredentials. The alias is used to identify
    the credential in the app credential manager, and should be unique. The file is read
    and validated, and then stored in the app credentials directory with a filename based
    on the alias.
    """
    settings = ctx.obj["esi-auth-settings"]
    settings = cast(EsiAuthSettings, settings)
    console = Console()
    if not file_path.is_file():
        console.print(f"[red]File not found: {file_path}[/red]")
        raise typer.Exit(code=1)
    try:
        credential = EveAppCredentials.model_validate_json(file_path.read_text())
    except Exception as e:
        console.print(f"[red]Error reading credential file: {e}[/red]")
        raise typer.Exit(code=1) from e

    app_credentials_path = settings.credentials_dir
    manager = AppCredentialManager(app_credentials_path)
    app_credentials = AppCredentials(alias=alias, credentials=credential)
    try:
        manager.add_credentials(app_credentials)
    except Exception as e:
        console.print(f"[red]Error adding credential: {e}[/red]")
        raise typer.Exit(code=1) from e
    console.print(f"Added app credential with alias '{alias}' from file {file_path}")
