#!/usr/bin/env python3
"""
Migração COMPLETA - VERSÃO CORRIGIDA
"""
import sqlite3

import psycopg

print("=" * 70)
print("MIGRAÇÃO COMPLETA - 6 AÇOUGUEIROS (CORRIGIDA)")
print("=" * 70)

sqlite_conn = sqlite3.connect("/opt/multimax-data/estoque.db")
pg_conn = psycopg.connect("host=multimax-postgres port=5432 dbname=multimax user=multimax password=multimax123")

sqlite_cur = sqlite_conn.cursor()
pg_cur = pg_conn.cursor()

nomes = ["Luciano", "Diogo", "Renato", "Edilson", "Natalino", "Welvins"]

# Mapear IDs
print("\n[1/6] Mapeando IDs...")
sqlite_cur.execute("SELECT id, name FROM collaborator WHERE name IN ({})".format(",".join(["?" for _ in nomes])), nomes)
id_map_old = {row[1]: row[0] for row in sqlite_cur.fetchall()}

pg_cur.execute("SELECT id, nome FROM colaboradores WHERE nome IN ({})".format(",".join(["%s" for _ in nomes])), nomes)
id_map_new = {row[1]: row[0] for row in pg_cur.fetchall()}
print(f"  ✓ {len(id_map_new)} colaboradores mapeados")

# 1. REGISTRO_JORNADA
print("\n[2/6] Migrando registros de jornada...")
migrados = 0
for nome in nomes:
    old_id = id_map_old.get(nome)
    new_id = id_map_new.get(nome)
    if not old_id or not new_id:
        continue

    sqlite_cur.execute("SELECT * FROM registro_jornada WHERE collaborator_id = ?", (old_id,))
    cols = [desc[0] for desc in sqlite_cur.description]

    for row in sqlite_cur.fetchall():
        data = dict(zip(cols, row))
        try:
            pg_cur.execute(
                """
                INSERT INTO registro_jornada (
                    id, collaborator_id, tipo_registro, valor, data,
                    observacao, created_at, updated_at
                )
                VALUES (gen_random_uuid()::text, %s, %s, %s, %s, %s, NOW(), NOW())
            """,
                (
                    new_id,
                    data.get("tipo_registro", "entrada"),
                    data.get("valor", 0),
                    data.get("data"),
                    data.get("observacao"),
                ),
            )
            migrados += 1
        except Exception as e:
            pg_conn.rollback()

pg_conn.commit()
print(f"  ✓ {migrados} jornadas migradas")

