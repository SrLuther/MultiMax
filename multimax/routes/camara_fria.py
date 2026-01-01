from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from ..models import ColdRoomOccupancy, ProductLot, TemperatureLog, TemperatureLocation, db
from sqlalchemy import func, desc

bp = Blueprint('camara_fria', __name__, url_prefix='/camara-fria')

# ============================================================================
# Constantes
# ============================================================================

CAPACIDADE_PADRAO_KG = 10000.0

# ============================================================================
# Funções auxiliares
# ============================================================================

def _get_locais_camara_fria():
    """Busca localizações de câmara fria"""
    locais = TemperatureLocation.query.filter_by(ativo=True, tipo='camara_fria').all()
    if not locais:
        # Se não houver locais cadastrados, usar valores padrão
        locais = [type('obj', (object,), {'nome': 'Câmara Fria Principal', 'temp_min': -18.0, 'temp_max': -12.0})()]
    return locais


def _calcular_ocupacao_local(local, capacidade_total: float = CAPACIDADE_PADRAO_KG) -> dict:
    """Calcula ocupação de um local"""
    lotes = ProductLot.query.filter_by(localizacao=local.nome, ativo=True).all()
    capacidade_utilizada = sum(l.quantidade_atual for l in lotes)
    percentual = (capacidade_utilizada / capacidade_total * 100) if capacidade_total > 0 else 0
    
    temp_atual = None
    temp_log = TemperatureLog.query.filter_by(local=local.nome).order_by(desc(TemperatureLog.data_registro)).first()
    if temp_log:
        temp_atual = temp_log.temperatura
    
    return {
        'localizacao': local.nome,
        'capacidade_total': capacidade_total,
        'capacidade_utilizada': capacidade_utilizada,
        'percentual': percentual,
        'temperatura_atual': temp_atual,
        'temp_min': local.temp_min if hasattr(local, 'temp_min') else -18.0,
        'temp_max': local.temp_max if hasattr(local, 'temp_max') else -12.0,
        'lotes_count': len(lotes)
    }


def _get_ocupacoes():
    """Busca todas as ocupações de câmara fria"""
    locais = _get_locais_camara_fria()
    return [_calcular_ocupacao_local(local) for local in locais]


# ============================================================================
# Rotas
# ============================================================================

@bp.route('/', methods=['GET'])
@login_required
def index():
    localizacao = request.args.get('localizacao', '').strip()
    ocupacoes = _get_ocupacoes()
    
    return render_template(
        'camara_fria/index.html',
        ocupacoes=ocupacoes,
        localizacao=localizacao,
        active_page='camara_fria'
    )

@bp.route('/registrar-ocupacao', methods=['POST'])
@login_required
def registrar_ocupacao():
    if current_user.nivel == 'visualizador':
        flash('Visualizadores não têm permissão para fazer alterações.', 'danger')
        return redirect(url_for('camara_fria.index'))
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Você não tem permissão para registrar ocupação.', 'danger')
        return redirect(url_for('camara_fria.index'))
    
    localizacao = request.form.get('localizacao', '').strip()
    capacidade_total = float(request.form.get('capacidade_total', '0') or '0')
    temperatura = float(request.form.get('temperatura', '0') or '0')
    observacao = request.form.get('observacao', '').strip()
    
    if not localizacao or capacidade_total <= 0:
        flash('Dados inválidos.', 'warning')
        return redirect(url_for('camara_fria.index'))
    
    # Calcular ocupação atual
    lotes = ProductLot.query.filter_by(localizacao=localizacao, ativo=True).all()
    capacidade_utilizada = sum(l.quantidade_atual for l in lotes)
    percentual = (capacidade_utilizada / capacidade_total * 100) if capacidade_total > 0 else 0
    
    ocupacao = ColdRoomOccupancy()
    ocupacao.localizacao = localizacao
    ocupacao.capacidade_total_kg = capacidade_total
    ocupacao.capacidade_utilizada_kg = capacidade_utilizada
    ocupacao.percentual_ocupacao = percentual
    ocupacao.temperatura_atual = temperatura
    ocupacao.observacao = observacao
    
    try:
        db.session.add(ocupacao)
        db.session.commit()
        flash('Ocupação registrada com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao registrar ocupação: {e}', 'danger')
    
    return redirect(url_for('camara_fria.index'))

