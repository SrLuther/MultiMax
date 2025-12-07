from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from .. import db
from ..models import User, Produto, Historico, CleaningHistory, SystemLog, NotificationRead
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
            return redirect(url_for('usuarios.users'))
        if username_input:
            base_username = ''.join(ch for ch in username_input.lower() if ch.isalnum()) or 'user'
            username = base_username
            if User.query.filter_by(username=username).first() is not None:
                flash('Login já existe. Escolha outro.', 'danger')
                return redirect(url_for('usuarios.users'))
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
        return redirect(url_for('usuarios.users'))
    all_users: list[User] = User.query.all()
    senha_sugestao = '123456'
    return render_template('users.html', users=all_users, active_page='users', senha_sugestao=senha_sugestao)


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
    return redirect(url_for('usuarios.users'))

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
        return redirect(url_for('usuarios.users'))
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
    return redirect(url_for('usuarios.users'))

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
        flash('Acesso negado. Apenas Administradores podem acessar o Monitor.', 'danger')
        return redirect(url_for('estoque.index'))
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
    b64 = base64.b64encode(buf.getvalue()).decode('ascii')
    hist_estoque = Historico.query.order_by(Historico.data.desc()).limit(50).all()
    hist_limpeza = CleaningHistory.query.order_by(CleaningHistory.data_conclusao.desc()).limit(50).all()
    hist_sistema = SystemLog.query.order_by(SystemLog.data.desc()).limit(50).all()
    logs = []
    for h in hist_estoque:
        logs.append({
            'data': h.data,
            'origem': 'Estoque',
            'evento': h.action,
            'detalhes': h.details,
            'usuario': h.usuario,
            'produto': h.product_name,
            'quantidade': h.quantidade,
        })
    for h in hist_limpeza:
        logs.append({
            'data': h.data_conclusao,
            'origem': 'Limpeza',
            'evento': 'conclusao',
            'detalhes': h.observacao,
            'usuario': h.usuario_conclusao,
            'produto': h.nome_limpeza,
            'quantidade': None,
        })
    for s in hist_sistema:
        logs.append({
            'data': s.data,
            'origem': s.origem,
            'evento': s.evento,
            'detalhes': s.detalhes,
            'usuario': s.usuario,
            'produto': None,
            'quantidade': None,
        })
    logs.sort(key=lambda x: x['data'], reverse=True)
    return render_template('monitor.html', active_page='monitor', url=url, qr_base64=b64, logs=logs)

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
