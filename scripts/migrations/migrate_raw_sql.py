#!/usr/bin/env python3
import sqlite3

# Conectar ao SQLite
sqlite_db = sqlite3.connect("/opt/multimax-data/estoque.db")
sqlite_cursor = sqlite_db.cursor()

# Ler Setores
sqlite_cursor.execute("SELECT id, nome FROM setor ORDER BY id")
setores = sqlite_cursor.fetchall()

# Ler Ciclos Semanais
sqlite_cursor.execute("SELECT * FROM ciclos_semanais ORDER BY id LIMIT 5")
ciclos_sem = sqlite_cursor.fetchall()

# Ler Colaboradores
sqlite_cursor.execute("SELECT DISTINCT nome_colaborador FROM ciclo WHERE nome_colaborador IS NOT NULL")
colaboradores = [row[0] for row in sqlite_cursor.fetchall()]

print("[*] Dados do SQLite:")
print(f"  Setores: {len(setores)}")
print(f"  Ciclos Semanais: {ciclos_sem}")
print(f"  Colaboradores unicos: {len(colaboradores)}")

sql_inserts = []

# Gerar INSERTs para Setores
for setor_id, nome in setores:
    safe_nome = nome.replace("'", "''")
    sql = f"INSERT INTO setor (id, nome, ativo, created_at) " f"VALUES ({setor_id}, '{safe_nome}', true, NOW());"
    sql_inserts.append(sql)

print("[*] Comandos SQL gerados:")
for sql in sql_inserts:
    print(f"  {sql}")

# Salvar em arquivo
with open("/tmp/migrate.sql", "w") as f:
    for sql in sql_inserts:
        f.write(sql + "\n")

print("[OK] Salvo em /tmp/migrate.sql")

sqlite_db.close()
