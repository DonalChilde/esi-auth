from dataclasses import dataclass
from time import perf_counter_ns
from typing import Annotated

import typer

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
    start_time: int = perf_counter_ns()
    debug: bool = False
    verbosity: int = 1
    silent: bool = False

    def __repr__(self) -> str:
        return (
            f"CliConfig("
            f"app_name={self.app_name}, "
            f"start_time={self.start_time}, "
            f"debug={self.debug}, "
            f"verbosity={self.verbosity}, "
            f"silent={self.silent}"
            ")"
        )

    def __str__(self) -> str:
        return (
            f"CliConfig:\n"
            f" app_name={self.app_name}\n"
            f" start_time={self.start_time}\n"
            f" debug={self.debug}\n"
            f" verbosity={self.verbosity}\n"
            f" silent={self.silent}"
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
    ctx.ensure_object(CliConfig)
    ctx.obj.start_time = perf_counter_ns()
    ctx.obj.debug = debug
    ctx.obj.verbosity = verbosity
    ctx.obj.silent = silent
    init_config(ctx)

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


def init_config(ctx: typer.Context) -> None:
    """Initialize configuration based on CLI options."""
    pass
