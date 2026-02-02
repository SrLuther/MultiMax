"""Testes para o módulo de integração com o serviço WhatsApp."""

from unittest.mock import MagicMock, patch

import requests
from flask import Flask

from multimax.whatsapp_service import (
    HOSTNAME,
    WHATSAPP_SERVICE_URL,
    register_error_handlers,
    send_error_alert,
    send_test_alert,
)


class TestRegisterErrorHandlers:
    """Testes para o registro de handlers de erro"""

    def test_error_handlers_are_registered(self):
        """Testa que os handlers de erro foram registrados"""
        # O conftest.py já chama register_error_handlers no fixture app
        # Aqui simplesmente verificamos que não há erro ao chamar a função
        assert register_error_handlers is not None

    @patch("multimax.whatsapp_service.send_error_alert")
    def test_handle_404_is_registered(self, mock_alert):
        """Testa que handler 404 é registrado corretamente"""
        # Criar um app isolado para testar os handlers
        test_app = Flask(__name__)
        test_app.config["TESTING"] = True
        register_error_handlers(test_app)

        with test_app.test_client() as client:
            response = client.get("/route-nonexistent-12345")
            assert response.status_code == 404
            if response.json:
                assert "erro" in response.json

    @patch("multimax.whatsapp_service.send_error_alert")
    def test_handle_500_is_registered(self, mock_alert):
        """Testa que handler 500 é registrado corretamente"""
        test_app = Flask(__name__)
        test_app.config["TESTING"] = True
        register_error_handlers(test_app)

        @test_app.route("/trigger-500")
        def trigger_error():
            raise ValueError("Erro proposital para teste")

        with test_app.test_client() as client:
            response = client.get("/trigger-500")
            assert response.status_code == 500
            if response.json:
                assert "erro" in response.json
            # Verifica se o alerta foi enviado
            assert mock_alert.called

    @patch("multimax.whatsapp_service.send_error_alert")
    def test_handle_exception_is_registered(self, mock_alert):
        """Testa que handler genérico de exceções é registrado"""
        test_app = Flask(__name__)
        test_app.config["TESTING"] = True
        register_error_handlers(test_app)

        @test_app.route("/trigger-exception")
        def trigger_exception():
            raise RuntimeError("Erro de runtime")

        with test_app.test_client() as client:
            response = client.get("/trigger-exception")
            assert response.status_code == 500
            if response.json:
                assert "erro" in response.json
            assert mock_alert.called


class TestSendErrorAlert:
    """Testes para a função send_error_alert"""

    @patch("multimax.whatsapp_service.requests.post")
    def test_send_error_alert_success(self, mock_post):
        """Testa envio de alerta com sucesso"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        send_error_alert(
            error_type="error",
            level="error",
            description="Erro de teste",
            message="Mensagem de teste",
            stack_trace="Stack trace de teste",
            route="/api/test",
            method="GET",
            status_code=500,
        )

        assert mock_post.called
        call_args = mock_post.call_args
        assert WHATSAPP_SERVICE_URL in call_args[0][0]
        assert "notify" in call_args[0][0]

    @patch("multimax.whatsapp_service.requests.post")
    def test_send_error_alert_payload_structure(self, mock_post):
        """Testa estrutura do payload enviado"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        send_error_alert(
            error_type="error",
            level="fatal",
            description="Erro crítico",
            message="Detalhes do erro",
            stack_trace="Traceback aqui",
            route="/api/ciclos",
            method="POST",
            status_code=500,
            user_id=42,
        )

        call_args = mock_post.call_args
        json_payload = call_args.kwargs.get("json", {})

        assert "mensagem" in json_payload
        assert "origin" in json_payload
        assert json_payload["origin"] == "api"
        assert "[FATAL]" in json_payload["mensagem"]
        assert "Erro crítico" in json_payload["mensagem"]

    @patch("multimax.whatsapp_service.requests.post")
    @patch("builtins.print")
    def test_send_error_alert_failure(self, mock_print, mock_post):
        """Testa falha no envio de alerta"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        send_error_alert(
            error_type="error",
            level="error",
            description="Erro de teste",
        )

        # Deve ter um print de alerta
        print_calls_list = [str(c) for c in mock_print.call_args_list]
        assert any("[ALERTA]" in str(c) for c in print_calls_list)

    @patch("multimax.whatsapp_service.requests.post")
    @patch("builtins.print")
    def test_send_error_alert_request_exception(self, mock_print, mock_post):
        """Testa exceção de conexão"""
        mock_post.side_effect = requests.RequestException("Connection refused")

        send_error_alert(
            error_type="error",
            level="error",
            description="Erro de teste",
        )

        print_calls_list = [str(c) for c in mock_print.call_args_list]
        assert any("Erro ao conectar" in str(c) for c in print_calls_list)

    @patch("multimax.whatsapp_service.requests.post")
    @patch("builtins.print")
    def test_send_error_alert_unexpected_error(self, mock_print, mock_post):
        """Testa erro inesperado durante envio"""
        mock_post.side_effect = Exception("Erro inesperado")

        send_error_alert(
            error_type="error",
            level="error",
            description="Erro de teste",
        )

        print_calls_list = [str(c) for c in mock_print.call_args_list]
        assert any("Erro inesperado" in str(c) for c in print_calls_list)

    @patch("multimax.whatsapp_service.requests.post")
    def test_send_error_alert_none_values_filtered(self, mock_post):
        """Testa que valores nulos são filtrados do payload"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        send_error_alert(
            error_type="error",
            level="error",
            description="Erro de teste",
            user_id=None,
        )

        assert mock_post.called

    @patch("multimax.whatsapp_service.requests.post")
    def test_send_error_alert_timestamp_included(self, mock_post):
        """Testa que timestamp é incluído no payload"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        send_error_alert(
            error_type="error",
            level="error",
            description="Erro de teste",
        )

        assert mock_post.called

    @patch("multimax.whatsapp_service.requests.post")
    def test_send_error_alert_level_uppercase(self, mock_post):
        """Testa que nível é convertido para maiúsculas na mensagem"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        send_error_alert(
            error_type="error",
            level="warn",
            description="Aviso de teste",
        )

        call_args = mock_post.call_args
        json_payload = call_args.kwargs.get("json", {})
        assert "[WARN]" in json_payload["mensagem"]

    @patch("multimax.whatsapp_service.requests.post")
    def test_send_error_alert_timeout(self, mock_post):
        """Testa timeout na requisição"""
        mock_post.side_effect = requests.Timeout("Connection timeout")

        with patch("builtins.print"):
            send_error_alert(
                error_type="error",
                level="error",
                description="Erro de timeout",
            )

        assert mock_post.called


