"""
Modelos para Estoque de Produção e Escalas Especiais
"""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .. import db as app_db

db: Any = app_db


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
    setor = db.relationship("Setor", backref=db.backref("estoque_producao", lazy="dynamic"))
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


class EscalaEspecial(db.Model):
    """Modelo para escalas especiais/futuras (limpeza, feriados, redistribuições, etc)"""

    __tablename__ = "escala_especial"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False, index=True)
    descricao = db.Column(db.Text, nullable=True)
    tipo = db.Column(
        db.String(50), nullable=False, index=True
    )  # 'limpeza', 'feriado', 'redistribuicao', 'evento', 'outro'

    # Período de aplicação
    data_inicio = db.Column(db.Date, nullable=False, index=True)
    data_fim = db.Column(db.Date, nullable=False, index=True)

    # Configuração de atribuição de turno
    turno_customizado = db.Column(db.String(100), nullable=True)  # Ex: "08:00-17:00"
    criterio_atribuicao = db.Column(
        db.String(50), nullable=False, default="todos"
    )  # 'todos', 'por_equipe', 'por_numero', 'manual'

    # Se criterio_atribuicao for 'por_equipe'
    equipe_id = db.Column(db.Integer, db.ForeignKey("setor.id"), nullable=True)
    equipe = db.relationship("Setor", backref="escalas_especiais")

    # Se criterio_atribuicao for 'por_numero'
    numero_pessoas = db.Column(db.Integer, nullable=True)

    # Colaboradores selecionados (para critério manual)
    colaboradores_selecionados = db.Column(db.JSON, nullable=True)  # Lista de IDs

    # Status
    ativo = db.Column(db.Boolean, default=True, index=True)

    # Metadata
    criado_em = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")), nullable=False
    )
    atualizado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
        onupdate=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
        nullable=False,
    )
    criado_por = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<EscalaEspecial {self.nome} ({self.tipo}) - {self.data_inicio} a {self.data_fim}>"

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "descricao": self.descricao,
            "tipo": self.tipo,
            "data_inicio": self.data_inicio.isoformat(),
            "data_fim": self.data_fim.isoformat(),
            "turno_customizado": self.turno_customizado,
            "criterio_atribuicao": self.criterio_atribuicao,
            "numero_pessoas": self.numero_pessoas,
            "colaboradores_selecionados": self.colaboradores_selecionados,
            "ativo": self.ativo,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
            "atualizado_em": self.atualizado_em.isoformat() if self.atualizado_em else None,
            "criado_por": self.criado_por,
        }
