from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from .. import db
from ..models import User, Produto, Historico, CleaningHistory, SystemLog, NotificationRead, HourBankEntry, Collaborator, JobRole, LeaveCredit, LeaveAssignment, LeaveConversion, Shift
from datetime import datetime, timedelta, date
from collections import OrderedDict
from typing import TypedDict
import os
 

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
    folga_balance = 0
    folga_credits = []
    folga_assigned = []
    folga_conversions = []
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
            try:
                from sqlalchemy import func
                credits_sum = db.session.query(func.coalesce(func.sum(LeaveCredit.amount_days), 0)).filter(LeaveCredit.collaborator_id == collab.id).scalar() or 0
                assigned_sum = db.session.query(func.coalesce(func.sum(LeaveAssignment.days_used), 0)).filter(LeaveAssignment.collaborator_id == collab.id).scalar() or 0
                converted_sum = db.session.query(func.coalesce(func.sum(LeaveConversion.amount_days), 0)).filter(LeaveConversion.collaborator_id == collab.id).scalar() or 0
                folga_balance = int(credits_sum) - int(assigned_sum) - int(converted_sum)
            except Exception:
                folga_balance = 0
            try:
                folga_credits = LeaveCredit.query.filter_by(collaborator_id=collab.id).order_by(LeaveCredit.date.desc()).limit(50).all()
            except Exception:
                folga_credits = []
            try:
                folga_assigned = LeaveAssignment.query.filter_by(collaborator_id=collab.id).order_by(LeaveAssignment.date.desc()).limit(50).all()
            except Exception:
                folga_assigned = []
            try:
                folga_conversions = LeaveConversion.query.filter_by(collaborator_id=collab.id).order_by(LeaveConversion.date.desc()).limit(50).all()
            except Exception:
                folga_conversions = []
    except Exception:
        collab = None
        entries = []
        total = 0.0
    return render_template('perfil.html', active_page='perfil', collab=collab, entries=entries, total=total, folga_balance=folga_balance, folga_credits=folga_credits, folga_assigned=folga_assigned, folga_conversions=folga_conversions)

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
    view = (request.args.get('view') or '').strip()
    # QR removido
    try:
        from sqlalchemy import inspect, text
        insp = inspect(db.engine)
        cols_meta = [c['name'] for c in insp.get_columns('collaborator')]
        changed = False
        if 'name' not in cols_meta:
            db.session.execute(text('ALTER TABLE collaborator ADD COLUMN name TEXT'))
            changed = True
            if 'nome' in cols_meta:
                try:
                    db.session.execute(text('UPDATE collaborator SET name = nome WHERE name IS NULL'))
                except Exception:
                    pass
            else:
                try:
                    db.session.execute(text("UPDATE collaborator SET name = '' WHERE name IS NULL"))
                except Exception:
                    pass
        if changed:
            db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
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

    # Registro de Acessos (pagina e filtra por usuário)
    try:
        acc_user = (request.args.get('acc_user') or '').strip()
    except Exception:
        acc_user = ''
    try:
        acc_page = int(request.args.get('acc_page', '1'))
    except Exception:
        acc_page = 1
    if acc_page < 1:
        acc_page = 1
    aq = SystemLog.query.filter(SystemLog.origem == 'Acesso', SystemLog.evento == 'login')
    if acc_user:
        aq = aq.filter(SystemLog.usuario.ilike(f"%{acc_user}%"))
    access_all = aq.order_by(SystemLog.data.desc()).all()
    per_acc = 10
    acc_total = len(access_all)
    acc_total_pages = max(1, (acc_total + per_acc - 1) // per_acc)
    if acc_page > acc_total_pages:
        acc_page = acc_total_pages
    acc_start = (acc_page - 1) * per_acc
    acc_end = acc_start + per_acc
    access_page = access_all[acc_start:acc_end]

    senha_sugestao = '123456'
    roles = JobRole.query.order_by(JobRole.name.asc()).all()
    colaboradores = Collaborator.query.order_by(Collaborator.name.asc()).all()
    bank_balances = {}
    try:
        from sqlalchemy import func
        sums = db.session.query(HourBankEntry.collaborator_id, func.coalesce(func.sum(HourBankEntry.hours), 0.0)).group_by(HourBankEntry.collaborator_id).all()
        for cid, total in sums:
            bank_balances[int(cid)] = float(total or 0.0)
    except Exception:
        bank_balances = {}
    recent_entries = []
    try:
        recent_entries = HourBankEntry.query.order_by(HourBankEntry.date.desc()).limit(50).all()
    except Exception:
        recent_entries = []
    folgas = []
    try:
        from sqlalchemy import func
        for c in colaboradores:
            credits_sum = db.session.query(func.coalesce(func.sum(LeaveCredit.amount_days), 0)).filter(LeaveCredit.collaborator_id == c.id).scalar() or 0
            assigned_sum = db.session.query(func.coalesce(func.sum(LeaveAssignment.days_used), 0)).filter(LeaveAssignment.collaborator_id == c.id).scalar() or 0
            converted_sum = db.session.query(func.coalesce(func.sum(LeaveConversion.amount_days), 0)).filter(LeaveConversion.collaborator_id == c.id).scalar() or 0
            folgas.append({'collab': c, 'balance': int(credits_sum) - int(assigned_sum) - int(converted_sum)})
    except Exception:
        folgas = []
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
        view=view,
        senha_sugestao=senha_sugestao,
        roles=roles,
        colaboradores=colaboradores,
        folgas=folgas,
        users=all_users,
        bank_balances=bank_balances,
        recent_entries=recent_entries,
        access_page=access_page,
        acc_page=acc_page,
        acc_total_pages=acc_total_pages,
        acc_user=acc_user
    )


