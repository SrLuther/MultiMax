import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from flask_login import UserMixin

from . import db

# --- MODELO DE LOTE DE HORAS ---


class BulkHourOperation(db.Model):
    __tablename__ = "bulk_hour_operations"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))  # UUID
    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")), nullable=False
    )
    created_by = db.Column(db.String(100), nullable=False)
    custom_date = db.Column(db.Date, nullable=False)
    hours = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'acrescimo' ou 'desconto'
    observation = db.Column(db.String(500), nullable=False)
    cycle_week_id = db.Column(db.Integer, nullable=True)
    cycle_month_id = db.Column(db.Integer, nullable=True)
    total_collaborators = db.Column(db.Integer, nullable=False)
    correction_of_id = db.Column(
        db.String(36), db.ForeignKey("bulk_hour_operations.id"), nullable=True
    )  # Para rastrear correções
    # Relacionamento reverso para correções
    corrections = db.relationship("BulkHourOperation", backref=db.backref("original_lote", remote_side=[id]), lazy=True)


class User(UserMixin, db.Model):
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.Text)
    nivel = db.Column(db.String(20), default="visualizador")

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
    categoria = db.Column(db.String(50), nullable=True, index=True)
    unidade = db.Column(db.String(10), default="un")
    localizacao = db.Column(db.String(50), nullable=True)
    ativo = db.Column(db.Boolean, default=True, index=True)

    historicos = db.relationship("Historico", backref="produto", lazy=True)


class Historico(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
        index=True,
    )
    product_id = db.Column(db.Integer, db.ForeignKey("produto.id"), index=True)
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

    historicos = db.relationship("CleaningHistory", backref="task", lazy=True)
    checklist_template = db.relationship("CleaningChecklistTemplate", backref="task", lazy=True)


class CleaningHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("cleaning_task.id"), nullable=True)
    data_conclusao = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    nome_limpeza = db.Column(db.String(100))
    observacao = db.Column(db.String(500))
    designados = db.Column(db.String(255))
    usuario_conclusao = db.Column(db.String(100))
    duracao_minutos = db.Column(db.Integer, nullable=True)
    qualidade = db.Column(db.Integer, default=5)

    checklist_items = db.relationship(
        "CleaningChecklistItem",
        backref="history",
        lazy=True,
        cascade="all, delete-orphan",
    )
    photos = db.relationship(
        "CleaningHistoryPhoto",
        backref="history",
        lazy=True,
        cascade="all, delete-orphan",
    )


class CleaningChecklistTemplate(db.Model):
    __tablename__ = "cleaning_checklist_template"
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("cleaning_task.id"), nullable=True)
    tipo = db.Column(db.String(20), nullable=False)
    item_texto = db.Column(db.String(200), nullable=False)
    ordem = db.Column(db.Integer, default=0)
    obrigatorio = db.Column(db.Boolean, default=True)


class CleaningChecklistItem(db.Model):
    __tablename__ = "cleaning_checklist_item"
    id = db.Column(db.Integer, primary_key=True)
    history_id = db.Column(db.Integer, db.ForeignKey("cleaning_history.id"), nullable=False)
    item_texto = db.Column(db.String(200), nullable=False)
    concluido = db.Column(db.Boolean, default=False)
    concluido_por = db.Column(db.String(100))
    concluido_em = db.Column(db.DateTime(timezone=True))


class CleaningHistoryPhoto(db.Model):
    __tablename__ = "cleaning_history_photo"
    id = db.Column(db.Integer, primary_key=True)
    history_id = db.Column(db.Integer, db.ForeignKey("cleaning_history.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    tipo = db.Column(db.String(20), default="depois")
    caption = db.Column(db.String(200))
    uploaded_by = db.Column(db.String(100))
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )


class SystemLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    origem = db.Column(db.String(50))
    evento = db.Column(db.String(50))
    detalhes = db.Column(db.String(255))
    usuario = db.Column(db.String(100))


class NotificationRead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # 'estoque' ou 'limpeza'
    ref_id = db.Column(db.Integer, nullable=False)  # Produto.id ou CleaningTask.id
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )


class MeatReception(db.Model):
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
    recebedor_id = db.Column(db.Integer, db.ForeignKey("user.id"))


class MeatCarrier(db.Model):
    __tablename__ = "meat_carrier"
    id = db.Column(db.Integer, primary_key=True)
    reception_id = db.Column(db.Integer, db.ForeignKey("meat_reception.id"))
    nome = db.Column(db.String(100), nullable=False)
    peso = db.Column(db.Float, nullable=False)


