"""CLI commands for managing CharacterTokens."""

import asyncio
from typing import Annotated, Any, cast

import aiohttp
import typer
from rich.console import Console
from rich.json import JSON

from esi_auth.cli.helpers import (
    EsiAuthSettings,
    config_authenticator,
)
from esi_auth.models import CharacterToken
from esi_auth.settings import USER_AGENT
from esi_auth.simple_json_store import CharacterTokenManager

app = typer.Typer(no_args_is_help=True)


@app.command()
def add(
    ctx: typer.Context,
    test_token: Annotated[
        bool,
        typer.Option(
            "-t",
            "--test-token",
            help="Make a resquest to the EVE ESI to proven token is working",
        ),
    ] = False,
):
    """Add a new CharacterToken."""
    settings = ctx.obj["esi-auth-settings"]
    settings = cast(EsiAuthSettings, settings)
    console = Console()

    authenticator = config_authenticator(settings, console)
    token_manager = CharacterTokenManager(settings.tokens_dir, authenticator)
    request_params = authenticator.prepare_for_request()

    console.print(f"Navigate to the following URL to authenticate:\n")
    console.print(f"[link={request_params.url}]......Click ME......[/link]\n")
    console.print(
        f"Or copy and paste the URL into your browser if your terminal does not support clickable links.\n"
    )
    console.print(f"{request_params.url}\n")

    console.print(f"Listening on {authenticator.callback_url} for callback...\n")
    console.print(
        "The local server can take a second to start. If the link gives an error, try reloading the page after a moment.\n"
    )
    # Launch a web server to listen for the callback and get the authorization code.
    # then get and validate the token to make a CharacterToken.
    try:
        character_token = asyncio.run(
            authenticator.request_character_token(request_params)
        )
    except Exception as e:
        console.print(f"[red]Error requesting character token: {e}[/red]\n")
        raise typer.Exit(code=1) from e
    try:
        token_manager.add_token(character_token)
    except Exception as e:
        console.print(f"[red]Error saving token: {e}[/red]\n")
        raise typer.Exit(code=1) from e
    console.print(f"Token for {character_token.character_name} added successfully.\n")
    if test_token:
        console.print(f"Testing token by fetching character attributes from ESI...\n")
        try:
            attributes = asyncio.run(get_character_attributes(character_token))
            console.print(f"Token is valid. Character attributes:")
            console.print(JSON.from_data(attributes))
        except Exception as e:
            console.print(f"[red]Error testing token: {e}[/red]\n")
            raise typer.Exit(code=1) from e


@app.command()
def list(
    ctx: typer.Context,
):
    """List all CharacterTokens, optionally filtered by app alias."""
    settings = ctx.obj["esi-auth-settings"]
    settings = cast(EsiAuthSettings, settings)
    console = Console()
    authenticator = config_authenticator(settings, console)

    token_manager = CharacterTokenManager(settings.tokens_dir, authenticator)

    try:
        tokens = asyncio.run(token_manager.list_tokens(min_seconds=-1))
    except Exception as e:
        console.print(f"[red]Error listing tokens: {e}[/red]\n")
        raise typer.Exit(code=1) from e

    if not tokens:
        console.print("No tokens found.\n")
        return

    console.print(f"Found {len(tokens)} token(s):\n")
    for token in tokens:
        console.print(
            f"- {token.character_name} (ID: {token.character_id}), Expires in: {token.expires_in} seconds\n"
        )


@app.command()
def remove(
    ctx: typer.Context,
    character_id: Annotated[
        int, typer.Argument(help="ID of the character token to remove.")
    ],
):
    """Remove and revoke a CharacterToken by character ID."""
    settings = ctx.obj["esi-auth-settings"]
    settings = cast(EsiAuthSettings, settings)
    console = Console()

    authenticator = config_authenticator(settings, console)
    token_manager = CharacterTokenManager(settings.tokens_dir, authenticator)

    try:
        token = asyncio.run(token_manager.get_token(character_id, min_seconds=-1))
        token_manager.remove_token(character_id)

        async def revoke():
            async with aiohttp.ClientSession() as session:
                await authenticator.revoke_character_token(token, session)

        asyncio.run(revoke())
        console.print(f"Token for character ID {character_id} removed successfully.\n")
    except KeyError as e:
        console.print(f"[red]No token found for character ID {character_id}[/red]\n")
        raise typer.Exit(code=1) from e
    except Exception as e:
        console.print(f"[red]Error removing token: {e}[/red]\n")
        raise typer.Exit(code=1) from e


@app.command()
def refresh(
    ctx: typer.Context,
    character_id: Annotated[
        int, typer.Argument(help="ID of the character token to refresh.")
    ],
):
    """Refresh a CharacterToken by character ID."""
    settings = ctx.obj["esi-auth-settings"]
    settings = cast(EsiAuthSettings, settings)
    console = Console()
    authenticator = config_authenticator(settings, console)
    token_manager = CharacterTokenManager(settings.tokens_dir, authenticator)

    try:
        token = asyncio.run(token_manager.get_token(character_id, min_seconds=-1))
        console.print(
            f"Token for {token.character_name}-{token.character_id} expires in {token.expires_in} seconds.\n"
        )
        token = asyncio.run(token_manager.get_token(character_id, min_seconds=9000))
        console.print(
            f"Token for {token.character_name}-{token.character_id} has been refreshed, expires in {token.expires_in} seconds.\n"
        )
        return
    except KeyError as e:
        console.print(f"[red]No token found for character ID {character_id}[/red]\n")
        raise typer.Exit(code=1) from e
    except Exception as e:
        console.print(
            f"[red]Error refreshing token for character ID {character_id}: {e}[/red]\n"
        )
        raise typer.Exit(code=1) from e


@app.command()
def refresh_all(
    ctx: typer.Context,
):
    """Refresh all CharacterTokens."""
    settings = ctx.obj["esi-auth-settings"]
    settings = cast(EsiAuthSettings, settings)
    console = Console()
    authenticator = config_authenticator(settings, console)
    token_manager = CharacterTokenManager(settings.tokens_dir, authenticator)

    try:
        tokens = asyncio.run(token_manager.list_tokens(min_seconds=9000))
        if not tokens:
            console.print("No tokens found.\n")
            return

        console.print(f"Refreshed {len(tokens)} token(s):\n")
        for token in tokens:
            console.print(
                f"- {token.character_name} (ID: {token.character_id}), Expires in: {token.expires_in} seconds"
            )
    except Exception as e:
        console.print(f"[red]Error refreshing tokens: {e}[/red]\n")
        raise typer.Exit(code=1) from e


async def get_character_attributes(token: CharacterToken) -> dict[str, Any]:
    """Get character attributes from ESI using the token."""
    async with aiohttp.ClientSession() as session:
        headers: dict[str, str] = {
            "Authorization": f"Bearer {token.oauth_token.access_token}",
            "User-Agent": USER_AGENT,
        }
        url = f"https://esi.evetech.net/characters/{token.character_id}/attributes"
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                raise Exception(
                    f"Failed to get character attributes: {response.status} {response.reason}"
                )
            data = await response.json()
            return data
