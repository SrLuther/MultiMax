"""
Modelos para Operações, Histórico e Limpeza
"""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .. import db as app_db

db: Any = app_db


class Historico(db.Model):
    """Modelo para histórico de movimento de produtos"""

    __tablename__ = "historico"
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
        index=True,
    )
    product_id = db.Column(db.Integer, db.ForeignKey("produto.id"), index=True)
    product_name = db.Column(db.String(100))
    action = db.Column(db.String(10), index=True)
    quantidade = db.Column(db.Integer)
    details = db.Column(db.String(255))
    usuario = db.Column(db.String(100))

    def __repr__(self):
        return f"<Historico {self.product_name} - {self.action} - {self.quantidade}>"


class CleaningTask(db.Model):
    """Modelo para tarefas de limpeza"""

    __tablename__ = "cleaning_task"
    id = db.Column(db.Integer, primary_key=True)
    nome_limpeza = db.Column(db.String(100), nullable=False)
    frequencia = db.Column(db.String(20), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)
    ultima_data = db.Column(db.Date, nullable=False)
    proxima_data = db.Column(db.Date, nullable=False)
    observacao = db.Column(db.String(255))
    designados = db.Column(db.String(255))
    prioridade = db.Column(db.Integer, default=1)
    ativo = db.Column(db.Boolean, default=True)

    historicos = db.relationship("CleaningHistory", backref="task", lazy=True)
    checklist_template = db.relationship("CleaningChecklistTemplate", backref="task", lazy=True)

    def __repr__(self):
        return f"<CleaningTask {self.nome_limpeza}>"


class CleaningHistory(db.Model):
    """Modelo para histórico de execução de limpeza"""

    __tablename__ = "cleaning_history"
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("cleaning_task.id"), nullable=True)
    data_conclusao = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    nome_limpeza = db.Column(db.String(100))
    observacao = db.Column(db.String(500))
    designados = db.Column(db.String(255))
    usuario_conclusao = db.Column(db.String(100))
    duracao_minutos = db.Column(db.Integer, nullable=True)
    qualidade = db.Column(db.Integer, default=5)

    checklist_items = db.relationship(
        "CleaningChecklistItem",
        backref="history",
        lazy=True,
        cascade="all, delete-orphan",
    )
    photos = db.relationship(
        "CleaningHistoryPhoto",
        backref="history",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<CleaningHistory {self.nome_limpeza} - {self.data_conclusao}>"


class CleaningChecklistTemplate(db.Model):
    """Modelo para template de checklist de limpeza"""

    __tablename__ = "cleaning_checklist_template"
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("cleaning_task.id"), nullable=True)
    tipo = db.Column(db.String(20), nullable=False)
    item_texto = db.Column(db.String(200), nullable=False)
    ordem = db.Column(db.Integer, default=0)
    obrigatorio = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<CleaningChecklistTemplate {self.item_texto}>"


class CleaningChecklistItem(db.Model):
    """Modelo para itens do checklist de limpeza"""

    __tablename__ = "cleaning_checklist_item"
    id = db.Column(db.Integer, primary_key=True)
    history_id = db.Column(db.Integer, db.ForeignKey("cleaning_history.id"), nullable=False)
    item_texto = db.Column(db.String(200), nullable=False)
    concluido = db.Column(db.Boolean, default=False)
    concluido_por = db.Column(db.String(100))
    concluido_em = db.Column(db.DateTime(timezone=True))

    def __repr__(self):
        return f"<CleaningChecklistItem {self.item_texto} - {self.concluido}>"


class CleaningHistoryPhoto(db.Model):
    """Modelo para fotos de histórico de limpeza"""

    __tablename__ = "cleaning_history_photo"
    id = db.Column(db.Integer, primary_key=True)
    history_id = db.Column(db.Integer, db.ForeignKey("cleaning_history.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    tipo = db.Column(db.String(20), default="depois")
    caption = db.Column(db.String(200))
    uploaded_by = db.Column(db.String(100))
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )

    def __repr__(self):
        return f"<CleaningHistoryPhoto {self.filename}>"


class CronogramaBloco(db.Model):
    """Modelo para blocos do cronograma"""

    __tablename__ = "cronograma_bloco"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False, unique=True)
    setor = db.Column(db.String(120), nullable=False)
    tipo = db.Column(db.String(120), nullable=False)
    frequencia = db.Column(db.String(40), nullable=False)
    ultima_limpeza = db.Column(db.Date, nullable=True)
    proxima_limpeza = db.Column(db.Date, nullable=True)
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
        onupdate=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )

    registros = db.relationship(
        "CronogramaRegistro",
        backref="bloco",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<CronogramaBloco {self.nome}>"


class CronogramaRegistro(db.Model):
    """Modelo para registro de limpezas do cronograma"""

    __tablename__ = "cronograma_registro"
    id = db.Column(db.Integer, primary_key=True)
    bloco_id = db.Column(db.Integer, db.ForeignKey("cronograma_bloco.id"), nullable=False)
    data = db.Column(db.Date, nullable=False)
    equipe = db.Column(db.String(200), nullable=False)
    observacoes = db.Column(db.String(500))
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    created_by = db.Column(db.String(100))

    def __repr__(self):
        return f"<CronogramaRegistro {self.id} - {self.data}>"
