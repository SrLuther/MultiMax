"""
Modelos para Estoque de Produção
"""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .. import db as app_db

db: Any = app_db


class AppSetting(db.Model):
    """Configurações globais da aplicação"""

    __tablename__ = "app_setting"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Text)

    def __repr__(self):
        return f"<AppSetting {self.key}={self.value}>"


class EstoqueProducao(db.Model):
    """Modelo para estoque de produção com previsão de uso"""

    __tablename__ = "estoque_producao"
    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey("produto.id"), nullable=False, index=True)
    quantidade = db.Column(db.Float, nullable=False, default=0)  # Não pode ser negativo
    setor_id = db.Column(db.Integer, db.ForeignKey("setor.id"), nullable=False, index=True)
    previsao_uso = db.Column(db.String(100), nullable=True, index=True)  # Ex: "Carnaval 2026", "Fim de Semana"
    data_previsao = db.Column(db.Date, nullable=True, index=True)  # Data específica da previsão
    data_registro = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
        index=True,
    )
    criado_por = db.Column(db.String(100))
    observacao = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, default=True, index=True)

    # Relacionamentos
    produto = db.relationship("Produto", backref=db.backref("estoque_producao", lazy="dynamic"))
    setor = db.relationship(
        "Setor",
        foreign_keys=[setor_id],
        primaryjoin="EstoqueProducao.setor_id==Setor.id",
        backref=db.backref("estoque_producao", lazy="dynamic"),
    )
    historico = db.relationship(
        "HistoricoAjusteEstoque",
        backref="estoque",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<EstoqueProducao {self.produto.nome if self.produto else 'N/A'} - {self.quantidade}>"


class HistoricoAjusteEstoque(db.Model):
    """Modelo para histórico de ajustes no estoque"""

    __tablename__ = "historico_ajuste_estoque"
    id = db.Column(db.Integer, primary_key=True)
    estoque_id = db.Column(
        db.Integer,
        db.ForeignKey("estoque_producao.id"),
        nullable=False,
        index=True,
    )
    data_ajuste = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
        index=True,
    )
    tipo_ajuste = db.Column(db.String(20), nullable=False)  # 'entrada', 'saida', 'correcao'
    quantidade_anterior = db.Column(db.Float, nullable=False)
    quantidade_ajuste = db.Column(db.Float, nullable=False)  # Positivo ou negativo
    quantidade_nova = db.Column(db.Float, nullable=False)
    motivo = db.Column(db.String(255), nullable=False)
    ajustado_por = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<HistoricoAjusteEstoque {self.tipo_ajuste} - {self.quantidade_ajuste}>"
