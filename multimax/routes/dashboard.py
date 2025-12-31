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
    
    # Perdas do mês - otimizado: usar agregação SQL ao invés de carregar todos
    valor_perdas = db.session.query(func.coalesce(func.sum(LossRecord.custo_estimado), 0.0)).filter(
        func.date(LossRecord.data_registro) >= inicio_mes
    ).scalar() or 0.0
    
    # Alertas de temperatura
    alertas_temp = TemperatureLog.query.filter_by(alerta=True).count()
    
    # Ocupação câmara fria
    ocupacoes = ColdRoomOccupancy.query.order_by(desc(ColdRoomOccupancy.data_registro)).limit(5).all()
    
    # Produtos em promoção
    promocoes = DynamicPricing.query.filter(
        DynamicPricing.desconto_validade > 0,
        DynamicPricing.ativo == True
    ).count()
    
    # Rendimento médio - otimizado: usar AVG SQL ao invés de carregar todos
    rendimento_medio = db.session.query(func.coalesce(func.avg(YieldAnalysis.rendimento_percentual), 0.0)).filter(
        func.date(YieldAnalysis.data_analise) >= inicio_mes
    ).scalar() or 0.0
    
    # Gráfico de recepções (últimos 30 dias) - otimizado: uma query agrupada ao invés de 30
    hoje = date.today()
    inicio_30_dias = hoje - timedelta(days=29)
    recepcoes_agrupadas = db.session.query(
        func.date(MeatReception.data).label('dia'),
        func.count(MeatReception.id).label('count')
    ).filter(
        func.date(MeatReception.data) >= inicio_30_dias,
        func.date(MeatReception.data) <= hoje
    ).group_by(func.date(MeatReception.data)).all()
    
    # Criar dicionário para lookup rápido
    recepcoes_dict = {r.dia: r.count for r in recepcoes_agrupadas}
    
    # Preencher todos os dias (mesmo os sem recepções)
    recepcoes_30_dias = []
    for i in range(29, -1, -1):
        dia = hoje - timedelta(days=i)
        count = recepcoes_dict.get(dia, 0)
        recepcoes_30_dias.append({'data': dia.strftime('%d/%m'), 'count': count})
    
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

