"""Command line interface for esi-auth."""

import shutil
from dataclasses import dataclass
from importlib import metadata
from time import perf_counter_ns
from typing import Annotated

import typer
from rich.console import Console

from esi_auth.credential_storage import CredentialStoreJson
from esi_auth.settings import get_settings
from esi_auth.token_storage import TokenStoreJson

from .credential_store_cli import app as credentials_app
from .token_store_cli import app as token_store_app
from .util_cli import app as util_app
from .util_cli import example_env

app = typer.Typer(no_args_is_help=True)


app.add_typer(
    credentials_app, name="credentials", help="Manage application credentials."
)
app.add_typer(token_store_app, name="tokens", help="Manage token storage.")
app.add_typer(util_app, name="util", help="Utility commands.")


@dataclass
class CliConfig:
    app_name: str = "NOT SET"
    version: str = "NOT SET"
    start_time: int = perf_counter_ns()
    debug: bool = False
    verbosity: int = 1
    silent: bool = False

    def __repr__(self) -> str:
        """Return a string representation of the CLI configuration."""
        return (
            f"CliConfig("
            f"app_name={self.app_name!r}, "
            f"version={self.version!r}, "
            f"start_time={self.start_time!r}, "
            f"debug={self.debug!r}, "
            f"verbosity={self.verbosity!r}, "
            f"silent={self.silent!r}, "
            ")"
        )

    def __str__(self) -> str:
        """Return a user-friendly string representation of the CLI configuration."""
        return (
            f"CliConfig:\n"
            f" \tapp_name={self.app_name}\n"
            f" \tversion={self.version}\n"
            f" \tstart_time={self.start_time}\n"
            f" \tdebug={self.debug}\n"
            f" \tverbosity={self.verbosity}\n"
            f" \tsilent={self.silent}"
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
    console = Console()
    console.print("[bold]Welcome to esi-auth, a tool for managing EVE SSO tokens.")

    if ctx.obj.verbosity > 1:
        typer.echo("CLI configuration:")
        # TODO rework this with rich.
        # typer.echo(f"{indent_lines(str(ctx.obj), indent=2)}")
        typer.echo("App configuration:")
        # typer.echo(f"{indent_lines(str(CONFIG), indent=2)}")
    ensure_setup()


def init_config(
    ctx: typer.Context, *, debug: bool, verbosity: int, silent: bool
) -> None:
    """Initialize configuration based on CLI options."""
    start = perf_counter_ns()
    settings = get_settings()

    config = CliConfig(
        app_name=settings.app_name,
        version=metadata.version("esi-auth"),
        start_time=start,
        debug=debug,
        verbosity=verbosity,
        silent=silent,
    )
    ctx.obj = config


def ensure_setup():
    """Ensure that the application is properly set up."""
    settings = get_settings()
    settings.ensure_app_dir()
    token_path = settings.token_store_dir / settings.token_file_name
    if not token_path.is_file():
        TokenStoreJson.init_store(token_path)
    credentials_path = settings.credential_store_dir / settings.credential_file_name
    if not credentials_path.is_file():
        CredentialStoreJson.init_store(credentials_path)
    env_path = settings.app_dir / ".env"
    if not env_path.is_file():
        env_path.parent.mkdir(parents=True, exist_ok=True)
        env_path.write_text(example_env())


@app.command()
def version(ctx: typer.Context):
    """Display version information."""
    console = Console()
    console.print(f"{ctx.obj.app_name} version {ctx.obj.version}")
    console.print(f"App directory: {get_settings().app_dir}")


@app.command()
def reset(ctx: typer.Context):
    """Reset the application by deleting all stored data."""
    console = Console()
    console.print("[bold yellow]Resetting application...")
    console.print("[bold yellow]This will delete all stored credentials and tokens.")
    confirm = typer.confirm("Are you sure you want to continue?", default=False)
    if not confirm:
        console.print("[bold red]Reset cancelled.")
        raise typer.Abort()
    settings = get_settings()
    app_dir = settings.app_dir
    console.print(f"[bold yellow]Deleting application directory: {app_dir}")
    shutil.rmtree(app_dir, ignore_errors=True)
    console.print("[bold green]Application reset complete.")
