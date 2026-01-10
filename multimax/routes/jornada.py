from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, current_app
from flask_login import login_required, current_user
from .. import db
from ..models import Collaborator, TimeOffRecord
from datetime import datetime, date
from sqlalchemy import or_
import io
import csv

bp = Blueprint('jornada', __name__, url_prefix='/jornada')

def _get_all_collaborators():
    return Collaborator.query.order_by(Collaborator.name.asc()).all()

def _get_collaborator_display_name(collaborator):
    if not collaborator:
        return None
    if collaborator.user_id and collaborator.user:
        return collaborator.user.name
    return collaborator.name

def _calculate_simple_balance(collaborator_id, date_start=None, date_end=None):
    """Calcula o saldo simples de um colaborador
    
    Lógica simplificada:
    - Soma todas as horas (positivas e negativas)
    - Converte horas >= 8h em dias (8h = 1 dia)
    - Folgas adicionadas = folgas manuais (excluindo as que vêm de horas)
    - Folgas disponíveis = folgas manuais + dias convertidos das horas
    - Conversões só reduzem saldo se não excederem folgas disponíveis
    - Saldo = folgas disponíveis - folgas usadas - conversões
    """
    filters = [TimeOffRecord.collaborator_id == collaborator_id]
    if date_start:
        filters.append(TimeOffRecord.date >= date_start)
    if date_end:
        filters.append(TimeOffRecord.date <= date_end)
    
    # Horas totais (soma todas as horas, positivas e negativas)
    horas_records = TimeOffRecord.query.filter(*filters, TimeOffRecord.record_type == 'horas').all()
    total_horas = sum(float(r.hours or 0.0) for r in horas_records)
    
    # Dias convertidos das horas (apenas se total_horas >= 0)
    if total_horas >= 0:
        dias_das_horas = int(total_horas // 8.0)
        horas_residuais = total_horas % 8.0
    else:
        dias_das_horas = 0
        horas_residuais = 0.0
    
    # Folgas adicionadas (excluindo as que vêm de horas, para não duplicar)
    folgas_adicionadas_records = TimeOffRecord.query.filter(
        *filters, 
        TimeOffRecord.record_type == 'folga_adicional',
        or_(TimeOffRecord.origin != 'horas', TimeOffRecord.origin.is_(None))
    ).all()
    folgas_adicionadas = sum(int(r.days or 0) for r in folgas_adicionadas_records)
    
    # Folgas usadas
    folgas_usadas_records = TimeOffRecord.query.filter(*filters, TimeOffRecord.record_type == 'folga_usada').all()
    folgas_usadas = sum(int(r.days or 0) for r in folgas_usadas_records)
    
    # Conversões em dinheiro
    conversoes_records = TimeOffRecord.query.filter(*filters, TimeOffRecord.record_type == 'conversao').all()
    conversoes_totais = sum(int(r.days or 0) for r in conversoes_records)
    
    # Folgas disponíveis = folgas manuais + dias convertidos das horas
    folgas_disponiveis = folgas_adicionadas + dias_das_horas
    
    # Conversões só reduzem saldo se não excederem folgas disponíveis
    # (evita saldos negativos incorretos por conversões de períodos anteriores)
    conversoes = min(conversoes_totais, folgas_disponiveis) if folgas_disponiveis > 0 else 0
    
    # Saldo final
    saldo = folgas_disponiveis - folgas_usadas - conversoes
    
    return {
        'total_horas': total_horas,
        'dias_das_horas': dias_das_horas,
        'horas_residuais': horas_residuais,
        'folgas_adicionadas': folgas_adicionadas,
        'folgas_usadas': folgas_usadas,
        'conversoes': conversoes,
        'folgas_disponiveis': folgas_disponiveis,
        'saldo': saldo
    }

@bp.route('/', methods=['GET'], strict_slashes=False)
@login_required
def index():
    """Página principal única - lista todos os registros e estatísticas"""
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('home.index'))
    
    try:
        # Filtros
        collaborator_id = request.args.get('collaborator_id', type=int)
        data_inicio = request.args.get('inicio', '').strip()
        data_fim = request.args.get('fim', '').strip()
        record_type = request.args.get('tipo', '').strip()
        
        # Converter datas
        date_start = None
        date_end = None
        if data_inicio:
            try:
                date_start = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            except Exception:
                pass
        if data_fim:
            try:
                date_end = datetime.strptime(data_fim, '%Y-%m-%d').date()
            except Exception:
                pass
        
        # Buscar colaboradores
        colaboradores = _get_all_collaborators()
        
        # Buscar registros com filtros
        query = TimeOffRecord.query
        
        if collaborator_id:
            query = query.filter(TimeOffRecord.collaborator_id == collaborator_id)
        if date_start:
            query = query.filter(TimeOffRecord.date >= date_start)
        if date_end:
            query = query.filter(TimeOffRecord.date <= date_end)
        if record_type:
            query = query.filter(TimeOffRecord.record_type == record_type)
        
        records = query.order_by(TimeOffRecord.date.desc(), TimeOffRecord.id.desc()).limit(500).all()
        
        # Calcular estatísticas para todos os colaboradores
        all_stats = []
        for colab in colaboradores:
            balance = _calculate_simple_balance(colab.id, date_start, date_end)
            all_stats.append({
                'collaborator': colab,
                'display_name': _get_collaborator_display_name(colab),
                'balance': balance
            })
        
        # Estatísticas do colaborador selecionado
        selected_collaborator = None
        stats = None
        if collaborator_id:
            selected_collaborator = Collaborator.query.get(collaborator_id)
            if selected_collaborator:
                stats = _calculate_simple_balance(collaborator_id, date_start, date_end)
        
        # Totais gerais
        total_horas = sum(s['balance']['total_horas'] for s in all_stats)
        total_horas_residuais = sum(s['balance']['horas_residuais'] for s in all_stats)
        total_saldo = sum(s['balance']['saldo'] for s in all_stats)
        total_folgas_adicionadas = sum(s['balance']['folgas_adicionadas'] for s in all_stats)
        total_folgas_usadas = sum(s['balance']['folgas_usadas'] for s in all_stats)
        total_conversoes = sum(s['balance']['conversoes'] for s in all_stats)
        
        return render_template(
            'jornada/index.html',
            colaboradores=colaboradores,
            records=records,
            all_stats=all_stats,
            selected_collaborator=selected_collaborator,
            stats=stats,
            collaborator_id=collaborator_id or None,
            data_inicio=data_inicio or '',
            data_fim=data_fim or '',
            record_type=record_type or '',
            total_horas=total_horas,
            total_horas_residuais=total_horas_residuais,
            total_saldo=total_saldo,
            total_folgas_adicionadas=total_folgas_adicionadas,
            total_folgas_usadas=total_folgas_usadas,
            total_conversoes=total_conversoes,
            active_page='jornada'
        )
    except Exception as e:
        current_app.logger.error(f'Erro na rota jornada.index: {e}', exc_info=True)
        flash(f'Erro ao carregar página: {str(e)}', 'danger')
        return redirect(url_for('home.index'))

