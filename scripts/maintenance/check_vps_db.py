#!/usr/bin/env python3
import os
import sqlite3

print("[*] Verificando banco de dados na VPS...\n")

# Procurar pelos bancos de dados
paths_to_check = [
    "/opt/multimax/multimax.db",
    "/opt/multimax-data/estoque.db",
    "/opt/multimax-data/multimax.db",
    "/home/multimax/multimax.db",
]

found = False
for path in paths_to_check:
    if os.path.exists(path):
        print(f"[OK] Banco encontrado em: {path}\n")

        try:
            db = sqlite3.connect(path)
            cursor = db.cursor()

            # Verificar dados
            cursor.execute("SELECT COUNT(*) FROM setor")
            setor_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM ciclos_semanais")
            ciclo_sem_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM ciclos_mensais")
            ciclo_mes_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM colaboradores")
            colab_count = cursor.fetchone()[0]

            print("[DADOS NA VPS]")
            print("=" * 50)
            print(f"  Setores: {setor_count}")
            print(f"  Ciclos Semanais: {ciclo_sem_count}")
            print(f"  Ciclos Mensais: {ciclo_mes_count}")
            print(f"  Colaboradores: {colab_count}")
            print("=" * 50)

            db.close()
            found = True
            break
        except Exception as e:
            print(f"[ERRO] ao ler banco: {e}\n")

if not found:
    print("[ERRO] Nenhum banco SQLite encontrado em:\n")
    for path in paths_to_check:
        print(f"  - {path}")
