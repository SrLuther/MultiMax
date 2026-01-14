"""
Testes para funções de hash de senha.
"""
import pytest

from multimax.password_hash import check_password_hash, generate_password_hash


class TestPasswordHash:
    """Testes para hash de senha."""

    def test_generate_password_hash(self):
        """Testa geração de hash de senha."""
        password = "testpass123"
        hash_value = generate_password_hash(password)
        assert hash_value is not None
        assert isinstance(hash_value, str)
        assert hash_value != password
        assert len(hash_value) > 0

    def test_check_password_hash_success(self):
        """Testa verificação de senha correta."""
        password = "testpass123"
        hash_value = generate_password_hash(password)
        assert check_password_hash(hash_value, password) is True

    def test_check_password_hash_failure(self):
        """Testa verificação de senha incorreta."""
        password = "testpass123"
        wrong_password = "wrongpass456"
        hash_value = generate_password_hash(password)
        assert check_password_hash(hash_value, wrong_password) is False

    def test_different_hashes_for_same_password(self):
        """Testa que hashes diferentes são gerados para a mesma senha (salt)."""
        password = "testpass123"
        hash1 = generate_password_hash(password)
        hash2 = generate_password_hash(password)
        # Hashes devem ser diferentes devido ao salt
        assert hash1 != hash2
        # Mas ambos devem verificar a senha corretamente
        assert check_password_hash(hash1, password) is True
        assert check_password_hash(hash2, password) is True
