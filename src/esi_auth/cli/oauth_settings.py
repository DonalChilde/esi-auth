import asyncio
import json
from typing import Any, cast

import aiohttp
import typer
from rich.console import Console
from rich.json import JSON

from esi_auth.cli.helpers import EsiAuthSettings

app = typer.Typer(no_args_is_help=True)


@app.command()
def show(ctx: typer.Context):
    """Show the current ESI Auth settings."""
    settings = ctx.obj["esi-auth-settings"]
    settings = cast(EsiAuthSettings, settings)
    console = Console()
    oauth_path = settings.oauth_settings_file
    if oauth_path.exists():
        console.print(f"OAuth settings file found at {oauth_path}")
        console.print(JSON(oauth_path.read_text()))
    else:
        console.print(f"OAuth settings file not found at {oauth_path}")


@app.command()
def fetch(ctx: typer.Context):
    """Fetch the current OAuth settings from the ESI auth server and save them to the settings file."""
    settings = ctx.obj["esi-auth-settings"]
    settings = cast(EsiAuthSettings, settings)
    console = Console()
    console.print(f"Fetching OAuth settings from {settings.oauth_settings_url}")

    async def fetch_oauth_settings() -> dict[str, Any]:
        async with aiohttp.ClientSession() as session:
            async with session.get(settings.oauth_settings_url) as response:
                response.raise_for_status()
                data = await response.json()
                return data

    try:
        data = asyncio.run(fetch_oauth_settings())
    except Exception as e:
        console.print(f"[red]Error fetching OAuth settings: {e}[/red]")
        raise typer.Exit(code=1) from e
    console.print("Fetched OAuth settings:")
    console.print(JSON.from_data(data))
    console.print("")
    settings.oauth_settings_file.write_text(json.dumps(data, indent=2))
    console.print(f"Saved OAuth settings to {settings.oauth_settings_file}")
