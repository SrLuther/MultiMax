"""
Modelos para Sistema de Notificações
"""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .. import db as app_db

db: Any = app_db


class EventoDoDia(db.Model):
    """Eventos registrados durante o dia"""

    __tablename__ = "evento_do_dia"
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50), nullable=False)  # 'alerta', 'aviso', 'info'
    produto = db.Column(db.String(100), nullable=True)
    quantidade = db.Column(db.Integer, nullable=True)
    limite = db.Column(db.Integer, nullable=True)
    descricao = db.Column(db.String(500), nullable=True)
    data = db.Column(db.Date, nullable=False, index=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )

    def __repr__(self):
        return f"<EventoDoDia {self.tipo} - {self.data}>"

    def to_dict(self):
        return {
            "id": self.id,
            "tipo": self.tipo,
            "produto": self.produto,
            "quantidade": self.quantidade,
            "limite": self.limite,
            "descricao": self.descricao,
            "data": self.data.isoformat() if self.data else None,
            "created_at": (self.created_at.isoformat() if self.created_at else None),
        }


class NotificacaoDiaria(db.Model):
    """Relatórios de notificações enviadas diariamente"""

    __tablename__ = "notificacao_diaria"
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False, index=True)
    hora = db.Column(db.String(5), nullable=False)  # HH:MM
    tipo = db.Column(db.String(20), nullable=False)  # 'automatico', 'manual'
    conteudo = db.Column(db.Text, nullable=False)
    enviado = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )

    def __repr__(self):
        return f"<NotificacaoDiaria {self.data} - {self.hora}>"

    def to_dict(self):
        return {
            "id": self.id,
            "data": self.data.isoformat() if self.data else None,
            "hora": self.hora,
            "tipo": self.tipo,
            "conteudo": self.conteudo,
            "enviado": self.enviado,
            "created_at": (self.created_at.isoformat() if self.created_at else None),
        }


class NotificacaoPersonalizada(db.Model):
    """Mensagens personalizadas de notificação"""

    __tablename__ = "notificacao_personalizada"
    id = db.Column(db.Integer, primary_key=True)
    mensagem = db.Column(db.Text, nullable=False)
    enviar_novamente = db.Column(db.Boolean, default=True, nullable=False)  # Reenviar em seguida?
    enviada = db.Column(db.Boolean, default=False, nullable=False, index=True)
    data_criacao = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    data_envio = db.Column(db.DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<NotificacaoPersonalizada {self.id}>"

    def to_dict(self):
        return {
            "id": self.id,
            "mensagem": self.mensagem,
            "enviar_novamente": self.enviar_novamente,
            "enviada": self.enviada,
            "data_criacao": (self.data_criacao.isoformat() if self.data_criacao else None),
            "data_envio": (self.data_envio.isoformat() if self.data_envio else None),
        }
