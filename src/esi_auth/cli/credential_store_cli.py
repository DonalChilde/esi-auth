"""CLI commands for managing stored EVE Online application credentials."""

import json
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from esi_auth.cli.cli_helpers import get_auth_store
from esi_auth.esi_auth import EveCredentials

app = typer.Typer(
    help="Manage stored EVE Online application credentials.", no_args_is_help=True
)


@app.command("list", help="List all stored application credentials.")
def list_credentials(ctx: typer.Context):
    """List all stored application credentials in a table format."""
    # settings = get_settings()
    console = Console()
    console.rule(
        "[bold blue]List Stored EVE Online Application Credentials[/bold blue]"
    )
    table = Table(title="Stored EVE Online Application Credentials")

    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Alias", style="magenta")
    table.add_column("Client ID", style="green")
    table.add_column("Callback URL", style="yellow")
    table.add_column("Scopes", style="white")

    auth_store = get_auth_store(ctx)
    credentials = auth_store.list_credentials()

    for cred in credentials:
        table.add_row(
            cred.name,
            cred.client_alias or "",
            str(cred.client_id),
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
    console = Console()
    console.rule("[bold blue]Add Stored EVE Online Application Credentials[/bold blue]")

    try:
        with open(file_path) as f:
            cred_json = json.load(f)
            if alias is None:
                alias = cred_json["name"].lower().replace(" ", "_")
            credentials = EveCredentials(
                name=cred_json["name"],
                client_alias=alias,
                client_id=cred_json["clientId"],
                client_secret=cred_json["clientSecret"],
                callback_url=cred_json["callbackUrl"],
                scopes=cred_json["scopes"],
            )

            auth_store = get_auth_store(ctx)
            auth_store.store_credentials(credentials)
            console.print(
                f"[green]Successfully added credentials for {credentials.name}[/green]"
            )
    except Exception as e:
        console.print(f"[bold red]Error adding credentials: {e}[/red]")


@app.command("remove", help="Remove application credentials by client ID.")
def remove_credentials(ctx: typer.Context, client_id: str):
    """Remove application credentials by client ID."""
    console = Console()
    console.rule(
        "[bold blue]Remove Stored EVE Online Application Credentials[/bold blue]"
    )

    try:
        auth_store = get_auth_store(ctx)
        credentials = auth_store.get_credentials_from_id(client_id)
        if credentials is None:
            console.print(f"[red]No credentials found for client ID {client_id}[/red]")
            raise typer.Exit(code=1)
        auth_store.remove_credentials(credentials)
        console.print(
            f"[green]Successfully removed credentials for client ID {client_id}[/green]"
        )
    except Exception as e:
        console.print(f"[bold red]Error removing credentials: {e}[/red]")
