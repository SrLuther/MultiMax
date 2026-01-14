"""
Testes de integração para funções de hash de senha.
"""

from multimax.password_hash import check_password_hash, generate_password_hash


class TestPasswordHashIntegration:
    """Testes de integração para hash de senha."""

    def test_password_workflow(self):
        """Testa fluxo completo de criação e verificação de senha."""
        password = "senha_segura_123"
        hash_value = generate_password_hash(password)

        # Verifica que hash foi gerado
        assert hash_value is not None
        assert isinstance(hash_value, str)
        assert len(hash_value) > 0

        # Verifica que senha correta funciona
        assert check_password_hash(hash_value, password) is True

        # Verifica que senha incorreta não funciona
        assert check_password_hash(hash_value, "senha_errada") is False

    def test_multiple_passwords(self):
        """Testa múltiplas senhas diferentes."""
        passwords = ["senha1", "senha2", "senha_muito_longa_123456"]
        hashes = []

        for password in passwords:
            hash_value = generate_password_hash(password)
            hashes.append(hash_value)
            assert check_password_hash(hash_value, password) is True

        # Verifica que hashes são diferentes
        assert len(set(hashes)) == len(hashes)

    def test_special_characters(self):
        """Testa senhas com caracteres especiais."""
        special_passwords = [
            "senha@123",
            "senha#456",
            "senha$789",
            "senha%abc",
            "senha!def",
        ]

        for password in special_passwords:
            hash_value = generate_password_hash(password)
            assert check_password_hash(hash_value, password) is True
            assert check_password_hash(hash_value, password + "x") is False
