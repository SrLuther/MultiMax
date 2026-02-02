#!/usr/bin/env python3
"""
Diagnostica schemas das tabelas user e users
"""
from sqlalchemy import create_engine, text

engine = create_engine("postgresql://multimax:multimax123@localhost:5432/multimax")

with engine.connect() as conn:
    # Ver quais colunas existem na tabela 'user'
    result = conn.execute(
        text(
            """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'user'
        ORDER BY ordinal_position
    """
        )
    )
    user_columns = [row[0] for row in result]
    print(f"Colunas em 'user': {user_columns}")

    # Ver quais colunas existem na tabela 'users'
    result = conn.execute(
        text(
            """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'users'
        ORDER BY ordinal_position
    """
        )
    )
    users_columns = [row[0] for row in result]
    print(f"Colunas em 'users': {users_columns}")

    # Encontrar colunas em comum
    common_columns = list(set(user_columns) & set(users_columns))
    print(f"\nColunas em comum: {common_columns}")

    # Ver dados na tabela 'user'
    result = conn.execute(text('SELECT * FROM "user" LIMIT 2'))
    rows = result.fetchall()
    print(f"\nTotal registros em 'user': {len(rows)}")
    if rows:
        for row in rows:
            print(f"  Registro: {dict(zip(user_columns, row))}")
