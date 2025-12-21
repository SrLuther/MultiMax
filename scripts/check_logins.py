from multimax import create_app, db
from multimax.models import UserLogin

app = create_app()
with app.app_context():
    try:
        qs = UserLogin.query.order_by(UserLogin.login_at.desc()).limit(10).all()
        print('Found', len(qs))
        for u in qs:
            print(u.id, u.user_id, u.username, u.ip_address, u.login_at.strftime('%Y-%m-%d %H:%M:%S') if u.login_at else None)
    except Exception as e:
        print('ERR', e)
