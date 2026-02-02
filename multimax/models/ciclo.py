"""
Models: Ciclos e Histórico
"""

from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text

db = SQLAlchemy()


class CicloSemanal(db.Model):
    """Ciclos semanais - semanas de trabalho"""

    __tablename__ = "ciclos_semanais"

    id = db.Column(Integer, primary_key=True)
    numero_ciclo = db.Column(Integer, nullable=False, unique=True, index=True)
    data_inicio = db.Column(Date, nullable=False, index=True)
    data_fim = db.Column(Date, nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    observacoes = db.Column(Text, nullable=True)

    # Auditoria
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<CicloSemanal {self.numero_ciclo}>"


class CicloMensal(db.Model):
    """Ciclos mensais - meses fechados"""

    __tablename__ = "ciclos_mensais"

    id = db.Column(Integer, primary_key=True)
    mes = db.Column(Integer, nullable=False)  # 1-12
    ano = db.Column(Integer, nullable=False)
    data_inicio = db.Column(Date, nullable=False)
    data_fim = db.Column(Date, nullable=False)
    fechado = db.Column(db.Boolean, default=False, nullable=False)

    # Auditoria
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (db.UniqueConstraint("mes", "ano", name="uq_ciclo_mes_ano"),)

    def __repr__(self):
        return f"<CicloMensal {self.mes}/{self.ano}>"


class HistoricoColaborador(db.Model):
    """Histórico de horas, faltas, atrasos por colaborador"""

    __tablename__ = "historico_colaborador"

    id = db.Column(Integer, primary_key=True)
    colaborador_id = db.Column(Integer, ForeignKey("colaboradores.id"), nullable=False, index=True)
    ciclo_semanal_id = db.Column(Integer, ForeignKey("ciclos_semanais.id"), nullable=False, index=True)

    # Dados do ciclo
    horas_trabalhadas = db.Column(Float, default=0.0, nullable=False)
    horas_falta = db.Column(Float, default=0.0, nullable=False)
    horas_atraso = db.Column(Float, default=0.0, nullable=False)
    horas_extra = db.Column(Float, default=0.0, nullable=False)

    # Observações
    observacoes = db.Column(Text, nullable=True)

    # Auditoria
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<HistoricoColaborador col:{self.colaborador_id} ciclo:{self.ciclo_semanal_id}>"