class MeatPart(db.Model):
    __tablename__ = "meat_part"
    id = db.Column(db.Integer, primary_key=True)
    reception_id = db.Column(db.Integer, db.ForeignKey("meat_reception.id"))
    animal_numero = db.Column(db.Integer)
    categoria = db.Column(db.String(20))
    lado = db.Column(db.String(20))
    peso_bruto = db.Column(db.Float, nullable=False)
    carrier_id = db.Column(db.Integer, db.ForeignKey("meat_carrier.id"))
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
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    team_position = db.Column(db.Integer, default=1)
    telefone = db.Column(db.String(20), nullable=True)
    data_admissao = db.Column(db.Date, nullable=True)
    matricula = db.Column(db.String(30), nullable=True)
    departamento = db.Column(db.String(50), nullable=True)
    setor_id = db.Column(db.Integer, db.ForeignKey("setor.id"), nullable=True, index=True)

    user = db.relationship("User", backref="collaborator", lazy=True)
    shifts = db.relationship("Shift", backref="collaborator", lazy=True)
    setor = db.relationship("Setor", backref="colaboradores", lazy=True)
    # Relacionamentos antigos removidos - usar time_off_records


class Shift(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    collaborator_id = db.Column(db.Integer, db.ForeignKey("collaborator.id"))
    date = db.Column(db.Date, nullable=False)
    turno = db.Column(db.String(20))
    observacao = db.Column(db.String(255))
    start_dt = db.Column(db.DateTime(timezone=True))
    end_dt = db.Column(db.DateTime(timezone=True))
    shift_type = db.Column(db.String(30))
    is_sunday_holiday = db.Column(db.Boolean, default=False)
    auto_generated = db.Column(db.Boolean, default=False)


# Modelos antigos removidos - usar TimeOffRecord
# class LeaveCredit(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     collaborator_id = db.Column(db.Integer, db.ForeignKey('collaborator.id'))
#     date = db.Column(db.Date, nullable=False)
#     amount_days = db.Column(db.Integer, default=1)
#     origin = db.Column(db.String(20))
#     notes = db.Column(db.String(255))

# class HourBankEntry(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     collaborator_id = db.Column(db.Integer, db.ForeignKey('collaborator.id'))
#     date = db.Column(db.Date, nullable=False)
#     hours = db.Column(db.Float, nullable=False)
#     reason = db.Column(db.String(255))


class TemporaryEntry(db.Model):
    __tablename__ = "temporary_entry"
    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(20), nullable=False)
    collaborator_id = db.Column(db.Integer, db.ForeignKey("collaborator.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    amount_days = db.Column(db.Integer)
    hours = db.Column(db.Float)
    reason = db.Column(db.String(255))
    source = db.Column(db.String(50))
    status = db.Column(db.String(20), default="pendente")
    payload = db.Column(db.Text)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    collaborator = db.relationship("Collaborator", backref="temporary_entries", lazy=True)


class JobRole(db.Model):
    __tablename__ = "job_role"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    nivel = db.Column(db.String(20), nullable=False)


# class LeaveAssignment(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     collaborator_id = db.Column(db.Integer, db.ForeignKey('collaborator.id'))
#     date = db.Column(db.Date, nullable=False)
#     days_used = db.Column(db.Integer, default=1)
#     notes = db.Column(db.String(255))


class TimeOffRecord(db.Model):
    """Tabela unificada para armazenar horas extras, folgas adicionais e folgas usadas"""

    __tablename__ = "time_off_record"
    id = db.Column(db.Integer, primary_key=True)
    collaborator_id = db.Column(
        db.Integer,
        db.ForeignKey("collaborator.id"),
        nullable=False,
        index=True,
    )
    date = db.Column(db.Date, nullable=False, index=True)
    record_type = db.Column(
        db.String(20), nullable=False, index=True
    )  # 'horas', 'folga_adicional', 'folga_usada', 'conversao'
    hours = db.Column(db.Float, nullable=True)  # Para registros de horas
    days = db.Column(db.Integer, nullable=True)  # Para registros de folgas
    amount_paid = db.Column(db.Float, nullable=True)  # Para conversões em dinheiro
    rate_per_day = db.Column(db.Float, nullable=True)  # Para conversões
    origin = db.Column(db.String(50), nullable=True)  # Origem do registro (ex: 'horas', 'manual', 'excel')
    notes = db.Column(db.String(500), nullable=True)  # Observações/razão
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    created_by = db.Column(db.String(100), nullable=True)  # Usuário que criou o registro
    bulk_id = db.Column(
        db.String(36), db.ForeignKey("bulk_hour_operations.id"), nullable=True, index=True
    )  # Lote de origem

    collaborator = db.relationship("Collaborator", backref="time_off_records", lazy=True)
    bulk_operation = db.relationship("BulkHourOperation", backref="time_off_records", lazy=True)


class MonthStatus(db.Model):
    """Controle de estado mensal da jornada (EM ABERTO, FECHADO, ARQUIVADO)"""

    __tablename__ = "month_status"
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False, index=True)  # Ano (ex: 2026)
    month = db.Column(db.Integer, nullable=False, index=True)  # Mês (1-12)
    status = db.Column(db.String(20), nullable=False, default="aberto", index=True)  # 'aberto', 'fechado', 'arquivado'
    closed_at = db.Column(db.DateTime(timezone=True), nullable=True)  # Quando foi fechado
    closed_by = db.Column(db.String(100), nullable=True)  # Quem fechou
    archived_at = db.Column(db.DateTime(timezone=True), nullable=True)  # Quando foi arquivado
    archived_by = db.Column(db.String(100), nullable=True)  # Quem arquivou
    payment_confirmed = db.Column(db.Boolean, default=False)  # Pagamento confirmado
    payment_confirmed_at = db.Column(db.DateTime(timezone=True), nullable=True)  # Quando pagamento foi confirmado
    payment_confirmed_by = db.Column(db.String(100), nullable=True)  # Quem confirmou pagamento
    payment_date = db.Column(db.Date, nullable=True)  # Data do pagamento
    payment_amount = db.Column(db.Numeric(10, 2), nullable=True)  # Valor pago
    notes = db.Column(db.Text, nullable=True)  # Observações sobre o mês

    # Índice único para ano/mês
    __table_args__ = (db.UniqueConstraint("year", "month", name="_year_month_uc"),)

    def __repr__(self):
        return f"<MonthStatus {self.year}/{self.month:02d} - {self.status}>"

    @property
    def month_year_str(self):
        """Retorna string formatada do mês/ano"""
        month_names = [
            "",
            "Janeiro",
            "Fevereiro",
            "Março",
            "Abril",
            "Maio",
            "Junho",
            "Julho",
            "Agosto",
            "Setembro",
            "Outubro",
            "Novembro",
            "Dezembro",
        ]
        return f"{month_names[self.month]}/{self.year}"

    @property
    def is_open(self):
        """Verifica se o mês está em aberto"""
        return self.status == "aberto"

    @property
    def is_closed(self):
        """Verifica se o mês está fechado para revisão"""
        return self.status == "fechado"

    @property
    def is_archived(self):
        """Verifica se o mês está arquivado"""
        return self.status == "arquivado"


class JornadaArchive(db.Model):
    """Tabela para armazenar registros arquivados da jornada"""

    __tablename__ = "jornada_archive"
    id = db.Column(db.Integer, primary_key=True)
    archive_period_start = db.Column(db.Date, nullable=False, index=True)  # Data início do período arquivado
    archive_period_end = db.Column(db.Date, nullable=False, index=True)  # Data fim do período arquivado
    archived_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
        nullable=False,
        index=True,
    )
    archived_by = db.Column(db.String(100), nullable=True)  # Usuário que arquivou
    description = db.Column(db.String(500), nullable=True)  # Descrição do período arquivado

    # Dados do registro original (cópia)
    original_record_id = db.Column(db.Integer, nullable=False, index=True)  # ID original do registro
    collaborator_id = db.Column(
        db.Integer,
        db.ForeignKey("collaborator.id"),
        nullable=False,
        index=True,
    )
    date = db.Column(db.Date, nullable=False, index=True)
    record_type = db.Column(db.String(20), nullable=False, index=True)
    hours = db.Column(db.Float, nullable=True)
    days = db.Column(db.Integer, nullable=True)
    amount_paid = db.Column(db.Float, nullable=True)
    rate_per_day = db.Column(db.Float, nullable=True)
    origin = db.Column(db.String(50), nullable=True)
    notes = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=True)  # Data original de criação
    created_by = db.Column(db.String(100), nullable=True)  # Usuário que criou o registro original
    payment_date = db.Column(db.Date, nullable=True)  # Data do pagamento confirmado
    payment_amount = db.Column(db.Numeric(10, 2), nullable=True)  # Valor total pago no período

    collaborator = db.relationship("Collaborator", backref="jornada_archives", lazy=True)


