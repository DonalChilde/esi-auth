# """CLI commands for managing user-agent information."""

# from typing import Annotated

# import typer
# from rich.console import Console

# from esi_auth.cli.cli_helpers import esi_auth_getter

# app = typer.Typer(no_args_is_help=True)


# @app.command("set", help="Set user-agent information for the application.")
# def set_user_agent(
#     ctx: typer.Context,
#     character_name: Annotated[
#         str, typer.Argument(help="Character name to include in User-Agent header")
#     ],
#     user_email: Annotated[
#         str, typer.Argument(help="User email to include in User-Agent header")
#     ],
#     user_app_name: Annotated[
#         str, typer.Argument(help="Application name to include in User-Agent header")
#     ],
#     user_app_version: Annotated[
#         str, typer.Argument(help="Application version to include in User-Agent header")
#     ],
# ):
#     """Set user-agent information for the application."""
#     console = Console()
#     console.rule("[bold blue]Set User Agent Fields[/bold blue]")
#     esi_auth = esi_auth_getter(ctx)
#     esi_auth.update_user_agent(
#         character_name=character_name,
#         user_email=user_email,
#         user_app_name=user_app_name,
#         user_app_version=user_app_version,
#     )
#     console.print("[green]User-Agent information updated successfully.[/green]")
#     console.print(f"Character Name: {esi_auth.store.user_agent.character_name}")
#     console.print(f"User Email: {esi_auth.store.user_agent.user_email}")
#     console.print(f"App Name: {esi_auth.store.user_agent.user_app_name}")
#     console.print(f"App Version: {esi_auth.store.user_agent.user_app_version}")
