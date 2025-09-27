from dotenv import load_dotenv

from esi_auth.settings import get_settings

# Load test environment variables before any tests are run.
load_dotenv("tests/fixtures/test.environment", override=True)
# Use the SettingsManager singleton to load settings with test-specific environment variable prefix.
get_settings(_env_prefix="ESI_AUTH_TEST_")  # type: ignore
