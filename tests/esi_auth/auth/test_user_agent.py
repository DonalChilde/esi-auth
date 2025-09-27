from esi_auth.auth import get_package_url, get_user_agent


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


def test_get_package_url():
    url = get_package_url("esi-auth", "Source")
    assert url == "https://github.com/DonalChilde/esi-auth"