@bp.route('/gestao/colaboradores/criar', methods=['POST'])
@login_required
def gestao_colabs_criar():
    if current_user.nivel != 'admin':
        flash('Você não tem permissão para criar colaboradores.', 'danger')
        return redirect(url_for('usuarios.gestao'))
    nome = request.form.get('name', '').strip()
    cargo = request.form.get('role', '').strip()
    try:
        c = Collaborator()
        c.name = nome
        c.role = cargo
        c.active = True
        c.regular_team = (request.form.get('regular_team', '').strip() or None)
        c.sunday_team = (request.form.get('sunday_team', '').strip() or None)
        c.special_team = (request.form.get('special_team', '').strip() or None)
        uid_str = (request.form.get('user_id') or '').strip()
        try:
            c.user_id = int(uid_str) if uid_str else None
        except Exception:
            c.user_id = None
        db.session.add(c)
        db.session.commit()
        flash(f'Colaborador "{c.name}" criado.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao criar colaborador: {e}', 'danger')
    return redirect(url_for('usuarios.gestao'))

@bp.route('/gestao/colaboradores/<int:id>/editar', methods=['POST'])
@login_required
def gestao_colabs_editar(id: int):
    if current_user.nivel != 'admin':
        flash('Você não tem permissão para editar colaboradores.', 'danger')
        return redirect(url_for('usuarios.gestao'))
    c = Collaborator.query.get_or_404(id)
    try:
        c.name = ((request.form.get('name') or c.name or '').strip()) or c.name
        role_in = request.form.get('role')
        c.role = ((role_in or c.role or '').strip()) or None
        active_str = request.form.get('active', 'on') or 'on'
        c.active = True if active_str.lower() in ('on', 'true', '1') else False
        rt_in = request.form.get('regular_team') or (c.regular_team or '')
        st_in = request.form.get('sunday_team') or (c.sunday_team or '')
        xt_in = request.form.get('special_team') or (c.special_team or '')
        c.regular_team = (rt_in.strip() or None) if (rt_in.strip() in ('1','2')) else None
        c.sunday_team = (st_in.strip() or None) if (st_in.strip() in ('1','2')) else None
        c.special_team = (xt_in.strip() or None) if (xt_in.strip() in ('1','2')) else None
        uid_str = (request.form.get('user_id') or '').strip()
        try:
            c.user_id = int(uid_str) if uid_str else None
        except Exception:
            c.user_id = None
        db.session.commit()
        flash('Colaborador atualizado.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar colaborador: {e}', 'danger')
    return redirect(url_for('usuarios.gestao'))

@bp.route('/gestao/colaboradores/<int:id>/excluir', methods=['POST'])
@login_required
def gestao_colabs_excluir(id: int):
    if current_user.nivel != 'admin':
        flash('Apenas Gerente pode excluir colaboradores.', 'danger')
        return redirect(url_for('usuarios.gestao'))
    c = Collaborator.query.get_or_404(id)
    try:
        Shift.query.filter_by(collaborator_id=c.id).delete()
        db.session.delete(c)
        db.session.commit()
        flash('Colaborador excluído.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir colaborador: {e}', 'danger')
    return redirect(url_for('usuarios.gestao'))

