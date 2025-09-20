"""Application settings for ESI authentication.

This module contains Pydantic Settings models for managing configuration
including client credentials, application directory, and environment-specific
profiles.
"""

from pathlib import Path
from typing import ClassVar

import typer
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ESIAuthSettings(BaseSettings):
    """Application settings for ESI authentication.

    Settings are loaded from environment variables and .env files.
    The settings support different profiles for testing and production.
    """

    model_config = SettingsConfigDict(
        env_prefix="ESI_AUTH_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # OAuth2 credentials
    client_id: str = Field(
        ...,
        description="EVE Online application client ID from developers.eveonline.com",
    )
    client_secret: str = Field(
        ...,
        description="EVE Online application client secret from developers.eveonline.com",
    )

    # Application configuration
    app_name: str = Field(
        default="pfmsoft-esi-auth",
        description="Application name used for directory creation",
    )

    app_dir: Path = Field(
        default_factory=lambda: Path(typer.get_app_dir("pfmsoft-esi-auth")),
        description="Directory for storing application data",
    )

    # ESI API configuration
    esi_base_url: str = Field(
        default="https://esi.evetech.net", description="Base URL for EVE Online ESI API"
    )

    sso_base_url: str = Field(
        default="https://login.eveonline.com", description="Base URL for EVE Online SSO"
    )

    # OAuth2 flow configuration
    callback_host: str = Field(
        default="localhost", description="Host for OAuth callback server"
    )

    callback_port: int = Field(
        default=8080, description="Port for OAuth callback server"
    )

    # Token storage
    token_file_name: str = Field(
        default="character_tokens.json",
        description="Filename for storing character tokens",
    )

    # HTTP client configuration
    request_timeout: int = Field(
        default=30, description="HTTP request timeout in seconds"
    )

    max_retries: int = Field(
        default=3, description="Maximum number of HTTP request retries"
    )

    @property
    def token_file_path(self) -> Path:
        """Get the full path to the token storage file.

        Returns:
            Path object pointing to the token file.
        """
        return self.app_dir / self.token_file_name

    @property
    def callback_url(self) -> str:
        """Get the OAuth callback URL.

        Returns:
            The complete callback URL for OAuth flow.
        """
        return f"http://{self.callback_host}:{self.callback_port}/callback"

    @property
    def authorize_url(self) -> str:
        """Get the SSO authorization URL.

        Returns:
            The EVE Online SSO authorization endpoint URL.
        """
        return f"{self.sso_base_url}/v2/oauth/authorize"

    @property
    def token_url(self) -> str:
        """Get the SSO token URL.

        Returns:
            The EVE Online SSO token endpoint URL.
        """
        return f"{self.sso_base_url}/v2/oauth/token"

    def ensure_app_dir(self) -> None:
        """Ensure the application directory exists.

        Creates the application directory if it doesn't exist.
        """
        self.app_dir.mkdir(parents=True, exist_ok=True)


class TestingESIAuthSettings(ESIAuthSettings):
    """Testing-specific settings for ESI authentication.

    This class provides settings specifically for testing environments,
    including test client credentials and isolated data storage.
    """

    model_config = SettingsConfigDict(
        env_prefix="ESI_AUTH_TEST_",
        env_file=".env.test",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Testing OAuth2 credentials
    client_id: str = Field(
        default="test_client_id", description="Test EVE Online application client ID"
    )
    client_secret: str = Field(
        default="test_client_secret",
        description="Test EVE Online application client secret",
    )

    # Testing application configuration
    app_name: str = Field(
        default="pfmsoft-esi-auth-test", description="Test application name"
    )

    app_dir: Path = Field(
        default_factory=lambda: Path(typer.get_app_dir("pfmsoft-esi-auth-test")),
        description="Test directory for storing application data",
    )

    # Use different callback port for testing
    callback_port: int = Field(
        default=8081, description="Port for OAuth callback server during testing"
    )

    # Testing token storage
    token_file_name: str = Field(
        default="test_character_tokens.json",
        description="Filename for storing test character tokens",
    )


class SettingsManager:
    """Manager for application settings with profile support.

    This class manages different settings profiles and provides
    a unified interface for accessing configuration.
    """

    _instance: ClassVar["SettingsManager | None"] = None
    _settings: ESIAuthSettings | None = None
    _profile: str = "production"

    def __new__(cls) -> "SettingsManager":
        """Implement singleton pattern for settings manager.

        Returns:
            The singleton SettingsManager instance.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def set_profile(self, profile: str) -> None:
        """Set the active settings profile.

        Args:
            profile: The profile name ("production" or "testing").

        Raises:
            ValueError: If the profile is not supported.
        """
        if profile not in ["production", "testing"]:
            raise ValueError(f"Unsupported profile: {profile}")

        self._profile = profile
        self._settings = None  # Force reload of settings

    def get_settings(self) -> ESIAuthSettings:
        """Get the current settings based on active profile.

        Returns:
            The appropriate settings instance for the current profile.
        """
        if self._settings is None:
            if self._profile == "testing":
                self._settings = TestingESIAuthSettings()
            else:
                self._settings = ESIAuthSettings()

            # Ensure the app directory exists
            self._settings.ensure_app_dir()

        return self._settings

    @property
    def profile(self) -> str:
        """Get the current active profile.

        Returns:
            The name of the current active profile.
        """
        return self._profile


def get_settings() -> ESIAuthSettings:
    """Get the current application settings.

    This is a convenience function that returns the settings
    from the singleton SettingsManager instance.

    Returns:
        The current ESIAuthSettings instance.
    """
    manager = SettingsManager()
    return manager.get_settings()


def set_testing_profile() -> None:
    """Set the application to use testing profile.

    This is a convenience function for switching to testing mode.
    """
    manager = SettingsManager()
    manager.set_profile("testing")


def set_production_profile() -> None:
    """Set the application to use production profile.

    This is a convenience function for switching to production mode.
    """
    manager = SettingsManager()
    manager.set_profile("production")
