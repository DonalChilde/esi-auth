"""Utility CLI commands for esi_auth."""

import json
from pathlib import Path
from typing import Annotated, TypedDict

import typer
from rich.console import Console

from esi_auth.auth_helpers import fetch_oauth_metadata_sync
from esi_auth.helpers import get_user_agent
from esi_auth.models import CallbackUrl
from esi_auth.settings import get_settings

app = typer.Typer(no_args_is_help=True)


class AppConfig(TypedDict):
    name: str
    description: str
    clientId: str
    clientSecret: str
    callbackUrl: str
    scopes: list[str]


@app.command()
def parse_app_json(
    file_in: Annotated[Path, typer.Argument(..., exists=True, dir_okay=False)],
    file_out: Annotated[
        Path, typer.Argument(..., dir_okay=False, writable=True)
    ] = Path(".app-example.env"),
):
    """Parse the json representation of the app configuration from Eve Online Developers.

    You can manage your applications at https://developers.eveonline.com/applications,
    and you can download the app configuration as a JSON file.
    This command will parse the app configuration from the JSON file,
    and print the relevant settings to be placed in the .env file.
    """
    console = Console()
    file_txt = file_in.read_text()
    app_config: AppConfig = json.loads(file_txt)
    console.rule(f"[bold green]App Configuration: {app_config['name']}")
    console.print(app_config)
    console.print()
    console.rule("[bold green]Environment Variables")
    callback_url = CallbackUrl.parse(app_config["callbackUrl"])

    env_lines = [
        f'CLIENT_ID="{app_config["clientId"]}"',
        f'CLIENT_SECRET="{app_config["clientSecret"]}"',
        "# Note: The scopes must be a string representing a JSON array of strings.",
        f"SCOPES='{json.dumps(app_config['scopes'])}'",
        f'CALLBACK_HOST="{callback_url.callback_host}"',
        f'CALLBACK_PORT="{callback_url.callback_port}"',
        f'CALLBACK_ROUTE="{callback_url.callback_route}"',
    ]
    text_out = "\n".join(env_lines) + "\n"
    console.print("# The following lines can be placed in the .env file:")
    console.print(text_out, no_wrap=True, crop=False, overflow="ignore")
    file_out.write_text(text_out)
    console.print(f"Wrote settings to {file_out.absolute()}")


@app.command()
def generate_example_env():
    """Generate an example .env file with placeholder values."""
    console = Console()
    raise NotImplementedError("This command is not yet implemented.")
    # TODO implement this command


@app.command()
def parse_oauth_metadata():
    """Fetch and display the OAuth2 metadata from EVE Online.

    Display the OAuth2 metadata from the EVE Online authorization server, and
    output the metadata fields in env file format.
    """
    console = Console()
    settings = get_settings()
    oauth_metadata = fetch_oauth_metadata_sync(
        url=settings.oauth2_authorization_metadata_url,
        user_agent=get_user_agent(),
    )
    console.rule("[bold green]OAuth2 Metadata")
    console.print(oauth_metadata)
    console.print()
    console.rule("[bold green]Environment Variables")
    console.print("# The following lines can be placed in the .env file:")
    env_lines = [
        f'OAUTH2_AUTHORIZATION_ENDPOINT="{oauth_metadata.get("authorization_endpoint", "Unknown")}"',
        f'OAUTH2_TOKEN_ENDPOINT="{oauth_metadata.get("token_endpoint", "Unknown")}"',
        f'OAUTH2_JWKS_URI="{oauth_metadata.get("jwks_uri", "Unknown")}"',
        f'OAUTH2_ISSUER="{oauth_metadata.get("issuer", "Unknown")}"',
    ]
    text_out = "\n".join(env_lines) + "\n"
    console.print(text_out, no_wrap=True, crop=False, overflow="ignore")
