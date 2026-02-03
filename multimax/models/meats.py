"""
Modelos para Gestão de Recebimento de Carnes
"""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .. import db as app_db

db: Any = app_db


class MeatReception(db.Model):
    """Modelo para registrar recebimento de carnes do fornecedor"""

    __tablename__ = "meat_reception"
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    fornecedor = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(10), nullable=False)
    observacao = db.Column(db.String(255))
    reference_code = db.Column(db.String(32), unique=True)
    peso_nota = db.Column(db.Float)
    peso_frango = db.Column(db.Float)
    recebedor_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    def __repr__(self):
        return f"<MeatReception {self.fornecedor} - {self.data}>"


class MeatCarrier(db.Model):
    """Modelo para registrar transportistas de carne"""

    __tablename__ = "meat_carrier"
    id = db.Column(db.Integer, primary_key=True)
    reception_id = db.Column(db.Integer, db.ForeignKey("meat_reception.id"))
    nome = db.Column(db.String(100), nullable=False)
    peso = db.Column(db.Float, nullable=False)

    reception = db.relationship("MeatReception", backref=db.backref("carriers", lazy=True))

    def __repr__(self):
        return f"<MeatCarrier {self.nome} - {self.peso}>"


class MeatPart(db.Model):
    """Modelo para registrar partes de carne recebidas"""

    __tablename__ = "meat_part"
    id = db.Column(db.Integer, primary_key=True)
    reception_id = db.Column(db.Integer, db.ForeignKey("meat_reception.id"))
    animal_numero = db.Column(db.Integer)
    categoria = db.Column(db.String(20))
    lado = db.Column(db.String(20))
    peso_bruto = db.Column(db.Float, nullable=False)
    carrier_id = db.Column(db.Integer, db.ForeignKey("meat_carrier.id"))
    tara = db.Column(db.Float, default=0.0)

    reception = db.relationship("MeatReception", backref=db.backref("parts", lazy=True))
    carrier = db.relationship("MeatCarrier", backref=db.backref("parts", lazy=True))

    def __repr__(self):
        return f"<MeatPart {self.categoria} - {self.peso_bruto}>"
