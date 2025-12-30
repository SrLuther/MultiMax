from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from ..models import TemperatureProductAlert, TemperatureLog, ProductLot, Produto, db
from sqlalchemy import func, desc

bp = Blueprint('integracao_temp', __name__, url_prefix='/integracao-temperatura')

@bp.route('/alertas', methods=['GET'])
@login_required
def alertas():
    apenas_bloqueados = request.args.get('bloqueados', '') == '1'
    
    query = TemperatureProductAlert.query.filter_by(bloqueado=True) if apenas_bloqueados else TemperatureProductAlert.query
    
    alertas = query.order_by(desc(TemperatureProductAlert.data_alerta)).limit(100).all()
    
    return render_template('integracao_temp/alertas.html',
                         alertas=alertas,
                         apenas_bloqueados=apenas_bloqueados,
                         active_page='integracao_temp')

@bp.route('/verificar-temperaturas', methods=['POST'])
@login_required
def verificar_temperaturas():
    if current_user.nivel not in ['admin', 'DEV']:
        flash('Apenas administradores podem executar verificação.', 'danger')
        return redirect(url_for('integracao_temp.alertas'))
    
    # Buscar registros de temperatura das últimas 2 horas com alerta
    duas_horas_atras = datetime.now(ZoneInfo('America/Sao_Paulo')) - timedelta(hours=2)
    logs_alerta = TemperatureLog.query.filter(
        TemperatureLog.data_registro >= duas_horas_atras,
        TemperatureLog.alerta == True
    ).all()
    
    alertas_criados = 0
    for log in logs_alerta:
        # Buscar lotes naquela localização
        lotes = ProductLot.query.filter_by(localizacao=log.local, ativo=True).all()
        
        for lot in lotes:
            # Verificar se já existe alerta ativo
            alerta_existente = TemperatureProductAlert.query.filter_by(
                lot_id=lot.id,
                bloqueado=True
            ).first()
            
            if not alerta_existente:
                alerta = TemperatureProductAlert()
                alerta.temperature_log_id = log.id
                alerta.lot_id = lot.id
                alerta.produto_id = lot.produto_id
                alerta.bloqueado = True
                alerta.observacao = f'Temperatura fora da faixa: {log.temperatura}°C (ideal: {log.temp_min}°C a {log.temp_max}°C)'
                
                try:
                    db.session.add(alerta)
                    alertas_criados += 1
                except Exception:
                    db.session.rollback()
    
    try:
        db.session.commit()
        flash(f'{alertas_criados} alertas criados e produtos bloqueados!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao verificar temperaturas: {e}', 'danger')
    
    return redirect(url_for('integracao_temp.alertas'))

@bp.route('/alerta/<int:id>/resolver', methods=['POST'])
@login_required
def resolver_alerta(id):
    if current_user.nivel == 'visualizador':
        flash('Visualizadores não têm permissão para fazer alterações.', 'danger')
        return redirect(url_for('integracao_temp.alertas'))
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Você não tem permissão para resolver alertas.', 'danger')
        return redirect(url_for('integracao_temp.alertas'))
    
    alerta = TemperatureProductAlert.query.get_or_404(id)
    alerta.bloqueado = False
    alerta.data_resolucao = datetime.now(ZoneInfo('America/Sao_Paulo'))
    alerta.resolvido_por = current_user.name
    alerta.observacao = (alerta.observacao or '') + f' | Resolvido por: {current_user.name}'
    
    try:
        db.session.commit()
        flash('Alerta resolvido e produtos desbloqueados!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao resolver alerta: {e}', 'danger')
    
    return redirect(url_for('integracao_temp.alertas'))

