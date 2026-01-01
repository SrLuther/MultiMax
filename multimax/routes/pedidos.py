from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from datetime import datetime
from zoneinfo import ZoneInfo
from .. import db
from ..models import PurchaseOrder, PurchaseOrderItem, Produto, Fornecedor

bp = Blueprint('pedidos', __name__, url_prefix='/pedidos')

# ============================================================================
# Constantes
# ============================================================================

ALLOWED_STATUS = {'pendente', 'enviado', 'recebido', 'cancelado'}

# ============================================================================
# Funções auxiliares
# ============================================================================

def _now():
    """Retorna datetime atual com timezone"""
    return datetime.now(ZoneInfo('America/Sao_Paulo'))


def _get_pedidos_filtrados(page: int = 1, status_filter: str = '', fornecedor_filter: int | None = None, per_page: int = 10):
    """Busca pedidos com filtros e paginação"""
    query = PurchaseOrder.query
    if status_filter:
        query = query.filter(PurchaseOrder.status == status_filter)
    if fornecedor_filter:
        query = query.filter(PurchaseOrder.fornecedor_id == fornecedor_filter)
    query = query.order_by(PurchaseOrder.data_criacao.desc())
    return query.paginate(page=page, per_page=per_page, error_out=False)


def _enrich_pedidos(pedidos):
    """Enriquece lista de pedidos com objetos relacionados"""
    for p in pedidos:
        p.fornecedor_obj = Fornecedor.query.get(p.fornecedor_id)
        p.itens = PurchaseOrderItem.query.filter_by(order_id=p.id).all()


def _get_kpis_pedidos():
    """Calcula KPIs de pedidos"""
    return {
        'total': PurchaseOrder.query.count(),
        'pendentes': PurchaseOrder.query.filter_by(status='pendente').count(),
        'enviados': PurchaseOrder.query.filter_by(status='enviado').count(),
        'recebidos': PurchaseOrder.query.filter_by(status='recebido').count(),
    }


# ============================================================================
# Rotas
# ============================================================================

@bp.route('/', methods=['GET'], strict_slashes=False)
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '').strip()
    fornecedor_filter = request.args.get('fornecedor', '', type=int)
    
    pedidos_pag = _get_pedidos_filtrados(page, status_filter, fornecedor_filter)
    _enrich_pedidos(pedidos_pag.items)
    
    fornecedores = Fornecedor.query.filter_by(ativo=True).order_by(Fornecedor.nome).all()
    kpis = _get_kpis_pedidos()
    
    return render_template(
        'pedidos.html',
        active_page='pedidos',
        pedidos=pedidos_pag.items,
        pedidos_pag=pedidos_pag,
        fornecedores=fornecedores,
        status_filter=status_filter,
        fornecedor_filter=fornecedor_filter,
        **kpis
    )

