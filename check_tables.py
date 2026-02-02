#!/usr/bin/env python3
import psycopg

conn = psycopg.connect(
    host="www.multimax.tec.br", port=5432, dbname="multimax", user="multimax", password="multimax123", sslmode="disable"
)

cursor = conn.cursor()

# Check bulk_hour_operations
cursor.execute(
    "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'bulk_hour_operations' AND column_name = 'id'"
)
result = cursor.fetchone()
if result:
    print(f"bulk_hour_operations.id type: {result[1]}")

# Check registro_jornada
cursor.execute(
    "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'registro_jornada' AND column_name = 'id'"
)
result = cursor.fetchone()
if result:
    print(f"registro_jornada.id type: {result[1]}")
else:
    print("registro_jornada: table NOT FOUND")

# Check 'user'
cursor.execute(
    "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'user' AND column_name = 'id'"
)
result = cursor.fetchone()
if result:
    print(f"user.id type: {result[1]}")
else:
    print("user: table NOT FOUND")

# Check collaborator
cursor.execute(
    "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'collaborator' AND column_name = 'id'"
)
result = cursor.fetchone()
if result:
    print(f"collaborator.id type: {result[1]}")

conn.close()
