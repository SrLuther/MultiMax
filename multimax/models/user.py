"""
Model: Usuários
"""

from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Boolean, DateTime, Integer, String

db = SQLAlchemy()


class User(db.Model):
    """Usuários do MultiMax"""

    __tablename__ = "users"

    id = db.Column(Integer, primary_key=True)
    username = db.Column(String(80), unique=True, nullable=False, index=True)
    email = db.Column(String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(String(255), nullable=False)

    # Controle de acesso
    role = db.Column(String(20), default="user", nullable=False)  # admin, manager, user
    ativo = db.Column(Boolean, default=True, nullable=False)

    # Auditoria
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<User {self.username}>"
