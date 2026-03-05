"""Main entry point for the Esi Auth CLI using Typer."""

import logging

import typer
from rich.console import Console
from rich.text import Text

from esi_auth.v2 import __app_name__, __version__
from esi_auth.v2.cli.app_credentials import app as app_credentials_app
from esi_auth.v2.cli.auth_token import app as auth_token_app
from esi_auth.v2.cli.helpers import EsiAuthSettings
from esi_auth.v2.cli.oauth_settings import app as oauth_settings_app
from esi_auth.v2.logging_config import setup_logging
from esi_auth.v2.settings import (
    get_settings,
)

logger = logging.getLogger(__name__)
app = typer.Typer(no_args_is_help=True)

app.add_typer(
    oauth_settings_app, name="oauth", help="Commands for managing OAuth settings."
)
app.add_typer(
    app_credentials_app, name="creds", help="Commands for managing app credentials."
)
app.add_typer(
    auth_token_app, name="tokens", help="Commands for managing authentication tokens."
)


@app.callback(invoke_without_command=True)
def default_options(ctx: typer.Context):
    """Esi Auth Command Line Interface.

    Insert pithy saying here
    """
    settings = get_settings()
    setup_logging(log_dir=settings.log_dir)
    logger.info(f"Starting {__app_name__} v{__version__}")
    settings_object = EsiAuthSettings(
        credentials_file=settings.app_credentials_file,
        tokens_dir=settings.tokens_dir,
        oauth_settings_file=settings.oauth_settings_file,
        oauth_settings_url=settings.oauth_settings_url,
        auth_server_timeout=settings.auth_server_timeout,
    )
    ctx.obj = {"esi-auth-settings": settings_object}


@app.command()
def version():
    """Show the version of Esi Auth."""
    console = Console()
    console.print(Text(f"{__app_name__} v{__version__}"))


@app.command()
def status(ctx: typer.Context):
    """Show the status of the Esi Auth configuration."""
    console = Console()
    console.rule(Text("esi-auth Cli Configuration Information"))
    settings = get_settings()
    console.print(settings)