# class LeaveConversion(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     collaborator_id = db.Column(db.Integer, db.ForeignKey('collaborator.id'))
#     date = db.Column(db.Date, nullable=False)
#     amount_days = db.Column(db.Integer, nullable=False)
#     amount_paid = db.Column(db.Float, nullable=False)
#     rate_per_day = db.Column(db.Float, default=65.0)
#     notes = db.Column(db.String(255))


class Holiday(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    kind = db.Column(db.String(20))


class NotificacaoDiaria(db.Model):
    __tablename__ = "notificacao_diaria"
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False)
    hora = db.Column(db.String(5))
    tipo = db.Column(db.String(20))
    conteudo = db.Column(db.Text)
    enviado = db.Column(db.Boolean, default=False)


class NotificacaoPersonalizada(db.Model):
    __tablename__ = "notificacao_personalizada"
    id = db.Column(db.Integer, primary_key=True)
    mensagem = db.Column(db.Text, nullable=False)
    data_criacao = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    enviar_novamente = db.Column(db.Boolean, default=True)
    enviada = db.Column(db.Boolean, default=False)


class EventoDoDia(db.Model):
    __tablename__ = "evento_dia"
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50), nullable=False)
    produto = db.Column(db.String(100))
    quantidade = db.Column(db.Integer)
    limite = db.Column(db.Integer)
    descricao = db.Column(db.String(255))
    data = db.Column(db.Date, nullable=False)


