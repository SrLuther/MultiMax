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
from .ciclo import CicloMensal, CicloSemanal, HistoricoColaborador
from .colaborador import Colaborador
from .escala import Escala
from .logs import Heartbeat, LogDeploy, LogErro, LogWhatsapp
from .user import User
from .whatsapp_config import WhatsappConfig, WhatsappMessage

db: SQLAlchemy = app_db
Base = db.Model

# Legacy models (multimax/models.py) - compatibilidade
_LEGACY_PATH = Path(__file__).resolve().parent.parent / "models.py"
_legacy = None
if _LEGACY_PATH.exists():
    spec = importlib.util.spec_from_file_location("multimax._legacy_models", _LEGACY_PATH)
    if spec and spec.loader:
        _legacy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_legacy)


def _legacy_attr(name: str) -> Any:
    return getattr(_legacy, name, None)


Alert = _legacy_attr("Alert")
AppSetting = _legacy_attr("AppSetting")
ArticleVote = _legacy_attr("ArticleVote")
BackupVerification = _legacy_attr("BackupVerification")
BulkHourOperation = _legacy_attr("BulkHourOperation")
Ciclo = _legacy_attr("Ciclo")
CicloFechamento = _legacy_attr("CicloFechamento")
CicloFolga = _legacy_attr("CicloFolga")
CicloOcorrencia = _legacy_attr("CicloOcorrencia")
CicloSaldo = _legacy_attr("CicloSaldo")
CicloSemana = _legacy_attr("CicloSemana")
CleaningChecklistItem = _legacy_attr("CleaningChecklistItem")
CleaningChecklistTemplate = _legacy_attr("CleaningChecklistTemplate")
CleaningHistory = _legacy_attr("CleaningHistory")
CleaningHistoryPhoto = _legacy_attr("CleaningHistoryPhoto")
CleaningTask = _legacy_attr("CleaningTask")
Collaborator = _legacy_attr("Collaborator")
CustomSchedule = _legacy_attr("CustomSchedule")
EscalaEspecial = _legacy_attr("EscalaEspecial")
EstoqueProducao = _legacy_attr("EstoqueProducao")
EventoDoDia = _legacy_attr("EventoDoDia")
HelpArticle = _legacy_attr("HelpArticle")
Historico = _legacy_attr("Historico")
HistoricoAjusteEstoque = _legacy_attr("HistoricoAjusteEstoque")
Holiday = _legacy_attr("Holiday")
Incident = _legacy_attr("Incident")
IngredientCatalog = _legacy_attr("IngredientCatalog")
JobRole = _legacy_attr("JobRole")
JornadaArchive = _legacy_attr("JornadaArchive")
MaintenanceLog = _legacy_attr("MaintenanceLog")
MeatCarrier = _legacy_attr("MeatCarrier")
MeatPart = _legacy_attr("MeatPart")
MeatReception = _legacy_attr("MeatReception")
MedicalCertificate = _legacy_attr("MedicalCertificate")
MetricHistory = _legacy_attr("MetricHistory")
MonthStatus = _legacy_attr("MonthStatus")
NotificacaoDiaria = _legacy_attr("NotificacaoDiaria")
NotificacaoPersonalizada = _legacy_attr("NotificacaoPersonalizada")
NotificationRead = _legacy_attr("NotificationRead")
Produto = _legacy_attr("Produto")
QueryLog = _legacy_attr("QueryLog")
Recipe = _legacy_attr("Recipe")
RecipeIngredient = _legacy_attr("RecipeIngredient")
RegistroJornada = _legacy_attr("RegistroJornada")
RegistroJornadaChange = _legacy_attr("RegistroJornadaChange")
Setor = _legacy_attr("Setor")
Shift = _legacy_attr("Shift")
Suggestion = _legacy_attr("Suggestion")
SuggestionVote = _legacy_attr("SuggestionVote")
SystemLog = _legacy_attr("SystemLog")
TemporaryEntry = _legacy_attr("TemporaryEntry")
TimeOffRecord = _legacy_attr("TimeOffRecord")
UserLogin = _legacy_attr("UserLogin")
Vacation = _legacy_attr("Vacation")

_LEGACY_EXPORTS = [
    "Alert",
    "AppSetting",
    "ArticleVote",
    "BackupVerification",
    "BulkHourOperation",
    "Ciclo",
    "CicloFechamento",
    "CicloFolga",
    "CicloOcorrencia",
    "CicloSaldo",
    "CicloSemana",
    "CleaningChecklistItem",
    "CleaningChecklistTemplate",
    "CleaningHistory",
    "CleaningHistoryPhoto",
    "CleaningTask",
    "Collaborator",
    "CustomSchedule",
    "EscalaEspecial",
    "EstoqueProducao",
    "EventoDoDia",
    "HelpArticle",
    "Historico",
    "HistoricoAjusteEstoque",
    "Holiday",
    "Incident",
    "IngredientCatalog",
    "JobRole",
    "JornadaArchive",
    "MaintenanceLog",
    "MeatCarrier",
    "MeatPart",
    "MeatReception",
    "MedicalCertificate",
    "MetricHistory",
    "MonthStatus",
    "NotificacaoDiaria",
    "NotificacaoPersonalizada",
    "NotificationRead",
    "Produto",
    "QueryLog",
    "Recipe",
    "RecipeIngredient",
    "RegistroJornada",
    "RegistroJornadaChange",
    "Setor",
    "Shift",
    "Suggestion",
    "SuggestionVote",
    "SystemLog",
    "TemporaryEntry",
    "TimeOffRecord",
    "UserLogin",
    "Vacation",
]

__all__ = [
    "db",
    "Base",
    "User",
    "Colaborador",
    "CicloSemanal",
    "CicloMensal",
    "HistoricoColaborador",
    "Escala",
    "WhatsappConfig",
    "WhatsappMessage",
    "LogErro",
    "LogWhatsapp",
    "LogDeploy",
    "Heartbeat",
    *(_LEGACY_EXPORTS),
]