@bp.route('/novo', methods=['GET', 'POST'], strict_slashes=False)
@login_required
def novo():
    """Adicionar novo registro"""
    if current_user.nivel not in ['admin', 'DEV', 'operador']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('jornada.index'))
    
    if request.method == 'POST':
        try:
            collaborator_id = request.form.get('collaborator_id', type=int)
            record_date = request.form.get('date', '').strip()
            record_type = request.form.get('record_type', '').strip()
            
            if not collaborator_id or not record_date or not record_type:
                flash('Preencha todos os campos obrigatórios.', 'danger')
                return redirect(url_for('jornada.novo'))
            
            collaborator = Collaborator.query.get(collaborator_id)
            if not collaborator:
                flash('Colaborador não encontrado.', 'danger')
                return redirect(url_for('jornada.novo'))
            
            try:
                date_obj = datetime.strptime(record_date, '%Y-%m-%d').date()
            except Exception:
                flash('Data inválida.', 'danger')
                return redirect(url_for('jornada.novo'))
            
            record = TimeOffRecord()
            record.collaborator_id = collaborator_id
            record.date = date_obj
            record.record_type = record_type
            record.created_by = current_user.username
            
            if record_type == 'horas':
                hours = request.form.get('hours', type=float)
                if hours is None:
                    flash('Informe a quantidade de horas.', 'danger')
                    return redirect(url_for('jornada.novo'))
                record.hours = hours
                record.origin = request.form.get('origin', 'manual')
            elif record_type in ('folga_adicional', 'folga_usada'):
                days = request.form.get('days', type=int)
                if days is None or days <= 0:
                    flash('Informe a quantidade de dias.', 'danger')
                    return redirect(url_for('jornada.novo'))
                record.days = days
                record.origin = request.form.get('origin', 'manual')
            elif record_type == 'conversao':
                days = request.form.get('days', type=int)
                amount = request.form.get('amount', type=float)
                if days is None or days <= 0:
                    flash('Informe a quantidade de dias convertidos.', 'danger')
                    return redirect(url_for('jornada.novo'))
                record.days = days
                record.amount_paid = amount
                record.rate_per_day = (amount / days) if days > 0 else 0
            
            record.notes = request.form.get('notes', '').strip() or None
            
            db.session.add(record)
            db.session.commit()
            
            flash('Registro adicionado com sucesso!', 'success')
            return redirect(url_for('jornada.index', collaborator_id=collaborator_id))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Erro ao criar registro: {e}', exc_info=True)
            flash(f'Erro ao criar registro: {str(e)}', 'danger')
            return redirect(url_for('jornada.novo'))
    
    colaboradores = _get_all_collaborators()
    return render_template('jornada/novo.html', colaboradores=colaboradores, active_page='jornada')

