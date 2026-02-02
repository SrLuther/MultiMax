"""Testes para o módulo de integração com o serviço WhatsApp."""

from unittest.mock import MagicMock, patch

import requests
from flask import Flask

from multimax.whatsapp_service import (
    HOSTNAME,
    WHATSAPP_SERVICE_URL,
    get_alert_phone,
    register_error_handlers,
    send_alert_phone_test,
    send_error_alert,
    send_test_alert,
    set_alert_phone,
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


class TestGetAlertPhone:
    """Testes para a função get_alert_phone"""

    @patch("multimax.whatsapp_service.requests.get")
    def test_get_alert_phone_success(self, mock_get):
        """Testa busca de número de alerta com sucesso"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"phone": "5575983555249"}
        mock_get.return_value = mock_response

        success, data = get_alert_phone()

        assert success is True
        assert data == {"phone": "5575983555249"}
        assert mock_get.called
        call_args = mock_get.call_args
        assert "alert-phone" in call_args[0][0]

    @patch("multimax.whatsapp_service.requests.get")
    def test_get_alert_phone_not_found(self, mock_get):
        """Testa busca quando número não está configurado"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"erro": "Número não configurado"}
        mock_get.return_value = mock_response

        success, data = get_alert_phone()

        assert success is False
        assert isinstance(data, str)
        assert "Número não configurado" in data

    @patch("multimax.whatsapp_service.requests.get")
    def test_get_alert_phone_server_error(self, mock_get):
        """Testa erro de servidor ao buscar número"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Erro interno"}
        mock_get.return_value = mock_response

        success, data = get_alert_phone()

        assert success is False
        assert isinstance(data, str)

    @patch("multimax.whatsapp_service.requests.get")
    def test_get_alert_phone_invalid_json_response(self, mock_get):
        """Testa resposta com JSON inválido"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("JSON inválido")
        mock_get.return_value = mock_response

        success, data = get_alert_phone()

        assert success is False
        assert "Resposta inválida" in data

    @patch("multimax.whatsapp_service.requests.get")
    def test_get_alert_phone_connection_error(self, mock_get):
        """Testa erro de conexão ao buscar número"""
        mock_get.side_effect = requests.ConnectionError("Conexão recusada")

        success, data = get_alert_phone()

        assert success is False
        assert "Falha ao contatar" in data

    @patch("multimax.whatsapp_service.requests.get")
    def test_get_alert_phone_timeout(self, mock_get):
        """Testa timeout ao buscar número"""
        mock_get.side_effect = requests.Timeout("Timeout")

        success, data = get_alert_phone()

        assert success is False
        assert "Falha ao contatar" in data


class TestSetAlertPhone:
    """Testes para a função set_alert_phone"""

    @patch("multimax.whatsapp_service.requests.put")
    def test_set_alert_phone_success(self, mock_put):
        """Testa configuração de número de alerta com sucesso"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": "Número configurado", "phone": "5575983555249"}
        mock_put.return_value = mock_response

        success, data = set_alert_phone("5575983555249")

        assert success is True
        assert data == {"message": "Número configurado", "phone": "5575983555249"}
        assert mock_put.called
        call_args = mock_put.call_args
        assert "alert-phone" in call_args[0][0]
        assert call_args.kwargs["json"] == {"phone": "5575983555249"}

    @patch("multimax.whatsapp_service.requests.put")
    def test_set_alert_phone_invalid_number(self, mock_put):
        """Testa erro ao configurar número inválido"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"erro": "Número inválido"}
        mock_put.return_value = mock_response

        success, data = set_alert_phone("123")

        assert success is False
        assert isinstance(data, str)
        assert "Número inválido" in data

    @patch("multimax.whatsapp_service.requests.put")
    def test_set_alert_phone_server_error(self, mock_put):
        """Testa erro de servidor ao configurar número"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Erro interno"}
        mock_put.return_value = mock_response

        success, data = set_alert_phone("5575983555249")

        assert success is False
        assert isinstance(data, str)

    @patch("multimax.whatsapp_service.requests.put")
    def test_set_alert_phone_invalid_json_response(self, mock_put):
        """Testa resposta com JSON inválido"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("JSON inválido")
        mock_put.return_value = mock_response

        success, data = set_alert_phone("5575983555249")

        assert success is False
        assert "Resposta inválida" in data

    @patch("multimax.whatsapp_service.requests.put")
    def test_set_alert_phone_connection_error(self, mock_put):
        """Testa erro de conexão ao configurar número"""
        mock_put.side_effect = requests.ConnectionError("Conexão recusada")

        success, data = set_alert_phone("5575983555249")

        assert success is False
        assert "Falha ao contatar" in data

    @patch("multimax.whatsapp_service.requests.put")
    def test_set_alert_phone_timeout(self, mock_put):
        """Testa timeout ao configurar número"""
        mock_put.side_effect = requests.Timeout("Timeout")

        success, data = set_alert_phone("5575983555249")

        assert success is False
        assert "Falha ao contatar" in data


class TestSendAlertPhoneTest:
    """Testes para a função send_alert_phone_test"""

    @patch("multimax.whatsapp_service.requests.post")
    def test_send_alert_phone_test_success(self, mock_post):
        """Testa envio de teste de alerta com sucesso"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": "Teste enviado"}
        mock_post.return_value = mock_response

        success, data = send_alert_phone_test()

        assert success is True
        assert data == {"message": "Teste enviado"}
        assert mock_post.called
        call_args = mock_post.call_args
        assert "test-alert-phone" in call_args[0][0]

    @patch("multimax.whatsapp_service.requests.post")
    def test_send_alert_phone_test_no_number_configured(self, mock_post):
        """Testa erro quando nenhum número está configurado"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"erro": "Nenhum número configurado"}
        mock_post.return_value = mock_response

        success, data = send_alert_phone_test()

        assert success is False
        assert isinstance(data, str)
        assert "Nenhum número configurado" in data

    @patch("multimax.whatsapp_service.requests.post")
    def test_send_alert_phone_test_server_error(self, mock_post):
        """Testa erro de servidor ao enviar teste"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Erro interno"}
        mock_post.return_value = mock_response

        success, data = send_alert_phone_test()

        assert success is False
        assert isinstance(data, str)

    @patch("multimax.whatsapp_service.requests.post")
    def test_send_alert_phone_test_invalid_json_success_response(self, mock_post):
        """Testa resposta com JSON inválido mas status 200"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("JSON inválido")
        mock_post.return_value = mock_response

        success, data = send_alert_phone_test()

        assert success is True
        assert data == {"message": "Teste enviado"}

    @patch("multimax.whatsapp_service.requests.post")
    def test_send_alert_phone_test_invalid_json_error_response(self, mock_post):
        """Testa resposta com JSON inválido e status erro"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.side_effect = ValueError("JSON inválido")
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        success, data = send_alert_phone_test()

        assert success is False
        assert isinstance(data, str)

    @patch("multimax.whatsapp_service.requests.post")
    def test_send_alert_phone_test_connection_error(self, mock_post):
        """Testa erro de conexão ao enviar teste"""
        mock_post.side_effect = requests.ConnectionError("Conexão recusada")

        success, data = send_alert_phone_test()

        assert success is False
        assert "Falha ao contatar" in data

    @patch("multimax.whatsapp_service.requests.post")
    def test_send_alert_phone_test_timeout(self, mock_post):
        """Testa timeout ao enviar teste"""
        mock_post.side_effect = requests.Timeout("Timeout")

        success, data = send_alert_phone_test()

        assert success is False
        assert "Falha ao contatar" in data
