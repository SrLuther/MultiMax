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
    codigo = db.Column(db.String(20), unique=True, nullable=False, index=True)
    nome = db.Column(db.String(100), nullable=False, index=True)
    quantidade = db.Column(db.Integer, default=0, index=True)
    estoque_minimo = db.Column(db.Integer, default=0, index=True)
    preco_custo = db.Column(db.Float, default=0.00)
    preco_venda = db.Column(db.Float, default=0.00)
    data_validade = db.Column(db.Date, nullable=True, index=True)
    lote = db.Column(db.String(50), nullable=True)
    fornecedor_id = db.Column(db.Integer, db.ForeignKey('fornecedor.id'), nullable=True, index=True)
    categoria = db.Column(db.String(50), nullable=True, index=True)
    unidade = db.Column(db.String(10), default='un')
    localizacao = db.Column(db.String(50), nullable=True)
    ativo = db.Column(db.Boolean, default=True, index=True)
    
    fornecedor = db.relationship('Fornecedor', backref='produtos', lazy=True)
    historicos = db.relationship('Historico', backref='produto', lazy=True)

class Historico(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')), index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('produto.id'), index=True)
    product_name = db.Column(db.String(100))
    action = db.Column(db.String(10), index=True)
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
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=True, index=True)
    produto_nome = db.Column(db.String(100), nullable=False)
    quantidade = db.Column(db.Float, nullable=False)
    unidade = db.Column(db.String(20), default='kg')
    motivo = db.Column(db.String(50), nullable=False)
    custo_estimado = db.Column(db.Float, default=0.0)
    data_registro = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')), index=True)
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


# ========== NOVOS MODELOS PARA FUNCIONALIDADES DE AÇOUGUE E CÂMARA FRIA ==========

class MeatCut(db.Model):
    """Cadastro de tipos de cortes de carne"""
    __tablename__ = 'meat_cut'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(20), nullable=False)  # bovina, suina, frango
    tipo_corte = db.Column(db.String(50))  # picanha, alcatra, etc
    rendimento_esperado = db.Column(db.Float, default=0.0)  # percentual
    preco_base_kg = db.Column(db.Float, default=0.0)
    tempo_preparo_minutos = db.Column(db.Integer, default=0)
    instrucoes = db.Column(db.Text)
    equipamentos = db.Column(db.String(255))
    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))


class MeatCutExecution(db.Model):
    """Execução de corte - registro de quando um corte foi feito"""
    __tablename__ = 'meat_cut_execution'
    id = db.Column(db.Integer, primary_key=True)
    reception_id = db.Column(db.Integer, db.ForeignKey('meat_reception.id'), nullable=False)
    cut_id = db.Column(db.Integer, db.ForeignKey('meat_cut.id'), nullable=False)
    part_id = db.Column(db.Integer, db.ForeignKey('meat_part.id'), nullable=True)
    peso_entrada = db.Column(db.Float, nullable=False)
    peso_saida = db.Column(db.Float, nullable=False)
    rendimento_real = db.Column(db.Float)  # calculado automaticamente
    data_corte = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))
    responsavel = db.Column(db.String(100))
    observacao = db.Column(db.String(255))
    
    reception = db.relationship('MeatReception', backref='cut_executions', lazy=True)
    cut = db.relationship('MeatCut', backref='executions', lazy=True)
    part = db.relationship('MeatPart', backref='cut_executions', lazy=True)


class MeatMaturation(db.Model):
    """Controle de maturação de carnes"""
    __tablename__ = 'meat_maturation'
    id = db.Column(db.Integer, primary_key=True)
    reception_id = db.Column(db.Integer, db.ForeignKey('meat_reception.id'), nullable=False)
    part_id = db.Column(db.Integer, db.ForeignKey('meat_part.id'), nullable=True)
    data_inicio = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))
    data_prevista_pronto = db.Column(db.DateTime(timezone=True))
    data_pronto = db.Column(db.DateTime(timezone=True), nullable=True)
    dias_maturacao = db.Column(db.Integer, default=0)
    temperatura_ideal = db.Column(db.Float, default=2.0)
    umidade_ideal = db.Column(db.Float, default=85.0)
    status = db.Column(db.String(20), default='maturacao')  # maturacao, pronto, cancelado
    observacao = db.Column(db.String(255))
    
    reception = db.relationship('MeatReception', backref='maturations', lazy=True)
    part = db.relationship('MeatPart', backref='maturations', lazy=True)


