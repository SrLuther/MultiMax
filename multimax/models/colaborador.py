"""Model: Colaboradores"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Float, Integer, String

from .. import db as app_db

db: Any = app_db


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Colaborador(db.Model):
    """Colaboradores da empresa"""

    __tablename__ = "colaboradores"

    id = db.Column(Integer, primary_key=True)
    nome = db.Column(String(150), nullable=False, index=True)
    cpf = db.Column(String(11), unique=True, nullable=False, index=True)
    email = db.Column(String(120), nullable=True)
    telefone = db.Column(String(20), nullable=True)

    # Empresa/Cargo
    departamento = db.Column(String(100), nullable=True)
    funcao = db.Column(String(100), nullable=True)

    # Contratos
    data_admissao = db.Column(DateTime, nullable=True)
    data_demissao = db.Column(DateTime, nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)

    # Controle de horas
    horas_ciclo = db.Column(Float, default=40.0, nullable=False)  # Horas por ciclo
    saldo_horas = db.Column(Float, default=0.0, nullable=False)

    # Auditoria
    created_at = db.Column(DateTime, default=_utcnow, nullable=False)
    updated_at = db.Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    def __repr__(self):
        """String representation of Colaborador."""
        return f"<Colaborador {self.nome}>"

    @property
    def name(self):
        """Alias para nome (compatibilidade com templates e código)"""
        return self.nome

    @name.setter
    def name(self, value):
        """Setter para nome"""
        self.nome = value
