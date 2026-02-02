"""
Flask Routes: WhatsApp Configuration (Alert Phone)
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required
from sqlalchemy.exc import SQLAlchemyError

from multimax.models import WhatsappConfig, db

bp = Blueprint("whatsapp_config", __name__, url_prefix="/api/settings")


@bp.route("/alert-phone", methods=["GET"])
def get_alert_phone():
    """
    GET /api/settings/alert-phone
    Retorna o telefone de alerta configurado
    """
    try:
        config = WhatsappConfig.query.filter_by(chave="alert_phone", ativo=True).first()

        if not config:
            return jsonify({"status": "error", "message": "Telefone de alerta não configurado", "data": None}), 404

        return (
            jsonify(
                {
                    "status": "success",
                    "data": {
                        "phone": config.valor,
                        "description": config.descricao,
                        "active": config.ativo,
                        "updated_at": config.updated_at.isoformat(),
                    },
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"status": "error", "message": f"Erro ao recuperar telefone de alerta: {str(e)}"}), 500


@bp.route("/alert-phone", methods=["PUT"])
@login_required
def update_alert_phone():
    """
    PUT /api/settings/alert-phone
    Atualiza o telefone de alerta

    Body:
    {
        "phone": "+55 11 98765-4321",
        "description": "Telefone do gerente de turno"
    }
    """
    try:
        data = request.get_json() or {}
        phone = data.get("phone", "").strip()
        description = data.get("description", "").strip()

        # Validação básica
        if not phone:
            return jsonify({"status": "error", "message": "Telefone é obrigatório"}), 400

        # Tentar encontrar configuração existente
        config = WhatsappConfig.query.filter_by(chave="alert_phone").first()

        if not config:
            # Criar nova configuração
            config = WhatsappConfig(
                chave="alert_phone", valor=phone, descricao=description or "Telefone de alerta padrão", ativo=True
            )
            db.session.add(config)
        else:
            # Atualizar existente
            config.valor = phone
            if description:
                config.descricao = description
            config.ativo = True

        db.session.commit()

        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Telefone de alerta atualizado com sucesso",
                    "data": {
                        "phone": config.valor,
                        "description": config.descricao,
                        "active": config.ativo,
                        "updated_at": config.updated_at.isoformat(),
                    },
                }
            ),
            200,
        )

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Erro ao salvar telefone de alerta: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": f"Erro inesperado: {str(e)}"}), 500


@bp.route("/alert-phone/test", methods=["POST"])
@login_required
def test_alert_phone():
    """
    POST /api/settings/alert-phone/test
    Envia uma mensagem de teste para o telefone de alerta
    """
    try:
        config = WhatsappConfig.query.filter_by(chave="alert_phone", ativo=True).first()

        if not config:
            return jsonify({"status": "error", "message": "Nenhum telefone de alerta configurado"}), 404

        phone = config.valor

        # Tentar enviar mensagem de teste via WhatsApp Service
        import os

        import requests

        whatsapp_service_url = os.getenv("WHATSAPP_SERVICE_URL", "http://whatsapp-service:3000")

        try:
            response = requests.post(
                f"{whatsapp_service_url}/send-test",
                json={"phone": phone, "message": "Teste de alerta do MultiMax"},
                timeout=10,
            )

            if response.status_code == 200:
                return jsonify({"status": "success", "message": f"Mensagem de teste enviada para {phone}"}), 200
            else:
                return jsonify({"status": "error", "message": f"Erro ao enviar mensagem: {response.text}"}), 500

        except requests.RequestException as e:
            return jsonify({"status": "error", "message": f"Erro ao conectar ao serviço WhatsApp: {str(e)}"}), 500

    except Exception as e:
        return jsonify({"status": "error", "message": f"Erro inesperado: {str(e)}"}), 500
