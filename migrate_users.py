#!/usr/bin/env python3
"""
Migra dados da tabela 'user' para 'users' no PostgreSQL
"""
from sqlalchemy import create_engine, text

engine = create_engine("postgresql://multimax:multimax123@localhost:5432/multimax")

with engine.connect() as conn:
    # Copiar dados de user para users (apenas colunas em comum)
    result = conn.execute(
        text(
            """
        INSERT INTO users (id, name, username, password_hash, nivel, ativo, created_at, updated_at)
        SELECT id, name, username, password_hash, nivel, TRUE, NOW(), NOW()
        FROM "user"
        ON CONFLICT (id) DO NOTHING
    """
        )
    )
    conn.commit()

    print(f"✓ {result.rowcount} usuários copiados de 'user' para 'users'")

    # Verificar total
    result = conn.execute(text("SELECT COUNT(*) FROM users"))
    total = result.scalar()
    print(f"✓ Total de usuários em 'users': {total}")

    # Listar usuários
    result = conn.execute(text("SELECT id, username, name, nivel, ativo FROM users ORDER BY id"))
    print("\nUsuários migrados:")
    for row in result:
        print(f"  - ID: {row[0]}, Username: {row[1]}, Nome: {row[2]}, Nível: {row[3]}, Ativo: {row[4]}")
