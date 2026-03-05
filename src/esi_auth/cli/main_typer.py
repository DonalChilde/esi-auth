"""Main entry point for the Esi Auth CLI using Typer."""

import logging

import typer

from esi_auth import __app_name__, __version__
from esi_auth.cli.app_credentials import app as app_credentials_app
from esi_auth.cli.auth_token import app as auth_token_app
from esi_auth.cli.config_info import app as config_info_app
from esi_auth.cli.helpers import EsiAuthSettings
from esi_auth.cli.oauth_settings import app as oauth_settings_app
from esi_auth.logging_config import setup_logging
from esi_auth.settings import (
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
# Commands at the top level for showing configuration information, etc.
app.add_typer(config_info_app)


@app.callback(invoke_without_command=True)
def default_options(ctx: typer.Context):
    """Esi Auth Command Line Interface.

    Manage ESI authentication tokens for EVE Online applications. This CLI allows you
    to configure your application credentials, manage OAuth settings, and handle
    authentication tokens for your EVE Online applications.
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
