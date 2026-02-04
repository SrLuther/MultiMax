"""Modelos da Central de Colaboradores"""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .. import db as app_db

db: Any = app_db


class CentralColaborador(db.Model):
    """Colaborador da Central (independente da Gestão)"""

    __tablename__ = "central_colaborador"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False, index=True)
    username = db.Column(db.String(80), nullable=False, unique=True, index=True)
    email = db.Column(db.String(160), nullable=True)
    cargo = db.Column(db.String(120), nullable=True)
    setor = db.Column(db.String(120), nullable=True)
    permissao = db.Column(db.String(20), nullable=False, default="visualizador", index=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    created_by = db.Column(db.String(120), nullable=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=True)
    updated_by = db.Column(db.String(120), nullable=True)
    last_password_at = db.Column(db.DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<CentralColaborador {self.id} {self.nome}>"


class CentralLog(db.Model):
    """Histórico de ações da Central"""

    __tablename__ = "central_log"

    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(60), nullable=False)
    actor = db.Column(db.String(120), nullable=True)
    target_id = db.Column(db.Integer, nullable=True)
    target_nome = db.Column(db.String(120), nullable=True)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
        index=True,
    )

    def __repr__(self) -> str:
        return f"<CentralLog {self.action} {self.target_nome}>"
