#!/usr/bin/env python3
"""
Reseta senha do usuário dev para 'dev123'
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from werkzeug.security import generate_password_hash  # noqa: E402

from multimax import create_app, db  # noqa: E402
from multimax.models.user import User  # noqa: E402

app = create_app()

with app.app_context():
    # Buscar usuário dev
    dev = User.query.filter_by(username="dev").first()

    if dev:
        # Resetar senha
        dev.password_hash = generate_password_hash("dev123")
        db.session.commit()
        print("✓ Senha do usuário 'dev' resetada para 'dev123'")
        print(f"  Hash: {dev.password_hash[:50]}...")
    else:
        print("✗ Usuário 'dev' não encontrado")

    # Verificar
    dev = User.query.filter_by(username="dev").first()
    if dev:
        print("\n✓ Usuário confirmado:")
        print(f"  ID: {dev.id}")
        print(f"  Username: {dev.username}")
        print(f"  Name: {dev.name}")
        print(f"  Nível: {dev.nivel}")
        print(f"  Ativo: {dev.ativo}")