@bp.route('/novo', methods=['GET', 'POST'], strict_slashes=False)
@login_required
def novo():
    if current_user.nivel not in ('operador', 'admin', 'DEV'):
        flash('Sem permissão para criar pedidos.', 'warning')
        return redirect(url_for('pedidos.index'))
    
    if request.method == 'POST':
        fornecedor_id = request.form.get('fornecedor_id', type=int)
        data_prevista_str = request.form.get('data_prevista', '').strip()
        observacao = request.form.get('observacao', '').strip()
        
        if not fornecedor_id:
            flash('Selecione um fornecedor.', 'warning')
            return redirect(url_for('pedidos.novo'))
        
        pedido = PurchaseOrder()
        pedido.fornecedor_id = fornecedor_id
        pedido.status = 'pendente'
        pedido.usuario = current_user.username
        pedido.observacao = observacao
        pedido.data_criacao = _now()
        
        if data_prevista_str:
            try:
                pedido.data_prevista = datetime.strptime(data_prevista_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        db.session.add(pedido)
        db.session.flush()
        
        produto_ids = request.form.getlist('produto_id[]')
        quantidades = request.form.getlist('quantidade[]')
        precos = request.form.getlist('preco[]')
        
        valor_total = 0
        for i in range(len(produto_ids)):
            prod_id = int(produto_ids[i]) if produto_ids[i] else None
            qtd = float(quantidades[i].replace(',', '.')) if i < len(quantidades) and quantidades[i] else 0
            preco = float(precos[i].replace(',', '.')) if i < len(precos) and precos[i] else 0
            
            if qtd <= 0:
                continue
            
            produto = Produto.query.get(prod_id) if prod_id else None
            
            item = PurchaseOrderItem()
            item.order_id = pedido.id
            item.produto_id = prod_id
            item.produto_nome = produto.nome if produto else f'Produto #{prod_id}'
            item.quantidade = qtd
            item.preco_unitario = preco
            item.subtotal = qtd * preco
            valor_total += item.subtotal
            
            db.session.add(item)
        
        pedido.valor_total = valor_total
        db.session.commit()
        
        flash('Pedido criado com sucesso.', 'success')
        return redirect(url_for('pedidos.index'))
    
    fornecedores = Fornecedor.query.filter_by(ativo=True).order_by(Fornecedor.nome).all()
    produtos = Produto.query.order_by(Produto.nome).all()
    
    return render_template(
        'pedidos_novo.html',
        active_page='pedidos',
        fornecedores=fornecedores,
        produtos=produtos
    )

@bp.route('/gerar-automatico', methods=['GET', 'POST'], strict_slashes=False)
@login_required
def gerar_automatico():
    if current_user.nivel not in ('operador', 'admin', 'DEV'):
        flash('Sem permissão para gerar pedidos.', 'warning')
        return redirect(url_for('pedidos.index'))
    
    produtos_baixo = Produto.query.filter(
        Produto.quantidade <= Produto.estoque_minimo,
        Produto.fornecedor_id.isnot(None)
    ).order_by(Produto.fornecedor_id, Produto.nome).all()
    
    if request.method == 'POST':
        produto_ids = request.form.getlist('produto_id[]')
        quantidades = request.form.getlist('quantidade[]')
        
        pedidos_por_fornecedor = {}
        
        for i, prod_id in enumerate(produto_ids):
            if not prod_id:
                continue
            produto = Produto.query.get(int(prod_id))
            if not produto or not produto.fornecedor_id:
                continue
            
            qtd = float(quantidades[i].replace(',', '.')) if i < len(quantidades) and quantidades[i] else 0
            if qtd <= 0:
                continue
            
            if produto.fornecedor_id not in pedidos_por_fornecedor:
                pedido = PurchaseOrder()
                pedido.fornecedor_id = produto.fornecedor_id
                pedido.status = 'pendente'
                pedido.usuario = current_user.username
                pedido.auto_gerado = True
                pedido.data_criacao = _now()
                db.session.add(pedido)
                db.session.flush()
                pedidos_por_fornecedor[produto.fornecedor_id] = pedido
            
            pedido = pedidos_por_fornecedor[produto.fornecedor_id]
            
            item = PurchaseOrderItem()
            item.order_id = pedido.id
            item.produto_id = produto.id
            item.produto_nome = produto.nome
            item.quantidade = qtd
            item.preco_unitario = produto.preco_custo or 0
            item.subtotal = qtd * (produto.preco_custo or 0)
            db.session.add(item)
        
        for pedido in pedidos_por_fornecedor.values():
            itens = PurchaseOrderItem.query.filter_by(order_id=pedido.id).all()
            pedido.valor_total = sum(i.subtotal for i in itens)
        
        db.session.commit()
        
        total = len(pedidos_por_fornecedor)
        flash(f'{total} pedido(s) gerado(s) automaticamente.', 'success')
        return redirect(url_for('pedidos.index'))
    
    for p in produtos_baixo:
        p.fornecedor_obj = Fornecedor.query.get(p.fornecedor_id)
        falta = (p.estoque_minimo or 0) - (p.quantidade or 0)
        p.quantidade_sugerida = max(falta * 2, p.estoque_minimo or 10)
    
    return render_template(
        'pedidos_automatico.html',
        active_page='pedidos',
        produtos=produtos_baixo
    )

@bp.route('/<int:id>/status', methods=['POST'], strict_slashes=False)
@login_required
def atualizar_status(id: int):
    if current_user.nivel not in ('operador', 'admin', 'DEV'):
        flash('Sem permissão para atualizar status.', 'warning')
        return redirect(url_for('pedidos.index'))
    
    pedido = PurchaseOrder.query.get_or_404(id)
    novo_status = request.form.get('status', '').strip()
    
    if novo_status in ('pendente', 'enviado', 'recebido', 'cancelado'):
        pedido.status = novo_status
        db.session.commit()
        flash(f'Status atualizado para {novo_status}.', 'success')
    else:
        flash('Status inválido.', 'warning')
    
    return redirect(url_for('pedidos.index'))

@bp.route('/<int:id>/excluir', methods=['POST'], strict_slashes=False)
@login_required
def excluir(id: int):
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Apenas administradores podem excluir pedidos.', 'warning')
        return redirect(url_for('pedidos.index'))
    
    pedido = PurchaseOrder.query.get_or_404(id)
    try:
        PurchaseOrderItem.query.filter_by(order_id=pedido.id).delete()
        db.session.delete(pedido)
        db.session.commit()
        flash('Pedido excluído.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir: {e}', 'danger')
    
    return redirect(url_for('pedidos.index'))
