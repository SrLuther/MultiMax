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
    
    @property
    def collaborator_name(self):
        try:
            collab = Collaborator.query.filter_by(user_id=self.id).first()
            return collab.name if collab else None
        except Exception:
            return None

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    quantidade = db.Column(db.Integer, default=0)
    estoque_minimo = db.Column(db.Integer, default=0)
    preco_custo = db.Column(db.Float, default=0.00)
    preco_venda = db.Column(db.Float, default=0.00)
    data_validade = db.Column(db.Date, nullable=True)
    lote = db.Column(db.String(50), nullable=True)
    fornecedor_id = db.Column(db.Integer, db.ForeignKey('fornecedor.id'), nullable=True)
    categoria = db.Column(db.String(50), nullable=True)
    unidade = db.Column(db.String(10), default='un')
    localizacao = db.Column(db.String(50), nullable=True)
    ativo = db.Column(db.Boolean, default=True)
    
    fornecedor = db.relationship('Fornecedor', backref='produtos', lazy=True)
    historicos = db.relationship('Historico', backref='produto', lazy=True)

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
    prioridade = db.Column(db.Integer, default=1)
    ativo = db.Column(db.Boolean, default=True)
    
    historicos = db.relationship('CleaningHistory', backref='task', lazy=True)
    checklist_template = db.relationship('CleaningChecklistTemplate', backref='task', lazy=True)

class CleaningHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('cleaning_task.id'), nullable=True)
    data_conclusao = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))
    nome_limpeza = db.Column(db.String(100))
    observacao = db.Column(db.String(500))
    designados = db.Column(db.String(255))
    usuario_conclusao = db.Column(db.String(100))
    duracao_minutos = db.Column(db.Integer, nullable=True)
    qualidade = db.Column(db.Integer, default=5)
    
    checklist_items = db.relationship('CleaningChecklistItem', backref='history', lazy=True, cascade='all, delete-orphan')
    photos = db.relationship('CleaningHistoryPhoto', backref='history', lazy=True, cascade='all, delete-orphan')

class CleaningChecklistTemplate(db.Model):
    __tablename__ = 'cleaning_checklist_template'
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('cleaning_task.id'), nullable=True)
    tipo = db.Column(db.String(20), nullable=False)
    item_texto = db.Column(db.String(200), nullable=False)
    ordem = db.Column(db.Integer, default=0)
    obrigatorio = db.Column(db.Boolean, default=True)

class CleaningChecklistItem(db.Model):
    __tablename__ = 'cleaning_checklist_item'
    id = db.Column(db.Integer, primary_key=True)
    history_id = db.Column(db.Integer, db.ForeignKey('cleaning_history.id'), nullable=False)
    item_texto = db.Column(db.String(200), nullable=False)
    concluido = db.Column(db.Boolean, default=False)
    concluido_por = db.Column(db.String(100))
    concluido_em = db.Column(db.DateTime(timezone=True))

class CleaningHistoryPhoto(db.Model):
    __tablename__ = 'cleaning_history_photo'
    id = db.Column(db.Integer, primary_key=True)
    history_id = db.Column(db.Integer, db.ForeignKey('cleaning_history.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    tipo = db.Column(db.String(20), default='depois')
    caption = db.Column(db.String(200))
    uploaded_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))

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

class Fornecedor(db.Model):
    __tablename__ = 'fornecedor'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cnpj = db.Column(db.String(20), unique=True, nullable=True)
    telefone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    endereco = db.Column(db.String(200), nullable=True)
    observacao = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))

class Collaborator(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50))
    active = db.Column(db.Boolean, default=True)
    regular_team = db.Column(db.String(1))
    sunday_team = db.Column(db.String(1))
    special_team = db.Column(db.String(1))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    team_position = db.Column(db.Integer, default=1)
    telefone = db.Column(db.String(20), nullable=True)
    data_admissao = db.Column(db.Date, nullable=True)
    matricula = db.Column(db.String(30), nullable=True)
    departamento = db.Column(db.String(50), nullable=True)
    
    user = db.relationship('User', backref='collaborator', lazy=True)
    shifts = db.relationship('Shift', backref='collaborator', lazy=True)
    leave_credits = db.relationship('LeaveCredit', backref='collaborator', lazy=True)
    hour_bank_entries = db.relationship('HourBankEntry', backref='collaborator', lazy=True)