# 2. SHIFTS
print("\n[3/6] Migrando turnos...")
migrados = 0
for nome in nomes:
    old_id = id_map_old.get(nome)
    new_id = id_map_new.get(nome)
    if not old_id or not new_id:
        continue

    sqlite_cur.execute("SELECT * FROM shift WHERE collaborator_id = ?", (old_id,))
    cols = [desc[0] for desc in sqlite_cur.description]

    for row in sqlite_cur.fetchall():
        data = dict(zip(cols, row))
        try:
            pg_cur.execute(
                """
                INSERT INTO shift (
                    collaborator_id, date, turno, observacao,
                    start_dt, end_dt, shift_type, is_sunday_holiday, auto_generated
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
                (
                    new_id,
                    data.get("date"),
                    data.get("turno"),
                    data.get("observacao"),
                    data.get("start_dt"),
                    data.get("end_dt"),
                    data.get("shift_type"),
                    data.get("is_sunday_holiday", False),
                    data.get("auto_generated", False),
                ),
            )
            migrados += 1
        except Exception as e:
            pg_conn.rollback()

pg_conn.commit()
print(f"  ✓ {migrados} turnos migrados")

# 3. TIME_OFF_RECORD
print("\n[4/6] Migrando folgas...")
migrados = 0
for nome in nomes:
    old_id = id_map_old.get(nome)
    new_id = id_map_new.get(nome)
    if not old_id or not new_id:
        continue

    sqlite_cur.execute("SELECT * FROM time_off_record WHERE collaborator_id = ?", (old_id,))
    cols = [desc[0] for desc in sqlite_cur.description]

    for row in sqlite_cur.fetchall():
        data = dict(zip(cols, row))
        try:
            pg_cur.execute(
                """
                INSERT INTO time_off_record (
                    collaborator_id, date, record_type, hours, days,
                    amount_paid, rate_per_day, origin, notes, created_at, created_by
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)
            """,
                (
                    new_id,
                    data.get("date"),
                    data.get("record_type", "folga"),
                    data.get("hours", 0),
                    data.get("days", 0),
                    data.get("amount_paid", 0),
                    data.get("rate_per_day", 0),
                    data.get("origin", "migração"),
                    data.get("notes"),
                    data.get("created_by", "sistema"),
                ),
            )
            migrados += 1
        except Exception as e:
            pg_conn.rollback()

pg_conn.commit()
print(f"  ✓ {migrados} folgas migradas")

# 4. VACATION
print("\n[5/6] Migrando férias...")
migrados = 0
for nome in nomes:
    old_id = id_map_old.get(nome)
    new_id = id_map_new.get(nome)
    if not old_id or not new_id:
        continue

    sqlite_cur.execute("SELECT * FROM vacation WHERE collaborator_id = ?", (old_id,))
    cols = [desc[0] for desc in sqlite_cur.description]

    for row in sqlite_cur.fetchall():
        data = dict(zip(cols, row))
        try:
            pg_cur.execute(
                """
                INSERT INTO vacation (
                    collaborator_id, start_date, end_date, created_at
                )
                VALUES (%s, %s, %s, NOW())
            """,
                (new_id, data.get("start_date"), data.get("end_date")),
            )
            migrados += 1
        except Exception as e:
            pg_conn.rollback()

pg_conn.commit()
print(f"  ✓ {migrados} férias migradas")

# 5. MEDICAL_CERTIFICATE
print("\n[6/6] Migrando atestados médicos...")
migrados = 0
for nome in nomes:
    old_id = id_map_old.get(nome)
    new_id = id_map_new.get(nome)
    if not old_id or not new_id:
        continue

    sqlite_cur.execute("SELECT * FROM medical_certificate WHERE collaborator_id = ?", (old_id,))
    cols = [desc[0] for desc in sqlite_cur.description]

    for row in sqlite_cur.fetchall():
        data = dict(zip(cols, row))
        try:
            pg_cur.execute(
                """
                INSERT INTO medical_certificate (
                    collaborator_id, start_date, end_date, days, created_at
                )
                VALUES (%s, %s, %s, %s, NOW())
            """,
                (new_id, data.get("start_date"), data.get("end_date"), data.get("days", 1)),
            )
            migrados += 1
        except Exception as e:
            pg_conn.rollback()

pg_conn.commit()
print(f"  ✓ {migrados} atestados migrados")

# RESUMO
print("\n" + "=" * 70)
print("RESUMO FINAL")
print("=" * 70)

for nome in nomes:
    new_id = id_map_new.get(nome)
    if not new_id:
        continue

    print(f"\n📊 {nome}:")

    pg_cur.execute("SELECT COUNT(*) FROM registro_jornada WHERE collaborator_id = %s", (new_id,))
    print(f"   - Jornadas: {pg_cur.fetchone()[0]}")

    pg_cur.execute("SELECT COUNT(*) FROM shift WHERE collaborator_id = %s", (new_id,))
    print(f"   - Turnos: {pg_cur.fetchone()[0]}")

    pg_cur.execute("SELECT COUNT(*) FROM time_off_record WHERE collaborator_id = %s", (new_id,))
    print(f"   - Folgas: {pg_cur.fetchone()[0]}")

    pg_cur.execute("SELECT COUNT(*) FROM vacation WHERE collaborator_id = %s", (new_id,))
    print(f"   - Férias: {pg_cur.fetchone()[0]}")

    pg_cur.execute("SELECT COUNT(*) FROM medical_certificate WHERE collaborator_id = %s", (new_id,))
    print(f"   - Atestados: {pg_cur.fetchone()[0]}")

print("\n✅ MIGRAÇÃO COMPLETA!")

sqlite_conn.close()
pg_conn.close()
