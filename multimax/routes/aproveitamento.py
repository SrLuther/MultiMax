from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from ..models import WasteUtilization, Produto, ProductLot, Recipe, db
from sqlalchemy import func, desc

bp = Blueprint('aproveitamento', __name__, url_prefix='/aproveitamento')

# ============================================================================
# Funções auxiliares
# ============================================================================

def _get_sugestoes_filtradas(status: str = '', prioridade: str = ''):
    """Busca sugestões de aproveitamento com filtros"""
    query = WasteUtilization.query
    if status:
        query = query.filter_by(status=status)
    else:
        query = query.filter_by(status='pendente')
    if prioridade:
        query = query.filter_by(prioridade=int(prioridade))
    return query.order_by(WasteUtilization.prioridade, WasteUtilization.dias_para_validade).all()


# ============================================================================
# Rotas
# ============================================================================

@bp.route('/', methods=['GET'])
@login_required
def index():
    status = request.args.get('status', '').strip()
    prioridade = request.args.get('prioridade', '').strip()
    
    sugestoes = _get_sugestoes_filtradas(status, prioridade)
    
    return render_template(
        'aproveitamento/index.html',
        sugestoes=sugestoes,
        status=status,
        prioridade=prioridade,
        active_page='aproveitamento'
    )

@bp.route('/gerar-sugestoes', methods=['POST'])
@login_required
def gerar_sugestoes():
    if current_user.nivel == 'visualizador':
        flash('Visualizadores não têm permissão para fazer alterações.', 'danger')
        return redirect(url_for('aproveitamento.index'))
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Você não tem permissão para gerar sugestões.', 'danger')
        return redirect(url_for('aproveitamento.index'))
    
    hoje = date.today()
    lotes_vencendo = ProductLot.query.filter(
        ProductLot.data_validade >= hoje,
        ProductLot.data_validade <= hoje + timedelta(days=7),
        ProductLot.ativo == True,
        ProductLot.quantidade_atual > 0
    ).all()
    
    sugestoes_criadas = 0
    for lot in lotes_vencendo:
        # Verificar se já existe sugestão
        if WasteUtilization.query.filter_by(lot_id=lot.id, status='pendente').first():
            continue
        
        dias_para_validade = (lot.data_validade - hoje).days
        prioridade = 1 if dias_para_validade <= 1 else (2 if dias_para_validade <= 3 else 3)
        
        # Buscar receitas que usam este produto
        receitas = Recipe.query.filter_by(ativo=True).all()
        receita_sugerida = None
        for rec in receitas:
            # Verificar se receita usa este tipo de produto
            if lot.produto and lot.produto.categoria:
                if lot.produto.categoria.lower() in rec.nome.lower():
                    receita_sugerida = rec
                    break
        
        sugestao = WasteUtilization()
        sugestao.produto_id = lot.produto_id
        sugestao.lot_id = lot.id
        sugestao.dias_para_validade = dias_para_validade
        sugestao.prioridade = prioridade
        sugestao.receita_id = receita_sugerida.id if receita_sugerida else None
        
        if dias_para_validade <= 1:
            sugestao.tipo = 'promocao'
            sugestao.sugestao = f'Produto vence em {dias_para_validade} dia(s). Aplicar promoção urgente ou usar em receita.'
        elif dias_para_validade <= 3:
            sugestao.tipo = 'receita'
            sugestao.sugestao = f'Produto vence em {dias_para_validade} dias. Sugestão: usar em receita "{receita_sugerida.nome}"' if receita_sugerida else f'Produto vence em {dias_para_validade} dias. Considerar usar em receita.'
        else:
            sugestao.tipo = 'promocao'
            sugestao.sugestao = f'Produto vence em {dias_para_validade} dias. Considerar promoção preventiva.'
        
        try:
            db.session.add(sugestao)
            sugestoes_criadas += 1
        except Exception:
            db.session.rollback()
    
    try:
        db.session.commit()
        flash(f'{sugestoes_criadas} sugestões geradas!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao gerar sugestões: {e}', 'danger')
    
    return redirect(url_for('aproveitamento.index'))

@bp.route('/<int:id>/aplicar', methods=['POST'])
@login_required
def aplicar(id):
    if current_user.nivel == 'visualizador':
        flash('Visualizadores não têm permissão para fazer alterações.', 'danger')
        return redirect(url_for('aproveitamento.index'))
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Você não tem permissão para aplicar sugestões.', 'danger')
        return redirect(url_for('aproveitamento.index'))
    
    sugestao = WasteUtilization.query.get_or_404(id)
    sugestao.status = 'aplicado'
    sugestao.data_aplicacao = datetime.now(ZoneInfo('America/Sao_Paulo'))
    sugestao.usuario_aplicacao = current_user.name
    
    # Se for promoção, atualizar preço
    if sugestao.tipo == 'promocao' and sugestao.produto:
        from ..routes.precificacao import _calcular_preco_dinamico
        preco_promocao = _calcular_preco_dinamico(sugestao.produto, sugestao.lot)
        sugestao.produto.preco_venda = preco_promocao * 0.8  # 20% de desconto
    
    try:
        db.session.commit()
        flash('Sugestão aplicada com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao aplicar sugestão: {e}', 'danger')
    
    return redirect(url_for('aproveitamento.index'))

