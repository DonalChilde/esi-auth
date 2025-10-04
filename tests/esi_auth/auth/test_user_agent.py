import pytest

from esi_auth.helpers import get_package_url, get_user_agent

# FIXME make a test env generator to support testing env loading in a test environment.


@pytest.mark.skip
def test_get_user_agent():
    user_agent = get_user_agent()
    assert "esi-auth" in user_agent
    assert "eve:" in user_agent
    assert "/" in user_agent
    assert "(" in user_agent
    assert ")" in user_agent
    assert ";" in user_agent
    assert "pfmsoft" in user_agent
    print(f"User-Agent: {user_agent}")


@pytest.mark.skip
def test_get_package_url():
    url = get_package_url("esi-auth", "Source")
    assert url == "https://github.com/DonalChilde/esi-auth"
    # assert False
