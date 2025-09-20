"""ESI Authentication Library for EVE Online.

A simple library for managing EVE Online ESI authentication tokens.
"""

__version__ = "0.1.0"

# Public API exports
from .api import (
    authenticate_character,
    backup_characters,
    get_character,
    get_character_info,
    list_characters,
    load_characters,
    refresh_expired_tokens,
    refresh_token,
    remove_character,
    restore_characters,
    validate_token,
)
from .models import (
    AuthenticatedCharacters,
    AuthenticationError,
    CharacterInfo,
    CharacterToken,
    TokenRefreshError,
)
from .settings import (
    ESIAuthSettings,
    get_settings,
    set_production_profile,
    set_testing_profile,
)
from .storage import TokenStorage, TokenStorageError, get_token_storage

__all__ = [
    # Core API functions
    "authenticate_character",
    "load_characters",
    "list_characters",
    "get_character",
    "refresh_token",
    "refresh_expired_tokens",
    "remove_character",
    "validate_token",
    "get_character_info",
    "backup_characters",
    "restore_characters",
    # Models
    "CharacterToken",
    "AuthenticatedCharacters",
    "CharacterInfo",
    "AuthenticationError",
    "TokenRefreshError",
    "TokenStorageError",
    # Settings
    "ESIAuthSettings",
    "get_settings",
    "set_testing_profile",
    "set_production_profile",
    # Storage
    "TokenStorage",
    "get_token_storage",
]


# def main() -> None:
#     """Main entry point for the esi-auth CLI."""
#     print("Hello from esi-auth!")


# LOG_CONFIG: dict[str, Any] = {
#     "version": 1,
#     "disable_existing_loggers": False,
#     "formatters": {
#         "consoleFormatter": {
#             "format": "%(asctime)s | %(name)s | %(levelname)s : %(message)s",
#         },
#         "fileFormatter": {
#             "format": "%(asctime)s | %(name)s | %(levelname)-8s : %(message)s",
#         },
#         "brief": {
#             "datefmt": "%H:%M:%S",
#             "format": "%(levelname)-8s; %(name)s; %(message)s;",
#         },
#         "single-line": {
#             "datefmt": "%H:%M:%S",
#             "format": "%(levelname)-8s; %(asctime)s; %(name)s; %(module)s:%(funcName)s;%(lineno)d: %(message)s",
#         },
#         "multi-process": {
#             "datefmt": "%H:%M:%S",
#             "format": "%(levelname)-8s; [%(process)d]; %(name)s; %(module)s:%(funcName)s;%(lineno)d: %(message)s",
#         },
#         "multi-thread": {
#             "datefmt": "%H:%M:%S",
#             "format": "%(levelname)-8s; %(threadName)s; %(name)s; %(module)s:%(funcName)s;%(lineno)d: %(message)s",
#         },
#         "verbose": {
#             "format": "%(levelname)-8s; [%(process)d]; %(threadName)s; %(name)s; %(module)s:%(funcName)s;%(lineno)d"
#             ": %(message)s"
#         },
#         "multiline": {
#             "format": "Level: %(levelname)s\nTime: %(asctime)s\nProcess: %(process)d\nThread: %(threadName)s\nLogger"
#             ": %(name)s\nPath: %(module)s:%(lineno)d\nFunction :%(funcName)s\nMessage: %(message)s\n"
#         },
#         "mine": {
#             "format": "%(asctime)s | %(levelname)-8s | %(funcName)s | %(message)s | [in %(pathname)s | %(lineno)d]"
#         },
#         "mine-multi": {
#             "format": "%(asctime)s | %(levelname)-8s | %(funcName)s | [in %(pathname)s | %(lineno)d]\n\t %(message)s"
#         },
#     },
#     "handlers": {
#         "file": {
#             "filename": CONFIG.log_dir / "debug.log",
#             "level": "DEBUG",
#             "class": "logging.FileHandler",
#             "formatter": "mine",
#         },
#         "console": {
#             "level": "CRITICAL",
#             "class": "logging.StreamHandler",
#             "formatter": "consoleFormatter",
#         },
#         "rot_file_info": {
#             "class": "logging.handlers.RotatingFileHandler",
#             "formatter": "mine",
#             "level": "INFO",
#             "filename": CONFIG.log_dir / "rotating_info.log",
#             "mode": "a",
#             "encoding": "utf-8",
#             "maxBytes": 10000000,
#             "backupCount": 10,
#         },
#         "rot_file_warn": {
#             "class": "logging.handlers.RotatingFileHandler",
#             "formatter": "mine",
#             "level": "WARNING",
#             "filename": CONFIG.log_dir / "rotating_warn.log",
#             "mode": "a",
#             "encoding": "utf-8",
#             "maxBytes": 500000,
#             "backupCount": 4,
#         },
#     },
#     "loggers": {
#         "": {
#             "handlers": ["rot_file_info", "rot_file_warn", "console"],
#             "level": "DEBUG",
#         },
#     },
# }
