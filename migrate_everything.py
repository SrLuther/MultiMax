#!/usr/bin/env python3
"""
Migração COMPLETA de todos os dados dos 6 açougueiros
"""
import sqlite3
from datetime import datetime

import psycopg

print("=" * 70)
print("MIGRAÇÃO COMPLETA - 6 AÇOUGUEIROS")
print("=" * 70)

# Conectar
sqlite_conn = sqlite3.connect("/opt/multimax-data/estoque.db")
pg_conn = psycopg.connect("host=multimax-postgres port=5432 dbname=multimax user=multimax password=multimax123")

sqlite_cur = sqlite_conn.cursor()
pg_cur = pg_conn.cursor()

# Nomes dos açougueiros
nomes = ["Luciano", "Diogo", "Renato", "Edilson", "Natalino", "Welvins"]

# 1. Mapear IDs na tabela collaborator
print("\n[1/8] Mapeando IDs dos colaboradores...")
sqlite_cur.execute("SELECT id, name FROM collaborator WHERE name IN ({})".format(",".join(["?" for _ in nomes])), nomes)
id_map_old = {row[1]: row[0] for row in sqlite_cur.fetchall()}
print(f"  ✓ IDs antigos: {id_map_old}")

# IDs novos no PostgreSQL
pg_cur.execute("SELECT id, nome FROM colaboradores WHERE nome IN ({})".format(",".join(["%s" for _ in nomes])), nomes)
id_map_new = {row[1]: row[0] for row in pg_cur.fetchall()}
print(f"  ✓ IDs novos: {id_map_new}")

# 2. Migrar REGISTRO_JORNADA
print("\n[2/8] Migrando registros de jornada...")
sqlite_cur.execute(
    """
    SELECT rj.* FROM registro_jornada rj
    JOIN collaborator c ON rj.collaborator_id = c.id
    WHERE c.name IN ({})
""".format(
        ",".join(["?" for _ in nomes])
    ),
    nomes,
)

cols = [desc[0] for desc in sqlite_cur.description]
migrados = 0
for row in sqlite_cur.fetchall():
    data = dict(zip(cols, row))
    collab_name = None
    for nome, old_id in id_map_old.items():
        if data["collaborator_id"] == old_id:
            collab_name = nome
            break

    if collab_name and collab_name in id_map_new:
        try:
            pg_cur.execute(
                """
                INSERT INTO registro_jornada (
                    colaborador_id, data, hora_entrada, hora_saida,
                    horas_trabalhadas, observacoes, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT DO NOTHING
            """,
                (
                    id_map_new[collab_name],
                    data.get("date"),
                    data.get("clock_in"),
                    data.get("clock_out"),
                    data.get("total_hours", 0),
                    data.get("notes"),
                ),
            )
            migrados += 1
        except Exception as e:
            print(f"    Erro: {e}")

pg_conn.commit()
print(f"  ✓ {migrados} registros de jornada migrados")

# 3. Migrar SHIFTS (turnos)
print("\n[3/8] Migrando turnos...")
sqlite_cur.execute(
    """
    SELECT s.* FROM shift s
    JOIN collaborator c ON s.collaborator_id = c.id
    WHERE c.name IN ({})
""".format(
        ",".join(["?" for _ in nomes])
    ),
    nomes,
)

migrados = 0
cols = [desc[0] for desc in sqlite_cur.description]
for row in sqlite_cur.fetchall():
    data = dict(zip(cols, row))
    collab_name = None
    for nome, old_id in id_map_old.items():
        if data["collaborator_id"] == old_id:
            collab_name = nome
            break

    if collab_name and collab_name in id_map_new:
        try:
            pg_cur.execute(
                """
                INSERT INTO shift (
                    collaborator_id, date, shift_type, status,
                    notes, created_at
                )
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT DO NOTHING
            """,
                (
                    id_map_new[collab_name],
                    data.get("date"),
                    data.get("shift_type"),
                    data.get("status"),
                    data.get("notes"),
                ),
            )
            migrados += 1
        except Exception as e:
            pass

pg_conn.commit()
print(f"  ✓ {migrados} turnos migrados")

# 4. Migrar TIME_OFF_RECORD (folgas)
print("\n[4/8] Migrando folgas...")
sqlite_cur.execute(
    """
    SELECT t.* FROM time_off_record t
    JOIN collaborator c ON t.collaborator_id = c.id
    WHERE c.name IN ({})
""".format(
        ",".join(["?" for _ in nomes])
    ),
    nomes,
)

migrados = 0
cols = [desc[0] for desc in sqlite_cur.description]
for row in sqlite_cur.fetchall():
    data = dict(zip(cols, row))
    collab_name = None
    for nome, old_id in id_map_old.items():
        if data["collaborator_id"] == old_id:
            collab_name = nome
            break

    if collab_name and collab_name in id_map_new:
        try:
            pg_cur.execute(
                """
                INSERT INTO time_off_record (
                    collaborator_id, date, type, status,
                    notes, created_at
                )
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT DO NOTHING
            """,
                (
                    id_map_new[collab_name],
                    data.get("date"),
                    data.get("type"),
                    data.get("status", "approved"),
                    data.get("notes"),
                ),
            )
            migrados += 1
        except Exception as e:
            pass

pg_conn.commit()
print(f"  ✓ {migrados} folgas migradas")

# 5. Migrar VACATION (férias)
print("\n[5/8] Migrando férias...")
sqlite_cur.execute(
    """
    SELECT v.* FROM vacation v
    JOIN collaborator c ON v.collaborator_id = c.id
    WHERE c.name IN ({})
""".format(
        ",".join(["?" for _ in nomes])
    ),
    nomes,
)

