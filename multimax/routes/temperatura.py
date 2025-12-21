from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from werkzeug.utils import secure_filename
import os
from .. import db
from ..models import TemperatureLog, TemperatureLocation, TemperaturePhoto

bp = Blueprint('temperatura', __name__, url_prefix='/temperatura')

def _now():
    return datetime.now(ZoneInfo('America/Sao_Paulo'))

@bp.route('/', methods=['GET'], strict_slashes=False)
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    local_filter = request.args.get('local', '').strip()
    data_inicio = request.args.get('data_inicio', '').strip()
    data_fim = request.args.get('data_fim', '').strip()
    apenas_alertas = request.args.get('alertas', '') == '1'
    
    query = TemperatureLog.query
    if local_filter:
        query = query.filter(TemperatureLog.local == local_filter)
    if data_inicio:
        try:
            dt_ini = datetime.strptime(data_inicio, '%Y-%m-%d')
            query = query.filter(TemperatureLog.data_registro >= dt_ini)
        except ValueError:
            pass
    if data_fim:
        try:
            dt_fim = datetime.strptime(data_fim, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(TemperatureLog.data_registro < dt_fim)
        except ValueError:
            pass
    if apenas_alertas:
        query = query.filter(TemperatureLog.alerta.is_(True))
    
    query = query.order_by(TemperatureLog.data_registro.desc())
    per_page = int(current_app.config.get('PER_PAGE', 10))
    registros_pag = query.paginate(page=page, per_page=per_page, error_out=False)
    
    locais = TemperatureLocation.query.filter_by(ativo=True).order_by(TemperatureLocation.nome).all()
    
    total_registros = TemperatureLog.query.count()
    total_alertas = TemperatureLog.query.filter_by(alerta=True).count()
    ultimas_24h = TemperatureLog.query.filter(
        TemperatureLog.data_registro >= _now() - timedelta(hours=24)
    ).count()
    
    return render_template(
        'temperatura.html',
        active_page='temperatura',
        registros=registros_pag.items,
        registros_pag=registros_pag,
        locais=locais,
        local_filter=local_filter,
        data_inicio=data_inicio,
        data_fim=data_fim,
        apenas_alertas=apenas_alertas,
        total_registros=total_registros,
        total_alertas=total_alertas,
        ultimas_24h=ultimas_24h
    )

@bp.route('/registrar', methods=['POST'], strict_slashes=False)
@login_required
def registrar():
    if current_user.nivel not in ('operador', 'admin'):
        flash('Sem permissão para registrar temperatura.', 'warning')
        return redirect(url_for('temperatura.index'))
    
    local = (request.form.get('local') or '').strip()
    temperatura_str = (request.form.get('temperatura') or '').strip()
    observacao = (request.form.get('observacao') or '').strip()
    
    if not local or not temperatura_str:
        flash('Informe o local e a temperatura.', 'warning')
        return redirect(url_for('temperatura.index'))
    
    try:
        temperatura = float(temperatura_str.replace(',', '.'))
    except ValueError:
        flash('Temperatura inválida.', 'warning')
        return redirect(url_for('temperatura.index'))
    
    loc = TemperatureLocation.query.filter_by(nome=local).first()
    temp_min = loc.temp_min if loc else -18.0
    temp_max = loc.temp_max if loc else -12.0
    
    alerta = temperatura < temp_min or temperatura > temp_max
    
    reg = TemperatureLog()
    reg.local = local
    reg.temperatura = temperatura
    reg.temp_min = temp_min
    reg.temp_max = temp_max
    reg.observacao = observacao
    reg.usuario = current_user.username
    reg.alerta = alerta
    reg.data_registro = _now()
    
    db.session.add(reg)
    db.session.flush()
    
    foto = request.files.get('foto')
    if foto and foto.filename:
        upload_folder = os.path.join('static', 'uploads', 'temperatura')
        os.makedirs(upload_folder, exist_ok=True)
        filename = secure_filename(f'{reg.id}_{_now().strftime("%Y%m%d%H%M%S")}_{foto.filename}')
        filepath = os.path.join(upload_folder, filename)
        foto.save(filepath)
        
        photo = TemperaturePhoto()
        photo.temperature_log_id = reg.id
        photo.filename = filename
        photo.uploaded_by = current_user.username
        db.session.add(photo)
    
    db.session.commit()
    
    if alerta:
        flash(f'ALERTA: Temperatura {temperatura}°C fora da faixa permitida ({temp_min}°C a {temp_max}°C)!', 'danger')
    else:
        flash('Temperatura registrada com sucesso.', 'success')
    
    return redirect(url_for('temperatura.index'))

@bp.route('/excluir/<int:id>', methods=['POST'], strict_slashes=False)
@login_required
def excluir(id: int):
    if current_user.nivel != 'admin':
        flash('Apenas administradores podem excluir registros.', 'warning')
        return redirect(url_for('temperatura.index'))
    
    reg = TemperatureLog.query.get_or_404(id)
    try:
        db.session.delete(reg)
        db.session.commit()
        flash('Registro excluído.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir: {e}', 'danger')
    
    return redirect(url_for('temperatura.index'))

@bp.route('/locais', methods=['GET', 'POST'], strict_slashes=False)
@login_required
def locais():
    if current_user.nivel != 'admin':
        flash('Apenas administradores podem gerenciar locais.', 'warning')
        return redirect(url_for('temperatura.index'))
    
    if request.method == 'POST':
        nome = (request.form.get('nome') or '').strip()
        tipo = (request.form.get('tipo') or '').strip()
        temp_min_str = (request.form.get('temp_min') or '-18').strip()
        temp_max_str = (request.form.get('temp_max') or '-12').strip()
        
        if not nome:
            flash('Informe o nome do local.', 'warning')
            return redirect(url_for('temperatura.locais'))
        
        try:
            temp_min = float(temp_min_str.replace(',', '.'))
            temp_max = float(temp_max_str.replace(',', '.'))
        except ValueError:
            flash('Temperaturas inválidas.', 'warning')
            return redirect(url_for('temperatura.locais'))
        
        if TemperatureLocation.query.filter_by(nome=nome).first():
            flash('Já existe um local com este nome.', 'warning')
            return redirect(url_for('temperatura.locais'))
        
        loc = TemperatureLocation()
        loc.nome = nome
        loc.tipo = tipo
        loc.temp_min = temp_min
        loc.temp_max = temp_max
        loc.ativo = True
        
        db.session.add(loc)
        db.session.commit()
        flash('Local cadastrado com sucesso.', 'success')
        return redirect(url_for('temperatura.locais'))
    
    locais_list = TemperatureLocation.query.order_by(TemperatureLocation.nome).all()
    return render_template('temperatura_locais.html', active_page='temperatura', locais=locais_list)

@bp.route('/locais/editar/<int:id>', methods=['POST'], strict_slashes=False)
@login_required
def editar_local(id: int):
    if current_user.nivel != 'admin':
        flash('Apenas administradores podem editar locais.', 'warning')
        return redirect(url_for('temperatura.locais'))
    
    loc = TemperatureLocation.query.get_or_404(id)
    
    nome = (request.form.get('nome') or loc.nome).strip()
    tipo = (request.form.get('tipo') or loc.tipo or '').strip()
    temp_min_str = (request.form.get('temp_min') or str(loc.temp_min)).strip()
    temp_max_str = (request.form.get('temp_max') or str(loc.temp_max)).strip()
    ativo = request.form.get('ativo') == '1'
    
    try:
        loc.nome = nome
        loc.tipo = tipo
        loc.temp_min = float(temp_min_str.replace(',', '.'))
        loc.temp_max = float(temp_max_str.replace(',', '.'))
        loc.ativo = ativo
        db.session.commit()
        flash('Local atualizado.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar: {e}', 'danger')
    
    return redirect(url_for('temperatura.locais'))

@bp.route('/locais/excluir/<int:id>', methods=['POST'], strict_slashes=False)
@login_required
def excluir_local(id: int):
    if current_user.nivel != 'admin':
        flash('Apenas administradores podem excluir locais.', 'warning')
        return redirect(url_for('temperatura.locais'))
    
    loc = TemperatureLocation.query.get_or_404(id)
    try:
        db.session.delete(loc)
        db.session.commit()
        flash('Local excluído.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir: {e}', 'danger')
    
    return redirect(url_for('temperatura.locais'))

@bp.route('/fotos/<int:id>', methods=['GET'], strict_slashes=False)
@login_required
def get_fotos(id: int):
    reg = TemperatureLog.query.get_or_404(id)
    fotos_data = []
    for foto in reg.fotos:
        fotos_data.append({
            'id': foto.id,
            'filename': foto.filename,
            'created_at': foto.created_at.strftime('%d/%m/%Y %H:%M:%S') if foto.created_at else '-',
            'uploaded_by': foto.uploaded_by or '-'
        })
    return jsonify({'fotos': fotos_data})
