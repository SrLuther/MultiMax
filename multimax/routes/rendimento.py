from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from zoneinfo import ZoneInfo
from ..models import YieldAnalysis, MeatReception, MeatCutExecution, db
from sqlalchemy import func, desc

bp = Blueprint('rendimento', __name__, url_prefix='/rendimento')

# ============================================================================
# Funções auxiliares
# ============================================================================

def _get_analises_filtradas(reception_id: int | None = None, limit: int = 100):
    """Busca análises de rendimento com filtro"""
    query = YieldAnalysis.query
    if reception_id:
        query = query.filter_by(reception_id=reception_id)
    return query.order_by(desc(YieldAnalysis.data_analise)).limit(limit).all()


def _get_kpis_rendimento():
    """Calcula KPIs de rendimento"""
    return {
        'rendimento_medio': db.session.query(func.avg(YieldAnalysis.rendimento_percentual)).scalar() or 0,
        'total_analises': YieldAnalysis.query.count(),
    }


# ============================================================================
# Rotas
# ============================================================================

@bp.route('/', methods=['GET'])
@login_required
def index():
    reception_id = request.args.get('reception_id', type=int)
    
    analises = _get_analises_filtradas(reception_id)
    kpis = _get_kpis_rendimento()
    
    return render_template(
        'rendimento/index.html',
        analises=analises,
        reception_id=reception_id,
        active_page='rendimento',
        **kpis
    )

@bp.route('/analisar/<int:reception_id>', methods=['POST'])
@login_required
def analisar(reception_id):
    if current_user.nivel == 'visualizador':
        flash('Visualizadores não têm permissão para fazer alterações.', 'danger')
        return redirect(url_for('rendimento.index'))
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Você não tem permissão para analisar rendimento.', 'danger')
        return redirect(url_for('rendimento.index'))
    
    reception = MeatReception.query.get_or_404(reception_id)
    
    # Calcular peso de entrada (da recepção)
    peso_entrada = 0.0
    if reception.tipo == 'frango':
        peso_entrada = float(reception.peso_frango or 0.0)
    else:
        from ..models import MeatPart
        parts = MeatPart.query.filter_by(reception_id=reception_id).all()
        for part in parts:
            peso_entrada += float(part.peso_bruto or 0.0)
    
    # Calcular peso de saída (dos cortes executados)
    execucoes = MeatCutExecution.query.filter_by(reception_id=reception_id).all()
    peso_saida = sum(float(e.peso_saida or 0.0) for e in execucoes)
    
    # Calcular perdas
    perdas_kg = peso_entrada - peso_saida
    rendimento_percentual = (peso_saida / peso_entrada * 100) if peso_entrada > 0 else 0
    
    analise = YieldAnalysis()
    analise.reception_id = reception_id
    analise.peso_entrada = peso_entrada
    analise.peso_saida = peso_saida
    analise.rendimento_percentual = rendimento_percentual
    analise.perdas_kg = perdas_kg
    analise.tipo_perda = 'ossos_aparas'  # pode ser melhorado
    analise.responsavel = current_user.name
    analise.observacao = f'Análise automática de {len(execucoes)} corte(s) executado(s)'
    
    try:
        db.session.add(analise)
        db.session.commit()
        flash(f'Análise de rendimento concluída! Rendimento: {rendimento_percentual:.2f}%', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao analisar rendimento: {e}', 'danger')
    
    return redirect(url_for('rendimento.index', reception_id=reception_id))

