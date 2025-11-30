from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from .. import db
from ..models import User, Produto, Historico
from datetime import datetime, timedelta, date
from collections import defaultdict, OrderedDict

bp = Blueprint('usuarios', __name__)

@bp.route('/users', methods=['GET', 'POST'])
@login_required
def users():
    if current_user.nivel != 'admin':
        flash('Acesso negado. Apenas Administradores podem gerenciar usuários.', 'danger')
        return redirect(url_for('estoque.index'))
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '').strip()
        nivel = request.form.get('nivel', 'visualizador').strip()
        if not name or not password:
            flash('Nome e senha são obrigatórios.', 'warning')
            return redirect(url_for('usuarios.users'))
        base_username = ''.join(ch for ch in name.lower() if ch.isalnum()) or 'user'
        username = base_username
        suffix = 1
        while User.query.filter_by(username=username).first() is not None:
            username = f"{base_username}{suffix}"
            suffix += 1
        new_user = User(name=name, username=username, nivel=nivel)
        new_user.password_hash = generate_password_hash(password)
        try:
            db.session.add(new_user)
            db.session.commit()
            flash(f'Usuário "{name}" criado com login "{username}".', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar usuário: {e}', 'danger')
        return redirect(url_for('usuarios.users'))
    all_users = User.query.all()
    senha_sugestao = '123456'
    return render_template('users.html', users=all_users, active_page='users', senha_sugestao=senha_sugestao)

@bp.route('/graficos')
@login_required
def graficos():
    q = request.args.get('q', '').strip()
    produto_id = request.args.get('produto_id', type=int)
    data_inicio_str = request.args.get('data_inicio', '').strip()
    data_fim_str = request.args.get('data_fim', '').strip()

    produto = None
    resultados = []
    if produto_id:
        produto = Produto.query.get(produto_id)
    elif q:
        resultados = Produto.query.filter(
            (Produto.codigo.contains(q)) | (Produto.nome.contains(q))
        ).order_by(Produto.nome.asc()).all()
        if len(resultados) == 1:
            produto = resultados[0]

    def parse_date_safe(s):
        try:
            return datetime.strptime(s, '%Y-%m-%d').date()
        except Exception:
            return None

    data_inicio = parse_date_safe(data_inicio_str)
    data_fim = parse_date_safe(data_fim_str)
    if data_inicio and data_fim and data_inicio > data_fim:
        data_inicio, data_fim = data_fim, data_inicio

    def _fetch_hist(prod_id, start_date=None):
        query = Historico.query.filter_by(product_id=prod_id)
        if start_date:
            query = query.filter(Historico.data >= datetime.combine(start_date, datetime.min.time()))
        return query.order_by(Historico.data.asc()).all()

    def _agg_weekly(prod_id, weeks=8):
        end = date.today()
        start = end - timedelta(days=7*weeks)
        hist = _fetch_hist(prod_id, start)
        buckets = OrderedDict()
        # Fill buckets for each week starting Monday
        cursor = start - timedelta(days=start.weekday())
        while cursor <= end:
            key = f"{cursor.strftime('%Y-%m-%d')}"
            buckets[key] = {'entrada': 0, 'saida': 0, 'label': f"Semana {cursor.strftime('%d/%m')}"}
            cursor += timedelta(days=7)
        for h in hist:
            d = h.data.date()
            monday = d - timedelta(days=d.weekday())
            key = monday.strftime('%Y-%m-%d')
            if key in buckets:
                buckets[key][h.action] = buckets[key].get(h.action, 0) + (h.quantidade or 0)
        labels = [v['label'] for v in buckets.values()]
        entradas = [v['entrada'] for v in buckets.values()]
        saidas = [v['saida'] for v in buckets.values()]
        return {'labels': labels, 'entrada': entradas, 'saida': saidas}

    def _agg_monthly(prod_id, months=12):
        today = date.today()
        # Build month list
        buckets = OrderedDict()
        y, m = today.year, today.month
        for i in range(months-1, -1, -1):
            yy = y
            mm = m - i
            while mm <= 0:
                yy -= 1
                mm += 12
            key = f"{yy}-{mm:02d}"
            buckets[key] = {'entrada': 0, 'saida': 0, 'label': f"{mm:02d}/{yy}"}
        hist = _fetch_hist(prod_id)
        for h in hist:
            k = h.data.strftime('%Y-%m')
            if k in buckets:
                buckets[k][h.action] = buckets[k].get(h.action, 0) + (h.quantidade or 0)
        labels = [v['label'] for v in buckets.values()]
        entradas = [v['entrada'] for v in buckets.values()]
        saidas = [v['saida'] for v in buckets.values()]
        return {'labels': labels, 'entrada': entradas, 'saida': saidas}

    def _agg_yearly(prod_id, years=5):
        this_year = date.today().year
        buckets = OrderedDict()
        for yy in range(this_year - (years-1), this_year + 1):
            key = str(yy)
            buckets[key] = {'entrada': 0, 'saida': 0, 'label': key}
        hist = _fetch_hist(prod_id)
        for h in hist:
            k = h.data.strftime('%Y')
            if k in buckets:
                buckets[k][h.action] = buckets[k].get(h.action, 0) + (h.quantidade or 0)
        labels = [v['label'] for v in buckets.values()]
        entradas = [v['entrada'] for v in buckets.values()]
        saidas = [v['saida'] for v in buckets.values()]
        return {'labels': labels, 'entrada': entradas, 'saida': saidas}

    def _agg_custom(prod_id, di, df):
        if not di or not df:
            return {'labels': [], 'entrada': [], 'saida': []}
        hist = Historico.query.filter(
            Historico.product_id == prod_id,
            Historico.data >= datetime.combine(di, datetime.min.time()),
            Historico.data <= datetime.combine(df, datetime.max.time())
        ).order_by(Historico.data.asc()).all()
        buckets = OrderedDict()
        cursor = di
        while cursor <= df:
            key = cursor.strftime('%Y-%m-%d')
            buckets[key] = {'entrada': 0, 'saida': 0, 'label': cursor.strftime('%d/%m')}
            cursor += timedelta(days=1)
        for h in hist:
            k = h.data.strftime('%Y-%m-%d')
            if k in buckets:
                buckets[k][h.action] = buckets[k].get(h.action, 0) + (h.quantidade or 0)
        labels = [v['label'] for v in buckets.values()]
        entradas = [v['entrada'] for v in buckets.values()]
        saidas = [v['saida'] for v in buckets.values()]
        return {'labels': labels, 'entrada': entradas, 'saida': saidas}

    charts = None
    if produto:
        charts = {
            'weekly': _agg_weekly(produto.id),
            'monthly': _agg_monthly(produto.id),
            'yearly': _agg_yearly(produto.id),
            'custom': _agg_custom(produto.id, data_inicio, data_fim),
        }

    return render_template(
        'graficos.html',
        active_page='graficos',
        q=q,
        resultados=resultados,
        produto=produto,
        charts=charts,
        data_inicio=data_inicio_str,
        data_fim=data_fim_str,
    )

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
        db.session.commit()
        flash(f'Usuário "{user.name}" excluído com sucesso.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir usuário: {e}', 'danger')
    return redirect(url_for('usuarios.users'))
