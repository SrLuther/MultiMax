"""
Modelos para Monitoramento, Notificações, Incidentes e Alertas
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from . import db


class NotificationRead(db.Model):
    """Modelo para rastrear notificações lidas pelos usuários"""

    __tablename__ = "notification_read"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # 'estoque' ou 'limpeza'
    ref_id = db.Column(db.Integer, nullable=False)  # Produto.id ou CleaningTask.id
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )

    def __repr__(self):
        return f"<NotificationRead {self.user_id} - {self.tipo}>"


class Incident(db.Model):
    """Modelo para registrar incidentes e falhas do sistema"""

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

    def __repr__(self):
        return f"<Incident {self.service} - {self.error_type} - {self.status}>"


class Alert(db.Model):
    """Modelo para sistema de alertas proativos"""

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

    def __repr__(self):
        return f"<Alert {self.alert_type} - {self.status}>"


class MaintenanceLog(db.Model):
    """Modelo para log de operações de manutenção executadas"""

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

    def __repr__(self):
        return f"<MaintenanceLog {self.maintenance_type} - {self.status}>"
