import sqlite3

conn = sqlite3.connect("/opt/multimax-data/estoque.db")
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM colaboradores")
print("SQLite Total:", cursor.fetchone()[0])
cursor.execute("SELECT nome FROM colaboradores LIMIT 5")
print("Nomes:", [row[0] for row in cursor.fetchall()])
