"""
Modelos para Agendamento de Jornada, Ciclos e Registros de Horas
"""

import uuid
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .. import db as app_db

db: Any = app_db


class BulkHourOperation(db.Model):
    """Modelo para operações em lote de horas"""

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

    def __repr__(self):
        return f"<BulkHourOperation {self.type} - {self.hours}h - {self.custom_date}>"


class TimeOffRecord(db.Model):
    """Modelo para tabela unificada de horas extras, folgas adicionais e folgas usadas"""

    __tablename__ = "time_off_record"
    id = db.Column(db.Integer, primary_key=True)
    collaborator_id = db.Column(
        db.Integer,
        db.ForeignKey("colaboradores.id"),
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

    collaborator = db.relationship(
        "Colaborador",
        foreign_keys=[collaborator_id],
        primaryjoin="TimeOffRecord.collaborator_id==Colaborador.id",
        backref="time_off_records",
        lazy=True,
    )
    bulk_operation = db.relationship("BulkHourOperation", backref="time_off_records", lazy=True)

    def __repr__(self):
        return f"<TimeOffRecord {self.collaborator_id} - {self.record_type} - {self.date}>"


class MonthStatus(db.Model):
    """Modelo para controle de estado mensal da jornada (EM ABERTO, FECHADO, ARQUIVADO)"""

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


class CicloFolga(db.Model):
    """Folgas registradas dentro do sistema de Ciclos.

    Resetadas apenas no fechamento mensal com pagamento.
    """

    __tablename__ = "ciclo_folga"
    id = db.Column(db.Integer, primary_key=True)
    collaborator_id = db.Column(
        db.Integer,
        db.ForeignKey("colaboradores.id"),
        nullable=False,
        index=True,
    )
    setor_id = db.Column(
        db.Integer, db.ForeignKey("setor.id"), nullable=False, index=True
    )  # Campo para divisão por setor
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

    collaborator = db.relationship(
        "Colaborador",
        foreign_keys=[collaborator_id],
        primaryjoin="CicloFolga.collaborator_id==Colaborador.id",
        backref="ciclos_folgas",
        lazy=True,
    )
    setor = db.relationship(
        "Setor",
        foreign_keys=[setor_id],
        primaryjoin="CicloFolga.setor_id==Setor.id",
        backref="ciclos_folgas",
        lazy=True,
    )

    def __repr__(self):
        return f"<CicloFolga {self.collaborator_id} - {self.data_folga} - {self.tipo}>"


class CicloOcorrencia(db.Model):
    """Modelo para ocorrências gerais (atrasos, faltas, observações) vinculadas ao ciclo mensal."""

    __tablename__ = "ciclo_ocorrencia"
    id = db.Column(db.Integer, primary_key=True)
    collaborator_id = db.Column(
        db.Integer,
        db.ForeignKey("colaboradores.id"),
        nullable=False,
        index=True,
    )
    setor_id = db.Column(
        db.Integer, db.ForeignKey("setor.id"), nullable=False, index=True
    )  # Campo para divisão por setor
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

    collaborator = db.relationship(
        "Colaborador",
        foreign_keys=[collaborator_id],
        primaryjoin="CicloOcorrencia.collaborator_id==Colaborador.id",
        backref="ciclos_ocorrencias",
        lazy=True,
    )
    setor = db.relationship(
        "Setor",
        foreign_keys=[setor_id],
        primaryjoin="CicloOcorrencia.setor_id==Setor.id",
        backref="ciclos_ocorrencias",
        lazy=True,
    )

    def __repr__(self):
        return f"<CicloOcorrencia {self.collaborator_id} - {self.data_ocorrencia} - {self.tipo}>"


class CicloSemana(db.Model):
    """Modelo para arquivo de ciclos semanais (por ciclo mensal fechado) para pesquisa/histórico e PDFs."""

    __tablename__ = "ciclo_semana"
    id = db.Column(db.Integer, primary_key=True)
    ciclo_id = db.Column(db.Integer, nullable=False, index=True)  # ciclo mensal (CicloFechamento.ciclo_id)
    setor_id = db.Column(
        db.Integer, db.ForeignKey("setor.id"), nullable=False, index=True
    )  # Campo para divisão por setor
    week_start = db.Column(db.Date, nullable=False, index=True)
    week_end = db.Column(db.Date, nullable=False, index=True)
    label = db.Column(db.String(50), nullable=False, index=True)  # "Ciclo 1 | Janeiro" / "Ciclo Dezembro | Janeiro"
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )

    setor = db.relationship(
        "Setor",
        foreign_keys=[setor_id],
        backref="ciclos_semanas",
        lazy=True,
    )

    def __repr__(self):
        return f"<CicloSemana {self.label} - {self.week_start} a {self.week_end}>"


class CicloFechamento(db.Model):
    """Modelo para armazenar fechamentos de ciclos"""

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

    setor = db.relationship(
        "Setor",
        foreign_keys=[setor_id],
        backref="ciclos_fechamentos",
        lazy=True,
    )

    def __repr__(self):
        return f"<CicloFechamento {self.ciclo_id} - {self.data_fechamento}>"


class CicloSaldo(db.Model):
    """Modelo para armazenar saldo de horas para cada colaborador ao fim de cada mês."""

    __tablename__ = "ciclo_saldo"
    id = db.Column(db.Integer, primary_key=True)
    collaborator_id = db.Column(
        db.Integer,
        db.ForeignKey("colaboradores.id"),
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

    collaborator = db.relationship(
        "Colaborador",
        foreign_keys=[collaborator_id],
        primaryjoin="CicloSaldo.collaborator_id==Colaborador.id",
        backref="ciclos_saldos",
        lazy=True,
    )

    __table_args__ = (db.UniqueConstraint("collaborator_id", "mes_ano", name="uq_ciclo_saldo_collab_mesano"),)

    def __repr__(self):
        return f"<CicloSaldo {self.collaborator_id} - {self.mes_ano} - {self.saldo}h>"


class RegistroJornada(db.Model):
    """Modelo para registros de jornada de trabalho"""

    __tablename__ = "registro_jornada"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    collaborator_id = db.Column(db.Integer, db.ForeignKey("colaboradores.id"), nullable=False)
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

    collaborator = db.relationship(
        "Colaborador",
        foreign_keys=[collaborator_id],
        primaryjoin="RegistroJornada.collaborator_id==Colaborador.id",
        backref="registros_jornada",
        lazy=True,
    )

    def __repr__(self):
        return f"<RegistroJornada {self.collaborator_id} - {self.tipo_registro} - {self.valor}>"


class RegistroJornadaChange(db.Model):
    """Modelo para rastrear mudanças em registros de jornada"""

    __tablename__ = "registro_jornada_change"
    id = db.Column(db.Integer, primary_key=True)
    worklog_id = db.Column(db.String(36), db.ForeignKey("registro_jornada.id"), nullable=False)
    changed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
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

    worklog = db.relationship("RegistroJornada", backref="changes", lazy=True)

    def __repr__(self):
        return f"<RegistroJornadaChange {self.worklog_id} - {self.changed_at}>"
