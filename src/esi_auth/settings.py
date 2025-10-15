"""Application settings for esi-auth."""

from pathlib import Path
from typing import Any, ClassVar

import typer
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

NAMESPACE = "pfmsoft"
APPLICATION_NAME = "esi-auth"
DEFAULT_APP_DIR = Path(typer.get_app_dir(f"{NAMESPACE}-{APPLICATION_NAME}"))
ESI_BASE_URL = "https://esi.evetech.net"
SSO_BASE_URL = "https://login.eveonline.com"
OAUTH_METADATA_URL = (
    "https://login.eveonline.com/.well-known/oauth-authorization-server"
)
TOKEN_ENDPOINT = "https://login.eveonline.com/v2/oauth/token"
AUTHORIZATION_ENDPOINT = "https://login.eveonline.com/v2/oauth/authorize"
JWKS_URI = "https://login.eveonline.com/oauth/jwks"
OAUTH_ISSUER = ["https://login.eveonline.com"]
OAUTH_AUDIENCE = "EVE Online"


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
        env_file=(str(DEFAULT_APP_DIR / ".env"), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    ############################################################################
    # Application configuration
    ############################################################################
    # TODO possibly unneeded
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

    auth_store_dir: Path = Field(
        default=DEFAULT_APP_DIR, description="The directory containing the Auth Store."
    )
    auth_store_file_name: str = Field(
        default="auth-store.json", description="File Name for the Auth Store."
    )

    # HTTP client configuration
    request_timeout: int = Field(
        default=30, description="HTTP request timeout in seconds"
    )

    server_timeout: int = Field(
        default=300, description="The timeout for the authorization server."
    )

    # Authorization metadata endpoint - https://login.eveonline.com/.well-known/oauth-authorization-server
    oauth2_authorization_metadata_url: str = Field(
        default=OAUTH_METADATA_URL,
        description="URL for OAuth2 authorization server metadata",
    )

    def ensure_app_dir(self) -> None:
        """Ensure that the application directories exist."""
        self.app_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.auth_store_dir.mkdir(parents=True, exist_ok=True)
        # self.token_store_dir.mkdir(parents=True, exist_ok=True)
        # self.credential_store_dir.mkdir(parents=True, exist_ok=True)

    # @field_validator("oauth2_issuer", mode="before")
    # @classmethod
    # def json_decode(cls, v: Any) -> list[str]:
    #     """Decode JSON string to list if necessary."""
    #     if isinstance(v, str):
    #         try:
    #             return json.loads(v)
    #         except ValueError:
    #             pass
    #     if isinstance(v, list):
    #         return v  # pyright: ignore[reportUnknownVariableType]
    #     raise ValueError("Invalid format for scopes")


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

    def reset(self) -> None:
        """Reset the settings manager, clearing cached settings.

        This is primarily useful for testing scenarios where you need
        to reload settings with different parameters.
        """
        self._settings = None


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


def example_env() -> str:
    """Create the text of an example env file."""
    return ""
