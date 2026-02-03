#!/usr/bin/env python3
import sqlite3
from datetime import datetime, timedelta

db = sqlite3.connect("multimax.db")
cursor = db.cursor()

print("[*] Criando ciclos mensais...")

# Apenas criar ciclos para meses únicos
meses_criados = set()
ciclos_inseridos = 0

for month_offset in range(-2, 12):
    data = datetime.now() + timedelta(days=30 * month_offset)
    mes = data.month
    ano = data.year

    # Skip se já criamos esse mês/ano
    if (mes, ano) in meses_criados:
        print(f"  [!] Pulando {mes}/{ano} (duplicado)")
        continue

    meses_criados.add((mes, ano))

    data_inicio = data.replace(day=1)
    proximo = data_inicio + timedelta(days=32)
    data_fim = proximo.replace(day=1) - timedelta(days=1)

    fechado = 1 if month_offset < -1 else 0

    try:
        cursor.execute(
            """INSERT INTO ciclos_mensais
               (mes, ano, data_inicio, data_fim, fechado, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (mes, ano, str(data_inicio), str(data_fim), fechado, str(datetime.now()), str(datetime.now())),
        )
        ciclos_inseridos += 1
        print(f"  [+] {mes}/{ano}")
    except Exception as e:
        print(f"  [ERRO] {mes}/{ano}: {e}")

db.commit()

cursor.execute("SELECT COUNT(*) FROM ciclos_mensais")
total = cursor.fetchone()[0]
print(f"[OK] Total de ciclos mensais: {total}")

db.close()
