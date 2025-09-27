import json
from pathlib import Path
from typing import Annotated, TypedDict

import typer
from rich.console import Console

from esi_auth.models import CallbackUrl

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
    console.print("The following lines can be placed in the .env file:")
    console.print(text_out, no_wrap=True)
