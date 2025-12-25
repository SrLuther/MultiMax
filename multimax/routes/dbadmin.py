from flask import Blueprint, render_template, redirect, url_for, flash, send_file, current_app, request, jsonify
from flask_login import login_required, current_user
import os
import shutil
import time
from ..models import UserLogin
try:
    import psutil  # type: ignore
except Exception:
    psutil = None

bp = Blueprint('dbadmin', __name__, url_prefix='/db')

def _list_backups():
    bdir = str(current_app.config.get('BACKUP_DIR') or '').strip()
    try:
        if bdir:
            os.makedirs(bdir, exist_ok=True)
    except Exception:
        pass
    items = []
    try:
        if not bdir:
            return []
        for name in os.listdir(bdir):
            path = os.path.join(bdir, name)
            if not os.path.isfile(path):
                continue
            try:
                sz = os.path.getsize(path)
                mt = os.path.getmtime(path)
            except Exception:
                sz = 0
                mt = 0
            try:
                from datetime import datetime
                mt_str = datetime.fromtimestamp(mt).strftime('%d/%m/%Y %H:%M:%S') if mt else '-'
            except Exception:
                mt_str = '-'
            items.append({'name': name, 'size': sz, 'mtime': mt, 'mtime_str': mt_str})
        items.sort(key=lambda it: it['mtime'], reverse=True)
    except Exception:
        pass
    return items

