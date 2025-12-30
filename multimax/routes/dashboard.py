from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from ..models import (
    Produto, ProductLot, MeatReception, LossRecord, 
    TemperatureLog, ColdRoomOccupancy, DynamicPricing,
    YieldAnalysis, SupplierEvaluation, db
)
from sqlalchemy import func, desc

bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@bp.route('/', methods=['GET'])
@login_required
def index():
    # Estatísticas gerais
    total_produtos = Produto.query.filter_by(ativo=True).count()
    produtos_baixo_estoque = Produto.query.filter(
        Produto.quantidade <= Produto.estoque_minimo,
        Produto.estoque_minimo > 0
    ).count()
    
    # Lotes
    total_lotes = ProductLot.query.filter_by(ativo=True).count()
    lotes_vencendo = ProductLot.query.filter(
        ProductLot.data_validade >= date.today(),
        ProductLot.data_validade <= date.today() + timedelta(days=3),
        ProductLot.ativo == True
    ).count()
    
    # Recepções do mês
    inicio_mes = date.today().replace(day=1)
    recepcoes_mes = MeatReception.query.filter(
        func.date(MeatReception.data) >= inicio_mes
    ).count()
    
    # Perdas do mês
    perdas_mes = LossRecord.query.filter(
        func.date(LossRecord.data_registro) >= inicio_mes
    ).all()
    valor_perdas = sum(p.custo_estimado for p in perdas_mes)
    
    # Alertas de temperatura
    alertas_temp = TemperatureLog.query.filter_by(alerta=True).count()
    
    # Ocupação câmara fria
    ocupacoes = ColdRoomOccupancy.query.order_by(desc(ColdRoomOccupancy.data_registro)).limit(5).all()
    
    # Produtos em promoção
    promocoes = DynamicPricing.query.filter(
        DynamicPricing.desconto_validade > 0,
        DynamicPricing.ativo == True
    ).count()
    
    # Rendimento médio
    rendimentos = YieldAnalysis.query.filter(
        func.date(YieldAnalysis.data_analise) >= inicio_mes
    ).all()
    rendimento_medio = sum(r.rendimento_percentual for r in rendimentos) / len(rendimentos) if rendimentos else 0
    
    # Gráfico de recepções (últimos 30 dias)
    hoje = date.today()
    recepcoes_30_dias = []
    for i in range(30):
        dia = hoje - timedelta(days=i)
        count = MeatReception.query.filter(
            func.date(MeatReception.data) == dia
        ).count()
        recepcoes_30_dias.append({'data': dia.strftime('%d/%m'), 'count': count})
    recepcoes_30_dias.reverse()
    
    return render_template('dashboard/index.html',
                         total_produtos=total_produtos,
                         produtos_baixo_estoque=produtos_baixo_estoque,
                         total_lotes=total_lotes,
                         lotes_vencendo=lotes_vencendo,
                         recepcoes_mes=recepcoes_mes,
                         valor_perdas=valor_perdas,
                         alertas_temp=alertas_temp,
                         ocupacoes=ocupacoes,
                         promocoes=promocoes,
                         rendimento_medio=rendimento_medio,
                         recepcoes_30_dias=recepcoes_30_dias,
                         active_page='dashboard')