class Recipe(db.Model):
    __tablename__ = "recipe"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    preparo = db.Column(db.Text)
    embalagem = db.Column(db.String(10))
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    rendimento = db.Column(db.String(50), nullable=True)
    tempo_preparo = db.Column(db.Integer, nullable=True)

    ingredients = db.relationship(
        "RecipeIngredient",
        backref="recipe",
        lazy=True,
        cascade="all, delete-orphan",
    )


class RecipeIngredient(db.Model):
    __tablename__ = "recipe_ingredient"
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey("recipe.id"))
    produto_id = db.Column(db.Integer, db.ForeignKey("produto.id"), nullable=True)
    nome = db.Column(db.String(100), nullable=False)
    quantidade = db.Column(db.String(50), nullable=True)
    quantidade_kg = db.Column(db.Float, nullable=True)
    custo_unitario = db.Column(db.Float, nullable=True)


# ============================================================================
# Sistema de Setores
# ============================================================================


class Setor(db.Model):
    """Tabela para gerenciar setores da empresa"""

    __tablename__ = "setor"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True, index=True)
    descricao = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    created_by = db.Column(db.String(100), nullable=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=True)
    updated_by = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f"<Setor {self.nome}>"

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "descricao": self.descricao,
            "ativo": self.ativo,
            "created_at": (self.created_at.isoformat() if self.created_at else None),
            "updated_at": (self.updated_at.isoformat() if self.updated_at else None),
        }


# ============================================================================
# Sistema de Ciclos - Nova Implementação
# ============================================================================


class Ciclo(db.Model):
    """Tabela para armazenar lançamentos de horas do sistema de Ciclos"""

    __tablename__ = "ciclo"
    id = db.Column(db.Integer, primary_key=True)
    collaborator_id = db.Column(
        db.Integer,
        db.ForeignKey("collaborator.id"),
        nullable=False,
        index=True,
    )
    setor_id = db.Column(
        db.Integer, db.ForeignKey("setor.id"), nullable=False, index=True
    )  # Novo campo para divisão por setor
    nome_colaborador = db.Column(db.String(100), nullable=False)  # Cópia do nome para histórico
    data_lancamento = db.Column(db.Date, nullable=False, index=True)
    origem = db.Column(db.String(50), nullable=False)  # 'Domingo', 'Feriado', 'Horas adicionais', 'Outro'
    descricao = db.Column(db.String(500), nullable=True)  # Obrigatório se origem = 'Horas adicionais' ou 'Outro'
    valor_horas = db.Column(db.Numeric(5, 1), nullable=False)  # Decimal, múltiplos de 0.5, ponto como separador
    dias_fechados = db.Column(db.Integer, nullable=True, default=0)  # Calculado: floor(valor_horas / 8)
    horas_restantes = db.Column(db.Numeric(5, 1), nullable=True, default=0.0)  # Calculado: valor_horas % 8
    ciclo_id = db.Column(db.Integer, nullable=True, index=True)  # ID do ciclo (para agrupar por período de fechamento)
    status_ciclo = db.Column(db.String(20), nullable=False, default="ativo", index=True)  # 'ativo', 'fechado'
    valor_aproximado = db.Column(db.Numeric(10, 2), nullable=True)  # Valor em R$ aproximado (dias_fechados * valor_dia)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    created_by = db.Column(db.String(100), nullable=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=True)
    updated_by = db.Column(db.String(100), nullable=True)

    collaborator = db.relationship("Collaborator", backref="ciclos", lazy=True)
    setor = db.relationship("Setor", backref="ciclos", lazy=True)  # Novo relacionamento

    def __repr__(self):
        return f"<Ciclo {self.collaborator_id} - {self.data_lancamento} - {self.valor_horas}h>"


