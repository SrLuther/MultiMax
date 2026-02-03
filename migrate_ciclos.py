#!/usr/bin/env python3
import sqlite3
import psycopg

sqlite_db = sqlite3.connect('/opt/multimax-data/estoque.db')
sqlite_cursor = sqlite_db.cursor()

pg_conn = psycopg.connect(
    host='localhost', port=5432, dbname='multimax',
    user='multimax', password='multimax123'
)
pg_cursor = pg_conn.cursor()

# Migrar Ciclos Semanais
print('[*] Migrando Ciclos Semanais...')
sqlite_cursor.execute('''
    SELECT id, numero_ciclo, data_inicio, data_fim, ativo
    FROM ciclos_semanais
    ORDER BY id
''')
ciclos_sem = sqlite_cursor.fetchall()
print(f'  Total: {len(ciclos_sem)}')

for ciclo_id, numero, data_inicio, data_fim, ativo in ciclos_sem:
    try:
        pg_cursor.execute(
            '''INSERT INTO ciclos_semanais (numero_ciclo, data_inicio, data_fim, ativo, created_at, updated_at)
               VALUES (%s, %s, %s, %s, NOW(), NOW())''',
            (numero, data_inicio, data_fim, bool(ativo))
        )
    except Exception as e:
        print(f'  [ERRO] Ciclo {numero}: {e}')

pg_conn.commit()
print(f'[OK] {len(ciclos_sem)} ciclos semanais inseridos\n')

# Verificar total
pg_cursor.execute('SELECT COUNT(*) FROM ciclos_semanais')
total = pg_cursor.fetchone()[0]
print(f'Total na tabela: {total}')

sqlite_db.close()
pg_cursor.close()
pg_conn.close()
