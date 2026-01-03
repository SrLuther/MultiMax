from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, session
from flask_login import login_required, current_user
from .. import db
from ..models import Collaborator, User, TimeOffRecord, Holiday, SystemLog, Vacation, MedicalCertificate, JornadaArchive
from ..filename_utils import secure_filename
from datetime import datetime, date
from zoneinfo import ZoneInfo
from sqlalchemy import func, or_
import io
import csv
import os
from openpyxl import Workbook

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

bp = Blueprint('jornada', __name__, url_prefix='/jornada')

# ============================================================================
# Funções auxiliares
# ============================================================================

def _get_collaborator_display_name(collaborator):
    """Retorna o nome de exibição do colaborador (User.name se tiver user, senão Collaborator.name)"""
    if not collaborator:
        return None
    if collaborator.user_id and collaborator.user:
        return collaborator.user.name
    return collaborator.name

def _get_collaborator_by_user_or_id(user_id=None, collaborator_id=None):
    """Retorna colaborador por user_id ou collaborator_id (tratando como uma coisa só)"""
    if collaborator_id:
        return Collaborator.query.get(collaborator_id)
    if user_id:
        return Collaborator.query.filter_by(user_id=user_id).first()
    return None

def _calculate_collaborator_balance(collaborator_id, date_start=None, date_end=None):
    """Calcula o saldo completo de um colaborador"""
    filters = [TimeOffRecord.collaborator_id == collaborator_id]
    
    if date_start:
        filters.append(TimeOffRecord.date >= date_start)
    if date_end:
        filters.append(TimeOffRecord.date <= date_end)
    
    # Total bruto de horas (apenas positivas)
    hq = TimeOffRecord.query.filter(
        *filters,
        TimeOffRecord.record_type == 'horas'
    )
    total_bruto_hours = sum(float(r.hours or 0.0) for r in hq.all() if (r.hours or 0.0) > 0)
    
    # Dias convertidos das horas (8h = 1 dia)
    days_from_hours = int(total_bruto_hours // 8.0) if total_bruto_hours >= 0.0 else 0
    residual_hours = (total_bruto_hours % 8.0) if total_bruto_hours >= 0.0 else 0.0
    
    # Folgas adicionais
    cq = TimeOffRecord.query.filter(
        *filters,
        TimeOffRecord.record_type == 'folga_adicional'
    )
    credits_sum = int(cq.with_entities(func.coalesce(func.sum(TimeOffRecord.days), 0)).scalar() or 0)
    
    # Folgas usadas
    aq = TimeOffRecord.query.filter(
        *filters,
        TimeOffRecord.record_type == 'folga_usada'
    )
    assigned_sum = int(aq.with_entities(func.coalesce(func.sum(TimeOffRecord.days), 0)).scalar() or 0)
    
    # Conversões em dinheiro
    vq = TimeOffRecord.query.filter(
        *filters,
        TimeOffRecord.record_type == 'conversao'
    )
    converted_sum = int(vq.with_entities(func.coalesce(func.sum(TimeOffRecord.days), 0)).scalar() or 0)
    
    # Saldo final = folgas adicionais + dias convertidos - folgas usadas - conversões
    saldo_days = credits_sum + days_from_hours - assigned_sum - converted_sum
    
    return {
        'total_bruto_hours': total_bruto_hours,
        'days_from_hours': days_from_hours,
        'residual_hours': residual_hours,
        'credits_sum': credits_sum,
        'assigned_sum': assigned_sum,
        'converted_sum': converted_sum,
        'saldo_days': saldo_days
    }

def _get_all_collaborators():
    """Retorna todos os colaboradores ativos com informações de usuário (User e Collaborator são uma coisa só)"""
    return Collaborator.query.filter_by(active=True).order_by(Collaborator.name.asc()).all()

def _get_all_collaborators_with_users():
    """Retorna todos os colaboradores ativos com informações de usuário para exibição"""
    colaboradores = Collaborator.query.filter_by(active=True).order_by(Collaborator.name.asc()).all()
    result = []
    for colab in colaboradores:
        result.append({
            'id': colab.id,
            'name': colab.user.name if colab.user else colab.name,
            'collaborator': colab,
            'user': colab.user
        })
    return result

# ============================================================================
# Rotas principais
# ============================================================================

@bp.route('/unificado', methods=['GET', 'POST'], strict_slashes=False)
@login_required
def unificado():
    """Rota de compatibilidade - redireciona para index mantendo parâmetros"""
    collaborator_id = request.args.get('collaborator_id', type=int) or request.form.get('collaborator_id', type=int)
    if collaborator_id:
        return redirect(url_for('jornada.index', collaborator_id=collaborator_id))
    return redirect(url_for('jornada.index'))

@bp.route('/', methods=['GET'], strict_slashes=False)
@login_required
def index():
    """Página principal do sistema de Jornada - integrado com User e Collaborator"""
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('home.index'))
    
    # Filtros (User e Collaborator são uma coisa só)
    collaborator_id = request.args.get('collaborator_id', type=int)
    user_id = request.args.get('user_id', type=int)
    data_inicio = request.args.get('inicio', '').strip()
    data_fim = request.args.get('fim', '').strip()
    record_type = request.args.get('tipo', '').strip()
    
    # Processar datas
    di = None
    df = None
    if data_inicio:
        try:
            di = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        except Exception:
            pass
    if data_fim:
        try:
            df = datetime.strptime(data_fim, '%Y-%m-%d').date()
        except Exception:
            pass
    
    # Se filtrar por user_id, buscar colaborador vinculado (são a mesma coisa)
    if user_id and not collaborator_id:
        collab = _get_collaborator_by_user_or_id(user_id=user_id)
        if collab:
            collaborator_id = collab.id
    
    # Buscar todos os colaboradores (User e Collaborator unificados)
    colaboradores = _get_all_collaborators()
    
    # Buscar registros
    records = []
    if collaborator_id:
        q = TimeOffRecord.query.filter(TimeOffRecord.collaborator_id == collaborator_id)
        if di:
            q = q.filter(TimeOffRecord.date >= di)
        if df:
            q = q.filter(TimeOffRecord.date <= df)
        if record_type:
            q = q.filter(TimeOffRecord.record_type == record_type)
        records = q.order_by(TimeOffRecord.date.desc(), TimeOffRecord.id.desc()).limit(100).all()
    
    # Calcular estatísticas
    stats = None
    selected_collaborator = None
    
    if collaborator_id:
        selected_collaborator = Collaborator.query.get(collaborator_id)
        if selected_collaborator:
            stats = _calculate_collaborator_balance(collaborator_id, di, df)
    
    # Estatísticas gerais (todos os colaboradores - User e Collaborator são uma coisa só)
    all_stats = []
    for colab in colaboradores:
        balance = _calculate_collaborator_balance(colab.id, di, df)
        all_stats.append({
            'collaborator': colab,
            'display_name': _get_collaborator_display_name(colab),
            'balance': balance
        })
    
    # Buscar férias e atestados do colaborador selecionado
    ferias = []
    atestados = []
    if selected_collaborator:
        ferias = Vacation.query.filter_by(collaborator_id=selected_collaborator.id).order_by(Vacation.data_inicio.desc()).limit(50).all()
        atestados = MedicalCertificate.query.filter_by(collaborator_id=selected_collaborator.id).order_by(MedicalCertificate.data_inicio.desc()).limit(50).all()

    return render_template(
        'jornada/index.html',
        colaboradores=colaboradores,
        records=records,
        selected_collaborator=selected_collaborator,
        stats=stats,
        all_stats=all_stats,
        ferias=ferias,
        atestados=atestados,
        collaborator_id=collaborator_id,
        user_id=user_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        record_type=record_type,
        active_page='jornada'
    )

