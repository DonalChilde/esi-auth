from dataclasses import dataclass
from importlib import metadata
from time import perf_counter_ns
from typing import Annotated

import typer
from rich.console import Console

from esi_auth.settings import get_settings
from esi_auth.storage import TokenStorageProtocol, TokenStoreJson

from .auth_cli import app as auth_app
from .token_store_cli import app as token_store_app
from .util_cli import app as util_app

# TODO import SETTINGS
app = typer.Typer(no_args_is_help=True)


app.add_typer(auth_app, name="character", help="Manage authorized characters.")
app.add_typer(token_store_app, name="token-store", help="Manage token storage.")
app.add_typer(util_app, name="util", help="Utility commands.")


@dataclass
class CliConfig:
    app_name: str = "NOT SET"
    version: str = "NOT SET"
    start_time: int = perf_counter_ns()
    debug: bool = False
    verbosity: int = 1
    silent: bool = False
    token_store: TokenStorageProtocol | None = None

    def __repr__(self) -> str:
        return (
            f"CliConfig("
            f"app_name={self.app_name!r}, "
            f"version={self.version!r}, "
            f"start_time={self.start_time!r}, "
            f"debug={self.debug!r}, "
            f"verbosity={self.verbosity!r}, "
            f"silent={self.silent!r}, "
            f"token_store={self.token_store!r}"
            ")"
        )

    def __str__(self) -> str:
        return (
            f"CliConfig:\n"
            f" \tapp_name={self.app_name}\n"
            f" \tversion={self.version}\n"
            f" \tstart_time={self.start_time}\n"
            f" \tdebug={self.debug}\n"
            f" \tverbosity={self.verbosity}\n"
            f" \tsilent={self.silent}\n"
            f" \ttoken_store={self.token_store}"
        )


@app.callback(invoke_without_command=True)
def default_options(
    ctx: typer.Context,
    debug: Annotated[bool, typer.Option(help="Enable debug output.")] = False,
    verbosity: Annotated[int, typer.Option("-v", help="Verbosity.", count=True)] = 1,
    silent: Annotated[
        bool,
        typer.Option(help="Enable silent mode. Only results and errors will be shown."),
    ] = False,
):
    """Esi Auth Command Line Interface.

    Insert pithy saying here
    """
    init_config(ctx, debug=debug, verbosity=verbosity, silent=silent)

    # if ctx.obj.schema_store:
    #     schema_msg = "Schema loaded successfully."
    # else:
    #     schema_msg = "No schema found. Try `esi-link schema update`."

    # welcome = f"""
    # Welcome to Esi Link! Your CLI interface to the Eve Online ESI api.
    # Application data located at {CONFIG.app_dir}
    # Schema status: {schema_msg}
    # """
    # if not ctx.obj.silent:
    #     typer.echo(welcome)

    if ctx.obj.verbosity > 1:
        typer.echo("CLI configuration:")
        # TODO rework this with rich.
        # typer.echo(f"{indent_lines(str(ctx.obj), indent=2)}")
        typer.echo("App configuration:")
        # typer.echo(f"{indent_lines(str(CONFIG), indent=2)}")


def init_config(
    ctx: typer.Context, *, debug: bool, verbosity: int, silent: bool
) -> None:
    """Initialize configuration based on CLI options."""
    start = perf_counter_ns()
    settings = get_settings()
    token_path = settings.token_store_dir / settings.token_file_name
    config = CliConfig(
        app_name=settings.app_name,
        version=metadata.version("esi-auth"),
        start_time=start,
        debug=debug,
        verbosity=verbosity,
        silent=silent,
        token_store=TokenStoreJson(token_path),
    )
    ctx.obj = config


@app.command()
def version(ctx: typer.Context):
    """Display version information."""
    console = Console()
    console.print(f"{ctx.obj.app_name} version {ctx.obj.version}")
