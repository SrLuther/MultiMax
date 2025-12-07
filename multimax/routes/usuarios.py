from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from .. import db
from ..models import User, Produto, Historico, CleaningHistory, SystemLog, NotificationRead, HourBankEntry, Collaborator, JobRole
from datetime import datetime, timedelta, date
from collections import OrderedDict
from typing import TypedDict
import os
import socket
import base64
from io import BytesIO
import qrcode

bp = Blueprint('usuarios', __name__)

@bp.route('/users', methods=['GET', 'POST'])
@login_required
def users():
    if current_user.nivel != 'admin':
        flash('Acesso negado. Apenas Gerente pode gerenciar usuários.', 'danger')
        return redirect(url_for('estoque.index'))
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        username_input = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        nivel = request.form.get('nivel', 'visualizador').strip()
        if not name or not password:
            flash('Nome e senha são obrigatórios.', 'warning')
            return redirect(url_for('usuarios.gestao'))
        if username_input:
            base_username = ''.join(ch for ch in username_input.lower() if ch.isalnum()) or 'user'
            username = base_username
            if User.query.filter_by(username=username).first() is not None:
                flash('Login já existe. Escolha outro.', 'danger')
                return redirect(url_for('usuarios.gestao'))
        else:
            base_username = ''.join(ch for ch in name.lower() if ch.isalnum()) or 'user'
            username = base_username
            suffix = 1
            while User.query.filter_by(username=username).first() is not None:
                username = f"{base_username}{suffix}"
                suffix += 1
        new_user = User()
        new_user.name = name
        new_user.username = username
        new_user.nivel = nivel
        new_user.password_hash = generate_password_hash(password)
        try:
            db.session.add(new_user)
            log = SystemLog()
            log.origem = 'Usuarios'
            log.evento = 'criar'
            log.detalhes = f'Criado {name} ({username}) nivel {nivel}'
            log.usuario = current_user.name
            db.session.add(log)
            db.session.commit()
            flash(f'Usuário "{name}" criado com login "{username}".', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar usuário: {e}', 'danger')
        return redirect(url_for('usuarios.gestao'))
    return redirect(url_for('usuarios.gestao'))


@bp.route('/users/<int:user_id>/senha', methods=['POST'])
@login_required
def update_password(user_id):
    if current_user.nivel != 'admin':
        flash('Você não tem permissão para atualizar senhas.', 'danger')
        return redirect(url_for('estoque.index'))
    user = User.query.get_or_404(user_id)
    new_password = request.form.get('new_password', '').strip()
    if not new_password:
        flash('Informe a nova senha.', 'warning')
        return redirect(url_for('usuarios.users'))
    try:
        user.password_hash = generate_password_hash(new_password)
        log = SystemLog()
        log.origem = 'Usuarios'
        log.evento = 'senha'
        log.detalhes = f'Senha atualizada para {user.username}'
        log.usuario = current_user.name
        db.session.add(log)
        db.session.commit()
        flash(f'Senha de "{user.name}" atualizada.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar senha: {e}', 'danger')
    return redirect(url_for('usuarios.gestao'))

@bp.route('/users/<int:user_id>/reset_senha', methods=['POST'])
@login_required
def reset_password(user_id):
    if current_user.nivel != 'admin':
        flash('Você não tem permissão para redefinir senhas.', 'danger')
        return redirect(url_for('estoque.index'))
    user = User.query.get_or_404(user_id)
    default_password = '123456'
    try:
        user.password_hash = generate_password_hash(default_password)
        log = SystemLog()
        log.origem = 'Usuarios'
        log.evento = 'senha'
        log.detalhes = f'Senha redefinida para {user.username}'
        log.usuario = current_user.name
        db.session.add(log)
        db.session.commit()
        flash(f'Senha de "{user.name}" redefinida.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao redefinir senha: {e}', 'danger')
    return redirect(url_for('usuarios.users'))

@bp.route('/users/<int:user_id>/nivel', methods=['POST'])
@login_required
def update_level(user_id):
    if current_user.nivel != 'admin':
        flash('Você não tem permissão para alterar níveis de usuário.', 'danger')
        return redirect(url_for('estoque.index'))
    user = User.query.get_or_404(user_id)
    nivel = request.form.get('nivel', 'visualizador').strip()
    if nivel not in ('visualizador', 'operador', 'admin'):
        flash('Nível inválido.', 'warning')
        return redirect(url_for('usuarios.gestao'))
    try:
        user.nivel = nivel
        log = SystemLog()
        log.origem = 'Usuarios'
        log.evento = 'nivel'
        log.detalhes = f'Nivel {user.username} -> {nivel}'
        log.usuario = current_user.name
        db.session.add(log)
        db.session.commit()
        flash(f'Nivel do usuário "{user.name}" atualizado para "{nivel}".', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar nível: {e}', 'danger')
    return redirect(url_for('usuarios.gestao'))

@bp.route('/users/<int:user_id>/excluir', methods=['POST'])
@login_required
def excluir_user(user_id):
    if current_user.nivel != 'admin':
        flash('Você não tem permissão para excluir usuários.', 'danger')
        return redirect(url_for('estoque.index'))
    if current_user.id == user_id:
        flash('Você não pode excluir sua própria conta.', 'warning')
        return redirect(url_for('usuarios.users'))
    user = User.query.get_or_404(user_id)
    try:
        db.session.delete(user)
        log = SystemLog()
        log.origem = 'Usuarios'
        log.evento = 'excluir'
        log.detalhes = f'Excluido {user.name} ({user.username})'
        log.usuario = current_user.name
        db.session.add(log)
        db.session.commit()
        flash(f'Usuário "{user.name}" excluído com sucesso.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir usuário: {e}', 'danger')
    return redirect(url_for('usuarios.users'))

@bp.route('/monitor')
@login_required
def monitor():
    if current_user.nivel != 'admin':
        flash('Acesso negado. Apenas Administradores.', 'danger')
        return redirect(url_for('estoque.index'))
    return redirect(url_for('usuarios.gestao'))

@bp.route('/notifications/read')
@login_required
def notifications_read():
    tipo = request.args.get('tipo')
    ref_id = request.args.get('id', type=int)
    nxt = request.args.get('next', url_for('estoque.index'))
    if tipo in ('estoque', 'limpeza') and ref_id:
        try:
            if NotificationRead.query.filter_by(user_id=current_user.id, tipo=tipo, ref_id=ref_id).first() is None:
                nr = NotificationRead()
                nr.user_id = current_user.id
                nr.tipo = tipo
                nr.ref_id = ref_id
                db.session.add(nr)
                db.session.commit()
        except Exception:
            db.session.rollback()
    return redirect(nxt)

@bp.route('/notifications/unread')
@login_required
def notifications_unread():
    tipo = request.args.get('tipo')
    ref_id = request.args.get('id', type=int)
    nxt = request.args.get('next', url_for('estoque.index'))
    if tipo in ('estoque', 'limpeza') and ref_id:
        try:
            NotificationRead.query.filter_by(user_id=current_user.id, tipo=tipo, ref_id=ref_id).delete()
            db.session.commit()
        except Exception:
            db.session.rollback()
    return redirect(nxt)

@bp.route('/notifications/unread_all')
@login_required
def notifications_unread_all():
    nxt = request.args.get('next', url_for('estoque.index'))
    try:
        NotificationRead.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
    except Exception:
        db.session.rollback()
    return redirect(nxt)

@bp.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        username_input = (request.form.get('username') or '').strip().lower()
        if not name:
            flash('Nome é obrigatório.', 'warning')
            return redirect(url_for('usuarios.perfil'))
        if not username_input:
            flash('Login é obrigatório.', 'warning')
            return redirect(url_for('usuarios.perfil'))
        base_username = ''.join(ch for ch in username_input if ch.isalnum())
        if not base_username:
            flash('Login deve conter apenas letras e números.', 'warning')
            return redirect(url_for('usuarios.perfil'))
        if base_username != current_user.username:
            if User.query.filter_by(username=base_username).first() is not None:
                flash('Login já existe. Escolha outro.', 'danger')
                return redirect(url_for('usuarios.perfil'))
            current_user.username = base_username
        current_user.name = name
        try:
            db.session.commit()
            flash('Perfil atualizado.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar perfil: {e}', 'danger')
        return redirect(url_for('usuarios.perfil'))
    try:
        from sqlalchemy import inspect, text
        insp = inspect(db.engine)
        cols_meta = [c['name'] for c in insp.get_columns('collaborator')]
        if 'user_id' not in cols_meta:
            db.session.execute(text('ALTER TABLE collaborator ADD COLUMN user_id INTEGER'))
            db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
    collab = None
    entries = []
    total = 0.0
    try:
        collab = Collaborator.query.filter_by(user_id=current_user.id).first()
        if collab:
            entries = HourBankEntry.query.filter_by(collaborator_id=collab.id).order_by(HourBankEntry.date.desc()).limit(50).all()
            try:
                from sqlalchemy import func
                total = db.session.query(func.coalesce(func.sum(HourBankEntry.hours), 0.0)).filter(HourBankEntry.collaborator_id == collab.id).scalar() or 0.0
                total = float(total)
            except Exception:
                total = 0.0
    except Exception:
        collab = None
        entries = []
        total = 0.0
    return render_template('perfil.html', active_page='perfil', collab=collab, entries=entries, total=total)

@bp.route('/perfil/senha', methods=['POST'])
@login_required
def perfil_senha():
    senha_atual = request.form.get('senha_atual', '')
    nova_senha = request.form.get('nova_senha', '')
    confirmar = request.form.get('confirmar_senha', '')
    if not nova_senha or len(nova_senha) < 6:
        flash('Nova senha deve ter ao menos 6 caracteres.', 'warning')
        return redirect(url_for('usuarios.perfil'))
    if nova_senha != confirmar:
        flash('Confirmação de senha não confere.', 'warning')
        return redirect(url_for('usuarios.perfil'))
    if not check_password_hash(current_user.password_hash or '', senha_atual):
        flash('Senha atual inválida.', 'danger')
        return redirect(url_for('usuarios.perfil'))
    try:
        current_user.password_hash = generate_password_hash(nova_senha)
        db.session.commit()
        flash('Senha atualizada com sucesso.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar senha: {e}', 'danger')
    return redirect(url_for('usuarios.perfil'))

@bp.route('/gestao', methods=['GET'])
@login_required
def gestao():
    if current_user.nivel != 'admin':
        flash('Acesso negado. Apenas Administradores.', 'danger')
        return redirect(url_for('estoque.index'))
    q = (request.args.get('q') or '').strip()
    # Gerar QR do endereço de acesso (não exibimos o texto, apenas o QR)
    port = int(os.getenv('PORT', '5000'))
    ip = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = request.host.split(':')[0]
    url = f"http://{ip}:{port}"
    img = qrcode.make(url)
    buf = BytesIO()
    img.save(buf, 'PNG')
    qr_base64 = base64.b64encode(buf.getvalue()).decode('ascii')
    try:
        u_page = int(request.args.get('u_page', '1'))
    except Exception:
        u_page = 1
    try:
        l_page = int(request.args.get('l_page', '1'))
    except Exception:
        l_page = 1
    if u_page < 1: u_page = 1
    if l_page < 1: l_page = 1
    hist_estoque = Historico.query.order_by(Historico.data.desc()).limit(50).all()
    hist_limpeza = CleaningHistory.query.order_by(CleaningHistory.data_conclusao.desc()).limit(50).all()
    hist_sistema = SystemLog.query.order_by(SystemLog.data.desc()).limit(50).all()
    logs = []
    for h in hist_estoque:
        logs.append({'data': h.data, 'origem': 'Estoque', 'evento': h.action, 'detalhes': h.details, 'usuario': h.usuario, 'produto': h.product_name, 'quantidade': h.quantidade})
    for h in hist_limpeza:
        logs.append({'data': h.data_conclusao, 'origem': 'Limpeza', 'evento': 'conclusao', 'detalhes': h.observacao, 'usuario': h.usuario_conclusao, 'produto': h.nome_limpeza, 'quantidade': None})
    for s in hist_sistema:
        logs.append({'data': s.data, 'origem': s.origem, 'evento': s.evento, 'detalhes': s.detalhes, 'usuario': s.usuario, 'produto': None, 'quantidade': None})
    logs.sort(key=lambda x: x['data'], reverse=True)
    # Busca e paginação de usuários
    uq = User.query
    if q:
        uq = uq.filter(User.name.ilike(f"%{q}%"))
    all_users: list[User] = uq.order_by(User.username.asc()).all()
    per_users = 5
    total_users = len(all_users)
    u_total_pages = max(1, (total_users + per_users - 1) // per_users)
    if u_page > u_total_pages:
        u_page = u_total_pages
    u_start = (u_page - 1) * per_users
    u_end = u_start + per_users
    users_page = all_users[u_start:u_end]

    # Paginação de logs
    per_logs = 10
    total_logs = len(logs)
    l_total_pages = max(1, (total_logs + per_logs - 1) // per_logs)
    if l_page > l_total_pages:
        l_page = l_total_pages
    l_start = (l_page - 1) * per_logs
    l_end = l_start + per_logs
    logs_page = logs[l_start:l_end]

    senha_sugestao = '123456'
    roles = JobRole.query.order_by(JobRole.name.asc()).all()
    # Removido endereço de acesso (url/qr), mantendo somente dados necessários
    return render_template(
        'gestao.html',
        active_page='gestao',
        logs_page=logs_page,
        l_page=l_page,
        l_total_pages=l_total_pages,
        users_page=users_page,
        u_page=u_page,
        u_total_pages=u_total_pages,
        q=q,
        senha_sugestao=senha_sugestao,
        roles=roles,
        qr_base64=qr_base64
    )

@bp.route('/gestao/roles', methods=['POST'])
@login_required
def gestao_role_criar():
    if current_user.nivel != 'admin':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('usuarios.gestao'))
    name = (request.form.get('name') or '').strip()
    nivel = (request.form.get('nivel') or 'visualizador').strip()
    if not name:
        flash('Nome do cargo é obrigatório.', 'warning')
        return redirect(url_for('usuarios.gestao'))
    if nivel not in ('visualizador','operador','admin'):
        flash('Tipo de permissão inválido.', 'warning')
        return redirect(url_for('usuarios.gestao'))
    if JobRole.query.filter_by(name=name).first() is not None:
        flash('Cargo já existe.', 'danger')
        return redirect(url_for('usuarios.gestao'))
    try:
        r = JobRole(); r.name = name; r.nivel = nivel; db.session.add(r); db.session.commit()
        flash('Cargo criado.', 'success')
    except Exception as e:
        db.session.rollback(); flash(f'Erro ao criar cargo: {e}', 'danger')
    return redirect(url_for('usuarios.gestao'))

@bp.route('/gestao/roles/<int:id>/editar', methods=['POST'])
@login_required
def gestao_role_editar(id: int):
    if current_user.nivel != 'admin':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('usuarios.gestao'))
    role = JobRole.query.get_or_404(id)
    name = (request.form.get('name') or role.name).strip()
    nivel = (request.form.get('nivel') or role.nivel).strip()
    if nivel not in ('visualizador','operador','admin'):
        flash('Tipo de permissão inválido.', 'warning')
        return redirect(url_for('usuarios.gestao'))
    try:
        role.name = name; role.nivel = nivel; db.session.commit(); flash('Cargo atualizado.', 'info')
    except Exception as e:
        db.session.rollback(); flash(f'Erro ao atualizar cargo: {e}', 'danger')
    return redirect(url_for('usuarios.gestao'))

@bp.route('/gestao/roles/<int:id>/excluir', methods=['POST'])
@login_required
def gestao_role_excluir(id: int):
    if current_user.nivel != 'admin':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('usuarios.gestao'))
    role = JobRole.query.get_or_404(id)
    try:
        db.session.delete(role); db.session.commit(); flash('Cargo excluído.', 'danger')
    except Exception as e:
        db.session.rollback(); flash(f'Erro ao excluir cargo: {e}', 'danger')
    return redirect(url_for('usuarios.gestao'))
