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
    "User",
    "Colaborador",
    "Collaborator",  # Alias para compatibilidade
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
]
