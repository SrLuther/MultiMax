from datetime import datetime, date
from . import db
from flask_login import UserMixin

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    nivel = db.Column(db.String(20), default='visualizador')

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    quantidade = db.Column(db.Integer, default=0)
    estoque_minimo = db.Column(db.Integer, default=0)
    preco_custo = db.Column(db.Float, default=0.00)
    preco_venda = db.Column(db.Float, default=0.00)

class Historico(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.DateTime, default=datetime.utcnow)
    product_id = db.Column(db.Integer, db.ForeignKey('produto.id'))
    product_name = db.Column(db.String(100))
    action = db.Column(db.String(10))
    quantidade = db.Column(db.Integer)
    details = db.Column(db.String(255))
    usuario = db.Column(db.String(100))

class CleaningTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome_limpeza = db.Column(db.String(100), nullable=False)
    frequencia = db.Column(db.String(20), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)
    ultima_data = db.Column(db.Date, nullable=False)
    proxima_data = db.Column(db.Date, nullable=False)
    observacao = db.Column(db.String(255))
    designados = db.Column(db.String(255))

class CleaningHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data_conclusao = db.Column(db.DateTime, default=datetime.utcnow)
    nome_limpeza = db.Column(db.String(100))
    observacao = db.Column(db.String(500))
    designados = db.Column(db.String(255))
    usuario_conclusao = db.Column(db.String(100))
