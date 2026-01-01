from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from ..models import DynamicPricing, PricingHistory, Produto, ProductLot, db
from sqlalchemy import func, desc

bp = Blueprint('precificacao', __name__, url_prefix='/precificacao')

# ============================================================================
# Funções auxiliares
# ============================================================================

def _calcular_preco_dinamico(produto, lot=None):
    """Calcula preço dinâmico baseado em validade e demanda"""
    preco_base = produto.preco_custo or 0.0
    margem_minima = 20.0  # percentual padrão
    
    # Desconto por validade
    desconto_validade = 0.0
    if lot and lot.data_validade:
        dias_para_validade = (lot.data_validade - date.today()).days
        if dias_para_validade <= 1:
            desconto_validade = 30.0  # 30% de desconto
        elif dias_para_validade <= 3:
            desconto_validade = 20.0  # 20% de desconto
        elif dias_para_validade <= 7:
            desconto_validade = 10.0  # 10% de desconto
    
    # Desconto por demanda (baixa rotatividade)
    desconto_demanda = 0.0
    # Aqui poderia verificar histórico de vendas
    
    preco_final = preco_base * (1 + margem_minima/100) * (1 - desconto_validade/100) * (1 - desconto_demanda/100)
    return max(preco_base, preco_final)

def _get_precificacoes_filtradas(busca: str = '', apenas_promocoes: bool = False, limit: int = 100):
    """Busca precificações com filtros"""
    query = DynamicPricing.query.filter_by(ativo=True)
    if busca:
        query = query.join(Produto).filter(Produto.nome.ilike(f'%{busca}%'))
    if apenas_promocoes:
        query = query.filter(DynamicPricing.desconto_validade > 0)
    return query.order_by(desc(DynamicPricing.data_atualizacao)).limit(limit).all()


# ============================================================================
# Rotas
# ============================================================================

@bp.route('/', methods=['GET'])
@login_required
def index():
    busca = request.args.get('busca', '').strip()
    apenas_promocoes = request.args.get('promocoes', '') == '1'
    
    precificacoes = _get_precificacoes_filtradas(busca, apenas_promocoes)
    
    return render_template(
        'precificacao/index.html',
        precificacoes=precificacoes,
        busca=busca,
        apenas_promocoes=apenas_promocoes,
        active_page='precificacao'
    )

@bp.route('/atualizar/<int:produto_id>', methods=['POST'])
@login_required
def atualizar(produto_id):
    if current_user.nivel == 'visualizador':
        flash('Visualizadores não têm permissão para fazer alterações.', 'danger')
        return redirect(url_for('precificacao.index'))
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Você não tem permissão para atualizar preços.', 'danger')
        return redirect(url_for('precificacao.index'))
    
    produto = Produto.query.get_or_404(produto_id)
    lot = ProductLot.query.filter_by(produto_id=produto_id, ativo=True).first()
    
    preco_calculado = _calcular_preco_dinamico(produto, lot)
    
    pricing = DynamicPricing.query.filter_by(produto_id=produto_id).first()
    if not pricing:
        pricing = DynamicPricing()
        pricing.produto_id = produto_id
        pricing.preco_base = produto.preco_custo or 0.0
        pricing.margem_minima = 20.0
    
    preco_anterior = pricing.preco_atual
    pricing.preco_atual = preco_calculado
    if lot:
        pricing.dias_para_validade = (lot.data_validade - date.today()).days if lot.data_validade else 0
    pricing.desconto_validade = ((produto.preco_custo or 0.0) - preco_calculado) / (produto.preco_custo or 1.0) * 100 if produto.preco_custo else 0
    pricing.data_atualizacao = datetime.now(ZoneInfo('America/Sao_Paulo'))
    pricing.usuario = current_user.name
    
    # Atualizar preço do produto
    produto.preco_venda = preco_calculado
    
    # Registrar histórico
    if preco_anterior != preco_calculado:
        hist = PricingHistory()
        hist.pricing_id = pricing.id if pricing.id else None
        hist.preco_anterior = preco_anterior
        hist.preco_novo = preco_calculado
        hist.motivo = 'Atualização automática por validade' if lot and lot.data_validade else 'Atualização automática'
        hist.usuario = current_user.name
        db.session.add(hist)
    
    try:
        if not pricing.id:
            db.session.add(pricing)
        db.session.commit()
        flash(f'Preço atualizado: R$ {preco_calculado:.2f}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar preço: {e}', 'danger')
    
    return redirect(url_for('precificacao.index'))

@bp.route('/atualizar-todos', methods=['POST'])
@login_required
def atualizar_todos():
    if current_user.nivel not in ['admin', 'DEV']:
        flash('Apenas administradores podem atualizar todos os preços.', 'danger')
        return redirect(url_for('precificacao.index'))
    
    produtos = Produto.query.filter_by(ativo=True).all()
    atualizados = 0
    
    for produto in produtos:
        lot = ProductLot.query.filter_by(produto_id=produto.id, ativo=True).first()
        preco_calculado = _calcular_preco_dinamico(produto, lot)
        
        pricing = DynamicPricing.query.filter_by(produto_id=produto.id).first()
        if not pricing:
            pricing = DynamicPricing()
            pricing.produto_id = produto.id
            pricing.preco_base = produto.preco_custo or 0.0
            pricing.margem_minima = 20.0
            db.session.add(pricing)
        
        pricing.preco_atual = preco_calculado
        if lot:
            pricing.dias_para_validade = (lot.data_validade - date.today()).days if lot.data_validade else 0
        pricing.data_atualizacao = datetime.now(ZoneInfo('America/Sao_Paulo'))
        pricing.usuario = current_user.name
        
        produto.preco_venda = preco_calculado
        atualizados += 1
    
    try:
        db.session.commit()
        flash(f'{atualizados} preços atualizados com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar preços: {e}', 'danger')
    
    return redirect(url_for('precificacao.index'))

