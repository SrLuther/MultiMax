"""
Modelo para Feriados
"""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .. import db as app_db

db: Any = app_db


class Holiday(db.Model):
    """Modelo para registrar feriados configuráveis"""

    __tablename__ = "holiday"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True, index=True)
    name = db.Column(db.String(100), nullable=False)
    kind = db.Column(db.String(50), nullable=True)  # nacional, estadual, municipal, etc
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    updated_at = db.Column(db.DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Holiday {self.date} - {self.name}>"

    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date.isoformat() if self.date else None,
            "name": self.name,
            "kind": self.kind,
            "created_at": (self.created_at.isoformat() if self.created_at else None),
            "updated_at": (self.updated_at.isoformat() if self.updated_at else None),
        }
