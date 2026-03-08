"""Helper classes and functions for the ESI Auth CLI."""

import json
from dataclasses import dataclass
from pathlib import Path

import typer
from rich.console import Console

from esi_auth.authenticator import Authenticator
from esi_auth.models import EveAppCredentials, OauthMetadata


@dataclass(slots=True)
class EsiAuthSettings:
    """Settings for the ESI Auth CLI.

    These settings are passed through the Typer context to all esi-auth commands, and are used
    to configure the application. This is to ensure that all commands have access to the same
    configuration and can operate consistently, and allow for easy reuse of the typer commands
    in other apps.

    The context.obj should be a dict, and the settings should be stored under the
    "esi-auth-settings" key. e.g. ctx.obj["esi-auth-settings"] = EsiAuthSettings(...)
    """

    credentials_file: Path
    tokens_dir: Path
    oauth_settings_file: Path
    oauth_settings_url: str
    auth_server_timeout: int


def load_oauth_metadata(settings: EsiAuthSettings, console: Console) -> OauthMetadata:
    """Load the OAuth metadata from the settings file."""
    if settings.oauth_settings_file.exists():
        try:
            data = json.loads(settings.oauth_settings_file.read_text())
            return OauthMetadata(**data)
        except Exception as e:
            console.print(f"[red]Error loading OAuth metadata: {e}[/red]")
            raise typer.Exit(code=1) from e
    else:
        console.print(
            f"[red]OAuth settings file not found at {settings.oauth_settings_file}[/red]"
        )
        raise typer.Exit(code=1)


def load_credentials(settings: EsiAuthSettings, console: Console) -> EveAppCredentials:
    """Load the app credentials from the settings file."""
    try:
        credentials = EveAppCredentials.model_validate_json(
            settings.credentials_file.read_text()
        )
        console.print(f"App credentials loaded from {settings.credentials_file}")
    except FileNotFoundError as e:
        console.print(
            f"[red]App credentials file not found at {settings.credentials_file}[/red]"
        )
        raise typer.Exit(code=1) from e
    except Exception as e:
        console.print(f"[red]Error reading app credentials: {e}[/red]")
        raise typer.Exit(code=1) from e
    return credentials


def config_authenticator(settings: EsiAuthSettings, console: Console) -> Authenticator:
    """Configure the Authenticator instance from the settings."""
    credentials = load_credentials(settings, console)

    try:
        oauth_metadata = load_oauth_metadata(settings, console)
    except Exception as e:
        console.print(f"[red]Error loading OAuth metadata: {e}[/red]")
        raise typer.Exit(code=1) from e

    authenticator = Authenticator.from_dict(
        client_id=credentials.clientId,
        scopes=credentials.scopes,
        callback_url=credentials.callbackUrl,
        config_dict=oauth_metadata,
    )
    return authenticator
