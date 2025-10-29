"""ESI Authentication Library for EVE Online.

A simple library for managing EVE Online ESI authentication tokens.
"""

__app_name__ = "esi-auth"
__version__ = "0.2.0"
__author__ = "Chad Lowe"
__author_email__ = "pfmsoft.dev@gmail.com"
__license__ = "MIT"
__url__ = "https://github.com/DonalChilde/esi-auth"
__description__ = "A simple library for managing EVE Online ESI authentication tokens."

import logging
from pathlib import Path

import typer

from esi_auth.esi_auth import CharacterToken, EsiAuth, EveCredentials, TokenManager

logger = logging.getLogger(__name__)


__all__ = ["EsiAuth", "CharacterToken", "EveCredentials", "TokenManager"]
NAMESPACE = "pfmsoft"
APPLICATION_NAME = "esi-auth"
DEFAULT_APP_DIR = Path(typer.get_app_dir(f"{NAMESPACE}-{APPLICATION_NAME}"))
