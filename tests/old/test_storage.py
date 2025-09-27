"""Tests for token storage system."""

import pytest

from esi_auth.old.old_models import AuthenticatedCharacters
from esi_auth.old.old_storage import TokenStorage, TokenStorageError


class TestTokenStorage:
    """Test TokenStorage functionality."""

    def test_init_with_custom_path(self, temp_token_file):
        """Test initializing TokenStorage with custom path."""
        storage = TokenStorage(temp_token_file)
        assert storage.storage_path == temp_token_file

    def test_load_characters_no_file(self, temp_token_file):
        """Test loading characters when file doesn't exist."""
        storage = TokenStorage(temp_token_file)
        characters = storage.load_characters()

        assert isinstance(characters, AuthenticatedCharacters)
        assert len(characters.characters) == 0

    def test_save_and_load_characters(self, temp_token_file, sample_character_token):
        """Test saving and loading characters."""
        storage = TokenStorage(temp_token_file)

        # Create and save characters
        characters = AuthenticatedCharacters()
        characters.add_character(sample_character_token)
        storage.save_characters(characters)

        # Verify file exists
        assert temp_token_file.exists()

        # Load and verify
        loaded_characters = storage.load_characters()
        assert len(loaded_characters.characters) == 1

        loaded_token = loaded_characters.get_character(
            sample_character_token.character_id
        )
        assert loaded_token is not None
        assert loaded_token.character_name == sample_character_token.character_name
        assert loaded_token.access_token == sample_character_token.access_token

    def test_load_invalid_json(self, temp_token_file):
        """Test loading from file with invalid JSON."""
        # Write invalid JSON to file
        temp_token_file.write_text("invalid json content")

        storage = TokenStorage(temp_token_file)
        with pytest.raises(TokenStorageError):
            storage.load_characters()

    def test_add_character(self, temp_token_file, sample_character_token):
        """Test adding a character to storage."""
        storage = TokenStorage(temp_token_file)
        storage.add_character(sample_character_token)

        # Verify character was saved
        characters = storage.load_characters()
        assert len(characters.characters) == 1
        assert sample_character_token.character_id in characters.characters

    def test_remove_character(self, temp_token_file, sample_character_token):
        """Test removing a character from storage."""
        storage = TokenStorage(temp_token_file)

        # Add character first
        storage.add_character(sample_character_token)

        # Remove character
        removed = storage.remove_character(sample_character_token.character_id)
        assert removed is True

        # Verify character was removed
        characters = storage.load_characters()
        assert len(characters.characters) == 0

    def test_remove_nonexistent_character(self, temp_token_file):
        """Test removing a character that doesn't exist."""
        storage = TokenStorage(temp_token_file)
        removed = storage.remove_character(99999999)
        assert removed is False

    def test_get_character(self, temp_token_file, sample_character_token):
        """Test getting a character from storage."""
        storage = TokenStorage(temp_token_file)
        storage.add_character(sample_character_token)

        token = storage.get_character(sample_character_token.character_id)
        assert token is not None
        assert token.character_name == sample_character_token.character_name

    def test_get_nonexistent_character(self, temp_token_file):
        """Test getting a character that doesn't exist."""
        storage = TokenStorage(temp_token_file)
        token = storage.get_character(99999999)
        assert token is None

    def test_list_characters(
        self, temp_token_file, sample_character_token, expired_character_token
    ):
        """Test listing all characters from storage."""
        storage = TokenStorage(temp_token_file)
        storage.add_character(sample_character_token)
        storage.add_character(expired_character_token)

        characters = storage.list_characters()
        assert len(characters) == 2

        char_ids = [token.character_id for token in characters]
        assert sample_character_token.character_id in char_ids
        assert expired_character_token.character_id in char_ids

    def test_backup_storage(self, temp_token_file, sample_character_token, tmp_path):
        """Test creating a backup of storage."""
        storage = TokenStorage(temp_token_file)
        storage.add_character(sample_character_token)

        # Create backup
        backup_path = storage.backup_storage()

        # Verify backup exists and has correct content
        assert backup_path.exists()
        assert backup_path.parent == temp_token_file.parent

        # Verify backup content
        backup_storage = TokenStorage(backup_path)
        characters = backup_storage.load_characters()
        assert len(characters.characters) == 1

    def test_backup_nonexistent_file(self, temp_token_file):
        """Test backing up when storage file doesn't exist."""
        storage = TokenStorage(temp_token_file)

        with pytest.raises(TokenStorageError):
            storage.backup_storage()

    def test_restore_from_backup(
        self, temp_token_file, sample_character_token, tmp_path
    ):
        """Test restoring from a backup file."""
        # Create original storage with character
        storage = TokenStorage(temp_token_file)
        storage.add_character(sample_character_token)

        # Create backup
        backup_path = storage.backup_storage()

        # Clear original storage
        characters = AuthenticatedCharacters()
        storage.save_characters(characters)

        # Verify storage is empty
        assert len(storage.load_characters().characters) == 0

        # Restore from backup
        storage.restore_from_backup(backup_path)

        # Verify restoration
        characters = storage.load_characters()
        assert len(characters.characters) == 1
        assert sample_character_token.character_id in characters.characters

    def test_restore_from_nonexistent_backup(self, temp_token_file, tmp_path):
        """Test restoring from a nonexistent backup file."""
        storage = TokenStorage(temp_token_file)
        nonexistent_backup = tmp_path / "nonexistent_backup.json"

        with pytest.raises(TokenStorageError):
            storage.restore_from_backup(nonexistent_backup)

    def test_atomic_write(self, temp_token_file, sample_character_token):
        """Test that writes are atomic (using temporary file)."""
        storage = TokenStorage(temp_token_file)

        # Save character
        storage.add_character(sample_character_token)

        # Verify no .tmp file exists after successful write
        temp_files = list(temp_token_file.parent.glob("*.tmp"))
        assert len(temp_files) == 0
