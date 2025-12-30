from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from ..models import MeatMaturation, MeatReception, MeatPart, db
from sqlalchemy import func, desc

bp = Blueprint('maturacao', __name__, url_prefix='/maturacao')

@bp.route('/', methods=['GET'])
@login_required
def index():
    status = request.args.get('status', '').strip()
    
    query = MeatMaturation.query
    if status:
        query = query.filter_by(status=status)
    else:
        query = query.filter_by(status='maturacao')
    
    maturacoes = query.order_by(MeatMaturation.data_inicio).all()
    
    # Calcular dias decorridos e status
    hoje = datetime.now(ZoneInfo('America/Sao_Paulo'))
    for mat in maturacoes:
        if mat.data_inicio:
            dias_decorridos = (hoje - mat.data_inicio).days
            mat.dias_decorridos = dias_decorridos
            if mat.data_prevista_pronto:
                dias_restantes = (mat.data_prevista_pronto - hoje).days
                mat.dias_restantes = dias_restantes
                if dias_restantes <= 0 and mat.status == 'maturacao':
                    mat.status_alerta = 'pronto'
                elif dias_restantes <= 2:
                    mat.status_alerta = 'atencao'
                else:
                    mat.status_alerta = 'normal'
    
    return render_template('maturacao/index.html',
                         maturacoes=maturacoes,
                         status=status,
                         active_page='maturacao')

@bp.route('/nova', methods=['GET', 'POST'])
@login_required
def nova():
    if current_user.nivel == 'visualizador':
        flash('Visualizadores não têm permissão para fazer alterações.', 'danger')
        return redirect(url_for('maturacao.index'))
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Você não tem permissão para criar maturações.', 'danger')
        return redirect(url_for('maturacao.index'))
    
    if request.method == 'POST':
        reception_id = int(request.form.get('reception_id', '0') or '0')
        part_id = int(request.form.get('part_id', '0') or '0') if request.form.get('part_id') else None
        dias_maturacao = int(request.form.get('dias_maturacao', '0') or '0')
        temperatura_ideal = float(request.form.get('temperatura_ideal', '2.0') or '2.0')
        umidade_ideal = float(request.form.get('umidade_ideal', '85.0') or '85.0')
        observacao = request.form.get('observacao', '').strip()
        
        if not reception_id or dias_maturacao <= 0:
            flash('Dados inválidos para maturação.', 'warning')
            return redirect(url_for('maturacao.nova'))
        
        mat = MeatMaturation()
        mat.reception_id = reception_id
        mat.part_id = part_id
        mat.dias_maturacao = dias_maturacao
        mat.temperatura_ideal = temperatura_ideal
        mat.umidade_ideal = umidade_ideal
        mat.observacao = observacao
        
        hoje = datetime.now(ZoneInfo('America/Sao_Paulo'))
        mat.data_prevista_pronto = hoje + timedelta(days=dias_maturacao)
        
        try:
            db.session.add(mat)
            db.session.commit()
            flash('Maturação iniciada com sucesso!', 'success')
            return redirect(url_for('maturacao.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao iniciar maturação: {e}', 'danger')
    
    recepcoes = MeatReception.query.order_by(desc(MeatReception.data)).limit(50).all()
    return render_template('maturacao/nova.html',
                         recepcoes=recepcoes,
                         active_page='maturacao')

@bp.route('/<int:id>/finalizar', methods=['POST'])
@login_required
def finalizar(id):
    if current_user.nivel == 'visualizador':
        flash('Visualizadores não têm permissão para fazer alterações.', 'danger')
        return redirect(url_for('maturacao.index'))
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Você não tem permissão para finalizar maturações.', 'danger')
        return redirect(url_for('maturacao.index'))
    
    mat = MeatMaturation.query.get_or_404(id)
    mat.status = 'pronto'
    mat.data_pronto = datetime.now(ZoneInfo('America/Sao_Paulo'))
    
    try:
        db.session.commit()
        flash('Maturação finalizada!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao finalizar maturação: {e}', 'danger')
    
    return redirect(url_for('maturacao.index'))

