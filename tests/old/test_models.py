"""Tests for data models."""

from whenever import Instant

from esi_auth.old.old_models import AuthenticatedCharacters, CharacterToken


class TestCharacterToken:
    """Test CharacterToken model."""

    def test_character_token_creation(self, sample_character_token):
        """Test creating a character token."""
        assert sample_character_token.character_id == 12345678
        assert sample_character_token.character_name == "Test Character"
        assert sample_character_token.access_token == "test_access_token"
        assert sample_character_token.refresh_token == "test_refresh_token"
        assert sample_character_token.token_type == "Bearer"
        assert len(sample_character_token.scopes) == 1

    def test_is_expired_false(self, sample_character_token):
        """Test that a future token is not expired."""
        assert not sample_character_token.is_expired()

    def test_is_expired_true(self, expired_character_token):
        """Test that a past token is expired."""
        assert expired_character_token.is_expired()

    def test_needs_refresh_false(self, sample_character_token):
        """Test that a token with plenty of time doesn't need refresh."""
        assert not sample_character_token.needs_refresh(buffer_minutes=5)

    def test_needs_refresh_true(self):
        """Test that a token close to expiry needs refresh."""
        # Create token that expires in 2 minutes
        token = CharacterToken(
            character_id=12345678,
            character_name="Test Character",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            expires_at=Instant.now().add(minutes=2),
            scopes=["esi-characters.read_character.v1"],
        )

        assert token.needs_refresh(buffer_minutes=5)

    def test_needs_refresh_custom_buffer(self):
        """Test needs_refresh with custom buffer."""
        # Create token that expires in 10 minutes
        token = CharacterToken(
            character_id=12345678,
            character_name="Test Character",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            expires_at=Instant.now().add(minutes=10),
            scopes=["esi-characters.read_character.v1"],
        )

        assert not token.needs_refresh(buffer_minutes=5)
        assert token.needs_refresh(buffer_minutes=15)


class TestAuthenticatedCharacters:
    """Test AuthenticatedCharacters model."""

    def test_empty_collection(self):
        """Test creating an empty character collection."""
        characters = AuthenticatedCharacters()
        assert len(characters.characters) == 0
        assert len(characters.list_characters()) == 0

    def test_add_character(self, sample_character_token):
        """Test adding a character to the collection."""
        characters = AuthenticatedCharacters()
        characters.add_character(sample_character_token)

        assert len(characters.characters) == 1
        assert sample_character_token.character_id in characters.characters
        assert (
            characters.get_character(sample_character_token.character_id)
            == sample_character_token
        )

    def test_remove_character(self, sample_character_token):
        """Test removing a character from the collection."""
        characters = AuthenticatedCharacters()
        characters.add_character(sample_character_token)

        removed = characters.remove_character(sample_character_token.character_id)
        assert removed is True
        assert len(characters.characters) == 0
        assert characters.get_character(sample_character_token.character_id) is None

    def test_remove_nonexistent_character(self):
        """Test removing a character that doesn't exist."""
        characters = AuthenticatedCharacters()
        removed = characters.remove_character(99999999)
        assert removed is False

    def test_get_character_not_found(self):
        """Test getting a character that doesn't exist."""
        characters = AuthenticatedCharacters()
        result = characters.get_character(99999999)
        assert result is None

    def test_list_characters(self, sample_character_token, expired_character_token):
        """Test listing all characters."""
        characters = AuthenticatedCharacters()
        characters.add_character(sample_character_token)
        characters.add_character(expired_character_token)

        char_list = characters.list_characters()
        assert len(char_list) == 2
        assert sample_character_token in char_list
        assert expired_character_token in char_list

    def test_get_expired_tokens(self, sample_character_token, expired_character_token):
        """Test getting expired tokens."""
        characters = AuthenticatedCharacters()
        characters.add_character(sample_character_token)
        characters.add_character(expired_character_token)

        expired_tokens = characters.get_expired_tokens()
        assert len(expired_tokens) == 1
        assert expired_character_token in expired_tokens
        assert sample_character_token not in expired_tokens

    def test_get_tokens_needing_refresh(
        self, sample_character_token, expired_character_token
    ):
        """Test getting tokens that need refresh."""
        characters = AuthenticatedCharacters()
        characters.add_character(sample_character_token)
        characters.add_character(expired_character_token)

        # Create token that expires soon
        soon_expiring_token = CharacterToken(
            character_id=11111111,
            character_name="Soon Expiring Character",
            access_token="soon_expiring_access_token",
            refresh_token="soon_expiring_refresh_token",
            expires_at=Instant.now().add(minutes=2),
            scopes=["esi-characters.read_character.v1"],
        )
        characters.add_character(soon_expiring_token)

        # Test with default buffer (5 minutes)
        needing_refresh = characters.get_tokens_needing_refresh()
        assert len(needing_refresh) == 2  # expired and soon expiring
        assert expired_character_token in needing_refresh
        assert soon_expiring_token in needing_refresh
        assert sample_character_token not in needing_refresh
