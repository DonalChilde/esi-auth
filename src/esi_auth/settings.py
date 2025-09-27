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
        env_file=(str(DEFAULT_APP_DIR / ".env"), ".env"),
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
    scopes: Sequence[str] = Field(
        default=[
            "esi-corporations.read_projects.v1",
            "publicData",
            "esi-calendar.respond_calendar_events.v1",
            "esi-calendar.read_calendar_events.v1",
            "esi-location.read_location.v1",
            "esi-location.read_ship_type.v1",
            "esi-mail.organize_mail.v1",
            "esi-mail.read_mail.v1",
            "esi-mail.send_mail.v1",
            "esi-skills.read_skills.v1",
            "esi-skills.read_skillqueue.v1",
            "esi-wallet.read_character_wallet.v1",
            "esi-wallet.read_corporation_wallet.v1",
            "esi-search.search_structures.v1",
            "esi-clones.read_clones.v1",
            "esi-characters.read_contacts.v1",
            "esi-universe.read_structures.v1",
            "esi-killmails.read_killmails.v1",
            "esi-corporations.read_corporation_membership.v1",
            "esi-assets.read_assets.v1",
            "esi-planets.manage_planets.v1",
            "esi-fleets.read_fleet.v1",
            "esi-fleets.write_fleet.v1",
            "esi-ui.open_window.v1",
            "esi-ui.write_waypoint.v1",
            "esi-characters.write_contacts.v1",
            "esi-fittings.read_fittings.v1",
            "esi-fittings.write_fittings.v1",
            "esi-markets.structure_markets.v1",
            "esi-corporations.read_structures.v1",
            "esi-characters.read_loyalty.v1",
            "esi-characters.read_chat_channels.v1",
            "esi-characters.read_medals.v1",
            "esi-characters.read_standings.v1",
            "esi-characters.read_agents_research.v1",
            "esi-industry.read_character_jobs.v1",
            "esi-markets.read_character_orders.v1",
            "esi-characters.read_blueprints.v1",
            "esi-characters.read_corporation_roles.v1",
            "esi-location.read_online.v1",
            "esi-contracts.read_character_contracts.v1",
            "esi-clones.read_implants.v1",
            "esi-characters.read_fatigue.v1",
            "esi-killmails.read_corporation_killmails.v1",
            "esi-corporations.track_members.v1",
            "esi-wallet.read_corporation_wallets.v1",
            "esi-characters.read_notifications.v1",
            "esi-corporations.read_divisions.v1",
            "esi-corporations.read_contacts.v1",
            "esi-assets.read_corporation_assets.v1",
            "esi-corporations.read_titles.v1",
            "esi-corporations.read_blueprints.v1",
            "esi-contracts.read_corporation_contracts.v1",
            "esi-corporations.read_standings.v1",
            "esi-corporations.read_starbases.v1",
            "esi-industry.read_corporation_jobs.v1",
            "esi-markets.read_corporation_orders.v1",
            "esi-corporations.read_container_logs.v1",
            "esi-industry.read_character_mining.v1",
            "esi-industry.read_corporation_mining.v1",
            "esi-planets.read_customs_offices.v1",
            "esi-corporations.read_facilities.v1",
            "esi-corporations.read_medals.v1",
            "esi-characters.read_titles.v1",
            "esi-alliances.read_contacts.v1",
            "esi-characters.read_fw_stats.v1",
            "esi-corporations.read_fw_stats.v1",
        ],
        description="Default OAuth2 scopes for authentication",
    )

    # ESI API configuration
    esi_base_url: str = Field(
        default="https://esi.evetech.net", description="Base URL for EVE Online ESI API"
    )

    sso_base_url: str = Field(
        default="https://login.eveonline.com", description="Base URL for EVE Online SSO"
    )

    # Authorization metadata endpoint - https://login.eveonline.com/.well-known/oauth-authorization-server
    oauth2_authorization_metadata_url: str = Field(
        default="https://login.eveonline.com/.well-known/oauth-authorization-server",
        description="URL for OAuth2 authorization server metadata",
    )
    authorization_endpoint: str = Field(
        default="https://login.eveonline.com/v2/oauth/authorize",
        description="URL for OAuth2 authorization endpoint",
    )
    token_endpoint: str = Field(
        default="https://login.eveonline.com/v2/oauth/token",
        description="URL for OAuth2 token endpoint",
    )
    jwks_uri: str = Field(
        default="https://login.eveonline.com/oauth/jwks",
        description="URL for OAuth2 JSON Web Key Set (JWKS) endpoint",
    )

    # Audience for token validation
    oauth2_audience: str = Field(
        default="EVE Online", description="Audience for validating JWT tokens"
    )

    # Issuer for token validation
    oauth2_issuer: Sequence[str] = Field(
        default=["https://login.eveonline.com"],
        description="Issuer for validating JWT tokens",
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
