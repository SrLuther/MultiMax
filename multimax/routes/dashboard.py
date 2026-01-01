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

# ============================================================================
# Funções auxiliares
# ============================================================================

def _get_metricas_produtos():
    """Calcula métricas de produtos"""
    return {
        'total_produtos': Produto.query.filter_by(ativo=True).count(),
        'produtos_baixo_estoque': Produto.query.filter(
            Produto.quantidade <= Produto.estoque_minimo,
            Produto.estoque_minimo > 0
        ).count(),
    }


def _get_metricas_lotes():
    """Calcula métricas de lotes"""
    hoje = date.today()
    return {
        'total_lotes': ProductLot.query.filter_by(ativo=True).count(),
        'lotes_vencendo': ProductLot.query.filter(
            ProductLot.data_validade >= hoje,
            ProductLot.data_validade <= hoje + timedelta(days=3),
            ProductLot.ativo == True
        ).count(),
    }


def _get_metricas_mes(inicio_mes: date):
    """Calcula métricas do mês atual"""
    return {
        'recepcoes_mes': MeatReception.query.filter(
            func.date(MeatReception.data) >= inicio_mes
        ).count(),
        'valor_perdas': db.session.query(func.coalesce(func.sum(LossRecord.custo_estimado), 0.0)).filter(
            func.date(LossRecord.data_registro) >= inicio_mes
        ).scalar() or 0.0,
        'rendimento_medio': db.session.query(func.coalesce(func.avg(YieldAnalysis.rendimento_percentual), 0.0)).filter(
            func.date(YieldAnalysis.data_analise) >= inicio_mes
        ).scalar() or 0.0,
    }


def _get_metricas_gerais():
    """Calcula métricas gerais"""
    return {
        'alertas_temp': TemperatureLog.query.filter_by(alerta=True).count(),
        'promocoes': DynamicPricing.query.filter(
            DynamicPricing.desconto_validade > 0,
            DynamicPricing.ativo == True
        ).count(),
    }


def _get_recepcoes_30_dias():
    """Busca recepções dos últimos 30 dias agrupadas"""
    hoje = date.today()
    inicio_30_dias = hoje - timedelta(days=29)
    recepcoes_agrupadas = db.session.query(
        func.date(MeatReception.data).label('dia'),
        func.count(MeatReception.id).label('count')
    ).filter(
        func.date(MeatReception.data) >= inicio_30_dias,
        func.date(MeatReception.data) <= hoje
    ).group_by(func.date(MeatReception.data)).all()
    
    recepcoes_dict = {r.dia: r.count for r in recepcoes_agrupadas}
    recepcoes_30_dias = []
    for i in range(29, -1, -1):
        dia = hoje - timedelta(days=i)
        count = recepcoes_dict.get(dia, 0)
        recepcoes_30_dias.append({'data': dia.strftime('%d/%m'), 'count': count})
    
    return recepcoes_30_dias


# ============================================================================
# Rotas
# ============================================================================

@bp.route('/', methods=['GET'])
@login_required
def index():
    inicio_mes = date.today().replace(day=1)
    
    metricas_produtos = _get_metricas_produtos()
    metricas_lotes = _get_metricas_lotes()
    metricas_mes = _get_metricas_mes(inicio_mes)
    metricas_gerais = _get_metricas_gerais()
    recepcoes_30_dias = _get_recepcoes_30_dias()
    ocupacoes = ColdRoomOccupancy.query.order_by(desc(ColdRoomOccupancy.data_registro)).limit(5).all()
    
    return render_template(
        'dashboard/index.html',
        active_page='dashboard',
        ocupacoes=ocupacoes,
        recepcoes_30_dias=recepcoes_30_dias,
        **metricas_produtos,
        **metricas_lotes,
        **metricas_mes,
        **metricas_gerais
    )

