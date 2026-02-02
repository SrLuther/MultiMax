#!/usr/bin/env python3
import psycopg

conn = psycopg.connect(
    host="www.multimax.tec.br", port=5432, dbname="multimax", user="multimax", password="multimax123", sslmode="disable"
)

cursor = conn.cursor()

try:
    # Try the same queries from /gestao
    print("Testing queries from /gestao...")

    # 1. Test User.query.all()
    cursor.execute("SELECT * FROM users LIMIT 1")
    print(f"✓ users table: OK ({cursor.rowcount})")

    # 2. Test Collaborator.query.order_by(Collaborator.name.asc()).all()
    cursor.execute("SELECT * FROM collaborator ORDER BY name ASC LIMIT 1")
    print(f"✓ collaborator table: OK ({cursor.rowcount})")

    # 3. Test JobRole
    cursor.execute("SELECT * FROM job_role ORDER BY name ASC LIMIT 1")
    print(f"✓ job_role table: OK ({cursor.rowcount})")

    # 4. Test Setor
    cursor.execute("SELECT * FROM setor WHERE ativo = TRUE ORDER BY nome ASC LIMIT 1")
    print(f"✓ setor table: OK ({cursor.rowcount})")

    print("\n✓ All queries passed!")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback

    traceback.print_exc()

conn.close()
