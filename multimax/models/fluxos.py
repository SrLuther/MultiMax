"""Modelos para Fluxos mensais de horas."""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .. import db as app_db

db: Any = app_db


class Fluxo(db.Model):
    """Fluxo mensal (mês de referência)."""

    __tablename__ = "fluxo"

    id = db.Column(db.Integer, primary_key=True)
    mes_ano = db.Column(db.String(7), nullable=False, unique=True, index=True)  # YYYY-MM
    data_inicio = db.Column(db.Date, nullable=False)
    data_fim = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="aberto", index=True)
    valor_diaria = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    updated_at = db.Column(db.DateTime(timezone=True), nullable=True)

    ciclos = db.relationship("FluxoCiclo", backref="fluxo", lazy=True, cascade="all, delete-orphan")
    lancamentos = db.relationship("FluxoLancamento", backref="fluxo", lazy=True, cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Fluxo {self.mes_ano} ({self.status})>"


class FluxoCiclo(db.Model):
    """Ciclo semanal dentro de um fluxo mensal."""

    __tablename__ = "fluxo_ciclo"

    id = db.Column(db.Integer, primary_key=True)
    fluxo_id = db.Column(db.Integer, db.ForeignKey("fluxo.id"), nullable=False, index=True)
    week_start = db.Column(db.Date, nullable=False)
    week_end = db.Column(db.Date, nullable=False)
    label = db.Column(db.String(50), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )

    lancamentos = db.relationship("FluxoLancamento", backref="ciclo", lazy=True, cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<FluxoCiclo {self.label} {self.week_start} a {self.week_end}>"


class FluxoLancamento(db.Model):
    """Lançamentos de horas dentro de um fluxo/ciclo."""

    __tablename__ = "fluxo_lancamento"

    id = db.Column(db.Integer, primary_key=True)
    fluxo_id = db.Column(db.Integer, db.ForeignKey("fluxo.id"), nullable=False, index=True)
    ciclo_id = db.Column(db.Integer, db.ForeignKey("fluxo_ciclo.id"), nullable=False, index=True)
    collaborator_id = db.Column(db.Integer, db.ForeignKey("central_colaborador.id"), nullable=False, index=True)
    data = db.Column(db.Date, nullable=False)
    horas = db.Column(db.Float, nullable=False)
    descricao = db.Column(db.String(255), nullable=False)
    observacao = db.Column(db.String(255))
    created_by = db.Column(db.String(120))
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    updated_at = db.Column(db.DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<FluxoLancamento {self.collaborator_id} {self.data} {self.horas}>"


class FluxoConfig(db.Model):
    """Configurações globais do Fluxo (ex: valor da diária)."""

    __tablename__ = "fluxo_config"

    id = db.Column(db.Integer, primary_key=True)
    valor_diaria = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=True)


class FluxoArquivo(db.Model):
    """Arquivos PDF gerados ao fechar um fluxo."""

    __tablename__ = "fluxo_arquivo"

    id = db.Column(db.Integer, primary_key=True)
    fluxo_id = db.Column(db.Integer, db.ForeignKey("fluxo.id"), nullable=False, index=True)
    collaborator_id = db.Column(db.Integer, db.ForeignKey("central_colaborador.id"), nullable=False, index=True)
    arquivo_path = db.Column(db.String(255), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
