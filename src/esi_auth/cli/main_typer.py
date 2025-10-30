"""Command line interface for esi-auth."""

import logging
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from time import perf_counter_ns
from typing import Annotated

import typer
from rich.console import Console
from rich.text import Text

from esi_auth import __app_name__, __version__
from esi_auth.cli import STYLE_INFO
from esi_auth.cli.cli_helpers import ensure_env_example, esi_auth_getter
from esi_auth.esi_auth import AuthStoreException, EsiAuth, UserAgentSettings
from esi_auth.logging_config import setup_logging
from esi_auth.settings import EsiAuthSettings, get_settings

from .credential_store_cli import app as credentials_app
from .token_store_cli import app as token_store_app
from .util_cli import app as util_app

logger = logging.getLogger(__name__)

app = typer.Typer(no_args_is_help=True)
app.add_typer(
    credentials_app, name="credentials", help="Manage application credentials."
)
app.add_typer(token_store_app, name="tokens", help="Manage token storage.")
app.add_typer(util_app, name="util", help="Utility commands.")


@dataclass
class CliConfig:
    app_name: str = __app_name__
    version: str = __version__
    start_time: int = perf_counter_ns()
    debug: bool = False
    verbosity: int = 1
    silent: bool = False
    settings: EsiAuthSettings | None = None
    esi_auth: EsiAuth | None = None

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
            f"settings={self.settings!r}, "
            f"esi_auth={self.esi_auth.store_path if self.esi_auth else None}"
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
            f" \tsilent={self.silent}\n"
            f" \tsettings={self.settings!r}\n"
            f" \tesi_auth={self.esi_auth.store_path if self.esi_auth else None}\n"
        )


@app.callback(invoke_without_command=True)
def default_options(
    ctx: typer.Context,
    debug: Annotated[
        bool, typer.Option("-d", help="Enable debug output.(not implemented)")
    ] = False,
    verbosity: Annotated[
        int, typer.Option("-v", help="Verbosity. (not implemented)", count=True)
    ] = 1,
    silent: Annotated[
        bool,
        typer.Option(
            help="Enable silent mode. Only results and errors will be shown.(not implemented)"
        ),
    ] = False,
):
    """Esi Auth Command Line Interface.

    Insert pithy saying here
    """
    console = Console()
    settings = get_settings()
    setup_logging(log_dir=settings.log_dir)
    env_file_exists = ensure_env_example(file_path=settings.app_dir / ".esi-auth.env")
    if not env_file_exists:
        console.print(
            f"[bold yellow]An example .esi-auth.env file has been created at {settings.app_dir / '.esi-auth.env'}.[/bold yellow]"
        )
        console.print(
            "[bold yellow]Please edit this file to configure your User-Agent settings before using esi-auth.[/bold yellow]"
        )
        raise typer.Exit(code=1)
    if any((debug, verbosity > 1, silent)):
        typer.echo("Debug, verbosity, and silent options are not yet implemented.")
        raise typer.Exit(code=1)

    init_config(
        ctx,
        esi_auth_settings=settings,
        debug=debug,
        verbosity=verbosity,
        silent=silent,
    )
    console = Console()
    console.print("[bold]Welcome to esi-auth, a tool for managing EVE SSO tokens.")


def init_config(
    ctx: typer.Context,
    *,
    esi_auth_settings: EsiAuthSettings,
    debug: bool,
    verbosity: int,
    silent: bool,
) -> None:
    """Initialize configuration based on CLI options."""
    start = perf_counter_ns()
    config = CliConfig(
        start_time=start,
        debug=debug,
        verbosity=verbosity,
        silent=silent,
        settings=esi_auth_settings,
    )
    ctx.obj = config
    try:
        user_agent = UserAgentSettings(
            character_name=esi_auth_settings.character_name,
            user_email=esi_auth_settings.user_email,
            user_app_name=esi_auth_settings.user_app_name,
            user_app_version=esi_auth_settings.user_app_version,
        )
        esi_auth = EsiAuth(
            connection_string=esi_auth_settings.connection_string,
            auth_server_timeout=esi_auth_settings.auth_server_timeout,
            user_agent_settings=user_agent,
        )
        cli_config: CliConfig = ctx.obj
        cli_config.esi_auth = esi_auth

    except AuthStoreException as e:
        console = Console()
        console.print(f"[bold red]Error initializing auth store: {e}")
        raise typer.Exit(code=1) from e


@app.command()
def version(ctx: typer.Context):
    """Display version information."""
    console = Console()
    console.rule(Text("esi-auth Version Information", style=STYLE_INFO))
    cli_config: CliConfig = ctx.obj
    console.print(f"{cli_config.app_name} version {cli_config.version}")
    console.print("Configuration:")
    console.print(cli_config)


@app.command()
def reset(ctx: typer.Context):
    """Reset the application by deleting all stored data."""
    # TODO refactor this when multiple store types are supported.
    console = Console()
    esi_auth = esi_auth_getter(ctx)
    store_path = esi_auth.store_path
    console.print("[bold yellow]Resetting application...")
    console.print(
        f"[bold yellow]This will delete all stored credentials and tokens at {store_path}."
    )
    confirm = typer.confirm("Are you sure you want to continue?", default=False)
    if not confirm:
        console.print("[bold red]Reset cancelled.")
        raise typer.Abort()

    console.print(f"[bold yellow]Deleting application data at : {store_path}")
    if store_path is not None and store_path.is_file():  # type: ignore
        store_path.unlink(missing_ok=True)
    ctx.obj.esi_auth = EsiAuth(
        connection_string=f"esi-auth-file:{store_path.resolve()}",
        user_agent_settings=UserAgentSettings(
            character_name="Unknown",
            user_email="Unknown",
            user_app_name="Unknown",
            user_app_version="Unknown",
        ),
    )
    console.print("[bold green]Application reset complete.")


@app.command()
def example_env(
    file_path: Annotated[
        Path,
        typer.Argument(
            help="Path to create the example .esi-auth.env file.",
        ),
    ],
):
    """Create an example .esi-auth.env file for esi-auth configuration."""
    console = Console()
    exists = ensure_env_example(file_path=file_path)
    if exists:
        console.print(
            f"[bold yellow]File already exists at {file_path}. No changes made.[/bold yellow]"
        )
    else:
        console.print(
            f"[bold green]Example .env file created at {file_path}.[/bold green]"
        )
        console.print(
            "[bold green]Please edit this file to configure your User-Agent settings before using esi-auth.[/bold green]"
        )
