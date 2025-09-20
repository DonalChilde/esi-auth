"""Test configuration and fixtures for esi-auth tests."""

from pathlib import Path
from unittest.mock import Mock

import pytest
from whenever import Instant

from esi_auth.models import CharacterToken
from esi_auth.settings import set_testing_profile


@pytest.fixture(autouse=True)
def use_testing_profile():
    """Automatically use testing profile for all tests."""
    set_testing_profile()


@pytest.fixture
def sample_character_token() -> CharacterToken:
    """Create a sample character token for testing."""
    return CharacterToken(
        character_id=12345678,
        character_name="Test Character",
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        expires_at=Instant.now().add(hours=1),
        scopes=["esi-characters.read_character.v1"],
        token_type="Bearer",
    )


@pytest.fixture
def expired_character_token() -> CharacterToken:
    """Create an expired character token for testing."""
    return CharacterToken(
        character_id=87654321,
        character_name="Expired Character",
        access_token="expired_access_token",
        refresh_token="expired_refresh_token",
        expires_at=Instant.now().subtract(hours=1),  # Expired 1 hour ago
        scopes=["esi-characters.read_character.v1"],
        token_type="Bearer",
    )


@pytest.fixture
def temp_token_file(tmp_path: Path) -> Path:
    """Create a temporary token file path for testing."""
    return tmp_path / "test_tokens.json"


@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp session for testing."""
    session = Mock()

    # Mock successful token response
    token_response = Mock()
    token_response.status = 200
    token_response.json.return_value = {
        "access_token": "new_access_token",
        "refresh_token": "new_refresh_token",
        "expires_in": 3600,
        "token_type": "Bearer",
    }

    # Mock successful character verification
    verify_response = Mock()
    verify_response.status = 200
    verify_response.json.return_value = {
        "CharacterID": 12345678,
        "CharacterName": "Test Character",
        "Scopes": ["esi-characters.read_character.v1"],
    }

    # Mock successful character info response
    char_response = Mock()
    char_response.status = 200
    char_response.json.return_value = {
        "name": "Test Character",
        "description": "Test character description",
        "corporation_id": 98765432,
        "alliance_id": None,
        "birthday": "2021-01-01T00:00:00Z",
        "gender": "male",
        "race_id": 1,
        "bloodline_id": 1,
        "ancestry_id": 1,
        "security_status": 0.5,
    }

    session.post.return_value.__aenter__.return_value = token_response
    session.get.return_value.__aenter__.return_value = verify_response

    return session
