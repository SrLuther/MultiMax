#!/usr/bin/env python3
"""
Reseta senha do usuário admin para 'admin123'
"""
import os

os.environ["DATABASE_URL"] = "postgresql://multimax:multimax123@localhost:5432/multimax?sslmode=disable"

from werkzeug.security import generate_password_hash

from multimax import create_app, db
from multimax.models.user import User

app = create_app()

with app.app_context():
    # Buscar usuário admin
    admin = User.query.filter_by(username="admin").first()

    if admin:
        # Resetar senha
        admin.password_hash = generate_password_hash("admin123")
        db.session.commit()
        print(f"✓ Senha do usuário 'admin' resetada para 'admin123'")
        print(f"  Hash: {admin.password_hash[:50]}...")
    else:
        print("✗ Usuário 'admin' não encontrado")

    # Verificar
    admin = User.query.filter_by(username="admin").first()
    if admin:
        print(f"\n✓ Usuário confirmado:")
        print(f"  ID: {admin.id}")
        print(f"  Username: {admin.username}")
        print(f"  Name: {admin.name}")
        print(f"  Nível: {admin.nivel}")
        print(f"  Ativo: {admin.ativo}")
