"""
Integração da Central de Notificações do MultiMax com o API Flask

Adicione este middleware ao seu app.py para capturar e enviar erros
automaticamente para o WhatsApp
"""

import os
import socket
import traceback
from datetime import datetime

import requests
from flask import g, request

WHATSAPP_SERVICE_URL = os.getenv("WHATSAPP_SERVICE_URL", "http://localhost:3001")
HOSTNAME = socket.gethostname()


def register_error_handlers(app):
    """
    Registra handlers de erro no app Flask
    Deve ser chamado em app.py após criar a instância Flask

    Exemplo:
        from whatsapp_service import register_error_handlers
        app = Flask(__name__)
        register_error_handlers(app)
    """

    @app.errorhandler(500)
    def handle_internal_error(error):
        """Handler para erros 500"""
        send_error_alert(
            error_type="error",
            level="error",
            description="Erro interno do servidor (500)",
            message=str(error),
            stack_trace=traceback.format_exc(),
            route=request.path,
            method=request.method,
            status_code=500,
        )
        # Retornar resposta normal (não rethrow)
        return {"erro": "Erro interno do servidor"}, 500

    @app.errorhandler(404)
    def handle_not_found(error):
        """Handler para 404 (opcional)"""
        return {"erro": "Recurso não encontrado"}, 404

    @app.errorhandler(Exception)
    def handle_unhandled_exception(error):
        """Handler genérico para exceções não tratadas"""
        send_error_alert(
            error_type="error",
            level="fatal",
            description=f"Exceção não tratada: {type(error).__name__}",
            message=str(error),
            stack_trace=traceback.format_exc(),
            route=request.path,
            method=request.method,
            user_id=getattr(g, "user_id", None),
        )
        return {"erro": "Erro ao processar requisição"}, 500


def send_error_alert(**kwargs):
    """
    Envia alerta de erro para a Central de Notificações via HTTP

    Parâmetros:
        error_type: 'error', 'warning', 'info', etc.
        level: 'error', 'warn', 'fatal', etc.
        description: Descrição legível do erro
        message: Mensagem técnica
        stack_trace: Stack trace completo
        route: Rota que causou erro (ex: /api/ciclos)
        method: Método HTTP (GET, POST, etc.)
        status_code: Código HTTP da resposta
        user_id: ID do usuário (opcional)
    """
    try:
        payload = {
            "type": kwargs.get("error_type", "error"),
            "level": kwargs.get("level", "error"),
            "source": "api",
            "description": kwargs.get("description", "Erro do API"),
            "message": kwargs.get("message", ""),
            "stack": kwargs.get("stack_trace", ""),
            "context": f"api_error_{kwargs.get('method', 'UNKNOWN')}_{kwargs.get('route', 'unknown')}",
            "route": kwargs.get("route", ""),
            "host": HOSTNAME,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "statusCode": kwargs.get("status_code", 500),
            "user": kwargs.get("user_id", None),
        }

        # Remover campos nulos
        payload = {k: v for k, v in payload.items() if v is not None}

        # Enviar para whatsapp-service
        level = payload.get("level", "error")
        level_upper = level.upper() if level else "ERROR"
        response = requests.post(
            f"{WHATSAPP_SERVICE_URL}/notify",
            json={"mensagem": f"[{level_upper}] {payload.get('description')}", "origin": "api"},
            timeout=5,
        )

        if response.status_code != 200:
            print(f"[ALERTA] Falha ao enviar erro para WhatsApp: {response.text}")

    except requests.RequestException as e:
        print(f"[ALERTA] Erro ao conectar WhatsApp service: {str(e)}")
    except Exception as e:
        print(f"[ALERTA] Erro inesperado ao enviar alerta: {str(e)}")


def send_test_alert():
    """
    Testa a conectividade da Central de Notificações

    Exemplo de uso:
        from whatsapp_service import send_test_alert
        send_test_alert()  # Envia mensagem de teste
    """
    try:
        response = requests.post(f"{WHATSAPP_SERVICE_URL}/settings/test-alert-phone", timeout=5)

        if response.status_code == 200:
            print("✓ Teste enviado com sucesso!")
            return True
        else:
            print(f"✗ Erro ao enviar teste: {response.json().get('erro', 'Desconhecido')}")
            return False

    except requests.RequestException as e:
        print(f"✗ WhatsApp service indisponível: {str(e)}")
        return False


# ============================================================================
# Exemplo de uso em app.py
# ============================================================================

if __name__ == "__main__":
    """
    # Em seu app.py, importe e registre os handlers:

    from flask import Flask
    from whatsapp_service import register_error_handlers

    app = Flask(__name__)
    register_error_handlers(app)  # <-- Adicione esta linha

    @app.route('/api/test-error')
    def test_error():
        # Teste manual de erro
        raise Exception("Erro proposital para teste")

    if __name__ == '__main__':
        app.run(debug=True)

    # Testar:
    # 1. Acessar http://localhost:5000/api/test-error
    # 2. Verificar WhatsApp para mensagem de alerta
    """
    pass
