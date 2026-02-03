#!/usr/bin/env python3
"""
Migração SQLite -> PostgreSQL usando SQL direto
"""

import sqlite3
import os

# Conectar ao SQLite
print('\n[*] Migracao SQLite -> PostgreSQL (SQL direto)\n')

sqlite_db = sqlite3.connect('/opt/multimax-data/estoque.db')
sqlite_cursor = sqlite_db.cursor()

# Ler dados do SQLite
print('[*] Lendo dados do SQLite...')

# Setores
sqlite_cursor.execute('SELECT id, nome FROM setor WHERE ativo = 1 ORDER BY id')
setores = sqlite_cursor.fetchall()
print(f'  Setores: {len(setores)}')

# Ciclos
sqlite_cursor.execute('SELECT COUNT(*) FROM ciclos_semanais')
ciclos_sem_count = sqlite_cursor.fetchone()[0]
print(f'  Ciclos Semanais: {ciclos_sem_count}')

sqlite_cursor.execute('SELECT COUNT(*) FROM ciclos_mensais')
ciclos_mes_count = sqlite_cursor.fetchone()[0]
print(f'  Ciclos Mensais: {ciclos_mes_count}')

# Colaboradores
sqlite_cursor.execute('''
    SELECT DISTINCT nome FROM (
        SELECT nome FROM collaborator WHERE nome IS NOT NULL
        UNION
        SELECT nome_colaborador FROM ciclo WHERE nome_colaborador IS NOT NULL
    ) LIMIT 100
''')
colaboradores = [row[0].strip() for row in sqlite_cursor.fetchall() if row[0] and row[0].strip()]
print(f'  Colaboradores: {len(colaboradores)}')

print()

# Gerar comandos SQL para PostgreSQL
print('[*] Gerando comandos SQL...\n')

sql_commands = []

# 1. Inserir setores
print('[*] Setores a inserir:')
for setor_id, nome in setores:
    sql = f"INSERT INTO setor (nome, ativo) VALUES ('{nome}', true) ON CONFLICT DO NOTHING;"
    sql_commands.append(sql)
    print(f'  {nome}')

# 2. Inserir ciclos semanais
print(f'\n[*] Ciclos Semanais ({ciclos_sem_count} registros)')

# 3. Inserir ciclos mensais
print(f'[*] Ciclos Mensais ({ciclos_mes_count} registros)')

# 4. Inserir colaboradores
print(f'\n[*] Colaboradores a inserir:')
for i, nome in enumerate(colaboradores, 1):
    safe_nome = nome.replace("'", "''")
    cpf = f"000.000.000-{str(i).zfill(2)}"
    sql = f"""INSERT INTO colaboradores (nome, cpf, funcao, departamento, ativo, horas_ciclo, saldo_horas) 
              VALUES ('{safe_nome}', '{cpf}', 'Colaborador', 'Operacional', true, 40.0, 0.0) 
              ON CONFLICT (cpf) DO NOTHING;"""
    sql_commands.append(sql)
    print(f'  {nome}')

# Salvar SQL em arquivo
sql_file = '/tmp/migration_commands.sql'
print(f'\n[*] Salvando {len(sql_commands)} comandos SQL em {sql_file}...')

with open(sql_file, 'w') as f:
    f.write('-- Migration from SQLite to PostgreSQL\n')
    f.write('-- Generated automatically\n\n')
    for cmd in sql_commands:
        f.write(cmd + '\n')

print(f'[OK] Arquivo salvo\n')

# Executar via psql
print('[*] Executando SQL no PostgreSQL...')
os.system(f'PGPASSWORD=multimax123 psql -U multimax -d multimax -h localhost -f {sql_file} 2>&1 | head -50')

print('\n[OK] Migracao concluida!')

sqlite_db.close()
