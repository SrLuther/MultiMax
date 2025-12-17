from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required
from .. import db
from ..models import Recipe, RecipeIngredient, Produto

bp = Blueprint('receitas', __name__, url_prefix='/receitas')

def _calcular_custo_receita(receita_id):
    ingredientes = RecipeIngredient.query.filter_by(recipe_id=receita_id).all()
    custo_total = 0.0
    for ing in ingredientes:
        if ing.produto_id:
            produto = Produto.query.get(ing.produto_id)
            if produto and produto.preco_custo:
                custo_ing = (ing.quantidade_kg or 0) * produto.preco_custo
                ing.custo_unitario = custo_ing
                custo_total += custo_ing
        elif ing.custo_unitario:
            custo_total += ing.custo_unitario
    return custo_total

@bp.route('/', methods=['GET', 'POST'], strict_slashes=False)
@login_required
def index():
    if request.method == 'POST':
        nome = (request.form.get('nome') or '').strip()
        embalagem = (request.form.get('embalagem') or '').strip()
        preparo = (request.form.get('preparo') or '').strip()
        if not nome:
            flash('Informe o nome da receita.', 'warning')
            return redirect(url_for('receitas.index'))
        r = Recipe()
        r.nome = nome
        r.embalagem = embalagem
        r.preparo = preparo
        db.session.add(r)
        db.session.flush()
        nomes = request.form.getlist('ing_nome[]')
        qtds = request.form.getlist('ing_qtd[]')
        produto_ids = request.form.getlist('ing_produto_id[]')
        qtds_kg = request.form.getlist('ing_qtd_kg[]')
        for i in range(0, max(len(nomes), len(qtds))):
            n = (nomes[i] if i < len(nomes) else '').strip()
            q = (qtds[i] if i < len(qtds) else '').strip()
            if not n:
                continue
            it = RecipeIngredient()
            it.recipe_id = r.id
            it.nome = n
            it.quantidade = q
            if i < len(produto_ids) and produto_ids[i]:
                try:
                    it.produto_id = int(produto_ids[i])
                except:
                    pass
            if i < len(qtds_kg) and qtds_kg[i]:
                try:
                    it.quantidade_kg = float(qtds_kg[i].replace(',', '.'))
                except:
                    pass
            if it.produto_id:
                produto = Produto.query.get(it.produto_id)
                if produto and produto.preco_custo:
                    it.custo_unitario = (it.quantidade_kg or 0) * produto.preco_custo
            db.session.add(it)
        db.session.commit()
        flash('Receita cadastrada com sucesso.', 'success')
        return redirect(url_for('receitas.index'))
    rid = request.args.get('id', type=int)
    q = (request.args.get('q') or '').strip()
    page = request.args.get('page', 1, type=int)
    query = Recipe.query
    if q:
        query = query.filter(Recipe.nome.contains(q))
    query = query.order_by(Recipe.created_at.desc())
    per_page = int(current_app.config.get('PER_PAGE', 10))
    receitas_pag = query.paginate(page=page, per_page=per_page, error_out=False)
    selecionada = None
    ingredientes = []
    custo_total = 0.0
    if rid:
        selecionada = Recipe.query.get(rid)
        if selecionada:
            ingredientes = RecipeIngredient.query.filter_by(recipe_id=selecionada.id).order_by(RecipeIngredient.id.asc()).all()
            custo_total = _calcular_custo_receita(selecionada.id)
    produtos = Produto.query.order_by(Produto.nome.asc()).all()
    return render_template('receitas.html', active_page='receitas', receitas=receitas_pag.items, receitas_pag=receitas_pag, selecionada=selecionada, ingredientes=ingredientes, q=q, produtos=produtos, custo_total=custo_total)

@bp.route('/editar/<int:id>', methods=['POST'], strict_slashes=False)
@login_required
def editar(id: int):
    r = Recipe.query.get_or_404(id)
    nome = (request.form.get('nome') or r.nome or '').strip()
    embalagem = (request.form.get('embalagem') or r.embalagem or '').strip()
    preparo = (request.form.get('preparo') or r.preparo or '').strip()
    if not nome:
        flash('Informe o nome da receita.', 'warning')
        return redirect(url_for('receitas.index', id=id))
    try:
        r.nome = nome
        r.embalagem = embalagem
        r.preparo = preparo
        RecipeIngredient.query.filter_by(recipe_id=r.id).delete()
        nomes = request.form.getlist('ing_nome[]')
        qtds = request.form.getlist('ing_qtd[]')
        produto_ids = request.form.getlist('ing_produto_id[]')
        qtds_kg = request.form.getlist('ing_qtd_kg[]')
        for i in range(0, max(len(nomes), len(qtds))):
            n = (nomes[i] if i < len(nomes) else '').strip()
            q = (qtds[i] if i < len(qtds) else '').strip()
            if not n:
                continue
            it = RecipeIngredient()
            it.recipe_id = r.id
            it.nome = n
            it.quantidade = q
            if i < len(produto_ids) and produto_ids[i]:
                try:
                    it.produto_id = int(produto_ids[i])
                except:
                    pass
            if i < len(qtds_kg) and qtds_kg[i]:
                try:
                    it.quantidade_kg = float(qtds_kg[i].replace(',', '.'))
                except:
                    pass
            if it.produto_id:
                produto = Produto.query.get(it.produto_id)
                if produto and produto.preco_custo:
                    it.custo_unitario = (it.quantidade_kg or 0) * produto.preco_custo
            db.session.add(it)
        db.session.commit()
        flash('Receita atualizada.', 'success')
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f'Erro ao atualizar receita: {e}', 'danger')
    return redirect(url_for('receitas.index', id=id))

@bp.route('/duplicar/<int:id>', methods=['POST'], strict_slashes=False)
@login_required
def duplicar(id: int):
    r = Recipe.query.get_or_404(id)
    try:
        novo = Recipe()
        novo.nome = f"{r.nome} (copia)"
        novo.embalagem = r.embalagem
        novo.preparo = r.preparo
        db.session.add(novo)
        db.session.flush()
        ings = RecipeIngredient.query.filter_by(recipe_id=r.id).all()
        for ing in ings:
            ni = RecipeIngredient()
            ni.recipe_id = novo.id
            ni.nome = ing.nome
            ni.quantidade = ing.quantidade
            ni.produto_id = ing.produto_id
            ni.quantidade_kg = ing.quantidade_kg
            ni.custo_unitario = ing.custo_unitario
            db.session.add(ni)
        db.session.commit()
        flash('Receita duplicada.', 'success')
        q = (request.form.get('q') or '').strip()
        page = request.form.get('page', '1').strip()
        return redirect(url_for('receitas.index', id=novo.id, q=q or None, page=page))
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f'Erro ao duplicar receita: {e}', 'danger')
        q = (request.form.get('q') or '').strip()
        page = request.form.get('page', '1').strip()
        return redirect(url_for('receitas.index', id=id, q=q or None, page=page))

@bp.route('/excluir/<int:id>', methods=['POST'], strict_slashes=False)
@login_required
def excluir(id: int):
    r = Recipe.query.get_or_404(id)
    try:
        RecipeIngredient.query.filter_by(recipe_id=r.id).delete()
        db.session.delete(r)
        db.session.commit()
        flash('Receita excluida.', 'danger')
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f'Erro ao excluir receita: {e}', 'danger')
    q = (request.form.get('q') or '').strip()
    page = request.form.get('page', '1').strip()
    return redirect(url_for('receitas.index', q=q or None, page=page))
