import os

import psycopg

url = os.environ.get("DATABASE_URL")
if not url:
    print("NO DATABASE_URL")
else:
    try:
        conn = psycopg.connect(url)
        with conn.cursor() as cur:
            cur.execute("SELECT version_num FROM alembic_version")
            rows = cur.fetchall()
            print("ROWS:", rows)
    except Exception as e:
        print("ERR", e)