@bp.route('/gestao/usuarios/associar', methods=['POST'])
@login_required
def gestao_usuarios_associar():
    if current_user.nivel != 'admin':
        flash('Você não tem permissão para associar usuário a colaborador.', 'danger')
        return redirect(url_for('usuarios.gestao'))
    try:
        uid = int(request.form.get('user_id', '0'))
    except Exception:
        uid = 0
    try:
        cid = int(request.form.get('collaborator_id', '0'))
    except Exception:
        cid = 0
    if uid <= 0:
        flash('Usuário inválido.', 'warning')
        return redirect(url_for('usuarios.gestao'))
    try:
        # Limpa associações anteriores para este usuário
        try:
            Collaborator.query.filter(Collaborator.user_id == uid).update({'user_id': None})
        except Exception:
            pass
        if cid > 0:
            c = Collaborator.query.get(cid)
            if not c:
                flash('Colaborador não encontrado.', 'warning')
                return redirect(url_for('usuarios.gestao'))
            c.user_id = uid
            db.session.add(c)
        db.session.commit()
        flash('Associação atualizada.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao associar: {e}', 'danger')
    return redirect(url_for('usuarios.gestao'))
@bp.route('/gestao/colaboradores/horas/adicionar', methods=['POST'])
@login_required
def gestao_colabs_horas_adicionar():
    if current_user.nivel != 'admin':
        flash('Você não tem permissão para registrar horas.', 'danger')
        return redirect(url_for('usuarios.gestao_colaboradores'))
    cid_str = (request.form.get('collaborator_id', '').strip() or '')
    date_str = (request.form.get('date', '').strip() or '')
    hours_str = (request.form.get('hours', '0').strip() or '0')
    reason = (request.form.get('reason', '').strip() or '')
    try:
        cid = int(cid_str)
        d = datetime.strptime(date_str, '%Y-%m-%d').date()
        h = float(hours_str)
    except Exception:
        flash('Dados inválidos para banco de horas.', 'warning')
        return redirect(url_for('usuarios.gestao_colaboradores'))
    try:
        e = HourBankEntry()
        e.collaborator_id = cid
        e.date = d
        e.hours = h
        e.reason = reason
        db.session.add(e)
        db.session.commit()
        try:
            from sqlalchemy import func
            total_hours = db.session.query(func.coalesce(func.sum(HourBankEntry.hours), 0.0)).filter(HourBankEntry.collaborator_id == cid).scalar() or 0.0
            total_hours = float(total_hours)
            auto_credits = db.session.query(func.coalesce(func.sum(LeaveCredit.amount_days), 0)).filter(LeaveCredit.collaborator_id == cid, LeaveCredit.origin == 'horas').scalar() or 0
            auto_credits = int(auto_credits)
            desired_credits = int(total_hours // 8.0)
            missing = max(0, desired_credits - auto_credits)
            if missing > 0:
                from datetime import date as _date
                for _ in range(missing):
                    lc = LeaveCredit()
                    lc.collaborator_id = cid
                    lc.date = _date.today()
                    lc.amount_days = 1
                    lc.origin = 'horas'
                    lc.notes = 'Crédito automático por 8h no banco de horas'
                    db.session.add(lc)
                db.session.commit()
                flash(f'Horas registradas. Créditos de folga automáticos adicionados: {missing}.', 'success')
            else:
                flash('Horas registradas.', 'success')
        except Exception:
            flash('Horas registradas.', 'success')
    except Exception as ex:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f'Erro ao registrar horas: {ex}', 'danger')
    return redirect(url_for('usuarios.gestao_colaboradores'))

@bp.route('/gestao/colaboradores/horas/excluir/<int:id>', methods=['POST'])
@login_required
def gestao_colabs_horas_excluir(id: int):
    if current_user.nivel != 'admin':
        flash('Apenas Gerente pode excluir lançamentos.', 'danger')
        return redirect(url_for('usuarios.gestao_colaboradores'))
    e = HourBankEntry.query.get_or_404(id)
    try:
        db.session.delete(e)
        db.session.commit()
        flash('Lançamento excluído.', 'danger')
    except Exception as ex:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f'Erro ao excluir lançamento: {ex}', 'danger')
    return redirect(url_for('usuarios.gestao_colaboradores'))

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
