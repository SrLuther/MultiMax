"""
Models: Escalas de Trabalho
"""

from datetime import datetime
from typing import Any

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, Time

from .. import db as app_db

db: Any = app_db


class Escala(db.Model):
    """Escalas de trabalho - atribuições de turnos para colaboradores"""

    __tablename__ = "escalas"

    id = db.Column(Integer, primary_key=True)
    colaborador_id = db.Column(Integer, ForeignKey("colaboradores.id"), nullable=False, index=True)
    ciclo_semanal_id = db.Column(Integer, ForeignKey("ciclos_semanais.id"), nullable=False, index=True)

    # Dados da escala
    data_escala = db.Column(Date, nullable=False, index=True)
    tipo_dia = db.Column(String(20), nullable=False)  # 'trabalho', 'feriado', 'folga', 'férias', 'atestado'

    # Horários (se aplicável)
    hora_entrada = db.Column(Time, nullable=True)
    hora_saida = db.Column(Time, nullable=True)
    intervalo_minutos = db.Column(Integer, default=60, nullable=False)

    # Dados
    turno = db.Column(String(50), nullable=True)  # 'manhã', 'tarde', 'noturno', etc
    setor = db.Column(String(100), nullable=True)
    observacoes = db.Column(Text, nullable=True)

    # Auditoria
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (db.Index("ix_escala_colaborador_data", "colaborador_id", "data_escala"),)

    def __repr__(self):
        return f"<Escala col:{self.colaborador_id} data:{self.data_escala}>"
