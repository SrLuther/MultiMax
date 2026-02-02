"""
Model: Usuários
"""

from datetime import datetime
from typing import Any

from flask_login import UserMixin
from sqlalchemy import Boolean, DateTime, Integer, String, Text

from .. import db as app_db

db: Any = app_db


class User(UserMixin, db.Model):
    """Usuários do MultiMax"""

    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    id = db.Column(Integer, primary_key=True)
    name = db.Column(String(100), nullable=False)
    username = db.Column(String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(Text)
    nivel = db.Column(String(20), default="visualizador")

    # Campos legados/compatibilidade
    email = db.Column(String(120), nullable=True, index=True)
    role = db.Column(String(20), nullable=True)
    ativo = db.Column(Boolean, default=True, nullable=False)

    # Auditoria
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    @property
    def collaborator_name(self):
        try:
            from . import Collaborator

            collab = Collaborator.query.filter_by(user_id=self.id).first()
            return collab.name if collab else None
        except Exception:
            return None

    def __repr__(self):
        return f"<User {self.username}>"
