from flask import Blueprint, render_template, redirect, url_for, flash, send_file, current_app, request
from flask_login import login_required, current_user
import os

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
                sz = 0; mt = 0
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
    return render_template('db.html', active_page='dbadmin', is_sqlite=is_sqlite, backups=backups)

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
            ok = bool(fn(retain_count=10))
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