class Shift(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    collaborator_id = db.Column(db.Integer, db.ForeignKey('collaborator.id'))
    date = db.Column(db.Date, nullable=False)
    turno = db.Column(db.String(20))
    observacao = db.Column(db.String(255))
    start_dt = db.Column(db.DateTime(timezone=True))
    end_dt = db.Column(db.DateTime(timezone=True))
    shift_type = db.Column(db.String(30))
    is_sunday_holiday = db.Column(db.Boolean, default=False)
    auto_generated = db.Column(db.Boolean, default=False)

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

class TemporaryEntry(db.Model):
    __tablename__ = 'temporary_entry'
    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(20), nullable=False)
    collaborator_id = db.Column(db.Integer, db.ForeignKey('collaborator.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    amount_days = db.Column(db.Integer)
    hours = db.Column(db.Float)
    reason = db.Column(db.String(255))
    source = db.Column(db.String(50))
    status = db.Column(db.String(20), default='pendente')
    payload = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))
    collaborator = db.relationship('Collaborator', backref='temporary_entries', lazy=True)

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
    rendimento = db.Column(db.String(50), nullable=True)
    tempo_preparo = db.Column(db.Integer, nullable=True)
    
    ingredients = db.relationship('RecipeIngredient', backref='recipe', lazy=True, cascade='all, delete-orphan')

class RecipeIngredient(db.Model):
    __tablename__ = 'recipe_ingredient'
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'))
    nome = db.Column(db.String(100), nullable=False)
    quantidade = db.Column(db.String(50))
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=True)
    quantidade_kg = db.Column(db.Float, default=0.0)
    custo_unitario = db.Column(db.Float, default=0.0)

class TemperatureLog(db.Model):
    __tablename__ = 'temperature_log'
    id = db.Column(db.Integer, primary_key=True)
    local = db.Column(db.String(100), nullable=False)
    temperatura = db.Column(db.Float, nullable=False)
    temp_min = db.Column(db.Float, default=-18.0)
    temp_max = db.Column(db.Float, default=-12.0)
    data_registro = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))
    usuario = db.Column(db.String(100))
    observacao = db.Column(db.String(255))
    alerta = db.Column(db.Boolean, default=False)
    
    fotos = db.relationship('TemperaturePhoto', backref='temperature_log', lazy=True, cascade='all, delete-orphan')

class TemperatureLocation(db.Model):
    __tablename__ = 'temperature_location'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)
    temp_min = db.Column(db.Float, default=-18.0)
    temp_max = db.Column(db.Float, default=-12.0)
    ativo = db.Column(db.Boolean, default=True)
    tipo = db.Column(db.String(50))

class LossRecord(db.Model):
    __tablename__ = 'loss_record'
    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=True)
    produto_nome = db.Column(db.String(100), nullable=False)
    quantidade = db.Column(db.Float, nullable=False)
    unidade = db.Column(db.String(20), default='kg')
    motivo = db.Column(db.String(50), nullable=False)
    custo_estimado = db.Column(db.Float, default=0.0)
    data_registro = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))
    usuario = db.Column(db.String(100))
    observacao = db.Column(db.String(255))

class PurchaseOrder(db.Model):
    __tablename__ = 'purchase_order'
    id = db.Column(db.Integer, primary_key=True)
    fornecedor_id = db.Column(db.Integer, db.ForeignKey('fornecedor.id'), nullable=False)
    data_criacao = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))
    data_prevista = db.Column(db.Date)
    status = db.Column(db.String(20), default='pendente')
    valor_total = db.Column(db.Float, default=0.0)
    observacao = db.Column(db.Text)
    usuario = db.Column(db.String(100))
    auto_gerado = db.Column(db.Boolean, default=False)
    
    fornecedor = db.relationship('Fornecedor', backref='pedidos', lazy=True)
    items = db.relationship('PurchaseOrderItem', backref='order', lazy=True, cascade='all, delete-orphan')

class PurchaseOrderItem(db.Model):
    __tablename__ = 'purchase_order_item'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('purchase_order.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=True)
    produto_nome = db.Column(db.String(100), nullable=False)
    quantidade = db.Column(db.Float, nullable=False)
    unidade = db.Column(db.String(20), default='un')
    preco_unitario = db.Column(db.Float, default=0.0)
    subtotal = db.Column(db.Float, default=0.0)


class UserLogin(db.Model):
    __tablename__ = 'user_login'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    username = db.Column(db.String(80))
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(255))
    login_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))
    
    user = db.relationship('User', backref='logins', lazy=True)


class Vacation(db.Model):
    __tablename__ = 'vacation'
    id = db.Column(db.Integer, primary_key=True)
    collaborator_id = db.Column(db.Integer, db.ForeignKey('collaborator.id'), nullable=False)
    data_inicio = db.Column(db.Date, nullable=False)
    data_fim = db.Column(db.Date, nullable=False)
    observacao = db.Column(db.String(255))
    criado_por = db.Column(db.String(100))
    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))
    ativo = db.Column(db.Boolean, default=True)
    
    collaborator = db.relationship('Collaborator', backref='vacations', lazy=True)


