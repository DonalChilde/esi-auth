"""CLI commands for managing stored EVE Online application credentials."""

import json
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from esi_auth.credential_storage import CredentialStoreJson
from esi_auth.models import EveCredentials
from esi_auth.settings import get_settings

app = typer.Typer(
    help="Manage stored EVE Online application credentials.", no_args_is_help=True
)


@app.command("list", help="List all stored application credentials.")
def list_credentials(ctx: typer.Context):
    """List all stored application credentials in a table format."""
    settings = get_settings()
    console = Console()
    table = Table(title="Stored EVE Online Application Credentials")

    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Alias", style="magenta")
    table.add_column("Client ID", style="green")
    table.add_column("Callback URL", style="yellow")
    table.add_column("Scopes", style="white")

    # This is a placeholder for actual credential retrieval logic
    credential_store = CredentialStoreJson(
        settings.credential_store_dir / settings.credential_file_name
    )
    credentials = credential_store.list_credentials()

    for cred in credentials:
        table.add_row(
            cred.name,
            cred.alias or "",
            cred.client_id,
            cred.callback_url,
            ", ".join(cred.scopes),
        )

    console.print(table)


@app.command("add", help="Add new application credentials from file.")
def add_credentials(
    ctx: typer.Context,
    file_path: Annotated[
        str, typer.Argument(help="Path to the JSON file with credentials")
    ],
    alias: Annotated[
        str | None,
        typer.Option(
            "-a",
            "--client-alias",
            help="Alias for the application. If not provided, it will be generated from the application name.",
        ),
    ] = None,
):
    """Add new application credentials from a JSON file."""
    settings = get_settings()
    console = Console()

    try:
        with open(file_path) as f:
            cred_json = json.load(f)
            if alias is None:
                alias = cred_json["name"].lower().replace(" ", "_")
            credentials = EveCredentials(
                name=cred_json["name"],
                alias=alias,
                client_id=cred_json["clientId"],
                client_secret=cred_json["clientSecret"],
                callback_url=cred_json["callbackUrl"],
                scopes=cred_json["scopes"],
            )

            credential_store = CredentialStoreJson(
                settings.credential_store_dir / settings.credential_file_name
            )
            credential_store.add_credentials(credentials)
            console.print(
                f"[green]Successfully added credentials for {credentials.name}[/green]"
            )
    except Exception as e:
        console.print(f"[red]Error adding credentials: {e}[/red]")


@app.command("remove", help="Remove application credentials by client ID.")
def remove_credentials(ctx: typer.Context, client_id: str):
    """Remove application credentials by client ID."""
    settings = get_settings()
    console = Console()

    try:
        credential_store = CredentialStoreJson(
            settings.credential_store_dir / settings.credential_file_name
        )
        credential_store.remove_credentials(client_id)
        console.print(
            f"[green]Successfully removed credentials for client ID {client_id}[/green]"
        )
    except Exception as e:
        console.print(f"[red]Error removing credentials: {e}[/red]")


@app.command("clear", help="Clear all stored application credentials.")
def clear_credentials(ctx: typer.Context):
    """Clear all stored application credentials."""
    settings = get_settings()
    console = Console()

    try:
        file_path = settings.credential_store_dir / settings.credential_file_name
        file_path.unlink(missing_ok=True)
        console.print("[green]Successfully cleared all credentials[/green]")
    except Exception as e:
        console.print(f"[red]Error clearing credentials: {e}[/red]")