class ProductLot(db.Model):
    """Controle de lotes por recepção - rastreabilidade completa"""
    __tablename__ = 'product_lot'
    id = db.Column(db.Integer, primary_key=True)
    reception_id = db.Column(db.Integer, db.ForeignKey('meat_reception.id'), nullable=True, index=True)
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=True, index=True)
    lote_codigo = db.Column(db.String(50), unique=True, nullable=False, index=True)
    data_recepcao = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')), index=True)
    data_validade = db.Column(db.Date, nullable=True, index=True)
    quantidade_inicial = db.Column(db.Float, default=0.0)
    quantidade_atual = db.Column(db.Float, default=0.0)
    localizacao = db.Column(db.String(50))  # câmara fria, balcão, etc
    temperatura_armazenamento = db.Column(db.Float)
    fornecedor = db.Column(db.String(100))
    certificado_sanitario = db.Column(db.String(100))
    data_validade_certificado = db.Column(db.Date)
    ativo = db.Column(db.Boolean, default=True, index=True)
    
    reception = db.relationship('MeatReception', backref='lots', lazy=True)
    produto = db.relationship('Produto', backref='lots', lazy=True)
    movements = db.relationship('LotMovement', backref='lot', lazy=True, cascade='all, delete-orphan')


class LotMovement(db.Model):
    """Movimentações de lotes (entrada/saída da câmara fria)"""
    __tablename__ = 'lot_movement'
    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey('product_lot.id'), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # entrada, saida, transferencia
    quantidade = db.Column(db.Float, nullable=False)
    origem = db.Column(db.String(50))
    destino = db.Column(db.String(50))
    data_movimento = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))
    usuario = db.Column(db.String(100))
    observacao = db.Column(db.String(255))


class TemperatureProductAlert(db.Model):
    """Alertas de temperatura que bloqueiam produtos"""
    __tablename__ = 'temperature_product_alert'
    id = db.Column(db.Integer, primary_key=True)
    temperature_log_id = db.Column(db.Integer, db.ForeignKey('temperature_log.id'), nullable=False)
    lot_id = db.Column(db.Integer, db.ForeignKey('product_lot.id'), nullable=True)
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=True)
    bloqueado = db.Column(db.Boolean, default=True)
    data_alerta = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))
    data_resolucao = db.Column(db.DateTime(timezone=True), nullable=True)
    resolvido_por = db.Column(db.String(100))
    observacao = db.Column(db.String(255))
    
    temperature_log = db.relationship('TemperatureLog', backref='product_alerts', lazy=True)
    lot = db.relationship('ProductLot', backref='temperature_alerts', lazy=True)
    produto = db.relationship('Produto', backref='temperature_alerts', lazy=True)


class DynamicPricing(db.Model):
    """Precificação dinâmica baseada em custo, validade e demanda"""
    __tablename__ = 'dynamic_pricing'
    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False, index=True)
    preco_base = db.Column(db.Float, nullable=False)
    preco_atual = db.Column(db.Float, nullable=False)
    margem_minima = db.Column(db.Float, default=20.0)  # percentual
    desconto_validade = db.Column(db.Float, default=0.0)  # percentual de desconto por proximidade de validade
    desconto_demanda = db.Column(db.Float, default=0.0)  # percentual de desconto por baixa demanda
    dias_para_validade = db.Column(db.Integer, default=0)
    ativo = db.Column(db.Boolean, default=True, index=True)
    data_atualizacao = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')), index=True)
    usuario = db.Column(db.String(100))
    
    produto = db.relationship('Produto', backref='dynamic_pricing', lazy=True)
    history = db.relationship('PricingHistory', backref='pricing', lazy=True, cascade='all, delete-orphan')


class PricingHistory(db.Model):
    """Histórico de alterações de preço"""
    __tablename__ = 'pricing_history'
    id = db.Column(db.Integer, primary_key=True)
    pricing_id = db.Column(db.Integer, db.ForeignKey('dynamic_pricing.id'), nullable=False)
    preco_anterior = db.Column(db.Float)
    preco_novo = db.Column(db.Float)
    motivo = db.Column(db.String(100))
    data_alteracao = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))
    usuario = db.Column(db.String(100))


class WasteUtilization(db.Model):
    """Sugestões de aproveitamento de produtos próximos ao vencimento"""
    __tablename__ = 'waste_utilization'
    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False)
    lot_id = db.Column(db.Integer, db.ForeignKey('product_lot.id'), nullable=True)
    tipo = db.Column(db.String(50))  # receita, promocao, doacao, descarte
    sugestao = db.Column(db.Text, nullable=False)
    receita_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=True)
    dias_para_validade = db.Column(db.Integer)
    prioridade = db.Column(db.Integer, default=1)  # 1=alta, 2=média, 3=baixa
    status = db.Column(db.String(20), default='pendente')  # pendente, aplicado, descartado
    data_sugestao = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))
    data_aplicacao = db.Column(db.DateTime(timezone=True), nullable=True)
    usuario_aplicacao = db.Column(db.String(100))
    
    produto = db.relationship('Produto', backref='waste_utilizations', lazy=True)
    lot = db.relationship('ProductLot', backref='waste_utilizations', lazy=True)
    receita = db.relationship('Recipe', backref='waste_utilizations', lazy=True)


