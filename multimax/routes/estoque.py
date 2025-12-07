from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .. import db
from ..models import Produto, Historico
from typing import cast
from datetime import datetime, timedelta, date
from collections import OrderedDict

bp = Blueprint('estoque', __name__)

@bp.route('/estoque')
@login_required
def index():
    search_term = request.args.get('busca', '')
    page = request.args.get('page', 1, type=int)
    ppage = request.args.get('ppage', 1, type=int)
    cat = request.args.get('cat', '').strip().upper()
    allowed = {'CX','PC','VA','AV'}
    produtos_query = Produto.query
    if search_term:
        produtos_query = produtos_query.filter((Produto.codigo.contains(search_term)) | (Produto.nome.contains(search_term)))
    if cat in allowed:
        produtos_query = produtos_query.filter(Produto.codigo.like(f"{cat}-%"))
    produtos_query = produtos_query.order_by(Produto.nome.asc())
    produtos_pag = produtos_query.paginate(page=ppage, per_page=12, error_out=False)
    produtos_all = Produto.query.order_by(Produto.nome.asc()).all()
    historico = Historico.query.order_by(Historico.data.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    ids = [h.product_id for h in historico.items if h.product_id]
    code_map: dict[int, str] = {}
    if ids:
        rows = Produto.query.with_entities(Produto.id, Produto.codigo).filter(Produto.id.in_(ids)).all()
        for pid, cod in rows:
            code_map[int(pid)] = str(cod)
    # gráficos por produto dentro do estoque
    gq = request.args.get('gq', '').strip()
    g_produto_id = request.args.get('g_produto_id', type=int)
    g_data_inicio_str = request.args.get('g_data_inicio', '').strip()
    g_data_fim_str = request.args.get('g_data_fim', '').strip()
    g_produto: Produto | None = None
    g_resultados: list[Produto] = []
    if g_produto_id:
        g_produto = Produto.query.get(g_produto_id)
    elif gq:
        g_resultados = Produto.query.filter(
            (Produto.codigo.contains(gq)) | (Produto.nome.contains(gq))
        ).order_by(Produto.nome.asc()).all()
        if len(g_resultados) == 1:
            g_produto = g_resultados[0]
    def _parse_date_safe(s: str):
        try:
            return datetime.strptime(s, '%Y-%m-%d').date()
        except Exception:
            return None
    g_di = _parse_date_safe(g_data_inicio_str)
    g_df = _parse_date_safe(g_data_fim_str)
    if g_di and g_df and g_di > g_df:
        g_di, g_df = g_df, g_di
    def _fetch_hist(prod_id: int, start_date: date | None = None) -> list[Historico]:
        query = Historico.query.filter_by(product_id=prod_id)
        if start_date:
            query = query.filter(Historico.data >= datetime.combine(start_date, datetime.min.time()))
        return query.order_by(Historico.data.asc()).all()
    def _agg_weekly(prod_id: int, weeks: int = 8):
        end = date.today()
        start = end - timedelta(days=7*weeks)
        hist_w = _fetch_hist(prod_id, start)
        buckets: OrderedDict[str, dict] = OrderedDict()
        cursor = start - timedelta(days=start.weekday())
        while cursor <= end:
            key = f"{cursor.strftime('%Y-%m-%d')}"
            buckets[key] = {'entrada': 0, 'saida': 0, 'label': f"Semana {cursor.strftime('%d/%m')}"}
            cursor += timedelta(days=7)
        for h in hist_w:
            d = h.data.date()
            monday = d - timedelta(days=d.weekday())
            key = monday.strftime('%Y-%m-%d')
            if key in buckets:
                if h.action == 'entrada':
                    buckets[key]['entrada'] += h.quantidade or 0
                elif h.action == 'saida':
                    buckets[key]['saida'] += h.quantidade or 0
        labels = [v['label'] for v in buckets.values()]
        entradas = [v['entrada'] for v in buckets.values()]
        saidas = [v['saida'] for v in buckets.values()]
        return {'labels': labels, 'entrada': entradas, 'saida': saidas}
    def _agg_monthly(prod_id: int, months: int = 12):
        today = date.today()
        buckets: OrderedDict[str, dict] = OrderedDict()
        y, m = today.year, today.month
        for i in range(months-1, -1, -1):
            yy = y
            mm = m - i
            while mm <= 0:
                yy -= 1
                mm += 12
            key = f"{yy}-{mm:02d}"
            buckets[key] = {'entrada': 0, 'saida': 0, 'label': f"{mm:02d}/{yy}"}
        hist_m = _fetch_hist(prod_id)
        for h in hist_m:
            k = h.data.strftime('%Y-%m')
            if k in buckets:
                if h.action == 'entrada':
                    buckets[k]['entrada'] += h.quantidade or 0
                elif h.action == 'saida':
                    buckets[k]['saida'] += h.quantidade or 0
        labels = [v['label'] for v in buckets.values()]
        entradas = [v['entrada'] for v in buckets.values()]
        saidas = [v['saida'] for v in buckets.values()]
        return {'labels': labels, 'entrada': entradas, 'saida': saidas}
    def _agg_yearly(prod_id: int, years: int = 5):
        this_year = date.today().year
        buckets: OrderedDict[str, dict] = OrderedDict()
        for yy in range(this_year - (years-1), this_year + 1):
            key = str(yy)
            buckets[key] = {'entrada': 0, 'saida': 0, 'label': key}
        hist_y = _fetch_hist(prod_id)
        for h in hist_y:
            k = h.data.strftime('%Y')
            if k in buckets:
                if h.action == 'entrada':
                    buckets[k]['entrada'] += h.quantidade or 0
                elif h.action == 'saida':
                    buckets[k]['saida'] += h.quantidade or 0
        labels = [v['label'] for v in buckets.values()]
        entradas = [v['entrada'] for v in buckets.values()]
        saidas = [v['saida'] for v in buckets.values()]
        return {'labels': labels, 'entrada': entradas, 'saida': saidas}
    def _agg_custom(prod_id: int, di: date | None, df: date | None):
        if not di or not df:
            return {'labels': [], 'entrada': [], 'saida': []}
        hist_c: list[Historico] = Historico.query.filter(
            Historico.product_id == prod_id,
            Historico.data >= datetime.combine(di, datetime.min.time()),
            Historico.data <= datetime.combine(df, datetime.max.time())
        ).order_by(Historico.data.asc()).all()
        buckets: OrderedDict[str, dict] = OrderedDict()
        cursor = di
        while cursor <= df:
            key = cursor.strftime('%Y-%m-%d')
            buckets[key] = {'entrada': 0, 'saida': 0, 'label': cursor.strftime('%d/%m')}
            cursor += timedelta(days=1)
        for h in hist_c:
            k = h.data.strftime('%Y-%m-%d')
            if k in buckets:
                if h.action == 'entrada':
                    buckets[k]['entrada'] += h.quantidade or 0
                elif h.action == 'saida':
                    buckets[k]['saida'] += h.quantidade or 0
        labels = [v['label'] for v in buckets.values()]
        entradas = [v['entrada'] for v in buckets.values()]
        saidas = [v['saida'] for v in buckets.values()]
        return {'labels': labels, 'entrada': entradas, 'saida': saidas}
    charts_g = None
    if g_produto:
        charts_g = {
            'weekly': _agg_weekly(g_produto.id),
            'monthly': _agg_monthly(g_produto.id),
            'yearly': _agg_yearly(g_produto.id),
            'custom': _agg_custom(g_produto.id, g_di, g_df),
        }
    return render_template('index.html', produtos_pag=produtos_pag, produtos_all=produtos_all, historico=historico, busca=search_term, cat=cat, hist_code_map=code_map, active_page='index', gq=gq, g_resultados=g_resultados, g_produto=g_produto, charts_g=charts_g, g_data_inicio=g_data_inicio_str, g_data_fim=g_data_fim_str)

@bp.route('/produtos')
@login_required
def lista_produtos():
    produtos: list[Produto] = Produto.query.order_by(Produto.nome.asc()).all()
    return render_template('produtos.html', produtos=produtos, active_page='index')

@bp.route('/produtos/adicionar', methods=['POST'])
@login_required
def adicionar_produto():
    categoria = request.form.get('categoria', 'AV').strip().upper()
    prefix_map = {
        'CX': 'CX',  # Caixas
        'PC': 'PC',  # Pacotes
        'VA': 'VA',  # A vácuo
        'AV': 'AV',  # Avulsos/Não categorizados
    }
    prefix = prefix_map.get(categoria, 'AV')
    def gerar_codigo(pref: str) -> str:
        existentes = cast(list[tuple[str]], Produto.query.with_entities(Produto.codigo).filter(Produto.codigo.like(f"{pref}-%")).all())
        maior = 0
        for (cod,) in existentes:
            try:
                sufixo = cod.split('-', 1)[1]
                num = int(sufixo)
                if num > maior:
                    maior = num
            except Exception:
                continue
        return f"{pref}-{maior+1:04d}"
    codigo = gerar_codigo(prefix)
    nome = request.form.get('nome')
    try:
        quantidade = int(request.form.get('quantidade', '0'))
    except Exception:
        quantidade = 0
    estoque_minimo = int(request.form.get('estoque_minimo', '0'))
    preco_custo = float(request.form.get('preco_custo', '0'))
    preco_venda = float(request.form.get('preco_venda', '0'))
    novo = Produto()
    novo.codigo = codigo
    novo.nome = nome
    novo.quantidade = quantidade
    novo.estoque_minimo = estoque_minimo
    novo.preco_custo = preco_custo
    novo.preco_venda = preco_venda
    db.session.add(novo)
    db.session.commit()
    if quantidade > 0:
        hist = Historico()
        hist.product_id = novo.id
        hist.product_name = novo.nome
        hist.action = 'entrada'
        hist.quantidade = quantidade
        hist.details = 'Cadastro inicial'
        hist.usuario = current_user.username
        db.session.add(hist)
        db.session.commit()
    flash('Produto cadastrado com sucesso!', 'success')
    return redirect(url_for('estoque.lista_produtos'))

@bp.route('/produtos/editar/<int:id>', methods=['POST'])
@login_required
def editar_produto(id: int):
    produto = Produto.query.get_or_404(id)
    produto.nome = request.form.get('nome')
    produto.estoque_minimo = int(request.form.get('estoque_minimo', '0'))
    produto.preco_custo = float(request.form.get('preco_custo', str(produto.preco_custo)))
    produto.preco_venda = float(request.form.get('preco_venda', str(produto.preco_venda)))
    try:
        if produto.quantidade == 0:
            novo_codigo = request.form.get('codigo')
            if novo_codigo:
                produto.codigo = novo_codigo
    except Exception:
        pass
    db.session.commit()
    flash('Produto atualizado!', 'success')
    return redirect(url_for('estoque.lista_produtos'))

@bp.route('/produtos/excluir/<int:id>')
@login_required
def excluir_produto(id: int):
    produto = Produto.query.get_or_404(id)
    db.session.delete(produto)
    db.session.commit()
    flash('Produto removido.', 'info')
    return redirect(url_for('estoque.lista_produtos'))

@bp.route('/produtos/entrada/<int:id>', methods=['POST'])
@login_required
def entrada_produto(id: int):
    produto = Produto.query.get_or_404(id)
    qtd = int(request.form.get('quantidade', '0'))
    produto.quantidade += qtd
    db.session.commit()
    hist = Historico()
    hist.product_id = produto.id
    hist.product_name = produto.nome
    hist.action = 'entrada'
    hist.quantidade = qtd
    hist.details = request.form.get('detalhes')
    hist.usuario = current_user.username
    db.session.add(hist)
    db.session.commit()
    flash('Entrada registrada!', 'success')
    return redirect(url_for('estoque.lista_produtos'))

@bp.route('/produtos/saida/<int:id>', methods=['POST'])
@login_required
def saida_produto(id: int):
    produto = Produto.query.get_or_404(id)
    qtd = int(request.form.get('quantidade', '0'))
    if produto.quantidade < qtd:
        flash('Quantidade insuficiente em estoque.', 'danger')
        return redirect(url_for('estoque.lista_produtos'))
    produto.quantidade -= qtd
    db.session.commit()
    hist = Historico()
    hist.product_id = produto.id
    hist.product_name = produto.nome
    hist.action = 'saida'
    hist.quantidade = qtd
    hist.details = request.form.get('detalhes')
    hist.usuario = current_user.username
    db.session.add(hist)
    db.session.commit()
    flash('Saída registrada!', 'warning')
    return redirect(url_for('estoque.lista_produtos'))

@bp.route('/adicionar', methods=['POST'])
@login_required
def adicionar():
    if current_user.nivel not in ['operador', 'admin']:
        flash('Você não tem permissão para adicionar produtos.', 'danger')
        return redirect(url_for('estoque.index'))
    try:
        if Produto.query.filter_by(nome=request.form['nome']).first():
            flash(f'Produto com o nome "{request.form["nome"]}" já existe.', 'danger')
            return redirect(url_for('estoque.index'))
        categoria = request.form.get('categoria', 'AV').strip().upper()
        prefix_map = {
            'CX': 'CX',
            'PC': 'PC',
            'VA': 'VA',
            'AV': 'AV',
        }
        prefix = prefix_map.get(categoria, 'AV')
        def gerar_codigo(pref: str) -> str:
            existentes = cast(list[tuple[str]], Produto.query.with_entities(Produto.codigo).filter(Produto.codigo.like(f"{pref}-%")).all())
            maior = 0
            for (cod,) in existentes:
                try:
                    sufixo = cod.split('-', 1)[1]
                    num = int(sufixo)
                    if num > maior:
                        maior = num
                except Exception:
                    continue
            return f"{pref}-{maior+1:04d}"
        proximo_codigo = gerar_codigo(prefix)
        new_produto = Produto()
        new_produto.codigo = proximo_codigo
        new_produto.nome = request.form['nome']
        new_produto.quantidade = int(request.form['quantidade'])
        new_produto.estoque_minimo = int(request.form['estoque_minimo'])
        new_produto.preco_custo = float(request.form.get('preco_custo', '0'))
        new_produto.preco_venda = float(request.form.get('preco_venda', '0'))
        db.session.add(new_produto)
        db.session.flush()
        if new_produto.quantidade > 0:
            hist = Historico()
            hist.product_id = new_produto.id
            hist.product_name = new_produto.nome
            hist.action = 'entrada'
            hist.quantidade = new_produto.quantidade
            hist.details = 'Estoque inicial adicionado'
            hist.usuario = current_user.username
            db.session.add(hist)
        db.session.commit()
        flash(f'Produto "{new_produto.nome}" adicionado com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao adicionar produto: {e}', 'danger')
    return redirect(url_for('estoque.index'))

@bp.route('/entrada/<int:id>', methods=['POST'])
@login_required
def entrada(id: int):
    if current_user.nivel not in ['operador', 'admin']:
        flash('Você não tem permissão para registrar entrada.', 'danger')
        return redirect(url_for('estoque.index'))
    produto = Produto.query.get_or_404(id)
    try:
        quantidade = int(request.form['quantidade'])
        if quantidade <= 0:
            flash('A quantidade deve ser positiva.', 'warning')
            return redirect(url_for('estoque.index'))
        produto.quantidade += quantidade
        hist = Historico()
        hist.product_id = produto.id
        hist.product_name = produto.nome
        hist.action = 'entrada'
        hist.quantidade = quantidade
        hist.details = 'Entrada de estoque'
        hist.usuario = current_user.username
        db.session.add(hist)
        db.session.commit()
        flash(f'Registrada entrada de {quantidade} unidades de "{produto.nome}".', 'primary')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao registrar entrada: {e}', 'danger')
    return redirect(url_for('estoque.index'))

@bp.route('/saida/<int:id>', methods=['POST'])
@login_required
def saida(id: int):
    if current_user.nivel not in ['operador', 'admin']:
        flash('Você não tem permissão para registrar saída.', 'danger')
        return redirect(url_for('estoque.index'))
    produto = Produto.query.get_or_404(id)
    try:
        quantidade = int(request.form['quantidade'])
        if quantidade <= 0:
            flash('A quantidade deve ser positiva.', 'warning')
            return redirect(url_for('estoque.index'))
        if quantidade > produto.quantidade:
            flash(f'Saída de {quantidade} unidades excede o estoque atual ({produto.quantidade}).', 'warning')
            return redirect(url_for('estoque.index'))
        produto.quantidade -= quantidade
        hist = Historico()
        hist.product_id = produto.id
        hist.product_name = produto.nome
        hist.action = 'saida'
        hist.quantidade = quantidade
        hist.details = 'Saída de estoque (Venda/Uso)'
        hist.usuario = current_user.username
        db.session.add(hist)
        db.session.commit()
        flash(f'Registrada saída de {quantidade} unidades de "{produto.nome}".', 'warning')
        if produto.quantidade <= produto.estoque_minimo:
            flash(f'ALERTA: O estoque de "{produto.nome}" está abaixo do nível mínimo!', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao registrar saída: {e}', 'danger')
    return redirect(url_for('estoque.index'))

@bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id: int):
    if current_user.nivel not in ['operador', 'admin']:
        flash('Você não tem permissão para editar produtos.', 'danger')
        return redirect(url_for('estoque.index'))
    produto = Produto.query.get_or_404(id)
    if request.method == 'POST':
        try:
            produto.nome = request.form['nome']
            produto.estoque_minimo = int(request.form['estoque_minimo'])
            db.session.commit()
            flash(f'Produto "{produto.nome}" atualizado com sucesso!', 'info')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao editar produto: {e}', 'danger')
        return redirect(url_for('estoque.index'))
    return render_template('editar_produto.html', produto=produto, active_page='index')

@bp.route('/excluir/<int:id>')
@login_required
def excluir(id: int):
    if current_user.nivel != 'admin':
        flash('Você não tem permissão para excluir produtos.', 'danger')
        return redirect(url_for('estoque.index'))
    produto = Produto.query.get_or_404(id)
    try:
        Historico.query.filter_by(product_id=id).delete()
        db.session.delete(produto)
        db.session.commit()
        flash(f'Produto "{produto.nome}" excluído com sucesso!', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir produto: {e}', 'danger')
    return redirect(url_for('estoque.index'))

@bp.route('/produtos/<int:id>/minimo', methods=['POST'])
@login_required
def atualizar_minimo(id: int):
    if current_user.nivel not in ['operador', 'admin']:
        flash('Você não tem permissão para atualizar estoque mínimo.', 'danger')
        return redirect(url_for('estoque.index'))
    produto = Produto.query.get_or_404(id)
    try:
        novo_min = int(request.form.get('novo_minimo', str(produto.estoque_minimo)))
        if novo_min < 0:
            novo_min = 0
        produto.estoque_minimo = novo_min
        db.session.commit()
        flash(f'Estoque mínimo de "{produto.nome}" atualizado para {novo_min}.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar estoque mínimo: {e}', 'danger')
    return redirect(request.form.get('next') or url_for('estoque.index'))
@bp.route('/gerenciar', methods=['POST'])
@login_required
def gerenciar():
    if current_user.nivel not in ['operador', 'admin']:
        flash('Você não tem permissão para gerenciar estoque.', 'danger')
        return redirect(url_for('estoque.index'))
    op = (request.form.get('op') or '').strip().lower()
    try:
        pid = int(request.form.get('product_id', '0'))
    except Exception:
        pid = 0
    if pid <= 0:
        flash('Produto inválido.', 'danger')
        return redirect(url_for('estoque.index'))
    produto = Produto.query.get_or_404(pid)
    if op in ('entrada','saida'):
        try:
            quantidade = int(request.form.get('quantidade', '0'))
        except Exception:
            quantidade = 0
        if quantidade <= 0:
            flash('A quantidade deve ser positiva.', 'warning')
            return redirect(url_for('estoque.index'))
        if op == 'saida' and quantidade > produto.quantidade:
            flash(f'Saída de {quantidade} unidades excede o estoque atual ({produto.quantidade}).', 'warning')
            return redirect(url_for('estoque.index'))
        if op == 'entrada':
            produto.quantidade += quantidade
        else:
            produto.quantidade -= quantidade
        hist = Historico()
        hist.product_id = produto.id
        hist.product_name = produto.nome
        hist.action = 'entrada' if op == 'entrada' else 'saida'
        hist.quantidade = quantidade
        hist.details = (request.form.get('detalhes') or '').strip() or ('Entrada de estoque' if op=='entrada' else 'Saída de estoque')
        hist.usuario = current_user.username
        db.session.add(hist)
        db.session.commit()
        flash(f"{('Entrada' if op=='entrada' else 'Saída')} registrada para \"{produto.nome}\".", 'success' if op=='entrada' else 'warning')
        if op == 'saida' and produto.quantidade <= produto.estoque_minimo:
            flash(f'ALERTA: O estoque de "{produto.nome}" está abaixo do nível mínimo!', 'danger')
        return redirect(url_for('estoque.index'))
    if op == 'excluir':
        if current_user.nivel != 'admin':
            flash('Você não tem permissão para excluir produtos.', 'danger')
            return redirect(url_for('estoque.index'))
        try:
            Historico.query.filter_by(product_id=produto.id).delete()
            db.session.delete(produto)
            db.session.commit()
            flash(f'Produto "{produto.nome}" excluído.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao excluir produto: {e}', 'danger')
        return redirect(url_for('estoque.index'))
    flash('Operação inválida.', 'danger')
    return redirect(url_for('estoque.index'))
