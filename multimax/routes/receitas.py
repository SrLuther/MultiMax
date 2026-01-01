from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required
from .. import db
from ..models import Recipe, RecipeIngredient, Produto, IngredientCatalog

bp = Blueprint('receitas', __name__, url_prefix='/receitas')

# ============================================================================
# Funções auxiliares
# ============================================================================

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

def _get_receitas_filtradas(q: str = '', page: int = 1, per_page: int = 10):
    """Busca receitas com filtro e paginação"""
    query = Recipe.query
    if q:
        query = query.filter(Recipe.nome.contains(q))
    query = query.order_by(Recipe.created_at.desc())
    return query.paginate(page=page, per_page=per_page, error_out=False)


def _get_receita_detalhes(rid: int) -> tuple[Recipe | None, list, float]:
    """Busca detalhes de uma receita (receita, ingredientes, custo)"""
    selecionada = Recipe.query.get(rid)
    if not selecionada:
        return None, [], 0.0
    
    ingredientes = RecipeIngredient.query.filter_by(recipe_id=selecionada.id).order_by(RecipeIngredient.id.asc()).all()
    custo_total = _calcular_custo_receita(selecionada.id)
    
    return selecionada, ingredientes, custo_total


# ============================================================================
# Rotas
# ============================================================================

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
                except Exception:
                    pass
            if i < len(qtds_kg) and qtds_kg[i]:
                try:
                    it.quantidade_kg = float(qtds_kg[i].replace(',', '.'))
                except Exception:
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
    
    receitas_pag = _get_receitas_filtradas(q, page)
    selecionada, ingredientes, custo_total = _get_receita_detalhes(rid) if rid else (None, [], 0.0)
    produtos = Produto.query.order_by(Produto.nome.asc()).all()
    
    return render_template(
        'receitas.html',
        active_page='receitas',
        receitas=receitas_pag.items,
        receitas_pag=receitas_pag,
        selecionada=selecionada,
        ingredientes=ingredientes,
        q=q,
        produtos=produtos,
        custo_total=custo_total
    )

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
                except Exception:
                    pass
            if i < len(qtds_kg) and qtds_kg[i]:
                try:
                    it.quantidade_kg = float(qtds_kg[i].replace(',', '.'))
                except Exception:
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


@bp.route('/catalogo', methods=['GET', 'POST'], strict_slashes=False)
@login_required
def catalogo():
    if request.method == 'POST':
        nome = (request.form.get('nome') or '').strip()
        categoria = (request.form.get('categoria') or '').strip()
        unidade = (request.form.get('unidade_padrao') or 'kg').strip()
        
        if not nome:
            flash('Informe o nome do ingrediente.', 'warning')
            return redirect(url_for('receitas.catalogo'))
        
        existente = IngredientCatalog.query.filter_by(nome=nome).first()
        if existente:
            flash('Ingrediente já cadastrado.', 'warning')
            return redirect(url_for('receitas.catalogo'))
        
        try:
            ing = IngredientCatalog()
            ing.nome = nome
            ing.categoria = categoria
            ing.unidade_padrao = unidade
            db.session.add(ing)
            db.session.commit()
            flash('Ingrediente cadastrado!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro: {e}', 'danger')
        
        return redirect(url_for('receitas.catalogo'))
    
    q = (request.args.get('q') or '').strip()
    cat = (request.args.get('categoria') or '').strip()
    
    query = IngredientCatalog.query.filter_by(ativo=True)
    if q:
        query = query.filter(IngredientCatalog.nome.ilike(f'%{q}%'))
    if cat:
        query = query.filter_by(categoria=cat)
    
    ingredientes = query.order_by(IngredientCatalog.nome.asc()).all()
    
    categorias = db.session.query(IngredientCatalog.categoria).filter(
        IngredientCatalog.ativo.is_(True),
        IngredientCatalog.categoria.isnot(None),
        IngredientCatalog.categoria != ''
    ).distinct().all()
    categorias = [c[0] for c in categorias]
    
    return render_template('receitas_catalogo.html', 
        active_page='receitas',
        ingredientes=ingredientes, 
        q=q, 
        categoria_atual=cat,
        categorias=categorias)


@bp.route('/catalogo/editar/<int:id>', methods=['POST'], strict_slashes=False)
@login_required
def catalogo_editar(id: int):
    ing = IngredientCatalog.query.get_or_404(id)
    nome = (request.form.get('nome') or ing.nome).strip()
    categoria = (request.form.get('categoria') or '').strip()
    unidade = (request.form.get('unidade_padrao') or 'kg').strip()
    
    try:
        ing.nome = nome
        ing.categoria = categoria
        ing.unidade_padrao = unidade
        db.session.commit()
        flash('Ingrediente atualizado.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro: {e}', 'danger')
    
    return redirect(url_for('receitas.catalogo'))


@bp.route('/catalogo/excluir/<int:id>', methods=['POST'], strict_slashes=False)
@login_required
def catalogo_excluir(id: int):
    ing = IngredientCatalog.query.get_or_404(id)
    try:
        ing.ativo = False
        db.session.commit()
        flash('Ingrediente removido do catálogo.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro: {e}', 'danger')
    
    return redirect(url_for('receitas.catalogo'))


@bp.route('/catalogo/api', methods=['GET'], strict_slashes=False)
@login_required
def catalogo_api():
    ingredientes = IngredientCatalog.query.filter_by(ativo=True).order_by(IngredientCatalog.nome.asc()).all()
    return [{'id': i.id, 'nome': i.nome, 'categoria': i.categoria, 'unidade': i.unidade_padrao} for i in ingredientes]