@bp.route('/editar/<int:id>', methods=['GET', 'POST'], strict_slashes=False)
@login_required
def editar(id):
    """Editar registro existente"""
    if current_user.nivel not in ['admin', 'DEV']:
        flash('Acesso negado. Apenas administradores podem editar.', 'danger')
        return redirect(url_for('jornada.index'))
    
    record = TimeOffRecord.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            record_date = request.form.get('date', '').strip()
            record_type = request.form.get('record_type', '').strip()
            
            if not record_date or not record_type:
                flash('Preencha todos os campos obrigatórios.', 'danger')
                return redirect(url_for('jornada.editar', id=id))
            
            try:
                date_obj = datetime.strptime(record_date, '%Y-%m-%d').date()
            except Exception:
                flash('Data inválida.', 'danger')
                return redirect(url_for('jornada.editar', id=id))
            
            record.date = date_obj
            record.record_type = record_type
            
            if record_type == 'horas':
                hours = request.form.get('hours', type=float)
                if hours is None:
                    flash('Informe a quantidade de horas.', 'danger')
                    return redirect(url_for('jornada.editar', id=id))
                record.hours = hours
                record.days = None
                record.amount_paid = None
                record.origin = request.form.get('origin', 'manual')
            elif record_type in ('folga_adicional', 'folga_usada'):
                days = request.form.get('days', type=int)
                if days is None or days <= 0:
                    flash('Informe a quantidade de dias.', 'danger')
                    return redirect(url_for('jornada.editar', id=id))
                record.days = days
                record.hours = None
                record.amount_paid = None
                record.origin = request.form.get('origin', 'manual')
            elif record_type == 'conversao':
                days = request.form.get('days', type=int)
                amount = request.form.get('amount', type=float)
                if days is None or days <= 0:
                    flash('Informe a quantidade de dias convertidos.', 'danger')
                    return redirect(url_for('jornada.editar', id=id))
                record.days = days
                record.amount_paid = amount
                record.rate_per_day = (amount / days) if days > 0 else 0
                record.hours = None
                record.origin = 'manual'
            
            record.notes = request.form.get('notes', '').strip() or None
            
            db.session.commit()
            
            flash('Registro atualizado com sucesso!', 'success')
            return redirect(url_for('jornada.index', collaborator_id=record.collaborator_id))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Erro ao editar registro: {e}', exc_info=True)
            flash(f'Erro ao editar registro: {str(e)}', 'danger')
            return redirect(url_for('jornada.editar', id=id))
    
    colaboradores = _get_all_collaborators()
    return render_template('jornada/editar.html', record=record, colaboradores=colaboradores, active_page='jornada')

@bp.route('/excluir/<int:id>', methods=['POST'], strict_slashes=False)
@login_required
def excluir(id):
    """Excluir registro"""
    if current_user.nivel not in ['admin', 'DEV']:
        flash('Acesso negado. Apenas administradores podem excluir.', 'danger')
        return redirect(url_for('jornada.index'))
    
    record = TimeOffRecord.query.get_or_404(id)
    collaborator_id = record.collaborator_id
    
    try:
        db.session.delete(record)
        db.session.commit()
        flash('Registro excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Erro ao excluir registro: {e}', exc_info=True)
        flash(f'Erro ao excluir registro: {str(e)}', 'danger')
    
    return redirect(url_for('jornada.index', collaborator_id=collaborator_id))

