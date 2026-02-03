"""
Modelos para Conteúdo, Artigos de Ajuda e Sugestões
"""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .. import db as app_db

db: Any = app_db


class CustomSchedule(db.Model):
    """Modelo para escalas customizadas"""

    __tablename__ = "custom_schedule"
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False)
    collaborator_id = db.Column(db.Integer, db.ForeignKey("colaborador.id"), nullable=False)
    turno_original = db.Column(db.String(50))
    turno_novo = db.Column(db.String(50))
    motivo = db.Column(db.String(255))
    substituto_id = db.Column(db.Integer, db.ForeignKey("colaborador.id"), nullable=True)
    criado_por = db.Column(db.String(100))
    criado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )

    collaborator = db.relationship(
        "Colaborador",
        foreign_keys=[collaborator_id],
        primaryjoin="and_(CustomSchedule.collaborator_id==Colaborador.id)",
        backref="custom_schedules",
    )
    substituto = db.relationship(
        "Colaborador",
        foreign_keys=[substituto_id],
        primaryjoin="and_(CustomSchedule.substituto_id==Colaborador.id)",
    )

    def __repr__(self):
        return f"<CustomSchedule {self.collaborator_id} - {self.data}>"


class HelpArticle(db.Model):
    """Modelo para artigos de ajuda"""

    __tablename__ = "help_article"
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    conteudo = db.Column(db.Text, nullable=False)
    categoria = db.Column(db.String(50), default="Geral")
    ordem = db.Column(db.Integer, default=0)
    ativo = db.Column(db.Boolean, default=True)

    votes = db.relationship("ArticleVote", backref="article", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<HelpArticle {self.titulo}>"


class Suggestion(db.Model):
    """Modelo para sugestões de melhorias"""

    __tablename__ = "suggestion"
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    categoria = db.Column(db.String(50), default="Melhoria")
    status = db.Column(db.String(20), default="pendente")
    votos = db.Column(db.Integer, default=0)
    criado_por = db.Column(db.String(100))
    criado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )

    votes = db.relationship(
        "SuggestionVote",
        backref="suggestion",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Suggestion {self.titulo}>"


class SuggestionVote(db.Model):
    """Modelo para votos em sugestões"""

    __tablename__ = "suggestion_vote"
    id = db.Column(db.Integer, primary_key=True)
    suggestion_id = db.Column(db.Integer, db.ForeignKey("suggestion.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    voted_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )

    def __repr__(self):
        return f"<SuggestionVote {self.suggestion_id} - {self.user_id}>"


class ArticleVote(db.Model):
    """Modelo para votos em artigos de ajuda"""

    __tablename__ = "article_vote"
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey("help_article.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    util = db.Column(db.Boolean, nullable=False)
    voted_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )

    def __repr__(self):
        return f"<ArticleVote {self.article_id} - {self.util}>"
