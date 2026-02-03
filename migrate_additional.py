#!/usr/bin/env python3
import sqlite3

import psycopg

sqlite_db = sqlite3.connect("/opt/multimax-data/estoque.db")
sqlite_cursor = sqlite_db.cursor()

pg_conn = psycopg.connect(host="localhost", port=5432, dbname="multimax", user="multimax", password="multimax123")
pg_cursor = pg_conn.cursor()

# 1. Migrar Ciclos Mensais
print("\n[*] Migrando Ciclos Mensais...")
sqlite_cursor.execute(
    """
    SELECT id, mes, ano, data_inicio, data_fim, fechado
    FROM ciclos_mensais
    ORDER BY id
"""
)
ciclos_mes = sqlite_cursor.fetchall()
print(f"  Total: {len(ciclos_mes)}")

for ciclo_id, mes, ano, data_inicio, data_fim, fechado in ciclos_mes:
    try:
        pg_cursor.execute(
            """INSERT INTO ciclos_mensais (mes, ano, data_inicio, data_fim, fechado, created_at, updated_at)
               VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
               ON CONFLICT DO NOTHING""",
            (mes, ano, data_inicio, data_fim, bool(fechado)),
        )
    except Exception as e:
        print(f"  [ERRO] Ciclo {mes}/{ano}: {e}")

pg_conn.commit()
pg_cursor.execute("SELECT COUNT(*) FROM ciclos_mensais")
result = pg_cursor.fetchone()
total_mes = result[0] if result else 0
print(f"[OK] Ciclos Mensais no PostgreSQL: {total_mes}\n")

# 2. Verificar dados de time_off_record
print("[*] Verificando Folgas e Férias...")
sqlite_cursor.execute("SELECT COUNT(*) FROM time_off_record")
folgas_count = sqlite_cursor.fetchone()[0]
print(f"  Registros de Folgas: {folgas_count}")

pg_cursor.execute("SELECT COUNT(*) FROM time_off_record")
result = pg_cursor.fetchone()
folgas_pg = result[0] if result else 0
print(f"  No PostgreSQL: {folgas_pg}\n")

# 3. Migrar Holidays/Feriados
print("[*] Migrando Feriados...")
sqlite_cursor.execute(
    """
    SELECT id, date, name, kind
    FROM holiday
    ORDER BY date
"""
)
holidays = sqlite_cursor.fetchall()
print(f"  Total: {len(holidays)}")

for h_id, h_date, h_name, h_kind in holidays:
    try:
        pg_cursor.execute(
            """INSERT INTO holiday (date, name, kind, created_at, updated_at)
               VALUES (%s, %s, %s, NOW(), NOW())
               ON CONFLICT DO NOTHING""",
            (h_date, h_name or "", h_kind or ""),
        )
    except Exception as e:
        print(f"  [ERRO] Feriado {h_date}: {e}")

pg_conn.commit()
pg_cursor.execute("SELECT COUNT(*) FROM holiday")
result = pg_cursor.fetchone()
total_hol = result[0] if result else 0
print(f"[OK] Feriados no PostgreSQL: {total_hol}\n")

print("[OK] Migração adicional concluída!")

sqlite_db.close()
pg_cursor.close()
pg_conn.close()