@bp.route('/', methods=['GET'], strict_slashes=False)
@login_required
def index():
    if current_user.nivel != 'admin':
        flash('Apenas Gerente pode acessar Banco de Dados.', 'danger')
        return redirect(url_for('home.index'))
    uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
    is_sqlite = isinstance(uri, str) and uri.startswith('sqlite:')
    backups = _list_backups()
    daily = None
    try:
        daily = next((it for it in backups if it.get('name') == 'backup-24h.sqlite'), None)
    except Exception:
        daily = None
    try:
        page = int(request.args.get('page', '1'))
    except Exception:
        page = 1
    if page < 1:
        page = 1
    per_page = 10
    total = len(backups)
    total_pages = max(1, (total + per_page - 1) // per_page)
    if page > total_pages:
        page = total_pages
    start = (page - 1) * per_page
    end = start + per_page
    backups_page = backups[start:end]
    try:
        login_page = int(request.args.get('login_page', '1'))
    except Exception:
        login_page = 1
    if login_page < 1:
        login_page = 1
    try:
        logins_pag = UserLogin.query.order_by(UserLogin.login_at.desc()).paginate(page=login_page, per_page=10, error_out=False)
        logins = list(logins_pag.items or [])
    except Exception:
        logins_pag = None
        logins = []
    return render_template(
        'db.html',
        active_page='dbadmin',
        is_sqlite=is_sqlite,
        backups=backups_page,
        page=page,
        total_pages=total_pages,
        daily_backup=daily,
        logins=logins,
        logins_pag=logins_pag
    )

@bp.route('/metrics', methods=['GET'], strict_slashes=False)
@login_required
def metrics():
    if current_user.nivel != 'admin':
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    cpu = None
    mem = None
    try:
        if psutil is not None:
            cpu = float(psutil.cpu_percent(interval=0.05))
            mem = float(psutil.virtual_memory().percent)
        else:
            cpu = None
            mem = None
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500
    from datetime import datetime
    return jsonify({'ok': True, 'ts': datetime.now().isoformat(), 'cpu': cpu, 'mem': mem})

@bp.route('/backup', methods=['POST'], strict_slashes=False)
@login_required
def backup_now():
    if current_user.nivel != 'admin':
        flash('Apenas Gerente pode executar backup.', 'danger')
        return redirect(url_for('home.index'))
    ok = False
    try:
        fn = getattr(current_app, 'perform_backup', None)
        if callable(fn):
            ok = bool(fn(retain_count=20, force=True))
    except Exception:
        ok = False
    flash('Backup criado.' if ok else 'Falha ao criar backup.', 'success' if ok else 'danger')
    return redirect(url_for('dbadmin.index'))

@bp.route('/download/<path:name>', methods=['GET'], strict_slashes=False)
@login_required
def download(name: str):
    if current_user.nivel != 'admin':
        flash('Apenas Gerente pode baixar backup.', 'danger')
        return redirect(url_for('home.index'))
    bdir = str(current_app.config.get('BACKUP_DIR') or '').strip()
    if not bdir:
        flash('Diretório de backup inválido.', 'danger')
        return redirect(url_for('dbadmin.index'))
    path = os.path.join(bdir, name)
    if not os.path.isfile(path):
        flash('Arquivo não encontrado.', 'warning')
        return redirect(url_for('dbadmin.index'))
    return send_file(path, as_attachment=True, download_name=name)

@bp.route('/excluir/<path:name>', methods=['POST'], strict_slashes=False)
@login_required
def excluir(name: str):
    if current_user.nivel != 'admin':
        flash('Apenas Gerente pode excluir backups.', 'danger')
        return redirect(url_for('home.index'))
    bdir = str(current_app.config.get('BACKUP_DIR') or '').strip()
    if not bdir:
        flash('Diretório de backup inválido.', 'danger')
        return redirect(url_for('dbadmin.index'))
    path = os.path.join(bdir, name)
    try:
        if os.path.isfile(path):
            os.remove(path)
            flash('Backup excluído.', 'danger')
        else:
            flash('Arquivo não encontrado.', 'warning')
    except Exception as e:
        flash(f'Erro ao excluir: {e}', 'danger')
    return redirect(url_for('dbadmin.index'))

@bp.route('/restaurar/<path:name>', methods=['POST'], strict_slashes=False)
@login_required
def restaurar(name: str):
    if current_user.nivel != 'admin':
        flash('Apenas Gerente pode restaurar backups.', 'danger')
        return redirect(url_for('home.index'))
    uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
    is_sqlite = isinstance(uri, str) and uri.startswith('sqlite:')
    if not is_sqlite:
        flash('Restauração disponível apenas para banco SQLite.', 'warning')
        return redirect(url_for('dbadmin.index'))
    bdir = str(current_app.config.get('BACKUP_DIR') or '').strip()
    db_path = str(current_app.config.get('DB_FILE_PATH') or '').strip()
    if not bdir or not db_path:
        flash('Configuração de backup ou banco inválida.', 'danger')
        return redirect(url_for('dbadmin.index'))
    src = os.path.join(bdir, name)
    if not os.path.isfile(src):
        flash('Backup não encontrado.', 'warning')
        return redirect(url_for('dbadmin.index'))
    try:
        try:
            from .. import db
            db.session.close()
            db.engine.dispose()
        except Exception:
            pass
        try:
            ok = False
            fn = getattr(current_app, 'perform_backup', None)
            if callable(fn):
                ok = bool(fn(retain_count=20, force=True))
            if not ok and os.path.exists(db_path):
                ts = time.strftime('%Y%m%d-%H%M%S')
                snap = os.path.join(bdir, f'pre-restore-{ts}.sqlite')
                shutil.copy2(db_path, snap)
            if ok:
                flash('Backup automático criado antes da restauração.', 'info')
        except Exception:
            pass
        shutil.copy2(src, db_path)
        flash('Banco restaurado a partir do backup.', 'success')
    except Exception as e:
        flash(f'Erro ao restaurar: {e}', 'danger')
    return redirect(url_for('dbadmin.index'))

@bp.route('/restaurar/snapshot', methods=['POST'], strict_slashes=False)
@login_required
def restaurar_snapshot():
    if current_user.nivel != 'admin':
        flash('Apenas Gerente pode restaurar backups.', 'danger')
        return redirect(url_for('home.index'))
    uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
    is_sqlite = isinstance(uri, str) and uri.startswith('sqlite:')
    if not is_sqlite:
        flash('Restauração disponível apenas para banco SQLite.', 'warning')
        return redirect(url_for('dbadmin.index'))
    bdir = str(current_app.config.get('BACKUP_DIR') or '').strip()
    db_path = str(current_app.config.get('DB_FILE_PATH') or '').strip()
    if not bdir or not db_path:
        flash('Configuração de backup ou banco inválida.', 'danger')
        return redirect(url_for('dbadmin.index'))
    try:
        candidates = []
        for name in os.listdir(bdir):
            if not isinstance(name, str):
                continue
            if not name.lower().endswith('.sqlite'):
                continue
            if not name.startswith('pre-restore-'):
                continue
            p = os.path.join(bdir, name)
            if os.path.isfile(p):
                try:
                    mt = os.path.getmtime(p)
                except Exception:
                    mt = 0
                candidates.append((mt, p))
        if not candidates:
            flash('Nenhum snapshot encontrado.', 'warning')
            return redirect(url_for('dbadmin.index'))
        candidates.sort(key=lambda t: t[0], reverse=True)
        src = candidates[0][1]
        try:
            from .. import db
            db.session.close()
            db.engine.dispose()
        except Exception:
            pass
        shutil.copy2(src, db_path)
        flash('Banco restaurado a partir do último snapshot.', 'success')
    except Exception as e:
        flash(f'Erro ao restaurar snapshot: {e}', 'danger')
    return redirect(url_for('dbadmin.index'))
