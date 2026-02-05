"""Modelos para Gestão de Setores, Turnos, Funções e Folgas."""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .. import db as app_db

db: Any = app_db


class Setor(db.Model):
    """Modelo para gerenciar setores da empresa"""

    __tablename__ = "setor"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True, index=True)
    descricao = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    created_by = db.Column(db.String(100), nullable=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=True)
    updated_by = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        """Representação do setor."""
        return f"<Setor {self.nome}>"

    def to_dict(self):
        """Serializa o setor para dicionário."""
        return {
            "id": self.id,
            "nome": self.nome,
            "descricao": self.descricao,
            "ativo": self.ativo,
            "created_at": (self.created_at.isoformat() if self.created_at else None),
            "updated_at": (self.updated_at.isoformat() if self.updated_at else None),
        }


class Shift(db.Model):
    """Modelo para registrar turnos de colaboradores"""

    __tablename__ = "shift"
    id = db.Column(db.Integer, primary_key=True)
    collaborator_id = db.Column(db.Integer, db.ForeignKey("colaboradores.id"))
    date = db.Column(db.Date, nullable=False)
    turno = db.Column(db.String(20))
    observacao = db.Column(db.String(255))
    start_dt = db.Column(db.DateTime(timezone=True))
    end_dt = db.Column(db.DateTime(timezone=True))
    shift_type = db.Column(db.String(30))
    is_sunday_holiday = db.Column(db.Boolean, default=False)
    auto_generated = db.Column(db.Boolean, default=False)

    collaborator = db.relationship(
        "Colaborador",
        foreign_keys=[collaborator_id],
        primaryjoin="Shift.collaborator_id==Colaborador.id",
        backref=db.backref("shifts", lazy=True),
    )

    def __repr__(self):
        """Representação do turno."""
        return f"<Shift {self.collaborator_id} - {self.date} - {self.turno}>"


class JobRole(db.Model):
    """Modelo para registrar funções/cargos"""

    __tablename__ = "job_role"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    nivel = db.Column(db.String(20), nullable=False)

    def __repr__(self):
        """Representação do cargo do sistema."""
        return f"<JobRole {self.name} - {self.nivel}>"


class SetorCargo(db.Model):
    """Cargos internos por setor (não afetam permissões do sistema)."""

    __tablename__ = "setor_cargo"
    __table_args__ = (db.UniqueConstraint("setor_id", "nome", name="uq_setor_cargo_nome"),)

    id = db.Column(db.Integer, primary_key=True)
    setor_id = db.Column(db.Integer, db.ForeignKey("setor.id"), nullable=False, index=True)
    nome = db.Column(db.String(120), nullable=False, index=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    created_by = db.Column(db.String(100), nullable=True)

    setor = db.relationship(
        "Setor",
        foreign_keys=[setor_id],
        primaryjoin="SetorCargo.setor_id==Setor.id",
        backref=db.backref("cargos", lazy=True, cascade="all, delete-orphan"),
    )

    def __repr__(self):
        """Representação do cargo do setor."""
        return f"<SetorCargo {self.nome} (setor {self.setor_id})>"


class Vacation(db.Model):
    """Modelo para registrar férias de colaboradores"""

    __tablename__ = "vacation"
    id = db.Column(db.Integer, primary_key=True)
    collaborator_id = db.Column(db.Integer, db.ForeignKey("colaboradores.id"), nullable=False)
    data_inicio = db.Column(db.Date, nullable=False)
    data_fim = db.Column(db.Date, nullable=False)
    observacao = db.Column(db.String(255))
    criado_por = db.Column(db.String(100))
    criado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    ativo = db.Column(db.Boolean, default=True)

    collaborator = db.relationship(
        "Colaborador",
        foreign_keys=[collaborator_id],
        primaryjoin="Vacation.collaborator_id==Colaborador.id",
        backref=db.backref("vacations", lazy=True),
    )

    def __repr__(self):
        """Representação das férias."""
        return f"<Vacation {self.collaborator_id} - {self.data_inicio} a {self.data_fim}>"


class MedicalCertificate(db.Model):
    """Modelo para registrar atestados médicos de colaboradores"""

    __tablename__ = "medical_certificate"
    id = db.Column(db.Integer, primary_key=True)
    collaborator_id = db.Column(db.Integer, db.ForeignKey("colaboradores.id"), nullable=False)
    data_inicio = db.Column(db.Date, nullable=False)
    data_fim = db.Column(db.Date, nullable=False)
    dias = db.Column(db.Integer, default=1)
    motivo = db.Column(db.String(255))
    foto_atestado = db.Column(db.String(255))
    cid = db.Column(db.String(20))
    medico = db.Column(db.String(100))
    criado_por = db.Column(db.String(100))
    criado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )

    collaborator = db.relationship(
        "Colaborador",
        foreign_keys=[collaborator_id],
        primaryjoin="MedicalCertificate.collaborator_id==Colaborador.id",
        backref=db.backref("medical_certificates", lazy=True),
    )

    def __repr__(self):
        """Representação do atestado médico."""
        return f"<MedicalCertificate {self.collaborator_id} - {self.data_inicio} a {self.data_fim}>"
