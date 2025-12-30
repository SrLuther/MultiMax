from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from ..models import Produto, Historico
from datetime import datetime, timedelta

bp = Blueprint('previsao', __name__, url_prefix='/previsao')

def calcular_consumo_medio(produto_id: int, dias: int = 30) -> float:
    data_inicio = datetime.now() - timedelta(days=dias)
    saidas = Historico.query.filter(
        Historico.product_id == produto_id,
        Historico.action == 'saida',
        Historico.data >= data_inicio
    ).all()
    total_saidas = sum(h.quantidade or 0 for h in saidas)
    return total_saidas / dias if dias > 0 else 0

def calcular_dias_restantes(produto: Produto, consumo_diario: float) -> int | None:
    if consumo_diario <= 0:
        return None
    return int(produto.quantidade / consumo_diario)

def calcular_sugestao_compra(produto: Produto, consumo_diario: float, dias_cobertura: int = 30) -> int:
    if consumo_diario <= 0:
        return 0
    necessidade = consumo_diario * dias_cobertura
    falta = necessidade - produto.quantidade
    if falta <= 0:
        return 0
    return int(falta) + 1

def obter_tendencia(produto_id: int) -> str:
    agora = datetime.now()
    mes_atual_inicio = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    mes_anterior_inicio = (mes_atual_inicio - timedelta(days=1)).replace(day=1)
    
    saidas_mes_atual = Historico.query.filter(
        Historico.product_id == produto_id,
        Historico.action == 'saida',
        Historico.data >= mes_atual_inicio
    ).all()
    
    saidas_mes_anterior = Historico.query.filter(
        Historico.product_id == produto_id,
        Historico.action == 'saida',
        Historico.data >= mes_anterior_inicio,
        Historico.data < mes_atual_inicio
    ).all()
    
    total_atual = sum(h.quantidade or 0 for h in saidas_mes_atual)
    total_anterior = sum(h.quantidade or 0 for h in saidas_mes_anterior)
    
    dias_mes_atual = (agora - mes_atual_inicio).days + 1
    dias_mes_anterior = (mes_atual_inicio - mes_anterior_inicio).days
    
    if dias_mes_atual > 0:
        media_atual = total_atual / dias_mes_atual
    else:
        media_atual = 0
    
    if dias_mes_anterior > 0:
        media_anterior = total_anterior / dias_mes_anterior
    else:
        media_anterior = 0
    
    if media_anterior == 0 and media_atual == 0:
        return 'estavel'
    elif media_anterior == 0:
        return 'alta'
    
    variacao = (media_atual - media_anterior) / media_anterior * 100
    
    if variacao > 10:
        return 'alta'
    elif variacao < -10:
        return 'baixa'
    return 'estavel'

@bp.route('/')
@login_required
def index():
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        from flask import flash, redirect, url_for
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('home.index'))
    
    produtos = Produto.query.order_by(Produto.nome.asc()).all()
    previsoes = []
    
    for produto in produtos:
        consumo_diario = calcular_consumo_medio(produto.id, 30)
        dias_restantes = calcular_dias_restantes(produto, consumo_diario)
        sugestao_compra = calcular_sugestao_compra(produto, consumo_diario, 30)
        tendencia = obter_tendencia(produto.id)
        
        status = 'ok'
        if dias_restantes is not None:
            if dias_restantes <= 7:
                status = 'critico'
            elif dias_restantes <= 14:
                status = 'atencao'
        
        previsoes.append({
            'produto': produto,
            'consumo_diario': round(consumo_diario, 2),
            'dias_restantes': dias_restantes,
            'sugestao_compra': sugestao_compra,
            'tendencia': tendencia,
            'status': status
        })
    
    previsoes_criticas = [p for p in previsoes if p['status'] == 'critico']
    previsoes_atencao = [p for p in previsoes if p['status'] == 'atencao']
    previsoes_ok = [p for p in previsoes if p['status'] == 'ok']
    
    previsoes_ordenadas = previsoes_criticas + previsoes_atencao + previsoes_ok
    
    return render_template('previsao.html', 
                         previsoes=previsoes_ordenadas, 
                         total_criticos=len(previsoes_criticas),
                         total_atencao=len(previsoes_atencao),
                         active_page='previsao')

@bp.route('/api/<int:produto_id>')
@login_required
def api_previsao(produto_id: int):
    produto = Produto.query.get_or_404(produto_id)
    
    consumo_7d = calcular_consumo_medio(produto_id, 7)
    consumo_30d = calcular_consumo_medio(produto_id, 30)
    consumo_90d = calcular_consumo_medio(produto_id, 90)
    
    dias_restantes = calcular_dias_restantes(produto, consumo_30d)
    sugestao = calcular_sugestao_compra(produto, consumo_30d, 30)
    tendencia = obter_tendencia(produto_id)
    
    historico_semanal = []
    for i in range(8, 0, -1):
        fim = datetime.now() - timedelta(days=(i-1)*7)
        inicio = fim - timedelta(days=7)
        
        saidas = Historico.query.filter(
            Historico.product_id == produto_id,
            Historico.action == 'saida',
            Historico.data >= inicio,
            Historico.data < fim
        ).all()
        
        total = sum(h.quantidade or 0 for h in saidas)
        historico_semanal.append({
            'semana': f'Semana {9-i}',
            'consumo': total
        })
    
    return jsonify({
        'produto': {
            'id': produto.id,
            'codigo': produto.codigo,
            'nome': produto.nome,
            'quantidade': produto.quantidade,
            'estoque_minimo': produto.estoque_minimo
        },
        'consumo': {
            '7_dias': round(consumo_7d, 2),
            '30_dias': round(consumo_30d, 2),
            '90_dias': round(consumo_90d, 2)
        },
        'dias_restantes': dias_restantes,
        'sugestao_compra': sugestao,
        'tendencia': tendencia,
        'historico_semanal': historico_semanal
    })
