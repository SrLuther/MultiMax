#!/usr/bin/env python3
"""
Script para popular banco SQLite com Setores e Ciclos
Versão simples e direta - sem verificações complexas
"""

import os
import sqlite3
from datetime import datetime, timedelta

db_path = os.path.join(os.path.dirname(__file__), "multimax.db")

if not os.path.exists(db_path):
    print(f"❌ Arquivo {db_path} não encontrado")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("\n[*] Iniciando populacao do banco com Setores e Ciclos...\n")

# 1. Limpar dados existentes (se houver)
print("[*] Limpando dados existentes...")
try:
    cursor.execute("DELETE FROM setor")
    cursor.execute("DELETE FROM ciclos_semanais")
    cursor.execute("DELETE FROM ciclos_mensais")
    cursor.execute("DELETE FROM colaboradores")
    conn.commit()
    print("[OK] Dados anteriores removidos\n")
except Exception as e:
    print(f"[!] Nao havia dados para remover: {e}\n")

# 2. Inserir Setores
print("[*] Criando Setores...")
setores = [
    ("Produção", "Setor de produção e fabricação", 1),
    ("Expedição", "Setor de expedição e logística", 1),
    ("Qualidade", "Setor de controle de qualidade", 1),
    ("Manutenção", "Setor de manutenção e reparo", 1),
    ("Administrativo", "Setor administrativo", 1),
    ("Financeiro", "Setor financeiro e contabilidade", 1),
    ("RH", "Setor de recursos humanos", 1),
]

try:
    for nome, descricao, ativo in setores:
        cursor.execute("INSERT INTO setor (nome, descricao, ativo) VALUES (?, ?, ?)", (nome, descricao, ativo))
        print(f"  [+] {nome}")
    conn.commit()
    print(f"[OK] {len(setores)} setores criados\n")
except Exception as e:
    print(f"[ERRO] Erro ao criar setores: {e}\n")
    exit(1)

# 3. Inserir Ciclos Semanais
print("[*] Criando Ciclos Semanais...")
today = datetime.now().date()
ciclos_inseridos = 0

try:
    for week in range(26):  # 26 semanas (6 meses)
        data_inicio = today - timedelta(days=today.weekday()) + timedelta(weeks=week)
        data_fim = data_inicio + timedelta(days=6)
        numero_ciclo = 1 + week
        ativo = 1 if week < 4 else 0

        cursor.execute(
            """INSERT INTO ciclos_semanais
               (numero_ciclo, data_inicio, data_fim, ativo, observacoes, created_at, updated_at)
               VALUES (?, ?, ?, ?, NULL, ?, ?)""",
            (numero_ciclo, data_inicio, data_fim, ativo, datetime.now(), datetime.now()),
        )
        ciclos_inseridos += 1

        if week < 5:
            print(f"  [+] Ciclo {numero_ciclo}: {data_inicio} a {data_fim}")

    if ciclos_inseridos > 5:
        print(f"  ... e mais {ciclos_inseridos - 5} ciclos")

    conn.commit()
    print(f"[OK] {ciclos_inseridos} ciclos semanais criados\n")
except Exception as e:
    print(f"[ERRO] Erro ao criar ciclos semanais: {e}\n")
    exit(1)

# 4. Inserir Ciclos Mensais
print("[*] Criando Ciclos Mensais...")
ciclos_mensais_inseridos = 0

try:
    # Verificar ciclos mensais existentes
    cursor.execute("SELECT DISTINCT mes, ano FROM ciclos_mensais")
    existing = set((row[0], row[1]) for row in cursor.fetchall())

    for month_offset in range(-2, 12):  # 2 meses anteriores + 12 meses futuros
        data = datetime.now() + timedelta(days=30 * month_offset)
        mes = data.month
        ano = data.year

        # Skip se já existe
        if (mes, ano) in existing:
            continue

        data_inicio = data.replace(day=1)
        # Último dia do mês
        proximo_mes = data_inicio + timedelta(days=32)
        data_fim = proximo_mes.replace(day=1) - timedelta(days=1)

        fechado = 1 if month_offset < -1 else 0

        cursor.execute(
            """INSERT INTO ciclos_mensais
               (mes, ano, data_inicio, data_fim, fechado, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (mes, ano, data_inicio, data_fim, fechado, datetime.now(), datetime.now()),
        )
        ciclos_mensais_inseridos += 1

    conn.commit()
    print(f"[OK] {ciclos_mensais_inseridos} ciclos mensais criados\n")
except Exception as e:
    print(f"[ERRO] Erro ao criar ciclos mensais: {e}\n")
    exit(1)

# 5. Inserir Colaboradores de exemplo
print("[*] Criando Colaboradores de exemplo...")
colaboradores = [
    ("Joao Silva", "11122233344", "Operario", 1),
    ("Maria Santos", "22233344455", "Supervisora", 1),
    ("Pedro Costa", "33344455566", "Encarregado", 2),
    ("Ana Oliveira", "44455566677", "Analista QA", 3),
    ("Carlos Martins", "55566677788", "Tecnico", 4),
]

try:
    for nome, cpf, funcao, setor_id in colaboradores:
        cursor.execute(
            """INSERT INTO colaboradores
               (nome, cpf, funcao, departamento, ativo, horas_ciclo, saldo_horas, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (nome, cpf, funcao, "Operacional", 1, 40.0, 0.0, datetime.now(), datetime.now()),
        )
        print(f"  [+] {nome}")

    conn.commit()
    print(f"[OK] {len(colaboradores)} colaboradores criados\n")
except Exception as e:
    print(f"[ERRO] Erro ao criar colaboradores: {e}\n")
    exit(1)

# 6. Resumo final
print("=" * 60)
print("[RESULTADO] POPULACAO DO BANCO CONCLUIDA")
print("=" * 60)

cursor.execute("SELECT COUNT(*) FROM setor")
setor_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM ciclos_semanais")
ciclo_semanal_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM ciclos_mensais")
ciclo_mensal_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM colaboradores")
colab_count = cursor.fetchone()[0]

print(f"[+] Setores: {setor_count}")
print(f"[+] Ciclos Semanais: {ciclo_semanal_count}")
print(f"[+] Ciclos Mensais: {ciclo_mensal_count}")
print(f"[+] Colaboradores: {colab_count}")
print("=" * 60)

conn.close()

print("\n[OK] Banco de dados sincronizado com sucesso!\n")
print("[*] Para testar:")
print("    1. Abra a aplicacao")
print("    2. Acesse a pagina de Ciclos")
print("    3. Acesse a pagina de Colaboradores/Setores")
print("    4. Verifique se os dados aparecem corretamente\n")