class CicloFolga(db.Model):
    """Folgas registradas dentro do sistema de Ciclos (resetadas apenas no fechamento mensal com pagamento)."""

    __tablename__ = "ciclo_folga"
    id = db.Column(db.Integer, primary_key=True)
    collaborator_id = db.Column(
        db.Integer,
        db.ForeignKey("collaborator.id"),
        nullable=False,
        index=True,
    )
    setor_id = db.Column(
        db.Integer, db.ForeignKey("setor.id"), nullable=False, index=True
    )  # Novo campo para divisão por setor
    nome_colaborador = db.Column(db.String(100), nullable=False)
    data_folga = db.Column(db.Date, nullable=False, index=True)
    tipo = db.Column(db.String(20), nullable=False)  # 'folga', 'folga_adicional', 'feriado'
    dias = db.Column(db.Integer, nullable=False, default=1)
    observacao = db.Column(db.Text, nullable=True)
    ciclo_id = db.Column(db.Integer, nullable=True, index=True)  # ID do ciclo (para agrupar por período de fechamento)
    status_ciclo = db.Column(db.String(20), nullable=False, default="ativo", index=True)  # 'ativo', 'fechado'
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )

    collaborator = db.relationship("Collaborator", backref="ciclos_folgas", lazy=True)
    setor = db.relationship("Setor", backref="ciclos_folgas", lazy=True)  # Novo relacionamento


class CicloOcorrencia(db.Model):
    """Ocorrências gerais (atrasos, faltas, observações) vinculadas ao ciclo mensal."""

    __tablename__ = "ciclo_ocorrencia"
    id = db.Column(db.Integer, primary_key=True)
    collaborator_id = db.Column(
        db.Integer,
        db.ForeignKey("collaborator.id"),
        nullable=False,
        index=True,
    )
    setor_id = db.Column(
        db.Integer, db.ForeignKey("setor.id"), nullable=False, index=True
    )  # Novo campo para divisão por setor
    nome_colaborador = db.Column(db.String(100), nullable=False)
    data_ocorrencia = db.Column(db.Date, nullable=False, index=True)
    tipo = db.Column(db.String(30), nullable=False, index=True)  # 'atraso' | 'falta' | 'observacao' | 'outro'
    descricao = db.Column(db.String(800), nullable=True)
    ciclo_id = db.Column(db.Integer, nullable=True, index=True)
    status_ciclo = db.Column(db.String(20), nullable=False, default="ativo", index=True)  # 'ativo' | 'fechado'
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    created_by = db.Column(db.String(100), nullable=True)

    collaborator = db.relationship("Collaborator", backref="ciclos_ocorrencias", lazy=True)
    setor = db.relationship("Setor", backref="ciclos_ocorrencias", lazy=True)  # Novo relacionamento


class CicloSemana(db.Model):
    """Arquivo de ciclos semanais (por ciclo mensal fechado) para pesquisa/histórico e PDFs."""

    __tablename__ = "ciclo_semana"
    id = db.Column(db.Integer, primary_key=True)
    ciclo_id = db.Column(db.Integer, nullable=False, index=True)  # ciclo mensal (CicloFechamento.ciclo_id)
    setor_id = db.Column(
        db.Integer, db.ForeignKey("setor.id"), nullable=False, index=True
    )  # Novo campo para divisão por setor
    week_start = db.Column(db.Date, nullable=False, index=True)
    week_end = db.Column(db.Date, nullable=False, index=True)
    label = db.Column(db.String(50), nullable=False, index=True)  # "Ciclo 1 | Janeiro" / "Ciclo Dezembro | Janeiro"
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )

    setor = db.relationship("Setor", backref="ciclos_semanas", lazy=True)  # Novo relacionamento


class CicloFechamento(db.Model):
    """Tabela para armazenar fechamentos de ciclos"""

    __tablename__ = "ciclo_fechamento"
    id = db.Column(db.Integer, primary_key=True)
    ciclo_id = db.Column(db.Integer, nullable=False, unique=True, index=True)  # ID do ciclo fechado
    setor_id = db.Column(
        db.Integer, db.ForeignKey("setor.id"), nullable=True, index=True
    )  # Campo para divisão por setor (nullable para compatibilidade com bancos antigos)
    data_fechamento = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
        nullable=False,
    )
    total_horas = db.Column(db.Numeric(10, 1), nullable=False)  # Total de horas lançadas no ciclo
    total_dias = db.Column(db.Integer, nullable=False)  # Total de dias completos do ciclo
    colaboradores_envolvidos = db.Column(db.Integer, nullable=False)  # Quantidade de colaboradores
    observacoes = db.Column(db.Text, nullable=True)
    payment_date = db.Column(db.Date, nullable=True)  # Data do pagamento
    payment_amount = db.Column(db.Numeric(10, 2), nullable=True)  # Valor pago confirmado

    setor = db.relationship("Setor", backref="ciclos_fechamentos", lazy=True)  # Novo relacionamento

    def __repr__(self):
        return f"<CicloFechamento {self.ciclo_id} - {self.data_fechamento}>"


