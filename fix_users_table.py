#!/usr/bin/env python3
from sqlalchemy import create_engine, text

engine = create_engine("postgresql://multimax:multimax123@localhost:5432/multimax")

with engine.connect() as conn:
    # Copiar dados de user para users (apenas colunas que existem em 'user')
    conn.execute(
        text(
            """
        INSERT INTO users (id, name, username, password_hash, nivel, ativo)
        SELECT
            id,
            name,
            username,
            password_hash,
            nivel,
            TRUE as ativo
        ON CONFLICT (id) DO NOTHING
    """
        )
    )
    conn.commit()

    # Verificar total
    result = conn.execute(text("SELECT COUNT(*) FROM users"))
    total = result.scalar()
    print(f"✓ Total de usuários em 'users': {total}")

    # Listar usuários
    result = conn.execute(text("SELECT id, username, name, nivel FROM users LIMIT 5"))
    print("\nUsuários migrados:")
    for row in result:
        print(f"  - ID: {row[0]}, Username: {row[1]}, Nome: {row[2]}, Nível: {row[3]}")
