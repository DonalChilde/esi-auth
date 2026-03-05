"""Utility CLI commands for esi_auth."""

import typer

app = typer.Typer(no_args_is_help=True)


@app.command("placeholder", help="A placeholder command.")
def placeholder() -> None:
    """Placeholder command to ensure the CLI module is not empty."""
    pass
