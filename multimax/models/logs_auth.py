"""
Models para logging de autenticação e eventos do sistema
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from .. import db


class UserLogin(db.Model):
    """Registro de login de usuários"""

    __tablename__ = "user_login"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    username = db.Column(db.String(80))
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(255))
    login_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )

    def __repr__(self):
        return f"<UserLogin {self.username} @ {self.login_at}>"


class SystemLog(db.Model):
    """Log de eventos do sistema"""

    __tablename__ = "system_log"

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    origem = db.Column(db.String(50))
    evento = db.Column(db.String(50))
    detalhes = db.Column(db.String(255))
    usuario = db.Column(db.String(100))

    def __repr__(self):
        return f"<SystemLog {self.evento} @ {self.data}>"
