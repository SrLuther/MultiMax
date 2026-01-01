from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
from ..models import ProductLot, LotMovement, MeatReception, Produto, TraceabilityRecord, db
from sqlalchemy import func, desc

bp = Blueprint('lotes', __name__, url_prefix='/lotes')

# ============================================================================
# Funções auxiliares
# ============================================================================

def _get_lotes_filtrados(busca: str = '', localizacao: str = '', status: str = '', limit: int = 100):
    """Busca lotes com filtros"""
    query = ProductLot.query
    
    if busca:
        query = query.filter(
            (ProductLot.lote_codigo.ilike(f'%{busca}%')) |
            (ProductLot.fornecedor.ilike(f'%{busca}%'))
        )
    if localizacao:
        query = query.filter_by(localizacao=localizacao)
    
    hoje = date.today()
    if status == 'ativo':
        query = query.filter_by(ativo=True)
    elif status == 'inativo':
        query = query.filter_by(ativo=False)
    elif status == 'vencido':
        query = query.filter(ProductLot.data_validade < hoje, ProductLot.ativo == True)
    elif status == 'vencendo':
        vencendo = hoje + timedelta(days=3)
        query = query.filter(
            ProductLot.data_validade >= hoje,
            ProductLot.data_validade <= vencendo,
            ProductLot.ativo == True
        )
    
    return query.order_by(desc(ProductLot.data_recepcao)).limit(limit).all()


def _get_kpis_lotes():
    """Calcula KPIs de lotes"""
    hoje = date.today()
    return {
        'total_lotes': ProductLot.query.filter_by(ativo=True).count(),
        'vencendo_hoje': ProductLot.query.filter(
            ProductLot.data_validade == hoje,
            ProductLot.ativo == True
        ).count(),
        'vencidos': ProductLot.query.filter(
            ProductLot.data_validade < hoje,
            ProductLot.ativo == True
        ).count(),
    }


# ============================================================================
# Rotas
# ============================================================================

@bp.route('/', methods=['GET'])
@login_required
def index():
    busca = request.args.get('busca', '').strip()
    localizacao = request.args.get('localizacao', '').strip()
    status = request.args.get('status', '').strip()
    
    lotes = _get_lotes_filtrados(busca, localizacao, status)
    kpis = _get_kpis_lotes()
    
    return render_template(
        'lotes/index.html',
        lotes=lotes,
        busca=busca,
        localizacao=localizacao,
        status=status,
        active_page='lotes',
        **kpis
    )

