"""Command line interface for esi-auth."""

from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from time import perf_counter_ns
from typing import Annotated

import typer
from rich.console import Console
from rich.text import Text

from esi_auth import DEFAULT_APP_DIR
from esi_auth.cli import STYLE_INFO
from esi_auth.cli.cli_helpers import esi_auth_getter
from esi_auth.esi_auth import AuthStoreException, EsiAuth

from .credential_store_cli import app as credentials_app
from .token_store_cli import app as token_store_app
from .user_agent_cli import app as user_agent_app
from .util_cli import app as util_app

app = typer.Typer(no_args_is_help=True)


app.add_typer(
    credentials_app, name="credentials", help="Manage application credentials."
)
app.add_typer(token_store_app, name="tokens", help="Manage token storage.")
app.add_typer(util_app, name="util", help="Utility commands.")
app.add_typer(user_agent_app, name="user-agent", help="Manage User-Agent settings.")


@dataclass
class CliConfig:
    app_name: str = "NOT SET"
    version: str = "NOT SET"
    start_time: int = perf_counter_ns()
    debug: bool = False
    verbosity: int = 1
    silent: bool = False
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
            f" \tsilent={self.silent}"
            f" \tesi_auth={self.esi_auth.store_path if self.esi_auth else None}\n"
        )


@app.callback(invoke_without_command=True)
def default_options(
    ctx: typer.Context,
    store_file_path: Annotated[
        Path,
        typer.Option(
            "--store-file-path",
            "-f",
            help="Path to the auth store file.",
            exists=False,
            file_okay=True,
            dir_okay=False,
            writable=True,
            readable=True,
            resolve_path=True,
        ),
    ] = DEFAULT_APP_DIR / "auth-store.json",
    server_timeout: Annotated[
        int,
        typer.Option(
            "--server-timeout",
            "-t",
            help="Timeout in seconds for the auth server to respond.",
            min=1,
            max=300,
        ),
    ] = 300,
    debug: Annotated[bool, typer.Option("-d", help="Enable debug output.")] = False,
    verbosity: Annotated[int, typer.Option("-v", help="Verbosity.", count=True)] = 1,
    silent: Annotated[
        bool,
        typer.Option(help="Enable silent mode. Only results and errors will be shown."),
    ] = False,
):
    """Esi Auth Command Line Interface.

    Insert pithy saying here
    """
    if any((debug, verbosity > 1, silent)):
        typer.echo("Debug, verbosity, and silent options are not yet implemented.")
        raise typer.Exit(code=1)
    print(store_file_path)
    init_config(
        ctx,
        store_file_path=store_file_path,
        server_timeout=server_timeout,
        debug=debug,
        verbosity=verbosity,
        silent=silent,
    )
    console = Console()
    console.print("[bold]Welcome to esi-auth, a tool for managing EVE SSO tokens.")

    if ctx.obj.verbosity > 1:
        typer.echo("CLI configuration:")
        # TODO rework this with rich.
        # typer.echo(f"{indent_lines(str(ctx.obj), indent=2)}")
        typer.echo("App configuration:")
        # typer.echo(f"{indent_lines(str(CONFIG), indent=2)}")


def init_config(
    ctx: typer.Context,
    *,
    store_file_path: Path,
    server_timeout: int = 300,
    debug: bool,
    verbosity: int,
    silent: bool,
) -> None:
    """Initialize configuration based on CLI options."""
    start = perf_counter_ns()

    try:
        # Try to load the auth store. Creates a new store if missing.
        # TODO refactor when multiple store types are supported.
        esi_auth = EsiAuth(
            connection_string=f"esi-auth-file:{store_file_path.resolve()}",
            auth_server_timeout=server_timeout,
        )
    except AuthStoreException as e:
        console = Console()
        console.print(f"[bold red]Error initializing auth store: {e}")
        raise typer.Exit(code=1) from e

    config = CliConfig(
        app_name="Esi Auth",
        version=metadata.version("esi-auth"),
        start_time=start,
        debug=debug,
        verbosity=verbosity,
        silent=silent,
        esi_auth=esi_auth,
    )
    ctx.obj = config


@app.command()
def version(ctx: typer.Context):
    """Display version information."""
    console = Console()
    console.rule(Text("esi-auth Version Information", style=STYLE_INFO))
    esi_auth = esi_auth_getter(ctx)
    console.print(f"{ctx.obj.app_name} version {ctx.obj.version}")
    console.print(f"Store File: {esi_auth.store_path}")


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
        connection_string=f"esi-auth-file:{store_path.resolve()}"
    )
    console.print("[bold green]Application reset complete.")
