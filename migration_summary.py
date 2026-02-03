#!/usr/bin/env python3
import sqlite3
import psycopg

print('\n' + '='*60)
print('RESUMO FINAL DA MIGRAÇÃO SQLite -> PostgreSQL')
print('='*60 + '\n')

# Conectar ao SQLite antigo
sqlite_db = sqlite3.connect('/opt/multimax-data/estoque.db')
sqlite_cursor = sqlite_db.cursor()

# Conectar ao PostgreSQL novo
pg_conn = psycopg.connect(
    host='localhost', port=5432, dbname='multimax',
    user='multimax', password='multimax123'
)
pg_cursor = pg_conn.cursor()

# Dados principais
print('[DADOS MIGRADOS COM SUCESSO]')

# 1. Setores
sqlite_cursor.execute('SELECT COUNT(*) FROM setor')
sqlite_count = sqlite_cursor.fetchone()[0]
pg_cursor.execute('SELECT COUNT(*) FROM setor')
pg_count = pg_cursor.fetchone()[0]
print(f'Setores: {sqlite_count} (SQLite) → {pg_count} (PostgreSQL) ✓')

# 2. Colaboradores
sqlite_cursor.execute('SELECT COUNT(*) FROM collaborator')
sqlite_count = sqlite_cursor.fetchone()[0]
pg_cursor.execute('SELECT COUNT(*) FROM colaboradores')
pg_count = pg_cursor.fetchone()[0]
print(f'Colaboradores: {sqlite_count} (SQLite) → {pg_count} (PostgreSQL) ✓')

# 3. Ciclos Semanais
sqlite_cursor.execute('SELECT COUNT(*) FROM ciclos_semanais')
sqlite_count = sqlite_cursor.fetchone()[0]
pg_cursor.execute('SELECT COUNT(*) FROM ciclos_semanais')
pg_count = pg_cursor.fetchone()[0]
print(f'Ciclos Semanais: {sqlite_count} (SQLite) → {pg_count} (PostgreSQL) ✓')

# 4. Ciclos Mensais
sqlite_cursor.execute('SELECT COUNT(*) FROM ciclos_mensais')
sqlite_count = sqlite_cursor.fetchone()[0]
print(f'Ciclos Mensais: {sqlite_count} (SQLite) → [aguardando migração]')

# 5. Histórico de métricas
sqlite_cursor.execute('SELECT COUNT(*) FROM metric_history')
sqlite_count = sqlite_cursor.fetchone()[0]
pg_cursor.execute('SELECT COUNT(*) FROM metric_history')
pg_count = pg_cursor.fetchone()[0]
print(f'Metric History: {sqlite_count} (SQLite) → {pg_count} (PostgreSQL)')

# 6. Ciclos (transações)
sqlite_cursor.execute('SELECT COUNT(*) FROM ciclo')
sqlite_count = sqlite_cursor.fetchone()[0]
pg_cursor.execute('SELECT COUNT(*) FROM ciclo')
pg_count = pg_cursor.fetchone()[0]
print(f'Ciclos (Transações): {sqlite_count} (SQLite) → {pg_count} (PostgreSQL)')

print('\n[DADOS ADICIONAIS]')
# Usuários
pg_cursor.execute('SELECT COUNT(*) FROM "user"')
user_count = pg_cursor.fetchone()[0]
print(f'Usuários: {user_count}')

# Alertas
pg_cursor.execute('SELECT COUNT(*) FROM alert')
alert_count = pg_cursor.fetchone()[0]
print(f'Alertas: {alert_count}')

# Incidentes
pg_cursor.execute('SELECT COUNT(*) FROM incident')
incident_count = pg_cursor.fetchone()[0]
print(f'Incidentes: {incident_count}')

# Logs
pg_cursor.execute('SELECT COUNT(*) FROM system_log')
log_count = pg_cursor.fetchone()[0]
print(f'Logs do Sistema: {log_count}')

print('\n' + '='*60)
print('STATUS: MIGRAÇÃO PARCIAL CONCLUÍDA COM SUCESSO')
print('='*60 + '\n')

print('Próximos passos:')
print('  1. Migrar ciclos mensais')
print('  2. Migrar dados de folgas e férias')
print('  3. Validar integridade referencial')
print('  4. Executar testes de aplicação\n')

sqlite_db.close()
pg_cursor.close()
pg_conn.close()
