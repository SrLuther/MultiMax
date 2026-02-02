#!/usr/bin/env python3
import psycopg
from psycopg import sql

conn = psycopg.connect(
    host="www.multimax.tec.br", port=5432, dbname="multimax", user="multimax", password="multimax123", sslmode="disable"
)

cursor = conn.cursor()

try:
    # Rollback first
    try:
        conn.rollback()
    except:
        pass

    seq_name = "user_id_seq"
    table_name = "user"

    # Use sql.Identifier for table names
    cursor.execute(sql.SQL("DROP SEQUENCE IF EXISTS {seq_name} CASCADE").format(seq_name=sql.Identifier(seq_name)))

    cursor.execute(sql.SQL("CREATE SEQUENCE {seq_name} START WITH 1").format(seq_name=sql.Identifier(seq_name)))

    # Get max id
    cursor.execute(
        sql.SQL("SELECT COALESCE(MAX({id_col}), 0) FROM {table}").format(
            id_col=sql.Identifier("id"), table=sql.Identifier(table_name)
        )
    )
    result = cursor.fetchone()
    max_id = int(result[0]) if result and result[0] is not None else 0

    print(f"✓ Max ID from '{table_name}' table: {max_id}")

    # Set sequence value
    cursor.execute(sql.SQL("SELECT setval({seq_name}, %s)").format(seq_name=sql.Literal(seq_name)), (max_id + 1,))

    # Apply DEFAULT
    cursor.execute(
        sql.SQL("ALTER TABLE {table} ALTER COLUMN {id_col} SET DEFAULT nextval({seq_name})").format(
            table=sql.Identifier(table_name), id_col=sql.Identifier("id"), seq_name=sql.Literal(seq_name)
        )
    )

    conn.commit()
    print(f"✓ 'user' table fixed successfully!")

except Exception as e:
    print(f"✗ Error: {e}")
    conn.rollback()

conn.close()
