"""An implementation of the AuthProviderProtocol."""

from esi_auth.models import CharacterAuth
from esi_auth.protocols import AuthProviderProtocol, CharacterTokenManagerProtocol


class AuthProvider(AuthProviderProtocol):
    """AuthProvider implementation."""

    def __init__(self, token_manager: CharacterTokenManagerProtocol):
        self.token_manager = token_manager

    async def character_auth(self, character_id: int) -> CharacterAuth:
        character_token = await self.token_manager.get_token(character_id)
        auth = CharacterAuth(
            character_id=character_token.character_id,
            character_name=character_token.character_name,
            auth_headers={
                "Authorization": f"Bearer {character_token.oauth_token.access_token}"
            },
            expires_at=character_token.expires,
        )
        return auth

    async def available_characters(self) -> list[int]:
        tokens = await self.token_manager.list_tokens()
        return [x.character_id for x in tokens]
