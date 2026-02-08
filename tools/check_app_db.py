from sqlalchemy import text

from multimax import create_app, db

app = create_app()
with app.app_context():
    try:
        r = db.session.execute(text("select 1")).fetchone()
        print("DB_QUERY_OK", r)
    except Exception as e:
        print("DB_QUERY_ERR", e)