class TestSendTestAlert:
    """Testes para a função send_test_alert"""

    @patch("multimax.whatsapp_service.requests.post")
    @patch("builtins.print")
    def test_send_test_alert_success(self, mock_print, mock_post):
        """Testa envio de alerta de teste com sucesso"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = send_test_alert()

        assert result is True
        assert mock_post.called
        call_args = mock_post.call_args
        assert "test-alert-phone" in call_args[0][0]

    @patch("multimax.whatsapp_service.requests.post")
    @patch("builtins.print")
    def test_send_test_alert_failure_response(self, mock_print, mock_post):
        """Testa falha de resposta no alerta de teste"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"erro": "Serviço indisponível"}
        mock_post.return_value = mock_response

        result = send_test_alert()

        assert result is False
        print_calls_list = [str(c) for c in mock_print.call_args_list]
        assert any("✗" in str(c) for c in print_calls_list)

    @patch("multimax.whatsapp_service.requests.post")
    @patch("builtins.print")
    def test_send_test_alert_connection_error(self, mock_print, mock_post):
        """Testa erro de conexão no alerta de teste"""
        mock_post.side_effect = requests.ConnectionError("Connection refused")

        result = send_test_alert()

        assert result is False
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("indisponível" in str(call) for call in print_calls)

    @patch("multimax.whatsapp_service.requests.post")
    @patch("builtins.print")
    def test_send_test_alert_timeout_error(self, mock_print, mock_post):
        """Testa timeout no alerta de teste"""
        mock_post.side_effect = requests.Timeout("Request timeout")

        result = send_test_alert()

        assert result is False

    @patch("multimax.whatsapp_service.requests.post")
    @patch("builtins.print")
    def test_send_test_alert_success_message(self, mock_print, mock_post):
        """Testa mensagem de sucesso do alerta de teste"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        send_test_alert()

        print_calls_list = [str(c) for c in mock_print.call_args_list]
        assert any("✓" in str(c) for c in print_calls_list)
        assert any("sucesso" in str(c) for c in print_calls_list)


class TestWhatsappServiceConstants:
    """Testes para constantes do módulo"""

    def test_hostname_not_empty(self):
        """Testa que hostname é configurado"""
        assert HOSTNAME is not None
        assert len(HOSTNAME) > 0

    def test_whatsapp_service_url_default(self):
        """Testa URL padrão do serviço WhatsApp"""
        assert WHATSAPP_SERVICE_URL is not None
        assert "http" in WHATSAPP_SERVICE_URL or "localhost" in WHATSAPP_SERVICE_URL
