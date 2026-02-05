"""
Models: Logging e Monitoramento
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text

from .. import db as app_db

db: Any = app_db


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class LogErro(db.Model):
    """Log centralizado de erros da aplicação"""

    __tablename__ = "log_erros"

    id = db.Column(Integer, primary_key=True)
    nivel = db.Column(String(20), nullable=False, index=True)  # 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
    descricao = db.Column(Text, nullable=False)
    stack_trace = db.Column(Text, nullable=True)

    # Contexto
    rota = db.Column(String(255), nullable=True)
    usuario = db.Column(String(100), nullable=True)
    container = db.Column(String(100), nullable=True)  # 'flask', 'whatsapp-service', 'cron'

    # Rastreamento
    request_id = db.Column(String(100), nullable=True, index=True)

    # Auditoria
    created_at = db.Column(DateTime, default=_utcnow, nullable=False, index=True)
    updated_at = db.Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    __table_args__ = (db.Index("ix_log_erros_nivel_data", "nivel", "created_at"),)

    def __repr__(self):
        return f"<LogErro {self.nivel} {self.created_at}>"


class LogWhatsapp(db.Model):
    """Log detalhado de todas as operações WhatsApp"""

    __tablename__ = "log_whatsapp"

    id = db.Column(Integer, primary_key=True)
    acao = db.Column(String(100), nullable=False, index=True)  # 'enviar_mensagem', 'webhook_recebido', 'erro_api'
    telefone = db.Column(String(20), nullable=True)
    status = db.Column(String(50), nullable=False)  # 'sucesso', 'erro', 'pendente'
    detalhes = db.Column(Text, nullable=True)
    resposta_api = db.Column(Text, nullable=True)

    # Auditoria
    created_at = db.Column(DateTime, default=_utcnow, nullable=False, index=True)
    updated_at = db.Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    def __repr__(self):
        return f"<LogWhatsapp {self.acao} {self.status}>"


class LogDeploy(db.Model):
    """Log de eventos de deploy e atualizações"""

    __tablename__ = "log_deploy"

    id = db.Column(Integer, primary_key=True)
    versao = db.Column(String(50), nullable=False, index=True)
    evento = db.Column(String(100), nullable=False)  # 'start', 'update', 'shutdown', 'health_check'
    status = db.Column(String(50), nullable=False)  # 'sucesso', 'erro', 'aviso'
    detalhes = db.Column(Text, nullable=True)
    container = db.Column(String(100), nullable=False)  # 'multimax', 'whatsapp-service', 'postgres'

    # Auditoria
    created_at = db.Column(DateTime, default=_utcnow, nullable=False, index=True)

    def __repr__(self):
        return f"<LogDeploy {self.versao} {self.evento}>"


class Heartbeat(db.Model):
    """Pings de health check a cada 6 horas"""

    __tablename__ = "heartbeat"

    id = db.Column(Integer, primary_key=True)
    container = db.Column(String(100), nullable=False, index=True)  # 'multimax', 'whatsapp-service', 'postgres'
    status = db.Column(String(50), default="online", nullable=False)  # 'online', 'offline', 'error'
    versao = db.Column(String(50), nullable=True)
    uptime_segundos = db.Column(Integer, nullable=True)
    cpu_percent = db.Column(String(20), nullable=True)
    memoria_mb = db.Column(Integer, nullable=True)
    detalhes = db.Column(Text, nullable=True)

    # Auditoria
    created_at = db.Column(DateTime, default=_utcnow, nullable=False, index=True)

    __table_args__ = (db.Index("ix_heartbeat_container_data", "container", "created_at"),)

    def __repr__(self):
        return f"<Heartbeat {self.container} {self.status}>"
