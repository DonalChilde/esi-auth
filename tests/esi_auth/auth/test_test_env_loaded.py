from esi_auth.settings import SettingsManager, get_settings


def test_secret_test_env():
    # Reset the singleton to ensure we get fresh test settings
    manager = SettingsManager()
    manager.reset()

    # Get settings with test-specific environment prefix
    settings = get_settings(_env_prefix="ESI_AUTH_TEST_")
    assert settings.client_id is not None
    print(f"Client ID: {settings.client_id}")
    print(f"Client Secret: {settings.client_secret}")
    assert settings.client_secret == "TestSecret-Disregard"
