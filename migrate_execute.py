#!/usr/bin/env python3
"""
Migração SQLite -> PostgreSQL usando psycopg
"""

import sqlite3
import psycopg

# Conectar ao SQLite
sqlite_db = sqlite3.connect('/opt/multimax-data/estoque.db')
sqlite_cursor = sqlite_db.cursor()

print('[*] Conectando ao PostgreSQL...')
pg_conn = psycopg.connect(
    host='localhost',
    port=5432,
    dbname='multimax',
    user='multimax',
    password='multimax123'
)
pg_cursor = pg_conn.cursor()

# 1. Migrar Setores
print('\n[*] Migrando Setores...')
sqlite_cursor.execute('SELECT id, nome FROM setor ORDER BY id')
setores = sqlite_cursor.fetchall()

for setor_id, nome in setores:
    try:
        pg_cursor.execute(
            'INSERT INTO setor (id, nome, ativo) VALUES (%s, %s, true) ON CONFLICT DO NOTHING',
            (setor_id, nome)
        )
        print(f'  [OK] {nome}')
    except Exception as e:
        print(f'  [ERRO] {nome}: {e}')

pg_conn.commit()
print(f'[OK] {len(setores)} setores inseridos')

# 2. Verificar ciclos semanais
print('\n[*] Verificando ciclos semanais...')
sqlite_cursor.execute('''
    SELECT numero_ciclo, data_inicio, data_fim, ativo 
    FROM ciclos_semanais 
    LIMIT 5
''')
ciclos = sqlite_cursor.fetchall()
print(f'  Primeiro ciclo: {ciclos[0] if ciclos else "nenhum"}')

# 3. Verificar colaboradores
print('\n[*] Extraindo colaboradores...')
sqlite_cursor.execute('''
    SELECT DISTINCT TRIM(nome_colaborador) as nome 
    FROM ciclo 
    WHERE nome_colaborador IS NOT NULL AND nome_colaborador != ''
    ORDER BY nome
''')
colaboradores = [row[0] for row in sqlite_cursor.fetchall()]
print(f'  Total: {len(colaboradores)}')

# Inserir colaboradores
print('[*] Migrando Colaboradores...')
for i, nome in enumerate(colaboradores, 1):
    try:
        cpf = f"000.000.000-{str(i).zfill(2)}"
        pg_cursor.execute(
            'INSERT INTO colaboradores (nome, cpf, ativo, funcao, departamento, horas_ciclo, saldo_horas, created_at, updated_at) VALUES (%s, %s, true, %s, %s, %s, %s, NOW(), NOW())',
            (nome, cpf, 'Colaborador', 'Operacional', 40.0, 0.0)
        )
        print(f'  [OK] {nome}')
    except Exception as e:
        print(f'  [ERRO] {nome}: {e}')

pg_conn.commit()
print(f'[OK] {len(colaboradores)} colaboradores inseridos')

# Fechar conexões
sqlite_db.close()
pg_cursor.close()
pg_conn.close()

print('\n[OK] Migracao concluida!')
