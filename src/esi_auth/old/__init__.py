"""ESI Authentication Library for EVE Online.

A simple library for managing EVE Online ESI authentication tokens.
"""

__app_name__ = "esi-auth"
__version__ = "0.3.0"
__author__ = "Chad Lowe"
__author_email__ = "pfmsoft.dev@gmail.com"
__license__ = "MIT"
__url__ = "https://github.com/DonalChilde/esi-auth"
__description__ = "A simple library for managing EVE Online ESI authentication tokens."


from esi_auth.esi_auth import CharacterToken, EsiAuth, EveCredentials, TokenManager

__all__ = ["EsiAuth", "CharacterToken", "EveCredentials", "TokenManager"]
