from collections.abc import Sequence
from pathlib import Path
from typing import Any, ClassVar

import typer
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

APPLICATION_NAME = "pfmsoft-esi-auth"
DEFAULT_APP_DIR = Path(typer.get_app_dir(APPLICATION_NAME))

# TODO load and save to file
# TODO cli command to update oauth metadata


class EsiAuthSettings(BaseSettings):
    """Application settings for ESI authentication.

    Settings can be loaded from environment variables and .env files.
    The settings support different environments (e.g. development, testing, production).
    Environments can be managed using different .env files or environment variables.
    By default, settings are loaded from a .env file in the application directory,
    but different
    """

    model_config = SettingsConfigDict(
        env_prefix="ESI_AUTH_",
        env_file=str(DEFAULT_APP_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    ############################################################################
    # Application configuration
    ############################################################################
    app_name: str = Field(
        default=APPLICATION_NAME,
        description="Application name.",
    )

    app_dir: Path = Field(
        default=DEFAULT_APP_DIR,
        description="Directory for storing application data",
    )

    log_dir: Path = Field(
        default=DEFAULT_APP_DIR / "logs",
        description="Directory for storing log files",
    )

    token_store_dir: Path = Field(
        default=DEFAULT_APP_DIR / "token-store",
        description="Directory for storing token files",
    )

    token_file_name: str = Field(
        default="character_tokens.json",
        description="Filename for storing character tokens",
    )

    # HTTP client configuration
    request_timeout: int = Field(
        default=30, description="HTTP request timeout in seconds"
    )

    ############################################################################
    # Oauth2
    ############################################################################

    # OAuth2 credentials
    client_id: str = Field(
        default="NOT_SET",
        description="EVE Online application client ID from developers.eveonline.com",
    )
    client_secret: str = Field(
        default="NOT_SET",
        description="EVE Online application client secret from developers.eveonline.com",
    )

    # ESI API configuration
    esi_base_url: str = Field(
        default="https://esi.evetech.net", description="Base URL for EVE Online ESI API"
    )

    sso_base_url: str = Field(
        default="https://login.eveonline.com", description="Base URL for EVE Online SSO"
    )

    # Authorization endpoint - https://login.eveonline.com/.well-known/oauth-authorization-server
    oauth2_authorization_metadata_url: str = Field(
        default="https://login.eveonline.com/.well-known/oauth-authorization-server",
        description="URL for OAuth2 authorization server metadata",
    )

    # Audience for token validation
    oauth2_audience: str = Field(
        default="EVE Online", description="Audience for validating JWT tokens"
    )

    # Issuer for token validation
    oauth2_issuer: Sequence[str] = Field(
        default=["login.eveonline.com"], description="Issuer for validating JWT tokens"
    )

    # Callback url settings
    callback_host: str = Field(
        default="localhost", description="Host for OAuth callback server"
    )

    callback_port: int = Field(
        default=8080, description="Port for OAuth callback server"
    )

    callback_route: str = Field(
        default="/callback", description="Route for OAuth callback server"
    )

    ############################################################################
    # User agent configuration
    ############################################################################

    # User agent fields
    character_name: str = Field(
        default="Unknown", description="Character name for User-Agent header"
    )

    user_email: str = Field(
        default="Unknown", description="User email for User-Agent header"
    )
    user_app_name: str = Field(
        default="Unknown", description="App name for User-Agent header"
    )
    user_app_version: str = Field(
        default="Unknown", description="App version for User-Agent header"
    )

    def ensure_app_dir(self) -> None:
        """Ensure that the application directories exist."""
        self.app_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.token_store_dir.mkdir(parents=True, exist_ok=True)


class SettingsManager:
    """Manager for application settings with profile support.

    This class manages different settings profiles and provides
    a unified interface for accessing configuration.
    """

    _instance: ClassVar["SettingsManager | None"] = None
    _settings: EsiAuthSettings | None = None

    def __new__(cls) -> "SettingsManager":
        """Implement singleton pattern for settings manager.

        Returns:
            The singleton SettingsManager instance.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_settings(self, **kwargs: dict[str, Any]) -> EsiAuthSettings:
        """Get the current settings based on active profile.

        Returns:
            The appropriate settings instance for the current profile.
        """
        if self._settings is None:
            self._settings = EsiAuthSettings(**kwargs)  # type: ignore

            # Ensure the app directory exists
            self._settings.ensure_app_dir()

        return self._settings


def get_settings(**kwargs: dict[str, Any]) -> EsiAuthSettings:
    """Get the current application settings.

    This is a convenience function that returns the settings
    from the singleton SettingsManager instance.

    The kwargs are passed to the EsiAuthSettings constructor
    when the settings are first created, allowing for customization
    such as setting a different environment variable prefix, or loading a
    different .env file.

    Example kwargs:
        - _env_prefix: str = "ESI_AUTH_"  # Prefix for environment variables
        - _env_file: str = "/path/to/.env"  # Path to a .env file
        - _env_file_encoding: str = "utf-8"  # Encoding of the .env file

    https://docs.pydantic.dev/latest/concepts/pydantic_settings/#dotenv-env-support

    Returns:
        The current ESIAuthSettings instance.
    """
    manager = SettingsManager()
    return manager.get_settings(**kwargs)