@bp.route('/novo', methods=['GET', 'POST'], strict_slashes=False)
@login_required
def novo():
    """Criar novo registro de jornada"""
    if current_user.nivel not in ('admin', 'DEV', 'operador'):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('jornada.index'))
    
    if request.method == 'POST':
        try:
            collaborator_id = int(request.form.get('collaborator_id', 0))
            if not collaborator_id:
                flash('Colaborador é obrigatório.', 'danger')
                return redirect(url_for('jornada.novo'))
            
            data_str = request.form.get('date', '').strip()
            if not data_str:
                flash('Data é obrigatória.', 'danger')
                return redirect(url_for('jornada.novo'))
            
            try:
                record_date = datetime.strptime(data_str, '%Y-%m-%d').date()
            except Exception:
                flash('Data inválida.', 'danger')
                return redirect(url_for('jornada.novo'))
            
            record_type = request.form.get('record_type', '').strip()
            if record_type not in ('horas', 'folga_adicional', 'folga_usada', 'conversao'):
                flash('Tipo de registro inválido.', 'danger')
                return redirect(url_for('jornada.novo'))
            
            # Criar registro
            record = TimeOffRecord()
            record.collaborator_id = collaborator_id
            record.date = record_date
            record.record_type = record_type
            record.origin = request.form.get('origin', 'manual').strip()
            record.notes = request.form.get('notes', '').strip()
            record.created_by = current_user.name or current_user.username
            
            if record_type == 'horas':
                hours = float(request.form.get('hours', 0))
                record.hours = hours
            elif record_type in ('folga_adicional', 'folga_usada'):
                days = int(request.form.get('days', 1))
                record.days = days
            elif record_type == 'conversao':
                days = int(request.form.get('days', 0))
                amount_paid = float(request.form.get('amount_paid', 0))
                rate_per_day = float(request.form.get('rate_per_day', 65.0))
                record.days = days
                record.amount_paid = amount_paid
                record.rate_per_day = rate_per_day
            
            db.session.add(record)
            
            # Aplicar conversão automática se for horas
            if record_type == 'horas' and record.hours and record.hours > 0:
                try:
                    total_hours = db.session.query(func.coalesce(func.sum(TimeOffRecord.hours), 0.0)).filter(
                        TimeOffRecord.collaborator_id == collaborator_id,
                        TimeOffRecord.record_type == 'horas'
                    ).scalar() or 0.0
                    total_hours = float(total_hours)
                    
                    auto_credits = db.session.query(func.coalesce(func.sum(TimeOffRecord.days), 0)).filter(
                        TimeOffRecord.collaborator_id == collaborator_id,
                        TimeOffRecord.record_type == 'folga_adicional',
                        TimeOffRecord.origin == 'horas'
                    ).scalar() or 0
                    auto_credits = int(auto_credits)
                    
                    desired_credits = int(total_hours // 8.0)
                    missing = max(0, desired_credits - auto_credits)
                    
                    if missing > 0:
                        # Criar folgas adicionais
                        for _ in range(missing):
                            tor = TimeOffRecord()
                            tor.collaborator_id = collaborator_id
                            tor.date = date.today()
                            tor.record_type = 'folga_adicional'
                            tor.days = 1
                            tor.origin = 'horas'
                            tor.notes = 'Crédito automático por 8h no banco de horas'
                            tor.created_by = 'sistema'
                            db.session.add(tor)
                        
                        # Criar ajustes de horas
                        for _ in range(missing):
                            tor_adj = TimeOffRecord()
                            tor_adj.collaborator_id = collaborator_id
                            tor_adj.date = date.today()
                            tor_adj.record_type = 'horas'
                            tor_adj.hours = -8.0
                            tor_adj.origin = 'sistema'
                            tor_adj.notes = 'Conversão automática: -8h por +1 dia de folga'
                            tor_adj.created_by = 'sistema'
                            db.session.add(tor_adj)
                        
                        flash(f'Registro adicionado. Conversão automática: +{missing} dia(s) e -{missing*8}h.', 'success')
                    else:
                        flash('Registro adicionado com sucesso.', 'success')
                except Exception:
                    flash('Registro adicionado com sucesso.', 'success')
            else:
                flash('Registro adicionado com sucesso.', 'success')
            
            db.session.commit()
            return redirect(url_for('jornada.index', collaborator_id=collaborator_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar registro: {e}', 'danger')
            return redirect(url_for('jornada.novo'))
    
    # GET - mostrar formulário
    colaboradores = _get_all_collaborators()
    colaboradores_com_usuarios = _get_all_collaborators_with_users()
    hoje = date.today().strftime('%Y-%m-%d')
    return render_template('jornada/novo.html', 
                         colaboradores=colaboradores, 
                         colaboradores_com_usuarios=colaboradores_com_usuarios,
                         active_page='jornada', 
                         hoje=hoje)

@bp.route('/editar/<int:id>', methods=['GET', 'POST'], strict_slashes=False)
@login_required
def editar(id):
    """Editar registro de jornada"""
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Apenas Administradores podem editar registros.', 'danger')
        return redirect(url_for('jornada.index'))
    
    record = TimeOffRecord.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            data_str = request.form.get('date', '').strip()
            if data_str:
                record.date = datetime.strptime(data_str, '%Y-%m-%d').date()
            
            record.notes = request.form.get('notes', '').strip()
            
            if record.record_type == 'horas':
                hours = request.form.get('hours', '')
                if hours:
                    record.hours = float(hours)
            elif record.record_type in ('folga_adicional', 'folga_usada'):
                days = request.form.get('days', '')
                if days:
                    record.days = int(days)
            elif record.record_type == 'conversao':
                days = request.form.get('days', '')
                amount_paid = request.form.get('amount_paid', '')
                if days:
                    record.days = int(days)
                if amount_paid:
                    record.amount_paid = float(amount_paid)
            
            db.session.commit()
            flash('Registro atualizado com sucesso.', 'success')
            return redirect(url_for('jornada.index', collaborator_id=record.collaborator_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar registro: {e}', 'danger')
    
    colaboradores = _get_all_collaborators()
    return render_template('jornada/editar.html', record=record, colaboradores=colaboradores, active_page='jornada')

@bp.route('/excluir/<int:id>', methods=['POST'], strict_slashes=False)
@login_required
def excluir(id):
    """Excluir registro de jornada"""
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Apenas Administradores podem excluir registros.', 'danger')
        return redirect(url_for('jornada.index'))
    
    record = TimeOffRecord.query.get_or_404(id)
    collaborator_id = record.collaborator_id
    
    try:
        db.session.delete(record)
        db.session.commit()
        flash('Registro excluído com sucesso.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir registro: {e}', 'danger')

    return redirect(url_for('jornada.index', collaborator_id=collaborator_id))

@bp.route('/converter_horas', methods=['POST'], strict_slashes=False)
@login_required
def converter_horas():
    """Converter horas em dias manualmente (apenas admin/dev)"""
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('jornada.index'))
    
    collaborator_id = request.form.get('collaborator_id', type=int)
    if not collaborator_id:
        flash('Colaborador não especificado.', 'danger')
        return redirect(url_for('jornada.index'))
    
    try:
        balance = _calculate_collaborator_balance(collaborator_id)
        total_bruto_hours = balance['total_bruto_hours']
        days_from_hours = balance['days_from_hours']
        
        # Verificar quantos dias já foram convertidos
        auto_credits = db.session.query(func.coalesce(func.sum(TimeOffRecord.days), 0)).filter(
            TimeOffRecord.collaborator_id == collaborator_id,
            TimeOffRecord.record_type == 'folga_adicional',
            TimeOffRecord.origin == 'horas'
        ).scalar() or 0
        auto_credits = int(auto_credits)
        
        missing = max(0, days_from_hours - auto_credits)
        
        if missing > 0:
            # Criar folgas adicionais
            for _ in range(missing):
                tor = TimeOffRecord()
                tor.collaborator_id = collaborator_id
                tor.date = date.today()
                tor.record_type = 'folga_adicional'
                tor.days = 1
                tor.origin = 'horas'
                tor.notes = 'Crédito automático por 8h no banco de horas'
                tor.created_by = current_user.name or current_user.username
                db.session.add(tor)
            
            # Criar ajustes de horas
            for _ in range(missing):
                tor_adj = TimeOffRecord()
                tor_adj.collaborator_id = collaborator_id
                tor_adj.date = date.today()
                tor_adj.record_type = 'horas'
                tor_adj.hours = -8.0
                tor_adj.origin = 'sistema'
                tor_adj.notes = 'Conversão automática: -8h por +1 dia de folga'
                tor_adj.created_by = current_user.name or current_user.username
                db.session.add(tor_adj)
            
            db.session.commit()
            flash(f'Conversão realizada: +{missing} dia(s) e -{missing*8}h.', 'success')
        else:
            flash('Não há horas suficientes para conversão ou já foram convertidas.', 'info')
        
        return redirect(url_for('jornada.index', collaborator_id=collaborator_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao converter horas: {e}', 'danger')
        return redirect(url_for('jornada.index', collaborator_id=collaborator_id))

@bp.route('/export', methods=['GET'], strict_slashes=False)
@login_required
def export():
    """Exportar registros de jornada"""
    if current_user.nivel not in ('operador', 'admin', 'DEV'):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('jornada.index'))
    
    collaborator_id = request.args.get('collaborator_id', type=int)
    data_inicio = request.args.get('inicio', '').strip()
    data_fim = request.args.get('fim', '').strip()
    
    di = None
    df = None
    if data_inicio:
        try:
            di = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        except Exception:
            pass
    if data_fim:
        try:
            df = datetime.strptime(data_fim, '%Y-%m-%d').date()
        except Exception:
            pass
    
    q = TimeOffRecord.query
    if collaborator_id:
        q = q.filter(TimeOffRecord.collaborator_id == collaborator_id)
    if di:
        q = q.filter(TimeOffRecord.date >= di)
    if df:
        q = q.filter(TimeOffRecord.date <= df)
    
    records = q.order_by(TimeOffRecord.date.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Data', 'Colaborador/Usuário', 'Tipo', 'Horas', 'Dias', 'Valor Pago', 'Origem', 'Observações', 'Criado por'])
    
    for r in records:
        collab = r.collaborator
        display_name = _get_collaborator_display_name(collab)
        
        writer.writerow([
            r.date.strftime('%d/%m/%Y'),
            display_name or collab.name,
            r.record_type,
            r.hours or '',
            r.days or '',
            r.amount_paid or '',
            r.origin or '',
            r.notes or '',
            r.created_by or ''
        ])
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'jornada_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )

# ============================================================================
# Rotas de Férias
# ============================================================================

@bp.route('/ferias/adicionar', methods=['POST'])
@login_required
def ferias_adicionar():
    """Adicionar férias para um colaborador"""
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('jornada.index'))
    try:
        cid_str = (request.form.get('collaborator_id') or '').strip()
        di_str = (request.form.get('data_inicio') or '').strip()
        df_str = (request.form.get('data_fim') or '').strip()
        if not cid_str or not di_str or not df_str:
            flash('Dados obrigatórios ausentes.', 'warning')
            return redirect(url_for('jornada.index', collaborator_id=cid_str if cid_str else None))
        cid = int(cid_str)
        data_inicio = datetime.strptime(di_str, '%Y-%m-%d').date()
        data_fim = datetime.strptime(df_str, '%Y-%m-%d').date()
        observacao = request.form.get('observacao', '').strip()
        
        if data_fim < data_inicio:
            flash('Data final deve ser maior ou igual à data inicial.', 'warning')
            return redirect(url_for('jornada.index', collaborator_id=cid))
        
        v = Vacation()
        v.collaborator_id = cid
        v.data_inicio = data_inicio
        v.data_fim = data_fim
        v.observacao = observacao
        v.criado_por = current_user.name
        db.session.add(v)
        db.session.commit()
        flash('Férias registradas com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao registrar férias: {e}', 'danger')
    return redirect(url_for('jornada.index', collaborator_id=cid_str if cid_str else None))

@bp.route('/ferias/<int:id>/excluir', methods=['POST'])
@login_required
def ferias_excluir(id: int):
    """Excluir férias"""
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('jornada.index'))
    v = Vacation.query.get_or_404(id)
    collaborator_id = v.collaborator_id
    try:
        db.session.delete(v)
        db.session.commit()
        flash('Férias excluídas.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir: {e}', 'danger')
    return redirect(url_for('jornada.index', collaborator_id=collaborator_id))

# ============================================================================
# Rotas de Atestados Médicos
# ============================================================================

@bp.route('/atestado/adicionar', methods=['POST'])
@login_required
def atestado_adicionar():
    """Adicionar atestado médico para um colaborador"""
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('jornada.index'))
    try:
        cid_str = (request.form.get('collaborator_id') or '').strip()
        di_str = (request.form.get('data_inicio') or '').strip()
        df_str = (request.form.get('data_fim') or '').strip()
        if not cid_str or not di_str or not df_str:
            flash('Dados obrigatórios ausentes.', 'warning')
            return redirect(url_for('jornada.index', collaborator_id=cid_str if cid_str else None))
        cid = int(cid_str)
        data_inicio = datetime.strptime(di_str, '%Y-%m-%d').date()
        data_fim = datetime.strptime(df_str, '%Y-%m-%d').date()
        motivo = request.form.get('motivo', '').strip()
        cid_code = request.form.get('cid', '').strip()
        medico = request.form.get('medico', '').strip()
        
        if data_fim < data_inicio:
            flash('Data final deve ser maior ou igual à data inicial.', 'warning')
            return redirect(url_for('jornada.index', collaborator_id=cid))
        
        dias = (data_fim - data_inicio).days + 1
        
        foto_filename = None
        if 'foto_atestado' in request.files:
            foto = request.files['foto_atestado']
            if foto and foto.filename:
                if not allowed_file(foto.filename):
                    flash('Tipo de arquivo não permitido. Use imagens (PNG, JPG, JPEG, GIF).', 'warning')
                    return redirect(url_for('jornada.index', collaborator_id=cid))
                
                foto.seek(0, 2)
                size = foto.tell()
                foto.seek(0)
                if size > MAX_UPLOAD_SIZE:
                    flash('Arquivo muito grande. Máximo 10MB.', 'warning')
                    return redirect(url_for('jornada.index', collaborator_id=cid))
                
                upload_dir = os.path.join('static', 'uploads', 'atestados')
                os.makedirs(upload_dir, exist_ok=True)
                safe_name = secure_filename(foto.filename)
                ext = safe_name.rsplit('.', 1)[1].lower() if '.' in safe_name else 'jpg'
                foto_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{cid}.{ext}"
                foto.save(os.path.join(upload_dir, foto_filename))
        
        m = MedicalCertificate()
        m.collaborator_id = cid
        m.data_inicio = data_inicio
        m.data_fim = data_fim
        m.dias = dias
        m.motivo = motivo
        m.cid = cid_code
        m.medico = medico
        m.foto_atestado = foto_filename
        m.criado_por = current_user.name
        db.session.add(m)
        db.session.commit()
        flash('Atestado registrado com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao registrar atestado: {e}', 'danger')
    return redirect(url_for('jornada.index', collaborator_id=cid_str if cid_str else None))

@bp.route('/atestado/<int:id>/excluir', methods=['POST'])
@login_required
def atestado_excluir(id: int):
    """Excluir atestado médico"""
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('jornada.index'))
    m = MedicalCertificate.query.get_or_404(id)
    collaborator_id = m.collaborator_id
    try:
        if m.foto_atestado:
            path = os.path.join('static', 'uploads', 'atestados', m.foto_atestado)
            if os.path.exists(path):
                os.remove(path)
        db.session.delete(m)
        db.session.commit()
        flash('Atestado excluído.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir: {e}', 'danger')
    return redirect(url_for('jornada.index', collaborator_id=collaborator_id))



@bp.route('/arquivar', methods=['GET', 'POST'])
@login_required
def arquivar():
    """Arquivar todos os registros de jornada e reiniciar contadores"""
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Acesso negado. Apenas Administradores podem arquivar dados.', 'danger')
        return redirect(url_for('jornada.index'))
    
    if request.method == 'POST':
        period_start_str = request.form.get('period_start', '').strip()
        period_end_str = request.form.get('period_end', '').strip()
        description = request.form.get('description', '').strip()
        
        if not period_start_str or not period_end_str:
            flash('Período de início e fim são obrigatórios.', 'danger')
            first_record = TimeOffRecord.query.order_by(TimeOffRecord.date.asc()).first()
            last_record = TimeOffRecord.query.order_by(TimeOffRecord.date.desc()).first()
            suggested_start = first_record.date if first_record else date.today()
            suggested_end = last_record.date if last_record else date.today()
            return render_template('jornada/arquivar.html', active_page='jornada', suggested_start=suggested_start, suggested_end=suggested_end)
        
        try:
            period_start = datetime.strptime(period_start_str, '%Y-%m-%d').date()
            period_end = datetime.strptime(period_end_str, '%Y-%m-%d').date()
            
            if period_start > period_end:
                flash('Data de início deve ser anterior à data de fim.', 'danger')
                first_record = TimeOffRecord.query.order_by(TimeOffRecord.date.asc()).first()
                last_record = TimeOffRecord.query.order_by(TimeOffRecord.date.desc()).first()
                suggested_start = first_record.date if first_record else date.today()
                suggested_end = last_record.date if last_record else date.today()
                return render_template('jornada/arquivar.html', active_page='jornada', suggested_start=suggested_start, suggested_end=suggested_end)
            
            records_to_archive = TimeOffRecord.query.filter(TimeOffRecord.date >= period_start, TimeOffRecord.date <= period_end).all()
            
            if not records_to_archive:
                flash('Nenhum registro encontrado para arquivar no período especificado.', 'warning')
                first_record = TimeOffRecord.query.order_by(TimeOffRecord.date.asc()).first()
                last_record = TimeOffRecord.query.order_by(TimeOffRecord.date.desc()).first()
                suggested_start = first_record.date if first_record else date.today()
                suggested_end = last_record.date if last_record else date.today()
                return render_template('jornada/arquivar.html', active_page='jornada', suggested_start=suggested_start, suggested_end=suggested_end)
            
            archived_count = 0
            archived_at = datetime.now(ZoneInfo('America/Sao_Paulo'))
            
            for record in records_to_archive:
                archive_record = JornadaArchive(
                    archive_period_start=period_start,
                    archive_period_end=period_end,
                    archived_at=archived_at,
                    archived_by=current_user.username or current_user.name,
                    description=description,
                    original_record_id=record.id,
                    collaborator_id=record.collaborator_id,
                    date=record.date,
                    record_type=record.record_type,
                    hours=record.hours,
                    days=record.days,
                    amount_paid=record.amount_paid,
                    rate_per_day=record.rate_per_day,
                    origin=record.origin,
                    notes=record.notes,
                    created_at=record.created_at,
                    created_by=record.created_by
                )
                db.session.add(archive_record)
                archived_count += 1
            
            for record in records_to_archive:
                db.session.delete(record)
            
            db.session.commit()
            flash(f'{archived_count} registro(s) arquivado(s) com sucesso. Todos os dados foram reiniciados.', 'success')
            return redirect(url_for('jornada.index'))
            
        except ValueError:
            flash('Formato de data inválido. Use o formato YYYY-MM-DD.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao arquivar: {e}', 'danger')
    
    first_record = TimeOffRecord.query.order_by(TimeOffRecord.date.asc()).first()
    last_record = TimeOffRecord.query.order_by(TimeOffRecord.date.desc()).first()
    suggested_start = first_record.date if first_record else date.today()
    suggested_end = last_record.date if last_record else date.today()
    return render_template('jornada/arquivar.html', active_page='jornada', suggested_start=suggested_start, suggested_end=suggested_end)


@bp.route('/historico/<int:collaborator_id>')
@login_required
def historico_colaborador(collaborator_id):
    """Visualizar histórico completo (arquivado + atual) de um colaborador"""
    collab = Collaborator.query.get_or_404(collaborator_id)
    
    if current_user.nivel not in ('admin', 'DEV'):
        user_collab = Collaborator.query.filter_by(user_id=current_user.id).first()
        if not user_collab or user_collab.id != collaborator_id:
            flash('Acesso negado. Você só pode visualizar seu próprio histórico.', 'danger')
            return redirect(url_for('usuarios.perfil'))
    
    archived_records = JornadaArchive.query.filter_by(collaborator_id=collaborator_id).order_by(JornadaArchive.date.desc()).all()
    current_records = TimeOffRecord.query.filter_by(collaborator_id=collaborator_id).order_by(TimeOffRecord.date.desc()).all()
    
    all_records = []
    
    for arch in archived_records:
        all_records.append({
            'id': arch.id,
            'date': arch.date,
            'record_type': arch.record_type,
            'hours': arch.hours,
            'days': arch.days,
            'amount_paid': arch.amount_paid,
            'rate_per_day': arch.rate_per_day,
            'origin': arch.origin,
            'notes': arch.notes,
            'created_at': arch.created_at,
            'created_by': arch.created_by,
            'archived': True,
            'archive_period': f"{arch.archive_period_start.strftime('%d/%m/%Y')} - {arch.archive_period_end.strftime('%d/%m/%Y')}",
            'archived_at': arch.archived_at
        })
    
    for curr in current_records:
        all_records.append({
            'id': curr.id,
            'date': curr.date,
            'record_type': curr.record_type,
            'hours': curr.hours,
            'days': curr.days,
            'amount_paid': curr.amount_paid,
            'rate_per_day': curr.rate_per_day,
            'origin': curr.origin,
            'notes': curr.notes,
            'created_at': curr.created_at,
            'created_by': curr.created_by,
            'archived': False,
            'archive_period': None,
            'archived_at': None
        })
    
    all_records.sort(key=lambda x: x['date'], reverse=True)
    
    total_hours = sum(r['hours'] or 0.0 for r in all_records if r['hours'] and r['hours'] > 0)
    total_folgas_creditos = sum(r['days'] or 0 for r in all_records if r['record_type'] == 'folga_adicional' and (not r.get('origin') or r.get('origin') != 'horas'))
    total_folgas_usadas = sum(r['days'] or 0 for r in all_records if r['record_type'] == 'folga_usada')
    total_conversoes = sum(r['days'] or 0 for r in all_records if r['record_type'] == 'conversao')
    total_valor_pago = sum(r['amount_paid'] or 0.0 for r in all_records if r['amount_paid'])
    
    tipo_labels = {
        'horas': 'Horas Trabalhadas',
        'folga_adicional': 'Folga Adicional',
        'folga_usada': 'Folga Usada',
        'conversao': 'Conversão em R$'
    }
    
    return render_template('jornada/historico.html',
                         active_page='jornada',
                         collaborator=collab,
                         records=all_records,
                         tipo_labels=tipo_labels,
                         total_hours=total_hours,
                         total_folgas_creditos=total_folgas_creditos,
                         total_folgas_usadas=total_folgas_usadas,
                         total_conversoes=total_conversoes,
                         total_valor_pago=total_valor_pago)

