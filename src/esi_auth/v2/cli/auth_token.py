import asyncio
from typing import Annotated, cast

import aiohttp
import typer
from rich.console import Console

from esi_auth.v2.authenticate_esi import (
    generate_code_challenge,
    redirect_to_sso,
    request_token,
    run_callback_server,
    validate_jwt_token,
)
from esi_auth.v2.cli.helpers import EsiAuthSettings, load_oauth_metadata
from esi_auth.v2.models import (
    CharacterToken,
    OauthToken,
)
from esi_auth.v2.simple_json_store import AppCredentialProvider, CharacterTokenManager

app = typer.Typer(no_args_is_help=True)


@app.command()
def add(
    ctx: typer.Context,
    alias: Annotated[str, typer.Argument(help="Alias for the app credentials.")],
):
    """Add a new CharacterToken."""
    settings = ctx.obj["esi-auth-settings"]
    settings = cast(EsiAuthSettings, settings)
    console = Console()
    credential_provider = AppCredentialProvider(settings.credentials_dir)

    try:
        creds = credential_provider.by_alias(alias)
    except Exception as e:
        console.print(f"[red]Error checking for existing credential: {e}[/red]")
        raise typer.Exit(code=1) from e
    token_manager = CharacterTokenManager(settings.tokens_dir, credential_provider)
    try:
        oauth_metadata = load_oauth_metadata(settings)
    except Exception as e:
        console.print(f"[red]Error loading OAuth metadata: {e}[/red]")
        raise typer.Exit(code=1) from e
    console.print(f"OAuth settings loaded from file.\n")
    challenge = generate_code_challenge()

    # Assemble the parameters for the OAuth flow
    callback_url = creds.credentials.callbackUrl
    authorization_endpoint = oauth_metadata["authorization_endpoint"]
    code_challenge = challenge["code_challenge"]
    code_verifier = challenge["code_verifier"]
    token_endpoint = oauth_metadata["token_endpoint"]
    user_agent = "esi-auth-cli/1.0"
    jwks_uri = oauth_metadata["jwks_uri"]

    sso_url, state = redirect_to_sso(
        client_id=creds.credentials.clientId,
        scopes=creds.credentials.scopes,
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
                client_id=creds.credentials.clientId,
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
        app_alias=alias,
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
    alias: Annotated[
        str | None, typer.Argument(help="Alias for the app credentials.")
    ] = None,
):
    """List all CharacterTokens, optionally filtered by app alias."""
    settings = ctx.obj["esi-auth-settings"]
    settings = cast(EsiAuthSettings, settings)
    console = Console()
    credential_provider = AppCredentialProvider(settings.credentials_dir)
    token_manager = CharacterTokenManager(settings.tokens_dir, credential_provider)

    try:
        tokens = (
            token_manager.list_tokens(client_alias=alias)
            if alias
            else token_manager.list_all_tokens()
        )
    except Exception as e:
        console.print(f"[red]Error listing tokens: {e}[/red]\n")
        raise typer.Exit(code=1) from e

    if not tokens:
        console.print("No tokens found.\n")
        return

    console.print(f"Found {len(tokens)} token(s):\n")
    for token in tokens:
        console.print(
            f"- {token.character_name} (ID: {token.character_id}), App Alias: {token.app_alias}, Expires in: {token.expires_in} seconds\n"
        )
