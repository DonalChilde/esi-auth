"""Tests for core API functions."""

from unittest.mock import Mock, patch

from esi_auth.old import api
from esi_auth.old.models import AuthenticatedCharacters


class TestAPIFunctions:
    """Test core API functions."""

    def test_load_characters(self, temp_token_file, sample_character_token):
        """Test loading characters from storage."""
        # Create storage with test data
        with patch("esi_auth.api.get_token_storage") as mock_get_storage:
            mock_storage = Mock()
            mock_characters = AuthenticatedCharacters()
            mock_characters.add_character(sample_character_token)
            mock_storage.load_characters.return_value = mock_characters
            mock_get_storage.return_value = mock_storage

            characters = api.load_characters()

            assert len(characters.characters) == 1
            assert sample_character_token.character_id in characters.characters

    def test_list_characters(self, sample_character_token, expired_character_token):
        """Test listing all characters."""
        with patch("esi_auth.api.get_token_storage") as mock_get_storage:
            mock_storage = Mock()
            mock_storage.list_characters.return_value = [
                sample_character_token,
                expired_character_token,
            ]
            mock_get_storage.return_value = mock_storage

            characters = api.list_characters()

            assert len(characters) == 2
            assert sample_character_token in characters
            assert expired_character_token in characters

    def test_get_character(self, sample_character_token):
        """Test getting a specific character."""
        with patch("esi_auth.api.get_token_storage") as mock_get_storage:
            mock_storage = Mock()
            mock_storage.get_character.return_value = sample_character_token
            mock_get_storage.return_value = mock_storage

            character = api.get_character(sample_character_token.character_id)

            assert character == sample_character_token
            mock_storage.get_character.assert_called_once_with(
                sample_character_token.character_id
            )

    def test_get_character_not_found(self):
        """Test getting a character that doesn't exist."""
        with patch("esi_auth.api.get_token_storage") as mock_get_storage:
            mock_storage = Mock()
            mock_storage.get_character.return_value = None
            mock_get_storage.return_value = mock_storage

            character = api.get_character(99999999)

            assert character is None

    def test_remove_character(self, sample_character_token):
        """Test removing a character."""
        with patch("esi_auth.api.get_token_storage") as mock_get_storage:
            mock_storage = Mock()
            mock_storage.remove_character.return_value = True
            mock_get_storage.return_value = mock_storage

            removed = api.remove_character(sample_character_token.character_id)

            assert removed is True
            mock_storage.remove_character.assert_called_once_with(
                sample_character_token.character_id
            )

    def test_remove_character_not_found(self):
        """Test removing a character that doesn't exist."""
        with patch("esi_auth.api.get_token_storage") as mock_get_storage:
            mock_storage = Mock()
            mock_storage.remove_character.return_value = False
            mock_get_storage.return_value = mock_storage

            removed = api.remove_character(99999999)

            assert removed is False

    def test_backup_characters(self, tmp_path):
        """Test backing up characters."""
        backup_path = tmp_path / "backup.json"

        with patch("esi_auth.api.get_token_storage") as mock_get_storage:
            mock_storage = Mock()
            mock_storage.backup_storage.return_value = backup_path
            mock_get_storage.return_value = mock_storage

            result_path = api.backup_characters(backup_path)

            assert result_path == backup_path
            mock_storage.backup_storage.assert_called_once_with(backup_path)

    def test_restore_characters(self, tmp_path):
        """Test restoring characters from backup."""
        backup_path = tmp_path / "backup.json"

        with patch("esi_auth.api.get_token_storage") as mock_get_storage:
            mock_storage = Mock()
            mock_get_storage.return_value = mock_storage

            api.restore_characters(backup_path)

            mock_storage.restore_from_backup.assert_called_once_with(backup_path)
