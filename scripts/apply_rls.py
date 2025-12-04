import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from multimax import create_app, db
from sqlalchemy import text
from contextlib import suppress


def main():
    app = create_app()
    with app.app_context():
        uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        role = None
        try:
            uri_s = str(uri)
            if '://' in uri_s:
                creds = uri_s.split('://', 1)[1].split('@', 1)[0]
                role = creds.split(':', 1)[0]
                if role.startswith('postgres.'):
                    role = 'postgres'
        except Exception:
            pass

        tables = [
            'cleaning_task', 'cleaning_history', 'system_log', 'notification_read', 'app_setting',
            'produto', 'historico', 'meat_reception', 'meat_carrier', 'meat_part', 'collaborator',
            'shift', 'leave_credit', 'hour_bank_entry', 'user'
        ]

        for t in tables:
            try:
                db.session.execute(text(f'alter table public."{t}" enable row level security'))
                db.session.commit()
                print('RLS enabled:', t)
            except Exception as e:
                print('RLS enable failed:', t, str(e))
                with suppress(Exception):
                    db.session.rollback()
            if role:
                with suppress(Exception):
                    db.session.execute(text(f'drop policy if exists allow_server_all on public."{t}"'))
                    db.session.commit()
                try:
                    db.session.execute(text(f'create policy allow_server_all on public."{t}" for all to "{role}" using (true) with check (true)'))
                    db.session.commit()
                    print('Policy created:', t)
                except Exception as e:
                    print('Policy create failed:', t, str(e))
                    with suppress(Exception):
                        db.session.rollback()

        # verify
        names = ','.join([f"'{t}'" for t in tables])
        try:
            res = db.session.execute(text(f"select relname, relrowsecurity from pg_class where relname in ({names}) order by relname"))
            print('Verification:')
            for row in res:
                print(f' - {row[0]}: RLS={row[1]}')
        except Exception as e:
            print('Verification failed:', str(e))

        db.session.commit()
        print('done')


if __name__ == '__main__':
    main()
