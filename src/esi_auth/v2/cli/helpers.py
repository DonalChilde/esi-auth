"""Helper classes and functions for the ESI Auth CLI."""

import json
from dataclasses import dataclass
from pathlib import Path

from esi_auth.v2.authenticate_esi import OauthMetadata


@dataclass(slots=True)
class EsiAuthSettings:
    """Settings for the ESI Auth CLI.

    These settings are passed through the Typer context to all esi-auth commands, and are used
    to configure the application. This is to ensure that all commands have access to the same
    configuration and can operate consistently, and allow for easy reuse of the typer commands
    in other apps.

    The context.obj should be a dict, and the settings should be stored under the
    "esi-auth-settings" key.
    """

    credentials_dir: Path
    tokens_dir: Path
    oauth_settings_file: Path
    oauth_settings_url: str
    auth_server_timeout: int


def load_oauth_metadata(settings: EsiAuthSettings) -> OauthMetadata:
    """Load the OAuth metadata from the settings file."""
    if settings.oauth_settings_file.exists():
        data = json.loads(settings.oauth_settings_file.read_text())
        return OauthMetadata(**data)
    else:
        raise FileNotFoundError(
            f"OAuth settings file not found at {settings.oauth_settings_file}"
        )