class CicloSaldo(db.Model):
    """
    Tabela para armazenar saldo de horas para cada colaborador ao fim de cada mês.
    O saldo é a diferença entre horas totais e dias completos (saldo = total_horas % 8).
    Este saldo é carregado no próximo mês para compensar.
    """

    __tablename__ = "ciclo_saldo"
    id = db.Column(db.Integer, primary_key=True)
    collaborator_id = db.Column(
        db.Integer,
        db.ForeignKey("collaborator.id"),
        nullable=False,
        index=True,
    )
    mes_ano = db.Column(db.String(7), nullable=False, index=True)  # Formato: "01-2026", "02-2026", etc
    saldo = db.Column(db.Numeric(5, 1), nullable=False, default=0.0)  # Saldo em horas (pode ser positivo ou negativo)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    created_by = db.Column(db.String(100), nullable=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=True)
    updated_by = db.Column(db.String(100), nullable=True)

    collaborator = db.relationship("Collaborator", backref="ciclos_saldos", lazy=True)

    __table_args__ = (db.UniqueConstraint("collaborator_id", "mes_ano", name="uq_ciclo_saldo_collab_mesano"),)

    def __repr__(self):
        return f"<CicloSaldo {self.collaborator_id} - {self.mes_ano} - {self.saldo}h>"


class UserLogin(db.Model):
    __tablename__ = "user_login"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    username = db.Column(db.String(80))
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(255))
    login_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )

    user = db.relationship("User", backref="logins", lazy=True)


class Incident(db.Model):
    """Registro de incidentes e falhas do sistema"""

    __tablename__ = "incident"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
        nullable=False,
        index=True,
    )
    service = db.Column(
        db.String(50), nullable=False, index=True
    )  # 'database', 'backend', 'nginx', 'cpu', 'memory', 'disk'
    error_type = db.Column(db.String(50), nullable=False)  # 'connection_error', 'timeout', 'high_usage', etc
    message = db.Column(db.Text, nullable=False)  # Mensagem técnica do erro
    status = db.Column(db.String(20), nullable=False, default="open")  # 'open', 'resolved', 'acknowledged'
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    severity = db.Column(db.String(20), nullable=False, default="error")  # 'error', 'warning', 'info'


class MetricHistory(db.Model):
    """Histórico de métricas do sistema para análise de tendências"""

    __tablename__ = "metric_history"
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
        nullable=False,
        index=True,
    )
    metric_type = db.Column(
        db.String(50), nullable=False, index=True
    )  # 'cpu', 'memory', 'disk', 'database_response_time', 'http_latency'
    value = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=True)  # 'percent', 'ms', 'gb', 'mb'
    extra_data = db.Column(db.Text, nullable=True)  # JSON com informações adicionais


class Alert(db.Model):
    """Sistema de alertas proativos"""

    __tablename__ = "alert"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
        nullable=False,
        index=True,
    )
    alert_type = db.Column(
        db.String(50), nullable=False, index=True
    )  # 'cpu_high', 'memory_high', 'disk_high', 'database_slow', etc
    metric_type = db.Column(db.String(50), nullable=False)
    threshold_value = db.Column(db.Float, nullable=False)
    current_value = db.Column(db.Float, nullable=False)
    message = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), nullable=False, default="warning")  # 'critical', 'warning', 'info'
    status = db.Column(db.String(20), nullable=False, default="active")  # 'active', 'acknowledged', 'resolved'
    acknowledged_at = db.Column(db.DateTime(timezone=True), nullable=True)
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    acknowledged_by = db.Column(db.String(100), nullable=True)


class MaintenanceLog(db.Model):
    """Log de operações de manutenção executadas"""

    __tablename__ = "maintenance_log"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
        nullable=False,
        index=True,
    )
    maintenance_type = db.Column(
        db.String(50), nullable=False, index=True
    )  # 'cleanup_logs', 'optimize_database', 'cleanup_backups', etc
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="completed")  # 'completed', 'failed', 'running'
    duration_seconds = db.Column(db.Float, nullable=True)
    items_processed = db.Column(db.Integer, nullable=True)  # Quantos itens foram processados
    operation_details = db.Column(db.Text, nullable=True)  # JSON com detalhes da operação
    executed_by = db.Column(db.String(100), nullable=True)  # 'system' ou username


class QueryLog(db.Model):
    """Log de queries lentas do banco de dados"""

    __tablename__ = "query_log"
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
        nullable=False,
        index=True,
    )
    query = db.Column(db.Text, nullable=False)
    execution_time_ms = db.Column(db.Float, nullable=False, index=True)
    rows_returned = db.Column(db.Integer, nullable=True)
    endpoint = db.Column(db.String(200), nullable=True, index=True)
    user_id = db.Column(db.Integer, nullable=True)


