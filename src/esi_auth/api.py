"""The API functions for the esi_auth package."""

import logging

from esi_auth.models import CharacterToken
from esi_auth.settings import get_settings
from esi_auth.storage import TokenStoreJson

logger = logging.getLogger(__name__)


def get_authorized_characters(buffer_minutes: int = 5) -> list[CharacterToken]:
    """Get a list of all authorized characters.

    The function checks for tokens that are close to expiration (within the
    specified buffer time) and attempts to refresh them before returning the list.

    Args:
        buffer_minutes: Minutes before actual expiration to consider a token as needing refresh.

    Returns:
        List of CharacterToken objects.

    Raises:
        TokenStorageError: If the operation fails.
    """
    logger.debug("Retrieving all authorized characters")
    settings = get_settings()
    token_store_path = settings.token_store_dir / settings.token_file_name
    token_store = TokenStoreJson(storage_path=token_store_path)
    refresh_list = token_store.list_characters_needing_refresh(
        buffer_minutes=buffer_minutes
    )
    if refresh_list:
        logger.info(f"Refreshing {len(refresh_list)} tokens before returning list")
        success_ids, failure_ids = token_store.refresh_characters(refresh_list)
        _ = success_ids  # Unused variable
        if failure_ids:
            logger.warning(f"Failed to refresh tokens for character IDs: {failure_ids}")
            # TODO: Consider raising an exception or handling failures differently
    characters = token_store.list_characters()
    return characters
