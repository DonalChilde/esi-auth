"""Commands for showing the status of the Esi Auth configuration."""

from typing import cast

import typer
from rich.console import Console
from rich.text import Text

from esi_auth import __app_name__, __version__
from esi_auth.cli.helpers import EsiAuthSettings

app = typer.Typer(no_args_is_help=True)


@app.command()
def version():
    """Show the version of esi-auth."""
    console = Console()
    console.print(Text(f"{__app_name__} v{__version__}"))


@app.command()
def status(ctx: typer.Context):
    """Show the esi-auth CLI configuration settings."""
    console = Console()
    console.rule(Text("esi-auth CLI Configuration Information"))
    settings = ctx.obj["esi-auth-settings"]
    settings = cast(EsiAuthSettings, settings)
    console.print(settings)
