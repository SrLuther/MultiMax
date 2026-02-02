#!/usr/bin/env python3
"""
Cria usuário de teste com senha conhecida
"""
import os

os.environ["DATABASE_URL"] = "postgresql://multimax:multimax123@localhost:5432/multimax?sslmode=disable"

from werkzeug.security import generate_password_hash

from multimax import create_app, db
from multimax.models.user import User

app = create_app()

with app.app_context():
    # Verificar se usuário 'test' já existe
    test_user = User.query.filter_by(username="test").first()

    if not test_user:
        # Criar novo usuário de teste
        test_user = User(username="test", name="Usuário de Teste", nivel="admin", ativo=True)
        test_user.password_hash = generate_password_hash("teste123")
        db.session.add(test_user)
        db.session.commit()
        print("✓ Usuário 'test' criado com sucesso!")
        print("  Username: test")
        print("  Password: teste123")
    else:
        print(f"✓ Usuário 'test' já existe (ID: {test_user.id})")

    # Listar todos os usuários
    users = User.query.all()
    print(f"\nTotal de usuários: {len(users)}")
    for u in users[:5]:
        print(f"  - {u.username}: {u.name}")
