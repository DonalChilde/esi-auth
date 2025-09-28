import logging

import pytest
from dotenv import find_dotenv, load_dotenv

from esi_auth.settings import get_settings

logger = logging.getLogger(__name__)

# # Load test environment variables before any tests are run.
# load_dotenv(find_dotenv(".test.env"), override=True)
# # Use the SettingsManager singleton to load settings with test-specific environment variable prefix.
# get_settings(_env_prefix="ESI_AUTH_TEST_")  # type: ignore

# print("Loaded test environment variables from .test.env")
# print(os.environ)  # For debugging purposes, print all environment variables.


@pytest.fixture(autouse=True)
def load_env():
    """Fixture to ensure environment variables are loaded for each test."""
    env_file = find_dotenv(".test.env")
    if not env_file:
        pytest.fail("Could not find .test.env file for loading environment variables.")
    load_dotenv(env_file, override=True)
    # get_settings(_env_prefix="ESI_AUTH_TEST_")  # type: ignore
    logger.info("Loaded test environment variables from .test.env")


# TODO make a fixture for a test output directory
# TODO make a fixture to inject the app_dir env setting
