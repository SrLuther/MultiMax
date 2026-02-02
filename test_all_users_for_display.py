#!/usr/bin/env python3
import psycopg
from psycopg import sql

conn = psycopg.connect(
    host="www.multimax.tec.br", port=5432, dbname="multimax", user="multimax", password="multimax123", sslmode="disable"
)

cursor = conn.cursor()

try:
    # Test the exact query from _all_users_for_display
    cursor.execute(
        """
        SELECT u.id, u.name
        FROM users u
        ORDER BY u.name ASC
    """
    )
    users = cursor.fetchall()
    print(f"✓ users table select: {len(users)} users")

    # For each user, try to find collaborator
    for user_id, user_name in users:
        cursor.execute(
            """
            SELECT id FROM collaborator WHERE user_id = %s
        """,
            (user_id,),
        )
        collab = cursor.fetchone()
        print(f"  - User {user_id} ({user_name}): {'Has collab' if collab else 'No collab'}")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback

    traceback.print_exc()

conn.close()
