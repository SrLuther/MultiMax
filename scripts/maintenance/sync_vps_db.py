#!/usr/bin/env python3
"""
Script para sincronizar banco da VPS com dados de Setores e Ciclos
"""
import sqlite3
from datetime import datetime, timedelta

db_path = "/opt/multimax-data/estoque.db"

print("[*] Sincronizando banco da VPS...\n")

db = sqlite3.connect(db_path)
cursor = db.cursor()

# 1. Verificar setores existentes
print("[*] Verificando setores existentes...")
cursor.execute("SELECT id, nome FROM setor ORDER BY id")
existing_setores = {nome: id for id, nome in cursor.fetchall()}
print(f"    Encontrados: {list(existing_setores.keys())}")

# Se não tem os setores esperados, criar
expected_setores = [
    "Producao",  # Pode já existir
    "Expedicao",  # Pode já existir
    "Qualidade",  # Pode já existir
    "Manutencao",
    "Administrativo",
    "Financeiro",
    "RH",
]

print("\n[*] Adicionando setores faltantes...")
for nome in expected_setores:
    nome_search = nome.lower()
    exists = any(s.lower() == nome_search for s in existing_setores.keys())

    if not exists:
        cursor.execute("INSERT INTO setor (nome, ativo) VALUES (?, ?)", (nome, 1))
        print(f"    [+] {nome}")

db.commit()

# Recarregar setores
cursor.execute("SELECT id, nome FROM setor ORDER BY id")
setores = {nome: id for id, nome in cursor.fetchall()}
print(f"\n[OK] Total de setores agora: {len(setores)}")

# 2. Limpar ciclos existentes (se houver)
print("\n[*] Limpando ciclos semanais e mensais...")
cursor.execute("DELETE FROM ciclos_semanais")
cursor.execute("DELETE FROM ciclos_mensais")
db.commit()

# 3. Criar ciclos semanais
print("[*] Criando ciclos semanais...")
today = datetime.now().date()
ciclos_criados = 0

for week in range(26):
    data_inicio = today - timedelta(days=today.weekday()) + timedelta(weeks=week)
    data_fim = data_inicio + timedelta(days=6)
    numero_ciclo = 1 + week
    ativo = 1 if week < 4 else 0

    cursor.execute(
        """INSERT INTO ciclos_semanais
           (numero_ciclo, data_inicio, data_fim, ativo, observacoes, created_at, updated_at)
           VALUES (?, ?, ?, ?, NULL, ?, ?)""",
        (numero_ciclo, str(data_inicio), str(data_fim), ativo, str(datetime.now()), str(datetime.now())),
    )
    ciclos_criados += 1

db.commit()
print(f"[OK] {ciclos_criados} ciclos semanais criados")

# 4. Criar ciclos mensais
print("[*] Criando ciclos mensais...")
meses_criados = set()

for month_offset in range(-2, 12):
    data = datetime.now() + timedelta(days=30 * month_offset)
    mes = data.month
    ano = data.year

    if (mes, ano) in meses_criados:
        continue

    meses_criados.add((mes, ano))

    data_inicio = data.replace(day=1)
    proximo = data_inicio + timedelta(days=32)
    data_fim = proximo.replace(day=1) - timedelta(days=1)

    fechado = 1 if month_offset < -1 else 0

    cursor.execute(
        """INSERT INTO ciclos_mensais
           (mes, ano, data_inicio, data_fim, fechado, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (mes, ano, str(data_inicio), str(data_fim), fechado, str(datetime.now()), str(datetime.now())),
    )

db.commit()
print(f"[OK] {len(meses_criados)} ciclos mensais criados")

# 5. Verificar/criar colaboradores
print("[*] Verificando colaboradores...")
cursor.execute("SELECT COUNT(*) FROM colaboradores")
colab_count = cursor.fetchone()[0]

if colab_count == 0:
    print("    Adicionando colaboradores de exemplo...")
    colaboradores = [
        ("Joao Silva", "11122233344", "Operario", "Operacional", 1, 40.0, 0.0),
        ("Maria Santos", "22233344455", "Supervisora", "Operacional", 1, 40.0, 0.0),
        ("Pedro Costa", "33344455566", "Encarregado", "Operacional", 1, 40.0, 0.0),
        ("Ana Oliveira", "44455566677", "Analista QA", "Operacional", 1, 40.0, 0.0),
        ("Carlos Martins", "55566677788", "Tecnico", "Operacional", 1, 40.0, 0.0),
    ]

    for nome, cpf, funcao, dept, ativo, horas_ciclo, saldo in colaboradores:
        cursor.execute(
            """INSERT INTO colaboradores
               (nome, cpf, funcao, departamento, ativo, horas_ciclo, saldo_horas, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (nome, cpf, funcao, dept, ativo, horas_ciclo, saldo, str(datetime.now()), str(datetime.now())),
        )
        print(f"    [+] {nome}")

    db.commit()
else:
    print(f"    Ja existem {colab_count} colaboradores")

# Resumo final
print("\n[VERIFICACAO FINAL]")
print("=" * 50)

cursor.execute("SELECT COUNT(*) FROM setor")
print(f"  Setores: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(*) FROM ciclos_semanais")
print(f"  Ciclos Semanais: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(*) FROM ciclos_mensais")
print(f"  Ciclos Mensais: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(*) FROM colaboradores")
print(f"  Colaboradores: {cursor.fetchone()[0]}")

print("=" * 50)

db.close()

print("\n[OK] Sincronizacao concluida!")
