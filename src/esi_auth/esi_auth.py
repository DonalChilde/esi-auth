from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self

from pydantic import BaseModel, RootModel

from esi_auth import auth_helpers as AH


@dataclass(slots=True)
class AuthRequest:
    pass


@dataclass(slots=True)
class AuthCode:
    pass


class CharacterToken:
    # Placeholder for the actual CharacterToken implementation
    pass


class EsiCredentials:
    # Placeholder for the actual EsiCredentials implementation
    pass


class CredentialStore(RootModel[dict[int, EsiCredentials]]):
    pass


class TokenStore(RootModel[dict[int, dict[int, CharacterToken]]]):
    pass


class EsiAuthStore(BaseModel):
    credentials: CredentialStore
    tokens: TokenStore
    oauth_metadata: dict[str, Any]

    def save_to_disk(self, file_path: Path | None) -> None:
        # Atomic save
        if file_path is None:
            raise ValueError("file_path must be set before saving to disk.")
        pass

    @classmethod
    def load_from_disk(cls, file_path: Path) -> "EsiAuthStore":
        pass


class EsiAuth:
    def __init__(self, store_path: Path | None) -> None:
        """Initialize the EsiAuth instance.

        Pass None to store_path to create a new in-memory store.
        Set store_path later to save/load from disk.

        Args:
            store_path: Path to the file where the store is saved. If None, an in-memory store is used.
        """
        self.store_path = store_path
        if self.store_path is None:
            store = EsiAuthStore(
                credentials=CredentialStore(root={}),
                tokens=TokenStore(root={}),
                oauth_metadata={},
            )
            self.store = store
        else:
            self.store = EsiAuthStore.load_from_disk(self.store_path)

    #############################################################################
    # Authentication Flow Methods
    #############################################################################
    def prepare_request(self) -> AuthRequest:
        pass

    def request_authorization_code(self, request: AuthRequest) -> AuthCode:
        pass

    def exchange_code_for_token(self, code: AuthCode) -> CharacterToken:
        pass

    #############################################################################
    # Credential Storage Methods
    #############################################################################
    def store_credentials(self, credentials: EsiCredentials) -> None:
        pass

    def remove_credentials(self, client_id: int) -> None:
        pass

    def list_credentials(self) -> list[EsiCredentials]:
        pass

    def get_credentials_by_id(self, client_id: int) -> EsiCredentials | None:
        pass

    def get_credentials_by_alias(self, client_alias: str) -> EsiCredentials | None:
        pass

    #############################################################################
    # Token Storage Methods
    #############################################################################
    def store_token(self, token: CharacterToken, credentials: EsiCredentials) -> None:
        pass

    def remove_token(self, character_id: int, credentials: EsiCredentials) -> None:
        pass

    def list_tokens(self, credentials: EsiCredentials) -> list[CharacterToken]:
        pass

    def get_token(
        self, character_id: int, credentials: EsiCredentials
    ) -> CharacterToken | None:
        pass

    def refresh_token(self, token: CharacterToken, credentials: EsiCredentials) -> None:
        pass

    def refresh_all_tokens(self, credentials: EsiCredentials) -> None:
        pass

    ###############################################################################
    # Helper Methods
    ###############################################################################
    def update_oauth_metadata(self) -> None:
        # Update the OAuth metadata by downloading from the esi endpoint
        # "https://login.eveonline.com/.well-known/oauth-authorization-server"
        pass

    def _save_store(self) -> None:
        # Save the current store to disk if a path is set
        if self.store_path is not None:
            self.store.save_to_disk(self.store_path)
        else:
            pass
            # If no path is set, do nothing, using in-memory store only