class ColdRoomOccupancy(db.Model):
    """Controle de ocupação da câmara fria"""
    __tablename__ = 'cold_room_occupancy'
    id = db.Column(db.Integer, primary_key=True)
    localizacao = db.Column(db.String(50), nullable=False)
    capacidade_total_kg = db.Column(db.Float, nullable=False)
    capacidade_utilizada_kg = db.Column(db.Float, default=0.0)
    percentual_ocupacao = db.Column(db.Float, default=0.0)
    data_registro = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))
    temperatura_atual = db.Column(db.Float)
    observacao = db.Column(db.String(255))


class TraceabilityRecord(db.Model):
    """Registros de rastreabilidade completa"""
    __tablename__ = 'traceability_record'
    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey('product_lot.id'), nullable=False)
    reception_id = db.Column(db.Integer, db.ForeignKey('meat_reception.id'), nullable=True)
    etapa = db.Column(db.String(50), nullable=False)  # recepcao, corte, maturacao, armazenamento, venda
    data_etapa = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))
    responsavel = db.Column(db.String(100))
    temperatura = db.Column(db.Float)
    observacao = db.Column(db.String(255))
    certificado_anexo = db.Column(db.String(255))
    
    lot = db.relationship('ProductLot', backref='traceability_records', lazy=True)
    reception = db.relationship('MeatReception', backref='traceability_records', lazy=True)


class SupplierEvaluation(db.Model):
    """Avaliação de fornecedores"""
    __tablename__ = 'supplier_evaluation'
    id = db.Column(db.Integer, primary_key=True)
    fornecedor_id = db.Column(db.Integer, db.ForeignKey('fornecedor.id'), nullable=False)
    reception_id = db.Column(db.Integer, db.ForeignKey('meat_reception.id'), nullable=True)
    nota_qualidade = db.Column(db.Integer, default=5)  # 1-10
    nota_preco = db.Column(db.Integer, default=5)
    nota_pontualidade = db.Column(db.Integer, default=5)
    nota_atendimento = db.Column(db.Integer, default=5)
    observacao = db.Column(db.Text)
    data_avaliacao = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))
    avaliador = db.Column(db.String(100))
    
    fornecedor = db.relationship('Fornecedor', backref='evaluations', lazy=True)
    reception = db.relationship('MeatReception', backref='supplier_evaluations', lazy=True)


class SanitaryCertificate(db.Model):
    """Certificados sanitários"""
    __tablename__ = 'sanitary_certificate'
    id = db.Column(db.Integer, primary_key=True)
    reception_id = db.Column(db.Integer, db.ForeignKey('meat_reception.id'), nullable=True)
    fornecedor_id = db.Column(db.Integer, db.ForeignKey('fornecedor.id'), nullable=True)
    numero_certificado = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(50))  # SIF, SIM, etc
    data_emissao = db.Column(db.Date)
    data_validade = db.Column(db.Date, nullable=False)
    arquivo_anexo = db.Column(db.String(255))
    observacao = db.Column(db.String(255))
    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))
    
    reception = db.relationship('MeatReception', backref='sanitary_certificates', lazy=True)
    fornecedor = db.relationship('Fornecedor', backref='sanitary_certificates', lazy=True)


class YieldAnalysis(db.Model):
    """Análise de rendimento por recepção"""
    __tablename__ = 'yield_analysis'
    id = db.Column(db.Integer, primary_key=True)
    reception_id = db.Column(db.Integer, db.ForeignKey('meat_reception.id'), nullable=False)
    peso_entrada = db.Column(db.Float, nullable=False)
    peso_saida = db.Column(db.Float, nullable=False)
    rendimento_percentual = db.Column(db.Float)  # calculado
    perdas_kg = db.Column(db.Float, default=0.0)
    tipo_perda = db.Column(db.String(50))  # ossos, aparas, desperdicio
    data_analise = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))
    responsavel = db.Column(db.String(100))
    observacao = db.Column(db.String(255))
    
    reception = db.relationship('MeatReception', backref='yield_analyses', lazy=True)


class TemperatureCertificate(db.Model):
    """Certificados de temperatura para fiscalização"""
    __tablename__ = 'temperature_certificate'
    id = db.Column(db.Integer, primary_key=True)
    periodo_inicio = db.Column(db.DateTime(timezone=True), nullable=False)
    periodo_fim = db.Column(db.DateTime(timezone=True), nullable=False)
    localizacao = db.Column(db.String(100), nullable=False)
    temperatura_media = db.Column(db.Float)
    temperatura_min = db.Column(db.Float)
    temperatura_max = db.Column(db.Float)
    registros_count = db.Column(db.Integer, default=0)
    arquivo_pdf = db.Column(db.String(255))
    gerado_por = db.Column(db.String(100))
    gerado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')))
    observacao = db.Column(db.String(255))