class MedicalCertificate(db.Model):
    __tablename__ = 'medical_certificate'
    id = db.Column(db.Integer, primary_key=True)
    collaborator_id = db.Column(db.Integer, db.ForeignKey('collaborator.id'), nullable=False)
    data_inicio = db.Column(db.Date, nullable=False)
    data_fim = db.Column(db.Date, nullable=False)
    dias = db.Column(db.Integer, default=1)
    motivo = db.Column(db.String(255))
    foto_atestado = db.Column(db.String(255))
    cid = db.Column(db.String(20))
    medico = db.Column(db.String(100))
    criado_por = db.Column(db.String(100))
    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))
    
    collaborator = db.relationship('Collaborator', backref='medical_certificates', lazy=True)


class TemperaturePhoto(db.Model):
    __tablename__ = 'temperature_photo'
    id = db.Column(db.Integer, primary_key=True)
    temperature_log_id = db.Column(db.Integer, db.ForeignKey('temperature_log.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    uploaded_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))


class IngredientCatalog(db.Model):
    __tablename__ = 'ingredient_catalog'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)
    categoria = db.Column(db.String(50))
    unidade_padrao = db.Column(db.String(20), default='kg')
    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))


class CustomSchedule(db.Model):
    __tablename__ = 'custom_schedule'
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False)
    collaborator_id = db.Column(db.Integer, db.ForeignKey('collaborator.id'), nullable=False)
    turno_original = db.Column(db.String(50))
    turno_novo = db.Column(db.String(50))
    motivo = db.Column(db.String(255))
    substituto_id = db.Column(db.Integer, db.ForeignKey('collaborator.id'), nullable=True)
    criado_por = db.Column(db.String(100))
    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))
    
    collaborator = db.relationship('Collaborator', foreign_keys=[collaborator_id], backref='custom_schedules')
    substituto = db.relationship('Collaborator', foreign_keys=[substituto_id])


class HelpArticle(db.Model):
    __tablename__ = 'help_article'
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    conteudo = db.Column(db.Text, nullable=False)
    categoria = db.Column(db.String(50), default='Geral')
    ordem = db.Column(db.Integer, default=0)
    ativo = db.Column(db.Boolean, default=True)

class RegistroJornada(db.Model):
    __tablename__ = 'registro_jornada'
    id = db.Column(db.String(36), primary_key=True)
    collaborator_id = db.Column(db.Integer, db.ForeignKey('collaborator.id'), nullable=False)
    tipo_registro = db.Column(db.String(10), nullable=False)
    valor = db.Column(db.Numeric(8, 2), nullable=False)
    data = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))
    observacao = db.Column(db.String(255))

    collaborator = db.relationship('Collaborator', backref='registros_jornada', lazy=True)

class RegistroJornadaChange(db.Model):
    __tablename__ = 'registro_jornada_change'
    id = db.Column(db.Integer, primary_key=True)
    worklog_id = db.Column(db.String(36), db.ForeignKey('registro_jornada.id'), nullable=False)
    changed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    old_tipo = db.Column(db.String(10))
    old_valor = db.Column(db.Numeric(8, 2))
    old_data = db.Column(db.Date)
    new_tipo = db.Column(db.String(10))
    new_valor = db.Column(db.Numeric(8, 2))
    new_data = db.Column(db.Date)
    changed_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))

    worklog = db.relationship('RegistroJornada', backref='changes', lazy=True)
    votos_util = db.Column(db.Integer, default=0)
    votos_nao_util = db.Column(db.Integer, default=0)
    criado_por = db.Column(db.String(100))
    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))
    atualizado_em = db.Column(db.DateTime(timezone=True), onupdate=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))
    


class ArticleVote(db.Model):
    __tablename__ = 'article_vote'
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('help_article.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    util = db.Column(db.Boolean, nullable=False)
    voted_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))


class Suggestion(db.Model):
    __tablename__ = 'suggestion'
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    categoria = db.Column(db.String(50), default='Melhoria')
    status = db.Column(db.String(20), default='pendente')
    votos = db.Column(db.Integer, default=0)
    criado_por = db.Column(db.String(100))
    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))
    
    votes = db.relationship('SuggestionVote', backref='suggestion', lazy=True, cascade='all, delete-orphan')


class SuggestionVote(db.Model):
    __tablename__ = 'suggestion_vote'
    id = db.Column(db.Integer, primary_key=True)
    suggestion_id = db.Column(db.Integer, db.ForeignKey('suggestion.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    voted_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))