class BackupVerification(db.Model):
    """Verificação de integridade de backups"""

    __tablename__ = "backup_verification"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
        nullable=False,
        index=True,
    )
    backup_filename = db.Column(db.String(255), nullable=False)
    backup_size = db.Column(db.BigInteger, nullable=True)
    verification_status = db.Column(db.String(20), nullable=False)  # 'verified', 'failed', 'corrupted'
    verification_method = db.Column(db.String(50), nullable=False)  # 'size_check', 'integrity_check', 'restore_test'
    error_message = db.Column(db.Text, nullable=True)
    verified_by = db.Column(db.String(100), nullable=True)  # 'system' ou username


class Vacation(db.Model):
    __tablename__ = "vacation"
    id = db.Column(db.Integer, primary_key=True)
    collaborator_id = db.Column(db.Integer, db.ForeignKey("collaborator.id"), nullable=False)
    data_inicio = db.Column(db.Date, nullable=False)
    data_fim = db.Column(db.Date, nullable=False)
    observacao = db.Column(db.String(255))
    criado_por = db.Column(db.String(100))
    criado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    ativo = db.Column(db.Boolean, default=True)

    collaborator = db.relationship("Collaborator", backref="vacations", lazy=True)


class MedicalCertificate(db.Model):
    __tablename__ = "medical_certificate"
    id = db.Column(db.Integer, primary_key=True)
    collaborator_id = db.Column(db.Integer, db.ForeignKey("collaborator.id"), nullable=False)
    data_inicio = db.Column(db.Date, nullable=False)
    data_fim = db.Column(db.Date, nullable=False)
    dias = db.Column(db.Integer, default=1)
    motivo = db.Column(db.String(255))
    foto_atestado = db.Column(db.String(255))
    cid = db.Column(db.String(20))
    medico = db.Column(db.String(100))
    criado_por = db.Column(db.String(100))
    criado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )

    collaborator = db.relationship("Collaborator", backref="medical_certificates", lazy=True)


class IngredientCatalog(db.Model):
    __tablename__ = "ingredient_catalog"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)
    categoria = db.Column(db.String(50))
    unidade_padrao = db.Column(db.String(20), default="kg")
    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )


class CustomSchedule(db.Model):
    __tablename__ = "custom_schedule"
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False)
    collaborator_id = db.Column(db.Integer, db.ForeignKey("collaborator.id"), nullable=False)
    turno_original = db.Column(db.String(50))
    turno_novo = db.Column(db.String(50))
    motivo = db.Column(db.String(255))
    substituto_id = db.Column(db.Integer, db.ForeignKey("collaborator.id"), nullable=True)
    criado_por = db.Column(db.String(100))
    criado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )

    collaborator = db.relationship(
        "Collaborator",
        foreign_keys=[collaborator_id],
        backref="custom_schedules",
    )
    substituto = db.relationship("Collaborator", foreign_keys=[substituto_id])


class HelpArticle(db.Model):
    __tablename__ = "help_article"
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    conteudo = db.Column(db.Text, nullable=False)
    categoria = db.Column(db.String(50), default="Geral")
    ordem = db.Column(db.Integer, default=0)
    ativo = db.Column(db.Boolean, default=True)


class RegistroJornada(db.Model):
    __tablename__ = "registro_jornada"
    id = db.Column(db.String(36), primary_key=True)
    collaborator_id = db.Column(db.Integer, db.ForeignKey("collaborator.id"), nullable=False)
    tipo_registro = db.Column(db.String(10), nullable=False)
    valor = db.Column(db.Numeric(8, 2), nullable=False)
    data = db.Column(db.Date, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    observacao = db.Column(db.String(255))

    collaborator = db.relationship("Collaborator", backref="registros_jornada", lazy=True)


class RegistroJornadaChange(db.Model):
    __tablename__ = "registro_jornada_change"
    id = db.Column(db.Integer, primary_key=True)
    worklog_id = db.Column(db.String(36), db.ForeignKey("registro_jornada.id"), nullable=False)
    changed_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    old_tipo = db.Column(db.String(10))
    old_valor = db.Column(db.Numeric(8, 2))
    old_data = db.Column(db.Date)
    new_tipo = db.Column(db.String(10))
    new_valor = db.Column(db.Numeric(8, 2))
    new_data = db.Column(db.Date)
    changed_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )

    worklog = db.relationship("RegistroJornada", backref="changes", lazy=True)
    votos_util = db.Column(db.Integer, default=0)
    votos_nao_util = db.Column(db.Integer, default=0)
    criado_por = db.Column(db.String(100))
    criado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    atualizado_em = db.Column(
        db.DateTime(timezone=True),
        onupdate=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )


