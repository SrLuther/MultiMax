from datetime import datetime
from zoneinfo import ZoneInfo
from . import db
from flask_login import UserMixin

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.Text)
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
    data = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))
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
    data_conclusao = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))
    nome_limpeza = db.Column(db.String(100))
    observacao = db.Column(db.String(500))
    designados = db.Column(db.String(255))
    usuario_conclusao = db.Column(db.String(100))

class SystemLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))
    origem = db.Column(db.String(50))
    evento = db.Column(db.String(50))
    detalhes = db.Column(db.String(255))
    usuario = db.Column(db.String(100))

class NotificationRead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # 'estoque' ou 'limpeza'
    ref_id = db.Column(db.Integer, nullable=False)   # Produto.id ou CleaningTask.id
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))

class MeatReception(db.Model):
    __tablename__ = 'meat_reception'
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))
    fornecedor = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(10), nullable=False)
    observacao = db.Column(db.String(255))
    reference_code = db.Column(db.String(32), unique=True)
    peso_nota = db.Column(db.Float)
    peso_frango = db.Column(db.Float)
    recebedor_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class MeatCarrier(db.Model):
    __tablename__ = 'meat_carrier'
    id = db.Column(db.Integer, primary_key=True)
    reception_id = db.Column(db.Integer, db.ForeignKey('meat_reception.id'))
    nome = db.Column(db.String(100), nullable=False)
    peso = db.Column(db.Float, nullable=False)

class MeatPart(db.Model):
    __tablename__ = 'meat_part'
    id = db.Column(db.Integer, primary_key=True)
    reception_id = db.Column(db.Integer, db.ForeignKey('meat_reception.id'))
    animal_numero = db.Column(db.Integer)
    categoria = db.Column(db.String(20))
    lado = db.Column(db.String(20))
    peso_bruto = db.Column(db.Float, nullable=False)
    carrier_id = db.Column(db.Integer, db.ForeignKey('meat_carrier.id'))
    tara = db.Column(db.Float, default=0.0)

class AppSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Text)

class Collaborator(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50))
    active = db.Column(db.Boolean, default=True)
    regular_team = db.Column(db.String(1))
    sunday_team = db.Column(db.String(1))
    special_team = db.Column(db.String(1))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Shift(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    collaborator_id = db.Column(db.Integer, db.ForeignKey('collaborator.id'))
    date = db.Column(db.Date, nullable=False)
    turno = db.Column(db.String(20))
    observacao = db.Column(db.String(255))
    start_dt = db.Column(db.DateTime(timezone=True))
    end_dt = db.Column(db.DateTime(timezone=True))

class LeaveCredit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    collaborator_id = db.Column(db.Integer, db.ForeignKey('collaborator.id'))
    date = db.Column(db.Date, nullable=False)
    amount_days = db.Column(db.Integer, default=1)
    origin = db.Column(db.String(20))
    notes = db.Column(db.String(255))

class HourBankEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    collaborator_id = db.Column(db.Integer, db.ForeignKey('collaborator.id'))
    date = db.Column(db.Date, nullable=False)
    hours = db.Column(db.Float, nullable=False)
    reason = db.Column(db.String(255))

class JobRole(db.Model):
    __tablename__ = 'job_role'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    nivel = db.Column(db.String(20), nullable=False)

class LeaveAssignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    collaborator_id = db.Column(db.Integer, db.ForeignKey('collaborator.id'))
    date = db.Column(db.Date, nullable=False)
    days_used = db.Column(db.Integer, default=1)
    notes = db.Column(db.String(255))

class LeaveConversion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    collaborator_id = db.Column(db.Integer, db.ForeignKey('collaborator.id'))
    date = db.Column(db.Date, nullable=False)
    amount_days = db.Column(db.Integer, nullable=False)
    amount_paid = db.Column(db.Float, nullable=False)
    rate_per_day = db.Column(db.Float, default=65.0)
    notes = db.Column(db.String(255))

class Holiday(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    kind = db.Column(db.String(20))
class NotificacaoDiaria(db.Model):
    __tablename__ = 'notificacao_diaria'
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False)
    hora = db.Column(db.String(5))
    tipo = db.Column(db.String(20))
    conteudo = db.Column(db.Text)
    enviado = db.Column(db.Boolean, default=False)
class NotificacaoPersonalizada(db.Model):
    __tablename__ = 'notificacao_personalizada'
    id = db.Column(db.Integer, primary_key=True)
    mensagem = db.Column(db.Text, nullable=False)
    data_criacao = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))
    enviar_novamente = db.Column(db.Boolean, default=True)
    enviada = db.Column(db.Boolean, default=False)
class EventoDoDia(db.Model):
    __tablename__ = 'evento_dia'
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50), nullable=False)
    produto = db.Column(db.String(100))
    quantidade = db.Column(db.Integer)
    limite = db.Column(db.Integer)
    descricao = db.Column(db.String(255))
    data = db.Column(db.Date, nullable=False)
class Recipe(db.Model):
    __tablename__ = 'recipe'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    preparo = db.Column(db.Text)
    embalagem = db.Column(db.String(10))
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))
class RecipeIngredient(db.Model):
    __tablename__ = 'recipe_ingredient'
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'))
    nome = db.Column(db.String(100), nullable=False)
    quantidade = db.Column(db.String(50))
