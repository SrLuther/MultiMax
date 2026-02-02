"""
SQLAlchemy Models - PostgreSQL como fonte única da verdade
"""

from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import declarative_base

db = SQLAlchemy()
Base = declarative_base()

from .ciclo import CicloMensal, CicloSemanal, HistoricoColaborador
from .colaborador import Colaborador
from .escala import Escala
from .logs import Heartbeat, LogDeploy, LogErro, LogWhatsapp

# Importar todos os models aqui
from .user import User
from .whatsapp_config import WhatsappConfig

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
    "LogErro",
    "LogWhatsapp",
    "LogDeploy",
    "Heartbeat",
]
