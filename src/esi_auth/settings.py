"""Settings for the ESI Auth application."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from esi_auth import DEFAULT_APP_DIR

_app_env_prefix = "PFMSOFT_ESI_AUTH_"


class EsiAuthSettings(BaseSettings):
    """Settings for the ESI Auth application."""

    log_dir: Path = Field(
        default=DEFAULT_APP_DIR / "logs", description="Directory for log files."
    )
    app_dir: Path = Field(
        default=DEFAULT_APP_DIR, description="Directory for application data."
    )
    connection_string: str = Field(
        default=f"esi-auth-file:{DEFAULT_APP_DIR.resolve()}/esi-auth-store.json",
        description="Connection string for a json based auth store.",
    )
    auth_server_timeout: int = Field(
        default=300,
        description="Timeout in seconds for the auth server to respond.",
        ge=1,
        le=300,  # Max 5 minutes
    )
    character_name: str = Field(
        default="Unknown",
        description="Name of the EVE Online character of the developer of the app that is using ESI Auth.",
    )
    user_email: str = Field(
        default="Unknown",
        description="Email of the the developer of the app that is using ESI Auth.",
    )
    user_app_name: str = Field(
        default="Unknown", description="Name of the application using ESI Auth."
    )
    user_app_version: str = Field(
        default="Unknown", description="Version of the application using ESI Auth."
    )

    model_config = SettingsConfigDict(
        env_prefix=_app_env_prefix,
        env_file=(f"{DEFAULT_APP_DIR.resolve()}/.esi-auth.env", ".esi-auth.env"),
        env_file_encoding="utf-8",
    )


def get_settings() -> EsiAuthSettings:
    """Retrieve the ESI Auth settings.

    Returns:
        An instance of EsiAuthSettings with the loaded configuration.
    """
    return EsiAuthSettings()


def env_example() -> str:
    """Provide an example of the .esi-auth.env file configuration for user-agent settings.

    Returns:
        A string containing the example .esi-auth.env configuration.
    """
    env_example_str = f"""# ESI Auth .esi-auth.env Configuration Example
# Uncomment lines to use them.
# Replace the placeholder values with your actual information.

# esi-auth will look for this file in the application data directory and in the
# current working directory. If found in both places, settings from the current working
# directory take precedence.

# The App Directory is where application data is stored.
#{_app_env_prefix}APP_DIR="{DEFAULT_APP_DIR.resolve()}"

##### Logging and Store Configuration #####

# The logging directory is where log files will be stored.
#{_app_env_prefix}LOG_DIR="${{{_app_env_prefix}APP_DIR}}/logs"



# Connection string for the auth store. This example uses a file-based store.
# possible formats: 
#  - "esi-auth-file:/path/to/store.json"
#  - "esi-auth-sqlite:/path/to/store.db" (for future use)
#{_app_env_prefix}CONNECTION_STRING="esi-auth-file:${{{_app_env_prefix}APP_DIR}}/esi-auth-store.json"

##### Auth Server Timeout #####

# Timeout in seconds for the auth server to respond. Default is 300 seconds (5 minutes).
#{_app_env_prefix}AUTH_SERVER_TIMEOUT="300"

##### User-Agent Information #####

# These fields identify your application when making requests to the EVE Online ESI API.
# The information will be used by CCP to contact you in case of issues with your application.
# They must be set before making any network requests.

# The name of the EVE Online character of the developer of the app that is using ESI Auth.
{_app_env_prefix}CHARACTER_NAME="UNKNOWN"

# The email of the developer of the app that is using ESI Auth.
{_app_env_prefix}USER_EMAIL="UNKNOWN"

# The name of the application using ESI Auth.
{_app_env_prefix}USER_APP_NAME="UNKNOWN"

# The version of the application using ESI Auth.
{_app_env_prefix}USER_APP_VERSION="UNKNOWN"
"""
    return env_example_str