@bp.route('/converter_horas', methods=['POST'], strict_slashes=False)
@login_required
def converter_horas():
    """Converter horas residuais em dias de folga"""
    if current_user.nivel not in ['admin', 'DEV']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('jornada.index'))
    
    try:
        collaborator_id = request.form.get('collaborator_id', type=int)
        if not collaborator_id:
            flash('Colaborador não informado.', 'danger')
            return redirect(url_for('jornada.index'))
        
        balance = _calculate_simple_balance(collaborator_id)
        horas_residuais = balance['horas_residuais']
        
        if horas_residuais < 8.0:
            flash('Não há horas suficientes para converter (mínimo 8h).', 'warning')
            return redirect(url_for('jornada.index', collaborator_id=collaborator_id))
        
        dias_a_adicionar = int(horas_residuais // 8.0)
        horas_restantes = horas_residuais % 8.0
        
        hoje = date.today()
        
        # Criar registro de folga adicional
        folga = TimeOffRecord()
        folga.collaborator_id = collaborator_id
        folga.date = hoje
        folga.record_type = 'folga_adicional'
        folga.days = dias_a_adicionar
        folga.origin = 'horas'
        folga.notes = f'Conversão automática de {dias_a_adicionar * 8}h em {dias_a_adicionar} dia(s)'
        folga.created_by = current_user.username
        
        # Criar ajuste negativo de horas
        ajuste = TimeOffRecord()
        ajuste.collaborator_id = collaborator_id
        ajuste.date = hoje
        ajuste.record_type = 'horas'
        ajuste.hours = -(dias_a_adicionar * 8.0)
        ajuste.origin = 'horas'
        ajuste.notes = f'Ajuste de conversão: -{dias_a_adicionar * 8}h (convertido em {dias_a_adicionar} dia(s))'
        ajuste.created_by = current_user.username
        
        db.session.add(folga)
        db.session.add(ajuste)
        db.session.commit()
        
        flash(f'Conversão realizada: {dias_a_adicionar * 8}h convertidas em {dias_a_adicionar} dia(s). Horas restantes: {horas_restantes:.2f}h', 'success')
        return redirect(url_for('jornada.index', collaborator_id=collaborator_id))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Erro ao converter horas: {e}', exc_info=True)
        flash(f'Erro ao converter horas: {str(e)}', 'danger')
        return redirect(url_for('jornada.index'))

@bp.route('/export', methods=['GET'], strict_slashes=False)
@login_required
def export():
    """Exportar registros para CSV"""
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('jornada.index'))
    
    try:
        collaborator_id = request.args.get('collaborator_id', type=int)
        data_inicio = request.args.get('inicio', '').strip()
        data_fim = request.args.get('fim', '').strip()
        
        query = TimeOffRecord.query
        
        if collaborator_id:
            query = query.filter(TimeOffRecord.collaborator_id == collaborator_id)
        
        if data_inicio:
            try:
                date_start = datetime.strptime(data_inicio, '%Y-%m-%d').date()
                query = query.filter(TimeOffRecord.date >= date_start)
            except Exception:
                pass
        
        if data_fim:
            try:
                date_end = datetime.strptime(data_fim, '%Y-%m-%d').date()
                query = query.filter(TimeOffRecord.date <= date_end)
            except Exception:
                pass
        
        records = query.order_by(TimeOffRecord.date.desc(), TimeOffRecord.id.desc()).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Colaborador', 'Data', 'Tipo', 'Horas', 'Dias', 'Valor (R$)', 'Origem', 'Observações', 'Criado por', 'Criado em'])
        
        for r in records:
            colab_name = _get_collaborator_display_name(r.collaborator) if r.collaborator else 'N/A'
            writer.writerow([
                r.id, colab_name, r.date.strftime('%d/%m/%Y'), r.record_type,
                r.hours if r.hours else '', r.days if r.days else '',
                r.amount_paid if r.amount_paid else '', r.origin or '', r.notes or '',
                r.created_by or '', r.created_at.strftime('%d/%m/%Y %H:%M:%S') if r.created_at else ''
            ])
        
        output.seek(0)
        filename = f'jornada_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8-sig')),
            mimetype='text/csv; charset=utf-8-sig',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        current_app.logger.error(f'Erro ao exportar CSV: {e}', exc_info=True)
        flash(f'Erro ao exportar: {str(e)}', 'danger')
        return redirect(url_for('jornada.index'))
