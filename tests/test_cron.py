"""
Testes para scripts cron.
"""
import os
from unittest.mock import MagicMock, patch

import pytest


class TestRelatorioDiario:
    """Testes para relatorio_diario.py."""

    @patch("cron.relatorio_diario.create_app")
    @patch("cron.relatorio_diario.enviar_relatorio_diario")
    @patch.dict(os.environ, {"NOTIFICACOES_ENABLED": "true"})
    def test_main_with_notifications_enabled(self, mock_enviar, mock_create_app):
        """Testa execução quando notificações estão habilitadas."""
        mock_app = MagicMock()
        mock_create_app.return_value = mock_app
        mock_app.app_context.return_value.__enter__ = MagicMock()
        mock_app.app_context.return_value.__exit__ = MagicMock(return_value=None)

        from cron import relatorio_diario

        relatorio_diario.main()

        mock_create_app.assert_called_once()
        mock_enviar.assert_called_once_with("automatico", False)

    @patch("cron.relatorio_diario.create_app")
    @patch("cron.relatorio_diario.enviar_relatorio_diario")
    @patch.dict(os.environ, {"NOTIFICACOES_ENABLED": "false"}, clear=False)
    def test_main_with_notifications_disabled(self, mock_enviar, mock_create_app):
        """Testa execução quando notificações estão desabilitadas."""
        from cron import relatorio_diario

        relatorio_diario.main()

        mock_create_app.assert_called_once()
        mock_enviar.assert_not_called()
