from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .. import db
from ..models import Produto, Historico

bp = Blueprint('estoque', __name__)

@bp.route('/')
@login_required
def index():
    search_term = request.args.get('busca', '')
    page = request.args.get('page', 1, type=int)
    if search_term:
        produtos_query = Produto.query.filter(
            (Produto.codigo.contains(search_term)) | (Produto.nome.contains(search_term))
        ).order_by(Produto.id.desc())
    else:
        produtos_query = Produto.query.order_by(Produto.id.desc())
    produtos = produtos_query.all()
    historico = Historico.query.order_by(Historico.data.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    return render_template('index.html', produtos=produtos, historico=historico, busca=search_term, active_page='index')

@bp.route('/produtos')
@login_required
def lista_produtos():
    produtos = Produto.query.order_by(Produto.nome.asc()).all()
    return render_template('produtos.html', produtos=produtos, active_page='index')

@bp.route('/produtos/adicionar', methods=['POST'])
@login_required
def adicionar_produto():
    codigo = request.form.get('codigo')
    nome = request.form.get('nome')
    quantidade = int(request.form.get('quantidade', 0))
    estoque_minimo = int(request.form.get('estoque_minimo', 0))
    preco_custo = float(request.form.get('preco_custo', 0))
    preco_venda = float(request.form.get('preco_venda', 0))
    novo = Produto(
        codigo=codigo,
        nome=nome,
        quantidade=quantidade,
        estoque_minimo=estoque_minimo,
        preco_custo=preco_custo,
        preco_venda=preco_venda
    )
    db.session.add(novo)
    db.session.commit()
    hist = Historico(product_id=novo.id, product_name=novo.nome, action='entrada', quantidade=quantidade, details='Cadastro inicial', usuario=current_user.username)
    db.session.add(hist)
    db.session.commit()
    flash('Produto cadastrado com sucesso!', 'success')
    return redirect(url_for('estoque.lista_produtos'))

@bp.route('/produtos/editar/<int:id>', methods=['POST'])
@login_required
def editar_produto(id):
    produto = Produto.query.get_or_404(id)
    produto.codigo = request.form.get('codigo')
    produto.nome = request.form.get('nome')
    produto.estoque_minimo = int(request.form.get('estoque_minimo'))
    produto.preco_custo = float(request.form.get('preco_custo'))
    produto.preco_venda = float(request.form.get('preco_venda'))
    db.session.commit()
    flash('Produto atualizado!', 'success')
    return redirect(url_for('estoque.lista_produtos'))

@bp.route('/produtos/excluir/<int:id>')
@login_required
def excluir_produto(id):
    produto = Produto.query.get_or_404(id)
    db.session.delete(produto)
    db.session.commit()
    flash('Produto removido.', 'info')
    return redirect(url_for('estoque.lista_produtos'))

@bp.route('/produtos/entrada/<int:id>', methods=['POST'])
@login_required
def entrada_produto(id):
    produto = Produto.query.get_or_404(id)
    qtd = int(request.form.get('quantidade'))
    produto.quantidade += qtd
    db.session.commit()
    hist = Historico(product_id=produto.id, product_name=produto.nome, action='entrada', quantidade=qtd, details=request.form.get('detalhes'), usuario=current_user.username)
    db.session.add(hist)
    db.session.commit()
    flash('Entrada registrada!', 'success')
    return redirect(url_for('estoque.lista_produtos'))

@bp.route('/produtos/saida/<int:id>', methods=['POST'])
@login_required
def saida_produto(id):
    produto = Produto.query.get_or_404(id)
    qtd = int(request.form.get('quantidade'))
    if produto.quantidade < qtd:
        flash('Quantidade insuficiente em estoque.', 'danger')
        return redirect(url_for('estoque.lista_produtos'))
    produto.quantidade -= qtd
    db.session.commit()
    hist = Historico(product_id=produto.id, product_name=produto.nome, action='saida', quantidade=qtd, details=request.form.get('detalhes'), usuario=current_user.username)
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
        proximo_codigo = Produto.query.count() + 1
        new_produto = Produto(
            codigo=str(proximo_codigo).zfill(4),
            nome=request.form['nome'],
            quantidade=int(request.form['quantidade']),
            estoque_minimo=int(request.form['estoque_minimo']),
            preco_custo=float(request.form['preco_custo']),
            preco_venda=float(request.form['preco_venda'])
        )
        db.session.add(new_produto)
        db.session.flush()
        if new_produto.quantidade > 0:
            hist = Historico(product_id=new_produto.id, product_name=new_produto.nome, action='entrada', quantidade=new_produto.quantidade, details='Estoque inicial adicionado', usuario=current_user.name)
            db.session.add(hist)
        db.session.commit()
        flash(f'Produto "{new_produto.nome}" adicionado com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao adicionar produto: {e}', 'danger')
    return redirect(url_for('estoque.index'))

@bp.route('/entrada/<int:id>', methods=['POST'])
@login_required
def entrada(id):
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
        hist = Historico(product_id=produto.id, product_name=produto.nome, action='entrada', quantidade=quantidade, details='Entrada de estoque', usuario=current_user.name)
        db.session.add(hist)
        db.session.commit()
        flash(f'Registrada entrada de {quantidade} unidades de "{produto.nome}".', 'primary')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao registrar entrada: {e}', 'danger')
    return redirect(url_for('estoque.index'))

@bp.route('/saida/<int:id>', methods=['POST'])
@login_required
def saida(id):
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
        hist = Historico(product_id=produto.id, product_name=produto.nome, action='saida', quantidade=quantidade, details='Saída de estoque (Venda/Uso)', usuario=current_user.name)
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
def editar(id):
    if current_user.nivel not in ['operador', 'admin']:
        flash('Você não tem permissão para editar produtos.', 'danger')
        return redirect(url_for('estoque.index'))
    produto = Produto.query.get_or_404(id)
    if request.method == 'POST':
        try:
            produto.nome = request.form['nome']
            produto.estoque_minimo = int(request.form['estoque_minimo'])
            produto.preco_custo = float(request.form['preco_custo'])
            produto.preco_venda = float(request.form['preco_venda'])
            db.session.commit()
            flash(f'Produto "{produto.nome}" atualizado com sucesso!', 'info')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao editar produto: {e}', 'danger')
        return redirect(url_for('estoque.index'))
    return render_template('editar_produto.html', produto=produto, active_page='index')

@bp.route('/excluir/<int:id>')
@login_required
def excluir(id):
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

