"""CLI commands for managing CharacterTokens."""

import asyncio
from typing import Annotated, cast

import aiohttp
import typer
from rich.console import Console

from esi_auth.authenticate_esi import (
    generate_code_challenge,
    redirect_to_sso,
    request_token,
    run_callback_server,
    validate_jwt_token,
)
from esi_auth.cli.helpers import (
    EsiAuthSettings,
    load_credentials,
    load_oauth_metadata,
)
from esi_auth.models import (
    CharacterToken,
    OauthToken,
)
from esi_auth.simple_json_store import CharacterTokenManager

app = typer.Typer(no_args_is_help=True)


@app.command()
def add(
    ctx: typer.Context,
):
    """Add a new CharacterToken."""
    settings = ctx.obj["esi-auth-settings"]
    settings = cast(EsiAuthSettings, settings)
    console = Console()
    credentials = load_credentials(settings, console)
    token_manager = CharacterTokenManager(settings.tokens_dir)
    try:
        oauth_metadata = load_oauth_metadata(settings)
    except Exception as e:
        console.print(f"[red]Error loading OAuth metadata: {e}[/red]")
        raise typer.Exit(code=1) from e
    console.print(f"OAuth settings loaded from file.\n")
    challenge = generate_code_challenge()

    # Assemble the parameters for the OAuth flow
    callback_url = credentials.callbackUrl
    authorization_endpoint = oauth_metadata["authorization_endpoint"]
    code_challenge = challenge["code_challenge"]
    code_verifier = challenge["code_verifier"]
    token_endpoint = oauth_metadata["token_endpoint"]
    user_agent = "esi-auth-cli/1.0"
    jwks_uri = oauth_metadata["jwks_uri"]

    sso_url, state = redirect_to_sso(
        client_id=credentials.clientId,
        scopes=credentials.scopes,
        redirect_uri=callback_url,
        authorization_endpoint=authorization_endpoint,
        challenge=code_challenge,
    )
    console.print(f"Navigate to the following URL to authenticate:\n")
    console.print(f"[link={sso_url}]......Click ME......[/link]\n")
    console.print(
        f"Or copy and paste the URL into your browser if your terminal does not support clickable links.\n"
    )
    console.print(f"{sso_url}\n")

    console.print(f"Listening on {callback_url} for callback...\n")
    console.print(
        "The local server can take a second to start. If the link gives an error, try reloading the page after a moment.\n"
    )
    # Launch a web server to listen for the callback and get the authorization code.
    authorization_code = asyncio.run(
        run_callback_server(expected_state=state, callback_url=callback_url)
    )
    console.print(f"Received authorization code: {authorization_code}\n")

    async def get_token():
        async with aiohttp.ClientSession() as session:
            token = await request_token(
                client_id=credentials.clientId,
                authorization_code=authorization_code,
                code_verifier=code_verifier,
                token_endpoint=token_endpoint,
                user_agent=user_agent,
                client_session=session,
            )
            return token

    token = asyncio.run(get_token())
    console.print(f"Received token response\n")

    try:
        validated_token = validate_jwt_token(
            access_token=token["access_token"],
            jwks_uri=jwks_uri,
            audience="EVE Online",
            issuers=["https://login.eveonline.com"],
            user_agent=user_agent,
            jwks_client=None,
        )
        console.print("[green]Token is valid.[/green]\n")
    except Exception as e:
        console.print(f"[red]Token validation failed: {e}[/red]\n")
        raise typer.Exit(code=1) from e

    character_id = validated_token["sub"].split(":")[-1]
    character_name = validated_token.get("name", "Unknown Character")
    console.print(f"Authenticated character: {character_name} (ID: {character_id})\n")

    oauth_token = OauthToken.model_validate(token)

    character_token = CharacterToken(
        character_id=int(character_id),
        character_name=character_name,
        client_id=credentials.clientId,
        refreshed_at=int(validated_token["iat"]),
        oauth_token=oauth_token,
    )
    try:
        token_manager.add_token(character_token)
    except Exception as e:
        console.print(f"[red]Error saving token: {e}[/red]\n")
        raise typer.Exit(code=1) from e
    console.print(f"Token for {character_name} added successfully.\n")


@app.command()
def list(
    ctx: typer.Context,
):
    """List all CharacterTokens, optionally filtered by app alias."""
    settings = ctx.obj["esi-auth-settings"]
    settings = cast(EsiAuthSettings, settings)
    console = Console()

    token_manager = CharacterTokenManager(settings.tokens_dir)

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
    """Remove a CharacterToken by character ID."""
    settings = ctx.obj["esi-auth-settings"]
    settings = cast(EsiAuthSettings, settings)
    console = Console()

    token_manager = CharacterTokenManager(settings.tokens_dir)

    try:
        token_manager.remove_token(character_id)
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

    token_manager = CharacterTokenManager(settings.tokens_dir)

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

    token_manager = CharacterTokenManager(settings.tokens_dir)

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