migrados = 0
cols = [desc[0] for desc in sqlite_cur.description]
for row in sqlite_cur.fetchall():
    data = dict(zip(cols, row))
    collab_name = None
    for nome, old_id in id_map_old.items():
        if data["collaborator_id"] == old_id:
            collab_name = nome
            break

    if collab_name and collab_name in id_map_new:
        try:
            pg_cur.execute(
                """
                INSERT INTO vacation (
                    collaborator_id, start_date, end_date,
                    status, created_at
                )
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT DO NOTHING
            """,
                (id_map_new[collab_name], data.get("start_date"), data.get("end_date"), data.get("status", "approved")),
            )
            migrados += 1
        except Exception as e:
            pass

pg_conn.commit()
print(f"  ✓ {migrados} férias migradas")

# 6. Migrar MEDICAL_CERTIFICATE (atestados)
print("\n[6/8] Migrando atestados médicos...")
sqlite_cur.execute(
    """
    SELECT m.* FROM medical_certificate m
    JOIN collaborator c ON m.collaborator_id = c.id
    WHERE c.name IN ({})
""".format(
        ",".join(["?" for _ in nomes])
    ),
    nomes,
)

migrados = 0
cols = [desc[0] for desc in sqlite_cur.description]
for row in sqlite_cur.fetchall():
    data = dict(zip(cols, row))
    collab_name = None
    for nome, old_id in id_map_old.items():
        if data["collaborator_id"] == old_id:
            collab_name = nome
            break

    if collab_name and collab_name in id_map_new:
        try:
            pg_cur.execute(
                """
                INSERT INTO medical_certificate (
                    collaborator_id, start_date, end_date,
                    days, created_at
                )
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT DO NOTHING
            """,
                (id_map_new[collab_name], data.get("start_date"), data.get("end_date"), data.get("days")),
            )
            migrados += 1
        except Exception as e:
            pass

pg_conn.commit()
print(f"  ✓ {migrados} atestados migrados")

# 7. Migrar JORNADA_ARCHIVE
print("\n[7/8] Migrando jornadas arquivadas...")
sqlite_cur.execute(
    """
    SELECT j.* FROM jornada_archive j
    JOIN collaborator c ON j.collaborator_id = c.id
    WHERE c.name IN ({})
""".format(
        ",".join(["?" for _ in nomes])
    ),
    nomes,
)

migrados = 0
cols = [desc[0] for desc in sqlite_cur.description]
for row in sqlite_cur.fetchall():
    data = dict(zip(cols, row))
    collab_name = None
    for nome, old_id in id_map_old.items():
        if data["collaborator_id"] == old_id:
            collab_name = nome
            break

    if collab_name and collab_name in id_map_new:
        try:
            pg_cur.execute(
                """
                INSERT INTO jornada_archive (
                    collaborator_id, date, clock_in, clock_out,
                    total_hours, archived_at
                )
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT DO NOTHING
            """,
                (
                    id_map_new[collab_name],
                    data.get("date"),
                    data.get("clock_in"),
                    data.get("clock_out"),
                    data.get("total_hours"),
                ),
            )
            migrados += 1
        except Exception as e:
            pass

pg_conn.commit()
print(f"  ✓ {migrados} jornadas arquivadas migradas")

# 8. Migrar USER (contas de usuário)
print("\n[8/8] Migrando contas de usuário...")
sqlite_cur.execute(
    """
    SELECT u.* FROM user u
    JOIN collaborator c ON u.collaborator_id = c.id
    WHERE c.name IN ({})
""".format(
        ",".join(["?" for _ in nomes])
    ),
    nomes,
)

migrados = 0
cols = [desc[0] for desc in sqlite_cur.description]
for row in sqlite_cur.fetchall():
    data = dict(zip(cols, row))
    collab_name = None
    for nome, old_id in id_map_old.items():
        if data.get("collaborator_id") == old_id:
            collab_name = nome
            break

    if collab_name and collab_name in id_map_new:
        try:
            pg_cur.execute(
                """
                INSERT INTO "user" (
                    username, password_hash, email, role,
                    active, collaborator_id, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (username) DO NOTHING
            """,
                (
                    data.get("username"),
                    data.get("password_hash"),
                    data.get("email"),
                    data.get("role", "user"),
                    data.get("active", True),
                    id_map_new[collab_name],
                ),
            )
            migrados += 1
        except Exception as e:
            pass

pg_conn.commit()
print(f"  ✓ {migrados} usuários migrados")

# Resumo final
print("\n" + "=" * 70)
print("RESUMO DA MIGRAÇÃO")
print("=" * 70)

for nome in nomes:
    print(f"\n📊 {nome}:")

    # Contar no PostgreSQL
    new_id = id_map_new.get(nome)
    if new_id:
        pg_cur.execute("SELECT COUNT(*) FROM registro_jornada WHERE colaborador_id = %s", (new_id,))
        jornadas = pg_cur.fetchone()[0]

        pg_cur.execute("SELECT COUNT(*) FROM shift WHERE collaborator_id = %s", (new_id,))
        turnos = pg_cur.fetchone()[0]

        pg_cur.execute("SELECT COUNT(*) FROM time_off_record WHERE collaborator_id = %s", (new_id,))
        folgas = pg_cur.fetchone()[0]

        print(f"   - Jornadas: {jornadas}")
        print(f"   - Turnos: {turnos}")
        print(f"   - Folgas: {folgas}")

print("\n✅ MIGRAÇÃO COMPLETA!")

sqlite_conn.close()
pg_conn.close()
