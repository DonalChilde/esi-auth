"""The API functions for the esi_auth package."""

import logging

from esi_auth.credential_storage import get_credential_store
from esi_auth.models import CharacterToken
from esi_auth.settings import get_settings
from esi_auth.token_storage import TokenStoreJson

logger = logging.getLogger(__name__)


def get_authorized_characters(
    client_id: str | None = None,
    client_alias: str | None = None,
    buffer_minutes: int = 5,
) -> dict[int, CharacterToken]:
    """Get a list of all authorized characters.

    The function checks for tokens that are close to expiration (within the
    specified buffer time) and attempts to refresh them before returning the list.

    If tokens fail due to a network or server error, repeated calls to this function
    may succeed in refreshing them. Successfully refreshed tokens will be saved
    back to the token store, and will not be included in subsequent calls to this function.

    Args:
        buffer_minutes: Minutes before actual expiration to consider a token as needing refresh.
            Should not exceed 15 minutes, as the starting lifetime for a refreshed token is 20 minutes.

    Returns:
        A dictionary mapping character IDs to their corresponding CharacterToken objects.

    Raises:
        TokenStorageError: If the operation fails.
    """
    # FIXME move retrival of credentials by alisas or id to credential store module.
    # FIXME Include exception handling for not found, both specified, neither specified.
    if client_id and client_alias:
        raise ValueError("Specify either client_id or client_alias, not both.")
    if not any([client_id, client_alias]):
        raise ValueError("Either client_id or client_alias must be specified.")
    credential_store = get_credential_store()
    if client_alias:
        credentials = credential_store.get_credentials_by_alias(client_alias)
    else:
        credentials = credential_store.get_credentials(client_id)  # pyright: ignore[reportArgumentType]
    if credentials is None:
        raise ValueError(
            "No credentials found for the specified client_id or client_alias."
        )
    if buffer_minutes < 0:
        raise ValueError("buffer_minutes must be non-negative")
    if buffer_minutes > 15:
        raise ValueError("buffer_minutes should not exceed 15 minutes")
    logger.debug("Retrieving all authorized characters")
    settings = get_settings()
    token_store_path = settings.token_store_dir / settings.token_file_name
    token_store = TokenStoreJson(storage_path=token_store_path)
    refresh_list = token_store.list_characters_needing_refresh(
        credentials=credentials, buffer_minutes=buffer_minutes
    )
    if refresh_list:
        logger.info(f"Refreshing {len(refresh_list)} tokens before returning list")
        success_ids, failure_ids = token_store.refresh_characters(
            credentials=credentials, characters=refresh_list
        )
        _ = success_ids  # Unused variable
        if failure_ids:
            logger.warning(f"Failed to refresh tokens for character IDs: {failure_ids}")
            # TODO: Consider raising an exception or handling failures differently
    characters = token_store.list_characters(credentials=credentials)
    character_dict = {char.character_id: char for char in characters}
    return character_dict
