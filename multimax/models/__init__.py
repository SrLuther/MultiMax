"""
SQLAlchemy Models - PostgreSQL como fonte única da verdade
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import declarative_base

# Novos models (PostgreSQL)
from .ciclo import CicloMensal, CicloSemanal, HistoricoColaborador
from .colaborador import Colaborador
from .escala import Escala
from .logs import Heartbeat, LogDeploy, LogErro, LogWhatsapp
from .user import User
from .whatsapp_config import WhatsappConfig, WhatsappMessage

db = SQLAlchemy()
Base = declarative_base()

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


AppSetting = _legacy_attr("AppSetting")
BulkHourOperation = _legacy_attr("BulkHourOperation")
Ciclo = _legacy_attr("Ciclo")
CicloFechamento = _legacy_attr("CicloFechamento")
CicloFolga = _legacy_attr("CicloFolga")
CicloOcorrencia = _legacy_attr("CicloOcorrencia")
CicloSemana = _legacy_attr("CicloSemana")
CicloSaldo = _legacy_attr("CicloSaldo")
Collaborator = _legacy_attr("Collaborator")
MedicalCertificate = _legacy_attr("MedicalCertificate")
Setor = _legacy_attr("Setor")
SystemLog = _legacy_attr("SystemLog")
TimeOffRecord = _legacy_attr("TimeOffRecord")
Vacation = _legacy_attr("Vacation")

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
    "AppSetting",
    "BulkHourOperation",
    "Ciclo",
    "CicloFechamento",
    "CicloFolga",
    "CicloOcorrencia",
    "CicloSemana",
    "CicloSaldo",
    "Collaborator",
    "MedicalCertificate",
    "Setor",
    "SystemLog",
    "TimeOffRecord",
    "Vacation",
]