@bp.route('/novo', methods=['GET', 'POST'])
@login_required
def novo():
    if current_user.nivel == 'visualizador':
        flash('Visualizadores não têm permissão para fazer alterações.', 'danger')
        return redirect(url_for('lotes.index'))
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Você não tem permissão para criar lotes.', 'danger')
        return redirect(url_for('lotes.index'))
    
    if request.method == 'POST':
        reception_id = int(request.form.get('reception_id', '0') or '0') if request.form.get('reception_id') else None
        produto_id = int(request.form.get('produto_id', '0') or '0') if request.form.get('produto_id') else None
        lote_codigo = request.form.get('lote_codigo', '').strip()
        data_validade_str = request.form.get('data_validade', '').strip()
        quantidade_inicial = float(request.form.get('quantidade_inicial', '0') or '0')
        localizacao = request.form.get('localizacao', '').strip()
        temperatura = float(request.form.get('temperatura_armazenamento', '0') or '0')
        fornecedor = request.form.get('fornecedor', '').strip()
        certificado = request.form.get('certificado_sanitario', '').strip()
        data_validade_cert_str = request.form.get('data_validade_certificado', '').strip()
        
        if not lote_codigo:
            flash('Código do lote é obrigatório.', 'warning')
            return redirect(url_for('lotes.novo'))
        
        # Verificar se código já existe
        if ProductLot.query.filter_by(lote_codigo=lote_codigo).first():
            flash('Código de lote já existe.', 'danger')
            return redirect(url_for('lotes.novo'))
        
        lote = ProductLot()
        lote.reception_id = reception_id
        lote.produto_id = produto_id
        lote.lote_codigo = lote_codigo
        lote.quantidade_inicial = quantidade_inicial
        lote.quantidade_atual = quantidade_inicial
        lote.localizacao = localizacao
        lote.temperatura_armazenamento = temperatura
        lote.fornecedor = fornecedor
        lote.certificado_sanitario = certificado
        
        if data_validade_str:
            try:
                lote.data_validade = datetime.strptime(data_validade_str, '%Y-%m-%d').date()
            except Exception:
                pass
        if data_validade_cert_str:
            try:
                lote.data_validade_certificado = datetime.strptime(data_validade_cert_str, '%Y-%m-%d').date()
            except Exception:
                pass
        
        try:
            db.session.add(lote)
            db.session.flush()
            
            # Criar registro de rastreabilidade
            trace = TraceabilityRecord()
            trace.lot_id = lote.id
            trace.reception_id = reception_id
            trace.etapa = 'recepcao'
            trace.responsavel = current_user.name
            trace.observacao = 'Lote criado'
            db.session.add(trace)
            
            db.session.commit()
            flash(f'Lote "{lote_codigo}" criado com sucesso!', 'success')
            return redirect(url_for('lotes.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar lote: {e}', 'danger')
    
    # Buscar recepções recentes e produtos
    recepcoes = MeatReception.query.order_by(desc(MeatReception.data)).limit(20).all()
    produtos = Produto.query.filter_by(ativo=True).order_by(Produto.nome).all()
    
    return render_template('lotes/novo.html',
                         recepcoes=recepcoes,
                         produtos=produtos,
                         active_page='lotes')

@bp.route('/<int:id>/movimentar', methods=['POST'])
@login_required
def movimentar(id):
    if current_user.nivel == 'visualizador':
        flash('Visualizadores não têm permissão para fazer alterações.', 'danger')
        return redirect(url_for('lotes.index'))
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Você não tem permissão para movimentar lotes.', 'danger')
        return redirect(url_for('lotes.index'))
    
    lote = ProductLot.query.get_or_404(id)
    tipo = request.form.get('tipo', '').strip()
    quantidade = float(request.form.get('quantidade', '0') or '0')
    origem = request.form.get('origem', '').strip()
    destino = request.form.get('destino', '').strip()
    observacao = request.form.get('observacao', '').strip()
    
    if not tipo or quantidade <= 0:
        flash('Dados inválidos para movimentação.', 'warning')
        return redirect(url_for('lotes.detalhes', id=id))
    
    if tipo == 'saida' and quantidade > lote.quantidade_atual:
        flash('Quantidade insuficiente no lote.', 'danger')
        return redirect(url_for('lotes.detalhes', id=id))
    
    movimento = LotMovement()
    movimento.lot_id = lote.id
    movimento.tipo = tipo
    movimento.quantidade = quantidade
    movimento.origem = origem
    movimento.destino = destino
    movimento.observacao = observacao
    movimento.usuario = current_user.name
    
    if tipo == 'entrada':
        lote.quantidade_atual += quantidade
    elif tipo == 'saida':
        lote.quantidade_atual -= quantidade
    elif tipo == 'transferencia':
        lote.localizacao = destino
    
    try:
        db.session.add(movimento)
        
        # Atualizar registro de rastreabilidade
        trace = TraceabilityRecord()
        trace.lot_id = lote.id
        trace.etapa = tipo
        trace.responsavel = current_user.name
        trace.observacao = observacao or f'Movimentação: {tipo}'
        db.session.add(trace)
        
        db.session.commit()
        flash('Movimentação registrada com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao registrar movimentação: {e}', 'danger')
    
    return redirect(url_for('lotes.detalhes', id=id))

@bp.route('/<int:id>')
@login_required
def detalhes(id):
    lote = ProductLot.query.get_or_404(id)
    movimentos = LotMovement.query.filter_by(lot_id=id).order_by(desc(LotMovement.data_movimento)).all()
    rastreabilidade = TraceabilityRecord.query.filter_by(lot_id=id).order_by(desc(TraceabilityRecord.data_etapa)).all()
    
    return render_template('lotes/detalhes.html',
                         lote=lote,
                         movimentos=movimentos,
                         rastreabilidade=rastreabilidade,
                         active_page='lotes')

@bp.route('/<int:id>/rastreabilidade')
@login_required
def rastreabilidade(id):
    lote = ProductLot.query.get_or_404(id)
    registros = TraceabilityRecord.query.filter_by(lot_id=id).order_by(TraceabilityRecord.data_etapa).all()
    
    return render_template('lotes/rastreabilidade.html',
                         lote=lote,
                         registros=registros,
                         active_page='lotes')

