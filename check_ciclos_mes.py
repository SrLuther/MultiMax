#!/usr/bin/env python3
import sqlite3

sqlite_db = sqlite3.connect('/opt/multimax-data/estoque.db')
sqlite_cursor = sqlite_db.cursor()

# Verificar estrutura
sqlite_cursor.execute("PRAGMA table_info(ciclos_mensais)")
cols = sqlite_cursor.fetchall()
print('Colunas em ciclos_mensais:')
for col in cols:
    print(f'  {col[1]}: {col[2]}')

# Ver dados
sqlite_cursor.execute('SELECT * FROM ciclos_mensais LIMIT 1')
print('\nPrimeiro registro:')
print(sqlite_cursor.fetchone())

sqlite_db.close()
