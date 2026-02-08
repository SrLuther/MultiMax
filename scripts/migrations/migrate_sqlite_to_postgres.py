#!/usr/bin/env python3
"""
Script de Migração: SQLite → PostgreSQL
Migra todos os dados do banco SQLite para PostgreSQL preservando relacionamentos.
"""
import os
import sqlite3
import sys
from datetime import datetime

from sqlalchemy import create_engine, text

# Configuração
SQLITE_PATH = "/opt/multimax-data/estoque.db"
POSTGRES_URI = "postgresql://multimax:multimax123@localhost:5432/multimax?sslmode=disable"

# Cores para output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def log_info(msg):
    print(f"{BLUE}[INFO]{RESET} {msg}")


def log_success(msg):
    print(f"{GREEN}[✓]{RESET} {msg}")


def log_warning(msg):
    print(f"{YELLOW}[!]{RESET} {msg}")


def log_error(msg):
    print(f"{RED}[✗]{RESET} {msg}")


def get_sqlite_tables(conn):
    """Obtém lista de todas as tabelas do SQLite"""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    return [row[0] for row in cursor.fetchall()]


def get_table_schema(conn, table_name):
    """Obtém schema da tabela SQLite"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    return cursor.fetchall()


def get_row_count(conn, table_name):
    """Conta registros em uma tabela"""
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    return cursor.fetchone()[0]


def create_postgres_tables(pg_engine, sqlite_conn):
    """Cria tabelas no PostgreSQL copiando estrutura do SQLite"""
    log_info("Criando tabelas no PostgreSQL...")

    try:
        tables = get_sqlite_tables(sqlite_conn)

        with pg_engine.connect() as conn:
            for table in tables:
                # Obter schema da tabela
                schema = get_table_schema(sqlite_conn, table)

                # Criar definição da tabela
                columns = []
                for col in schema:
                    col_id, col_name, col_type, not_null, default_val, is_pk = col

                    # Mapear tipos SQLite para PostgreSQL
                    pg_type = col_type.upper()
                    if "INT" in pg_type:
                        pg_type = "INTEGER"
                    elif "CHAR" in pg_type or "TEXT" in pg_type:
                        pg_type = "TEXT"
                    elif "REAL" in pg_type or "DOUBLE" in pg_type or "FLOAT" in pg_type:
                        pg_type = "DOUBLE PRECISION"
                    elif "DATE" in pg_type or "TIME" in pg_type:
                        pg_type = "TIMESTAMP"
                    elif "BOOL" in pg_type:
                        pg_type = "BOOLEAN"

                    col_def = f"{col_name} {pg_type}"

                    if is_pk:
                        col_def += " PRIMARY KEY"
                    elif not_null:
                        col_def += " NOT NULL"

                    columns.append(col_def)

                create_sql = f'CREATE TABLE IF NOT EXISTS "{table}" ({", ".join(columns)})'
                conn.execute(text(create_sql))
                conn.commit()
                log_info(f"  Tabela '{table}' criada")

        log_success("Tabelas criadas no PostgreSQL!")
        return True

    except Exception as e:
        log_error(f"Erro ao criar tabelas: {e}")
        import traceback

        traceback.print_exc()
        return False


def migrate_table(sqlite_conn, pg_engine, table_name):
    """Migra dados de uma tabela específica"""
    log_info(f"Migrando tabela: {table_name}")

    try:
        # Contar registros no SQLite
        row_count = get_row_count(sqlite_conn, table_name)

        if row_count == 0:
            log_warning(f"  Tabela '{table_name}' está vazia, pulando...")
            return True

        log_info(f"  Registros a migrar: {row_count}")

        # Ler dados do SQLite
        cursor = sqlite_conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()

        # Obter nomes das colunas
        column_names = [description[0] for description in cursor.description]

        # Preparar query INSERT para PostgreSQL
        columns_str = ", ".join([f'"{col}"' for col in column_names])
        placeholders = ", ".join([f":{col}" for col in column_names])
        insert_query = f'INSERT INTO "{table_name}" ({columns_str}) VALUES ({placeholders})'

        # Inserir dados no PostgreSQL
        with pg_engine.connect() as conn:
            trans = conn.begin()
            try:
                for row in rows:
                    row_dict = dict(zip(column_names, row))
                    conn.execute(text(insert_query), row_dict)

                trans.commit()
                log_success(f"  {row_count} registros migrados para '{table_name}'")
                return True

            except Exception as err:
                trans.rollback()
                log_error(f"  Erro ao inserir dados em '{table_name}': {err}")
                return False

    except Exception as err:
        log_error(f"  Erro ao migrar '{table_name}': {err}")
        return False


def reset_sequences(pg_engine, tables):
    """Reseta as sequences do PostgreSQL para o próximo valor disponível"""
    log_info("Resetando sequences do PostgreSQL...")

    with pg_engine.connect() as conn:
        for table in tables:
            try:
                # Tentar resetar sequence para tabelas com coluna 'id'
                query = text(
                    f"""
                    SELECT setval(
                        pg_get_serial_sequence('"{table}"', 'id'),
                        COALESCE((SELECT MAX(id) FROM "{table}"), 1),
                        true
                    )
                """
                )
                conn.execute(query)
                conn.commit()
                log_success(f"  Sequence resetada para '{table}'")
            except Exception:
                # Ignorar erros (tabelas sem id ou sem sequence)
                pass


def validate_migration(sqlite_conn, pg_engine, tables):
    """Valida se a migração foi bem-sucedida comparando contagens"""
    log_info("\n" + "=" * 60)
    log_info("VALIDAÇÃO DA MIGRAÇÃO")
    log_info("=" * 60)

    all_valid = True

    for table in tables:
        sqlite_count = get_row_count(sqlite_conn, table)

        with pg_engine.connect() as conn:
            result = conn.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
            pg_count = result.scalar()

        if sqlite_count == pg_count:
            log_success(f"{table}: {sqlite_count} registros ✓")
        else:
            log_error(f"{table}: SQLite={sqlite_count}, PostgreSQL={pg_count} ✗")
            all_valid = False

    return all_valid


def main():
    print("\n" + "=" * 60)
    print("MIGRAÇÃO SQLite → PostgreSQL")
    print("=" * 60 + "\n")

    # Verificar se SQLite existe
    if not os.path.exists(SQLITE_PATH):
        log_error(f"Banco SQLite não encontrado: {SQLITE_PATH}")
        return 1

    log_success(f"Banco SQLite encontrado: {SQLITE_PATH}")

    # Conectar ao SQLite
    log_info("Conectando ao SQLite...")
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    log_success("Conectado ao SQLite!")

    # Conectar ao PostgreSQL
    log_info("Conectando ao PostgreSQL...")
    try:
        pg_engine = create_engine(POSTGRES_URI, echo=False)
        with pg_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        log_success("Conectado ao PostgreSQL!")
    except Exception as e:
        log_error(f"Erro ao conectar no PostgreSQL: {e}")
        return 1

    # Obter lista de tabelas do SQLite
    tables = get_sqlite_tables(sqlite_conn)
    log_info(f"\nTabelas encontradas no SQLite: {len(tables)}")
    for table in tables:
        count = get_row_count(sqlite_conn, table)
        print(f"  - {table}: {count} registros")

    # Confirmar migração
    print("\n" + "=" * 60)
    response = input("Deseja continuar com a migração? (sim/não): ").strip().lower()
    if response not in ["sim", "s", "yes", "y"]:
        log_warning("Migração cancelada pelo usuário")
        return 0

    # Criar tabelas no PostgreSQL
    if not create_postgres_tables(pg_engine, sqlite_conn):
        log_error("Falha ao criar tabelas no PostgreSQL")
        return 1

    # Ordem de migração (respeitando foreign keys)
    # Primeiro tabelas sem dependências, depois com dependências
    migration_order = [
        "users",  # Usuários primeiro
        "collaborators",  # Colaboradores
        "departments",  # Departamentos
        "positions",  # Cargos
        "shifts",  # Turnos
        "points",  # Pontos
        "leaves",  # Folgas
        "worksheets",  # Folhas de trabalho
        "products",  # Produtos
        "stock_movements",  # Movimentações de estoque
    ]

    # Adicionar tabelas que não estão na ordem específica (no final)
    for table in tables:
        if table not in migration_order:
            migration_order.append(table)

    # Filtrar apenas tabelas que existem
    migration_order = [t for t in migration_order if t in tables]

    # Migrar cada tabela
    print("\n" + "=" * 60)
    log_info("INICIANDO MIGRAÇÃO DE DADOS")
    print("=" * 60 + "\n")

    success_count = 0
    for table in migration_order:
        if migrate_table(sqlite_conn, pg_engine, table):
            success_count += 1

    # Resetar sequences
    reset_sequences(pg_engine, migration_order)

    # Validar migração
    if validate_migration(sqlite_conn, pg_engine, migration_order):
        print("\n" + "=" * 60)
        log_success("MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        log_success(f"{success_count}/{len(migration_order)} tabelas migradas")
        print("=" * 60 + "\n")

        # Fazer backup do SQLite
        backup_path = f"{SQLITE_PATH}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        import shutil

        shutil.copy2(SQLITE_PATH, backup_path)
        log_success(f"Backup do SQLite criado: {backup_path}")

        return 0
    else:
        print("\n" + "=" * 60)
        log_error("MIGRAÇÃO CONCLUÍDA COM ERROS!")
        log_warning("Verifique as contagens acima")
        print("=" * 60 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
