"""
Middleware Global de Erros - Logging centralizado
"""

import os
import traceback
import uuid
from datetime import datetime

from flask import g, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from multimax.models import LogErro, db


def init_error_handlers(app):
    """Inicializa handlers de erro globais"""

    @app.before_request
    def before_request():
        """Antes de processar request - gerar request_id e setup logging"""
        g.request_id = str(uuid.uuid4())
        g.request_start_time = datetime.utcnow()

    @app.errorhandler(400)
    def bad_request(error):
        """Erro 400 - Bad Request"""
        return _handle_error(error, 400, "Bad Request")

    @app.errorhandler(401)
    def unauthorized(error):
        """Erro 401 - Unauthorized"""
        return _handle_error(error, 401, "Unauthorized")

    @app.errorhandler(403)
    def forbidden(error):
        """Erro 403 - Forbidden"""
        return _handle_error(error, 403, "Forbidden")

    @app.errorhandler(404)
    def not_found(error):
        """Erro 404 - Not Found"""
        return _handle_error(error, 404, "Not Found", severity="INFO")

    @app.errorhandler(405)
    def method_not_allowed(error):
        """Erro 405 - Method Not Allowed"""
        return _handle_error(error, 405, "Method Not Allowed")

    @app.errorhandler(500)
    def internal_error(error):
        """Erro 500 - Internal Server Error"""
        return _handle_error(error, 500, "Internal Server Error", severity="ERROR", notify=True)

    @app.errorhandler(Exception)
    def handle_exception(error):
        """Catch-all para exceções não tratadas"""
        # SQLAlchemy errors
        if isinstance(error, SQLAlchemyError):
            db.session.rollback()
            return _handle_error(error, 500, "Database Error", severity="ERROR", notify=True)

        # Generic exceptions
        return _handle_error(error, 500, "Unexpected Error", severity="CRITICAL", notify=True)


def _handle_error(error, status_code, error_type, severity="WARNING", notify=False):
    """
    Manipula erro e realiza logging centralizado

    Args:
        error: Exception object
        status_code: HTTP status code
        error_type: Tipo de erro para logging
        severity: Nível de severidade (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        notify: Se deve notificar via WhatsApp
    """
    # Log imediato do erro com logging module
    import logging

    _logger = logging.getLogger("error_handler")
    _logger.critical(f"ERRO CAPTURADO: {error_type}: {error}")
    _logger.critical(f"Stack trace: {traceback.format_exc()}")

    try:
        # Dados do contexto
        user = getattr(request, "user", None)
        username = user.username if user else "anonymous"
        rota = request.path
        container = os.getenv("CONTAINER_NAME", "flask")
        request_id = g.get("request_id", "unknown")

        # Stack trace
        stack = traceback.format_exc()

        # Salvar em banco de dados
        try:
            log_error = LogErro(
                nivel=severity,
                descricao=f"{error_type}: {str(error)}",
                stack_trace=stack,
                rota=rota,
                usuario=username,
                container=container,
                request_id=request_id,
            )
            db.session.add(log_error)
            db.session.commit()
        except Exception as db_error:
            # Se falhar ao salvar no BD, pelo menos logar no stdout
            print(f"[ERROR] Failed to log error to database: {db_error}", flush=True)
            db.session.rollback()

        # Notificar via WhatsApp se crítico
        if notify and severity in ["ERROR", "CRITICAL"]:
            try:
                _notify_error_whatsapp(error_type, str(error), container, rota, request_id)
            except Exception as notify_error:
                print(f"[ERROR] Failed to notify via WhatsApp: {notify_error}", flush=True)

        # Resposta JSON
        response = {
            "status": "error",
            "message": error_type,
            "request_id": request_id,
        }

        # Incluir detalhes em desenvolvimento
        if os.getenv("FLASK_DEBUG", "false").lower() == "true":
            response["details"] = str(error)

        return jsonify(response), status_code

    except Exception as e:
        # Fallback completo se algo der ruim
        print(f"[CRITICAL] Error handler failed: {e}", flush=True)
        return jsonify({"status": "error", "message": "An unexpected error occurred"}), 500


def _notify_error_whatsapp(error_type, error_msg, container, rota, request_id):
    """Notifica via WhatsApp sobre erro crítico"""
    try:
        import requests

        # Recuperar telefone de alerta
        from multimax.models import WhatsappConfig

        config = WhatsappConfig.query.filter_by(chave="alert_phone", ativo=True).first()

        if not config:
            return

        phone = config.valor

        # Montar mensagem de alerta
        mensagem = f"""
🚨 ALERTA MultiMax 🚨

Erro: {error_type}
Descrição: {error_msg[:100]}...
Container: {container}
Rota: {rota}
Request: {request_id}
Hora: {datetime.utcnow().isoformat()}
"""

        # Enviar via WhatsApp Service
        whatsapp_service_url = os.getenv("WHATSAPP_SERVICE_URL", "http://whatsapp-service:3000")

        requests.post(
            f"{whatsapp_service_url}/send-alert", json={"phone": phone, "message": mensagem.strip()}, timeout=5
        )

    except Exception:
        # Não fazer nada se falhar - não vamos gerar erro ao enviar alerta
        pass
