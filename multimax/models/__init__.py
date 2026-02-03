"""
SQLAlchemy Models - PostgreSQL como fonte única da verdade
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, cast

from flask_sqlalchemy import SQLAlchemy

from .. import db as app_db

# Novos models (PostgreSQL)
from .analytics import BackupVerification, MetricHistory, QueryLog
from .ciclo import CicloMensal, CicloSemanal, HistoricoColaborador
from .colaborador import Colaborador
from .content import ArticleVote, CustomSchedule, HelpArticle, Suggestion, SuggestionVote
from .escala import Escala
from .logs import Heartbeat, LogDeploy, LogErro, LogWhatsapp
from .logs_auth import SystemLog, UserLogin
from .management import JobRole, MedicalCertificate, Setor, Shift, Vacation
from .meats import MeatCarrier, MeatPart, MeatReception
from .monitoring import Alert, Incident, MaintenanceLog, NotificationRead
from .operations import (
    CleaningChecklistItem,
    CleaningChecklistTemplate,
    CleaningHistory,
    CleaningHistoryPhoto,
    CleaningTask,
    Historico,
)
from .production import IngredientCatalog, Produto, Recipe, RecipeIngredient
from .scheduling import (
    BulkHourOperation,
    CicloFechamento,
    CicloFolga,
    CicloOcorrencia,
    CicloSaldo,
    CicloSemana,
    MonthStatus,
    RegistroJornada,
    RegistroJornadaChange,
    TimeOffRecord,
)
from .special import AppSetting, EscalaEspecial, EstoqueProducao, HistoricoAjusteEstoque
from .user import User
from .whatsapp_config import WhatsappConfig, WhatsappMessage

# Aliases para compatibilidade com código existente
Collaborator = Colaborador

db: SQLAlchemy = app_db
Base = db.Model

# Legacy models (multimax/models.py) - compatibilidade
# DESABILITADO: Carregamento de legacy models causa conflito no registry do SQLAlchemy
# Modelos novos em models/ devem ser usados em seu lugar
_LEGACY_PATH = None
_legacy = None


def _legacy_attr(name: str) -> Any:
    return getattr(_legacy, name, None) if _legacy else None


# Removido: todos os _legacy_attr agora retornam None porque legacy module está desabilitado
# A compatibilidade é mantida através de aliases (ex: Collaborator)

_LEGACY_EXPORTS = []

__all__ = [
    "db",
    "Base",
    # App Configuration
    "AppSetting",
    # User
    "User",
    "UserLogin",
    # Colaborador
    "Colaborador",
    "Collaborator",  # Alias para compatibilidade
    # Ciclos
    "CicloSemanal",
    "CicloMensal",
    "HistoricoColaborador",
    "CicloFolga",
    "CicloOcorrencia",
    "CicloSemana",
    "CicloFechamento",
    "CicloSaldo",
    # Escala
    "Escala",
    "EscalaEspecial",
    # Setores e Gestão
    "Setor",
    "Shift",
    "JobRole",
    "Vacation",
    "MedicalCertificate",
    # Carnes
    "MeatReception",
    "MeatCarrier",
    "MeatPart",
    # Produção
    "Produto",
    "Recipe",
    "RecipeIngredient",
    "IngredientCatalog",
    # Estoque
    "EstoqueProducao",
    "HistoricoAjusteEstoque",
    # Jornada
    "BulkHourOperation",
    "TimeOffRecord",
    "MonthStatus",
    "RegistroJornada",
    "RegistroJornadaChange",
    # Limpeza
    "CleaningTask",
    "CleaningHistory",
    "CleaningChecklistTemplate",
    "CleaningChecklistItem",
    "CleaningHistoryPhoto",
    "Historico",
    # Monitoramento
    "NotificationRead",
    "Incident",
    "Alert",
    "MaintenanceLog",
    # Conteúdo
    "CustomSchedule",
    "HelpArticle",
    "Suggestion",
    "SuggestionVote",
    "ArticleVote",
    # Analytics
    "MetricHistory",
    "QueryLog",
    "BackupVerification",
    # Logs
    "SystemLog",
    "LogErro",
    "LogWhatsapp",
    "LogDeploy",
    "Heartbeat",
    # WhatsApp
    "WhatsappConfig",
    "WhatsappMessage",
]
