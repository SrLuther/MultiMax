#!/usr/bin/env python
"""Executar migração manualmente sem alembic.ini"""

import os
from pathlib import Path

from alembic import command

# Setup alembic config programaticamente
from alembic.config import Config

# Settar DATABASE_URL
db_path = Path(__file__).parent / "instance" / "multimax.db"
os.environ["DATABASE_URL"] = f"sqlite:///{str(db_path)}"

# Criar config
alembic_dir = Path(__file__).parent / "alembic"
config = Config()
config.set_main_option("script_location", str(alembic_dir))
config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])

# Executar upgrade
print("Executando migração de setor_id...")
print(f"Database: {os.environ['DATABASE_URL']}")
try:
    # Primeiro stamp com a migration 001
    print("Stamping com revisão 001...")
    command.stamp(config, "001")
    print("✓ Stamp 001 completo")

    # Depois upgrade para head
    print("Fazendo upgrade para head...")
    command.upgrade(config, "head")
    print("✓ Migração executada com sucesso!")
except Exception as e:
    print(f"✗ Erro na migração: {e}")
    import traceback

    traceback.print_exc()