class ArticleVote(db.Model):
    __tablename__ = "article_vote"
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey("help_article.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    util = db.Column(db.Boolean, nullable=False)
    voted_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )


class Suggestion(db.Model):
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


class SuggestionVote(db.Model):
    __tablename__ = "suggestion_vote"
    id = db.Column(db.Integer, primary_key=True)
    suggestion_id = db.Column(db.Integer, db.ForeignKey("suggestion.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    voted_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )


# Estoque de Produção com Previsão de Uso
class EstoqueProducao(db.Model):
    __tablename__ = "estoque_producao"
    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey("produto.id"), nullable=False, index=True)
    quantidade = db.Column(db.Float, nullable=False, default=0)  # Não pode ser negativo
    setor_id = db.Column(db.Integer, db.ForeignKey("setor.id"), nullable=False, index=True)
    previsao_uso = db.Column(db.String(100), nullable=True, index=True)  # Ex: "Carnaval 2026", "Fim de Semana"
    data_previsao = db.Column(db.Date, nullable=True, index=True)  # Data específica da previsão
    data_registro = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
        index=True,
    )
    criado_por = db.Column(db.String(100))
    observacao = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, default=True, index=True)

    # Relacionamentos
    produto = db.relationship("Produto", backref=db.backref("estoque_producao", lazy="dynamic"))
    setor = db.relationship("Setor", backref=db.backref("estoque_producao", lazy="dynamic"))
    historico = db.relationship(
        "HistoricoAjusteEstoque",
        backref="estoque",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<EstoqueProducao {self.produto.nome if self.produto else 'N/A'} - {self.quantidade}>"


class HistoricoAjusteEstoque(db.Model):
    __tablename__ = "historico_ajuste_estoque"
    id = db.Column(db.Integer, primary_key=True)
    estoque_id = db.Column(
        db.Integer,
        db.ForeignKey("estoque_producao.id"),
        nullable=False,
        index=True,
    )
    data_ajuste = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
        index=True,
    )
    tipo_ajuste = db.Column(db.String(20), nullable=False)  # 'entrada', 'saida', 'correcao'
    quantidade_anterior = db.Column(db.Float, nullable=False)
    quantidade_ajuste = db.Column(db.Float, nullable=False)  # Positivo ou negativo
    quantidade_nova = db.Column(db.Float, nullable=False)
    motivo = db.Column(db.String(255), nullable=False)
    ajustado_por = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<HistoricoAjusteEstoque {self.tipo_ajuste} - {self.quantidade_ajuste}>"


class EscalaEspecial(db.Model):
    """Modelo para escalas especiais/futuras (limpeza, feriados, redistribuições, etc)"""

    __tablename__ = "escala_especial"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False, index=True)
    descricao = db.Column(db.Text, nullable=True)
    tipo = db.Column(
        db.String(50), nullable=False, index=True
    )  # 'limpeza', 'feriado', 'redistribuicao', 'evento', 'outro'

    # Período de aplicação
    data_inicio = db.Column(db.Date, nullable=False, index=True)
    data_fim = db.Column(db.Date, nullable=False, index=True)

    # Configuração de atribuição de turno
    turno_customizado = db.Column(db.String(100), nullable=True)  # Ex: "08:00-17:00"
    criterio_atribuicao = db.Column(
        db.String(50), nullable=False, default="todos"
    )  # 'todos', 'por_equipe', 'por_numero', 'manual'

    # Se criterio_atribuicao for 'por_equipe'
    equipe_id = db.Column(db.Integer, db.ForeignKey("setor.id"), nullable=True)
    equipe = db.relationship("Setor", backref="escalas_especiais")

    # Se criterio_atribuicao for 'por_numero'
    numero_pessoas = db.Column(db.Integer, nullable=True)

    # Colaboradores selecionados (para critério manual)
    colaboradores_selecionados = db.Column(db.JSON, nullable=True)  # Lista de IDs

    # Status
    ativo = db.Column(db.Boolean, default=True, index=True)

    # Metadata
    criado_em = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")), nullable=False
    )
    atualizado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
        onupdate=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
        nullable=False,
    )
    criado_por = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<EscalaEspecial {self.nome} ({self.tipo}) - {self.data_inicio} a {self.data_fim}>"

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "descricao": self.descricao,
            "tipo": self.tipo,
            "data_inicio": self.data_inicio.isoformat(),
            "data_fim": self.data_fim.isoformat(),
            "turno_customizado": self.turno_customizado,
            "criterio_atribuicao": self.criterio_atribuicao,
            "numero_pessoas": self.numero_pessoas,
            "colaboradores_selecionados": self.colaboradores_selecionados,
            "ativo": self.ativo,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
            "atualizado_em": self.atualizado_em.isoformat() if self.atualizado_em else None,
            "criado_por": self.criado_por,
        }
