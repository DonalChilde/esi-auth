from esi_auth.auth_helpers import get_token
from esi_auth.settings import get_settings


def test_get_token():
    settings = get_settings()
    assert settings.client_id is not None
    print(f"Client ID: {settings.client_id}")
    print(f"Client Secret: {settings.client_secret}")
    assert settings.client_secret == "TestSecret-Disregard"
    # token = get_token()
    # assert token is not None
    # assert isinstance(token, str)
    # assert len(token) > 0
    # print(f"Token: {token}")
