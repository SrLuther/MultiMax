#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect("/opt/multimax-data/estoque.db")
cursor = conn.cursor()

nomes = ["Luciano", "Diogo", "Renato", "Edilson", "Natalino", "Welvins"]

print("=" * 70)
print("CONTAGEM DE DADOS POR COLABORADOR NO SQLITE")
print("=" * 70)

# IDs
cursor.execute("SELECT id, name FROM collaborator WHERE name IN ({})".format(",".join(["?" for _ in nomes])), nomes)
id_map = {row[1]: row[0] for row in cursor.fetchall()}

for nome in nomes:
    old_id = id_map.get(nome)
    if not old_id:
        print(f"\n❌ {nome}: NÃO ENCONTRADO")
        continue

    print(f"\n📊 {nome} (ID={old_id}):")

    # Registro_jornada
    cursor.execute("SELECT COUNT(*) FROM registro_jornada WHERE collaborator_id = ?", (old_id,))
    count = cursor.fetchone()[0]
    print(f"   - Jornadas: {count}")

    # Shifts
    cursor.execute("SELECT COUNT(*) FROM shift WHERE collaborator_id = ?", (old_id,))
    count = cursor.fetchone()[0]
    print(f"   - Turnos: {count}")

    # Time off
    cursor.execute("SELECT COUNT(*) FROM time_off_record WHERE collaborator_id = ?", (old_id,))
    count = cursor.fetchone()[0]
    print(f"   - Folgas: {count}")

    # Vacation
    cursor.execute("SELECT COUNT(*) FROM vacation WHERE collaborator_id = ?", (old_id,))
    count = cursor.fetchone()[0]
    print(f"   - Férias: {count}")

    # Medical
    cursor.execute("SELECT COUNT(*) FROM medical_certificate WHERE collaborator_id = ?", (old_id,))
    count = cursor.fetchone()[0]
    print(f"   - Atestados: {count}")

    # Jornada archive
    cursor.execute("SELECT COUNT(*) FROM jornada_archive WHERE collaborator_id = ?", (old_id,))
    count = cursor.fetchone()[0]
    print(f"   - Jornadas arquivadas: {count}")

    # User
    try:
        cursor.execute("SELECT COUNT(*) FROM user WHERE collaborator_id = ?", (old_id,))
        count = cursor.fetchone()[0]
        print(f"   - Usuário: {count}")
    except Exception:  # noqa: E722
        pass

conn.close()
