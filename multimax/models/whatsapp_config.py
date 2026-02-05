"""
Models: Configurações WhatsApp
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text

from .. import db as app_db

db: Any = app_db


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class WhatsappConfig(db.Model):
    """Configurações e números do WhatsApp"""

    __tablename__ = "whatsapp_config"

    id = db.Column(Integer, primary_key=True)
    chave = db.Column(String(100), unique=True, nullable=False, index=True)  # 'alert_phone', 'webhook_token', etc
    valor = db.Column(Text, nullable=False)  # Número de telefone, token, url, etc
    descricao = db.Column(String(255), nullable=True)
    ativo = db.Column(Boolean, default=True, nullable=False)

    # Auditoria
    created_at = db.Column(DateTime, default=_utcnow, nullable=False)
    updated_at = db.Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    def __repr__(self):
        return f"<WhatsappConfig {self.chave}>"


class WhatsappMessage(db.Model):
    """Registro de todas as mensagens WhatsApp enviadas"""

    __tablename__ = "whatsapp_messages"

    id = db.Column(Integer, primary_key=True)
    telefone_destino = db.Column(String(20), nullable=False, index=True)
    mensagem = db.Column(Text, nullable=False)
    tipo = db.Column(String(50), nullable=False)  # 'alerta', 'notificação', 'teste', 'relatório'
    status = db.Column(String(20), default="pendente", nullable=False)  # 'pendente', 'enviado', 'erro'
    resposta_whatsapp = db.Column(Text, nullable=True)
    erro = db.Column(Text, nullable=True)

    # Referências
    ciclo_semanal_id = db.Column(Integer, nullable=True)
    colaborador_id = db.Column(Integer, nullable=True)

    # Auditoria
    created_at = db.Column(DateTime, default=_utcnow, nullable=False)
    updated_at = db.Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)
    enviado_em = db.Column(DateTime, nullable=True)

    __table_args__ = (
        db.Index("ix_whatsapp_messages_status", "status"),
        db.Index("ix_whatsapp_messages_tipo", "tipo"),
        db.Index("ix_whatsapp_messages_data", "created_at"),
    )

    def __repr__(self):
        return f"<WhatsappMessage {self.tipo} -> {self.telefone_destino}>"
