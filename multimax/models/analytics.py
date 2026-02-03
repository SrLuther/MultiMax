"""
Modelos para Análise e Registros de Analytics
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from . import db


class MetricHistory(db.Model):
    """Modelo para histórico de métricas do sistema para análise de tendências"""

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

    def __repr__(self):
        return f"<MetricHistory {self.metric_type} - {self.value}{self.unit}>"


class QueryLog(db.Model):
    """Modelo para log de queries lentas do banco de dados"""

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

    def __repr__(self):
        return f"<QueryLog {self.execution_time_ms}ms - {self.timestamp}>"


class BackupVerification(db.Model):
    """Modelo para verificação de integridade de backups"""

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

    def __repr__(self):
        return f"<BackupVerification {self.backup_filename} - {self.verification_status}>"
