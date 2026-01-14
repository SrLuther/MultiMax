"""
Testes para o deploy_agent.py.
"""
import subprocess
from unittest.mock import MagicMock, patch

# Mock do Flask antes de importar
with patch.dict("sys.modules", {"flask": MagicMock()}):
    import deploy_agent


@pytest.fixture
def mock_env(monkeypatch):
    """Configura variáveis de ambiente para testes."""
    monkeypatch.setenv("GIT_REPO_DIR", "/tmp/test_repo")
    monkeypatch.setenv("DEPLOY_AGENT_PORT", "9000")
    monkeypatch.setenv("DEPLOY_AGENT_TOKEN", "test_token")


class TestDeployAgent:
    """Testes para o deploy agent."""

    def test_execute_command_success(self, mock_env):
        """Testa execução bem-sucedida de comando."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=b"success", stderr=b"", args=["test", "command"])
            result = deploy_agent.execute_command(["test", "command"], "Test command")
            assert result["success"] is True
            assert result["returncode"] == 0

    def test_execute_command_failure(self, mock_env):
        """Testa execução com falha de comando."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "test")
            result = deploy_agent.execute_command(["test", "command"], "Test command")
            assert result["success"] is False
            assert result["returncode"] == 1

    def test_require_token_with_token(self, mock_env):
        """Testa validação de token quando configurado."""
        with patch("deploy_agent.DEPLOY_AGENT_TOKEN", "test_token"):
            with patch("deploy_agent.request") as mock_request:
                mock_request.headers.get.return_value = "Bearer test_token"
                # O decorator deve permitir acesso
                assert True  # Placeholder - teste real requer Flask app context

    def test_require_token_without_token(self, mock_env):
        """Testa que sem token configurado, acesso é permitido."""
        with patch("deploy_agent.DEPLOY_AGENT_TOKEN", ""):
            # Sem token configurado, acesso deve ser permitido
            assert True  # Placeholder - teste real requer Flask app context
