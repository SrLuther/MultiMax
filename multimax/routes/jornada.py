from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, session
from flask_login import login_required, current_user
from .. import db
from ..models import Collaborator, User, TimeOffRecord, Holiday, SystemLog, Vacation, MedicalCertificate, JornadaArchive, AppSetting, MonthStatus
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
# Funções auxiliares - Controle de Estados e Permissões
# ============================================================================

def _get_month_status(year, month):
    """Retorna o status do mês. Se não existir, cria como 'aberto'"""
    try:
        # Verificar se a tabela existe, se não existir, criar
        from sqlalchemy import inspect, text
        insp = inspect(db.engine)
        tables = insp.get_table_names()
        if 'month_status' not in tables:
            db.create_all()
            db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
    
    try:
        status = MonthStatus.query.filter_by(year=year, month=month).first()
        if not status:
            status = MonthStatus(year=year, month=month, status='aberto')
            db.session.add(status)
            db.session.commit()
        return status
    except Exception as e:
        # Se houver erro, tentar criar a tabela e tentar novamente
        try:
            db.session.rollback()
            db.create_all()
            db.session.commit()
            status = MonthStatus.query.filter_by(year=year, month=month).first()
            if not status:
                status = MonthStatus(year=year, month=month, status='aberto')
                db.session.add(status)
                db.session.commit()
            return status
        except Exception:
            db.session.rollback()
            # Retornar um objeto mock para não quebrar a aplicação
            from types import SimpleNamespace
            return SimpleNamespace(year=year, month=month, status='aberto', month_year_str=f"{month:02d}/{year}")

def _can_edit_record(record_date, user_level):
    """
    Verifica se o usuário pode editar um registro baseado em:
    - Perfil do usuário (DEV, ADMIN, OPERADOR)
    - Estado do mês do registro
    
    Regras:
    - DEV: pode editar sempre
    - ADMIN: pode editar apenas se mês NÃO estiver arquivado
    - OPERADOR: nunca pode editar
    """
    if user_level == 'DEV':
        return True
    
    if user_level == 'OPERADOR':
        return False
    
    if user_level == 'ADMIN':
        # ADMIN pode editar apenas se mês não estiver arquivado
        month_status = _get_month_status(record_date.year, record_date.month)
        return month_status.status != 'arquivado'
    
    return False

def _can_edit_month(year, month, user_level):
    """Verifica se o usuário pode editar registros de um mês específico"""
    if user_level == 'DEV':
        return True
    
    if user_level == 'OPERADOR':
        return False
    
    if user_level == 'ADMIN':
        month_status = _get_month_status(year, month)
        return month_status.status != 'arquivado'
    
    return False

def _get_month_status_display(status):
    """Retorna display amigável do status"""
    status_map = {
        'aberto': ('🟢 EM ABERTO', 'success'),
        'fechado': ('🟡 FECHADO PARA REVISÃO', 'warning'),
        'arquivado': ('🔴 ARQUIVADO', 'danger')
    }
    return status_map.get(status, ('❓ DESCONHECIDO', 'secondary'))

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
    
    # Folgas adicionais MANUAIS (excluindo as geradas automaticamente de horas)
    # As folgas com origin='horas' já são contadas via days_from_hours, então não devem ser contadas aqui
    cq = TimeOffRecord.query.filter(
        *filters,
        TimeOffRecord.record_type == 'folga_adicional',
        or_(TimeOffRecord.origin != 'horas', TimeOffRecord.origin.is_(None))
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

def _get_day_value():
    """Retorna o valor configurado por dia completo (padrão: 0.0)"""
    try:
        setting = AppSetting.query.filter_by(key='jornada_valor_dia').first()
        if setting and setting.value:
            return float(setting.value)
    except Exception:
        pass
    return 0.0

def _calculate_collaborator_values(collaborator_id, date_start=None, date_end=None):
    """Calcula os valores monetários de um colaborador"""
    balance = _calculate_collaborator_balance(collaborator_id, date_start, date_end)
    day_value = _get_day_value()
    
    # Dias completos (saldo de folgas)
    full_days = max(0, balance['saldo_days'])
    value_full_days = full_days * day_value
    
    # Horas residuais (menos de 8h) - cálculo proporcional
    residual_hours = max(0.0, balance['residual_hours'])
    value_residual_hours = (residual_hours / 8.0) * day_value if residual_hours > 0 else 0.0
    
    # Valor total individual (dias completos + horas parciais)
    value_total_individual = value_full_days + value_residual_hours
    
    return {
        'full_days': full_days,
        'residual_hours': residual_hours,
        'day_value': day_value,
        'value_full_days': value_full_days,
        'value_residual_hours': value_residual_hours,
        'value_total_individual': value_total_individual
    }

def _calculate_total_values(all_stats, date_start=None, date_end=None):
    """Calcula o valor total geral de todos os colaboradores"""
    total_full_days = 0
    total_residual_hours = 0.0
    total_value = 0.0
    
    for item in all_stats:
        values = _calculate_collaborator_values(item['collaborator'].id, date_start, date_end)
        total_full_days += values['full_days']
        total_residual_hours += values['residual_hours']
        total_value += values['value_total_individual']
    
    return {
        'total_full_days': total_full_days,
        'total_residual_hours': total_residual_hours,
        'total_value': total_value
    }

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
    """Página principal do sistema de Jornada - redireciona para EM ABERTO"""
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('home.index'))
    return redirect(url_for('jornada.em_aberto'))

@bp.route('/em-aberto', methods=['GET'], strict_slashes=False)
@login_required
def em_aberto():
    """Subpágina: Mês EM ABERTO - exibe apenas meses em aberto"""
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('home.index'))
    
    try:
        # Garantir que a tabela existe
        from sqlalchemy import inspect
        insp = inspect(db.engine)
        tables = insp.get_table_names()
        if 'month_status' not in tables:
            db.create_all()
            db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
    
    # Buscar meses em aberto
    try:
        meses_abertos = MonthStatus.query.filter_by(status='aberto').order_by(
            MonthStatus.year.desc(), MonthStatus.month.desc()
        ).all()
    except Exception as e:
        # Se houver erro na query, criar tabela e tentar novamente
        try:
            db.session.rollback()
            db.create_all()
            db.session.commit()
            meses_abertos = MonthStatus.query.filter_by(status='aberto').order_by(
                MonthStatus.year.desc(), MonthStatus.month.desc()
            ).all()
        except Exception:
            db.session.rollback()
            meses_abertos = []
    
    # Se não houver mês em aberto, criar para o mês atual
    hoje = date.today()
    try:
        mes_atual = _get_month_status(hoje.year, hoje.month)
        if not meses_abertos or (mes_atual.status == 'aberto' and mes_atual not in meses_abertos):
            # Garantir que o mês atual está na lista se estiver em aberto
            if mes_atual.status == 'aberto':
                meses_abertos.append(mes_atual)
                # Remover duplicatas mantendo ordem
                seen = set()
                meses_abertos = [x for x in meses_abertos if not (x in seen or seen.add((x.year, x.month)))]
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f'Erro ao obter status do mês atual: {e}', exc_info=True)
        # Se houver erro, usar lista vazia e criar mês atual como fallback
        try:
            mes_atual = MonthStatus(year=hoje.year, month=hoje.month, status='aberto')
            db.session.add(mes_atual)
            db.session.commit()
            meses_abertos = [mes_atual]
        except Exception:
            db.session.rollback()
            meses_abertos = []
    
    # Buscar registros apenas dos meses em aberto
    records = []
    if meses_abertos:
        for mes_status in meses_abertos:
            try:
                # Calcular início e fim do mês
                from calendar import monthrange
                first_day = date(mes_status.year, mes_status.month, 1)
                last_day = date(mes_status.year, mes_status.month, monthrange(mes_status.year, mes_status.month)[1])
                
                mes_records = TimeOffRecord.query.filter(
                    TimeOffRecord.date >= first_day,
                    TimeOffRecord.date <= last_day
                ).order_by(TimeOffRecord.date.desc(), TimeOffRecord.id.desc()).all()
                
                records.extend(mes_records)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f'Erro ao buscar registros do mês {mes_status.year}/{mes_status.month}: {e}', exc_info=True)
                continue
    
    # Filtros adicionais
    collaborator_id = request.args.get('collaborator_id', type=int)
    data_inicio = request.args.get('inicio', '').strip()
    data_fim = request.args.get('fim', '').strip()
    record_type = request.args.get('tipo', '').strip()
    
    # Aplicar filtros
    if collaborator_id:
        records = [r for r in records if r.collaborator_id == collaborator_id]
    if record_type:
        records = [r for r in records if r.record_type == record_type]
    
    # Processar datas
    di = None
    df = None
    if data_inicio:
        try:
            di = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            records = [r for r in records if r.date >= di]
        except Exception:
            pass
    if data_fim:
        try:
            df = datetime.strptime(data_fim, '%Y-%m-%d').date()
            records = [r for r in records if r.date <= df]
        except Exception:
            pass
    
    # Buscar todos os colaboradores
    colaboradores = _get_all_collaborators()
    
    # Calcular estatísticas apenas dos meses em aberto
    all_stats = []
    for colab in colaboradores:
        balance = _calculate_collaborator_balance(colab.id, di, df)
        all_stats.append({
            'collaborator': colab,
            'display_name': _get_collaborator_display_name(colab),
            'balance': balance
        })
    
    # Verificar permissões de edição
    can_edit = current_user.nivel in ('admin', 'DEV')
    
    # Buscar feriados para o calendário
    hoje = date.today()
    feriados = Holiday.query.filter(
        Holiday.date >= date(hoje.year, hoje.month, 1)
    ).order_by(Holiday.date.asc()).all()
    
    try:
        return render_template(
            'jornada/em_aberto.html',
            colaboradores=colaboradores,
            records=records[:100],  # Limitar a 100 registros
            all_stats=all_stats,
            meses_abertos=meses_abertos,
            collaborator_id=collaborator_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            record_type=record_type,
            can_edit=can_edit,
            feriados=feriados,
            active_page='jornada'
        )
    except Exception as e:
        # Log do erro para debug
        import logging
        logging.getLogger(__name__).error(f'Erro na rota em_aberto: {e}', exc_info=True)
        flash(f'Erro ao carregar página: {str(e)}. Verifique se a tabela month_status existe no banco de dados.', 'danger')
        # Tentar criar a tabela e redirecionar
        try:
            db.create_all()
            db.session.commit()
            return redirect(url_for('jornada.em_aberto'))
        except Exception:
            return redirect(url_for('home.index'))

@bp.route('/fechado-revisao', methods=['GET'], strict_slashes=False)
@login_required
def fechado_revisao():
    """Subpágina: FECHADO PARA REVISÃO - exibe apenas meses fechados aguardando pagamento"""
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('home.index'))
    
    # Buscar meses fechados
    meses_fechados = MonthStatus.query.filter_by(status='fechado').order_by(
        MonthStatus.year.desc(), MonthStatus.month.desc()
    ).all()
    
    # Buscar registros dos meses fechados
    records = []
    for mes_status in meses_fechados:
        from calendar import monthrange
        first_day = date(mes_status.year, mes_status.month, 1)
        last_day = date(mes_status.year, mes_status.month, monthrange(mes_status.year, mes_status.month)[1])
        
        mes_records = TimeOffRecord.query.filter(
            TimeOffRecord.date >= first_day,
            TimeOffRecord.date <= last_day
        ).order_by(TimeOffRecord.date.desc(), TimeOffRecord.id.desc()).all()
        
        records.extend(mes_records)
    
    # Filtros
    collaborator_id = request.args.get('collaborator_id', type=int)
    record_type = request.args.get('tipo', '').strip()
    
    if collaborator_id:
        records = [r for r in records if r.collaborator_id == collaborator_id]
    if record_type:
        records = [r for r in records if r.record_type == record_type]
    
    colaboradores = _get_all_collaborators()
    
    # Verificar permissões (DEV e ADMIN podem editar meses fechados)
    can_edit = current_user.nivel in ('admin', 'DEV')
    
    return render_template(
        'jornada/fechado_revisao.html',
        colaboradores=colaboradores,
        records=records[:100],
        meses_fechados=meses_fechados,
        collaborator_id=collaborator_id,
        record_type=record_type,
        can_edit=can_edit,
        active_page='jornada'
    )

@bp.route('/arquivados', methods=['GET'], strict_slashes=False)
@login_required
def arquivados():
    """Subpágina: ARQUIVADOS - exibe apenas meses arquivados (após pagamento confirmado)"""
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('home.index'))
    
    # Buscar meses arquivados
    meses_arquivados = MonthStatus.query.filter_by(status='arquivado').order_by(
        MonthStatus.year.desc(), MonthStatus.month.desc()
    ).all()
    
    # Buscar registros arquivados (da tabela JornadaArchive)
    collaborator_id = request.args.get('collaborator_id', type=int)
    data_inicio = request.args.get('inicio', '').strip()
    data_fim = request.args.get('fim', '').strip()
    record_type = request.args.get('tipo', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
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
    
    # Filtros adicionais: período de arquivamento
    periodo_inicio = request.args.get('periodo_inicio', '').strip()
    periodo_fim = request.args.get('periodo_fim', '').strip()
    periodo_di = None
    periodo_df = None
    if periodo_inicio:
        try:
            periodo_di = datetime.strptime(periodo_inicio, '%Y-%m-%d').date()
        except Exception:
            pass
    if periodo_fim:
        try:
            periodo_df = datetime.strptime(periodo_fim, '%Y-%m-%d').date()
        except Exception:
            pass
    
    # Buscar registros arquivados
    query = JornadaArchive.query
    
    if collaborator_id:
        query = query.filter(JornadaArchive.collaborator_id == collaborator_id)
    if di:
        query = query.filter(JornadaArchive.date >= di)
    if df:
        query = query.filter(JornadaArchive.date <= df)
    if record_type:
        query = query.filter(JornadaArchive.record_type == record_type)
    if periodo_di:
        query = query.filter(JornadaArchive.archive_period_start >= periodo_di)
    if periodo_df:
        query = query.filter(JornadaArchive.archive_period_end <= periodo_df)
    
    archived_records_pag = query.order_by(
        JornadaArchive.archived_at.desc(),
        JornadaArchive.date.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    # Preparar dados
    records = []
    for arch in archived_records_pag.items:
        collab = Collaborator.query.get(arch.collaborator_id)
        display_name = _get_collaborator_display_name(collab) if collab else f"ID {arch.collaborator_id}"
        
        records.append({
            'id': arch.id,
            'collaborator_id': arch.collaborator_id,
            'collaborator_name': display_name,
            'date': arch.date,
            'record_type': arch.record_type,
            'hours': arch.hours,
            'days': arch.days,
            'amount_paid': arch.amount_paid,
            'notes': arch.notes,
            'archived_at': arch.archived_at,
            'archived_by': arch.archived_by,
            'archive_period_start': arch.archive_period_start,
            'archive_period_end': arch.archive_period_end,
        })
    
    # Estatísticas
    stats_query = JornadaArchive.query
    if collaborator_id:
        stats_query = stats_query.filter(JornadaArchive.collaborator_id == collaborator_id)
    if di:
        stats_query = stats_query.filter(JornadaArchive.date >= di)
    if df:
        stats_query = stats_query.filter(JornadaArchive.date <= df)
    if record_type:
        stats_query = stats_query.filter(JornadaArchive.record_type == record_type)
    
    all_archived = stats_query.all()
    total_hours = sum(float(r.hours or 0.0) for r in all_archived if r.record_type == 'horas' and (r.hours or 0.0) > 0)
    total_folgas_creditos = sum(int(r.days or 0) for r in all_archived if r.record_type == 'folga_adicional' and (not r.origin or r.origin != 'horas'))
    total_folgas_usadas = sum(int(r.days or 0) for r in all_archived if r.record_type == 'folga_usada')
    total_conversoes = sum(int(r.days or 0) for r in all_archived if r.record_type == 'conversao')
    total_valor_pago = sum(float(r.amount_paid or 0.0) for r in all_archived if r.amount_paid)
    
    colaboradores = _get_all_collaborators()
    
    # Permissões: apenas DEV pode editar meses arquivados
    can_edit = current_user.nivel == 'DEV'
    
    tipo_labels = {
        'horas': 'Horas Trabalhadas',
        'folga_adicional': 'Folga Adicional',
        'folga_usada': 'Folga Usada',
        'conversao': 'Conversão em R$'
    }
    
    return render_template(
        'jornada/arquivados.html',
        active_page='jornada',
        records=records,
        archived_records_pag=archived_records_pag,
        meses_arquivados=meses_arquivados,
        colaboradores=colaboradores,
        collaborator_id=collaborator_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        record_type=record_type,
        periodo_inicio=periodo_inicio,
        periodo_fim=periodo_fim,
        tipo_labels=tipo_labels,
        total_hours=total_hours,
        total_folgas_creditos=total_folgas_creditos,
        total_folgas_usadas=total_folgas_usadas,
        total_conversoes=total_conversoes,
        total_valor_pago=total_valor_pago,
        can_edit=can_edit
    )
    day_value = _get_day_value()

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
        collaborator_values=collaborator_values,
        total_values=total_values,
        day_value=day_value,
        active_page='jornada'
    )

@bp.route('/novo', methods=['GET', 'POST'], strict_slashes=False)
@login_required
def novo():
    """Criar novo registro de jornada"""
    if current_user.nivel not in ('admin', 'DEV', 'operador'):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('jornada.em_aberto'))
    
    if current_user.nivel == 'operador':
        flash('Acesso negado. Operadores não podem criar registros.', 'danger')
        return redirect(url_for('jornada.em_aberto'))
    
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
            
            # Verificar permissão de edição baseada no estado do mês
            if not _can_edit_month(record_date.year, record_date.month, current_user.nivel):
                month_status = _get_month_status(record_date.year, record_date.month)
                status_display, _ = _get_month_status_display(month_status.status)
                flash(f'Não é possível criar registro. Mês {month_status.month_year_str} está {status_display}. Apenas DEV pode editar meses arquivados.', 'danger')
                return redirect(url_for('jornada.em_aberto'))
            
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
            return redirect(url_for('jornada.em_aberto', collaborator_id=collaborator_id))
            
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
    if current_user.nivel == 'operador':
        flash('Acesso negado. Operadores não podem editar registros.', 'danger')
        return redirect(url_for('jornada.em_aberto'))
    
    record = TimeOffRecord.query.get_or_404(id)
    
    # Verificar permissão de edição baseada no estado do mês
    if not _can_edit_record(record.date, current_user.nivel):
        month_status = _get_month_status(record.date.year, record.date.month)
        status_display, _ = _get_month_status_display(month_status.status)
        flash(f'Não é possível editar registro. Mês {month_status.month_year_str} está {status_display}. Apenas DEV pode editar meses arquivados.', 'danger')
        return redirect(url_for('jornada.em_aberto'))
    
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
    
    # Verificar estado do mês e permissões
    month_status = _get_month_status(record.date.year, record.date.month)
    can_edit = _can_edit_record(record.date, current_user.nivel)
    status_display, status_color = _get_month_status_display(month_status.status)
    
    return render_template('jornada/editar.html', 
                         record=record, 
                         colaboradores=colaboradores, 
                         month_status=month_status,
                         status_display=status_display,
                         status_color=status_color,
                         can_edit=can_edit,
                         active_page='jornada')

@bp.route('/excluir/<int:id>', methods=['POST'], strict_slashes=False)
@login_required
def excluir(id):
    """Excluir registro de jornada"""
    if current_user.nivel == 'OPERADOR':
        flash('Acesso negado. Operadores não podem excluir registros.', 'danger')
        return redirect(url_for('jornada.em_aberto'))
    
    record = TimeOffRecord.query.get_or_404(id)
    
    # Verificar permissão de edição baseada no estado do mês
    if not _can_edit_record(record.date, current_user.nivel):
        month_status = _get_month_status(record.date.year, record.date.month)
        status_display, _ = _get_month_status_display(month_status.status)
        flash(f'Não é possível excluir registro. Mês {month_status.month_year_str} está {status_display}. Apenas DEV pode editar meses arquivados.', 'danger')
        return redirect(url_for('jornada.em_aberto'))
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



def _get_pending_records_ids(collaborator_id, period_start=None, period_end=None):
    """Retorna IDs dos registros DENTRO DO PERÍODO que compõem Horas Residuais e Saldo de Folgas pendentes.
    
    Preserva apenas registros do período selecionado que ainda contribuem para os saldos pendentes.
    """
    pending_ids = set()
    
    if not period_start or not period_end:
        return pending_ids
    
    # Calcular saldo atual (total) para identificar o que é pendente
    balance_total = _calculate_collaborator_balance(collaborator_id)
    residual_hours_total = balance_total['residual_hours']
    saldo_days_total = balance_total['saldo_days']
    
    # Se não há saldos pendentes, retorna vazio
    if residual_hours_total <= 0 and saldo_days_total <= 0:
        return pending_ids
    
    # 1. Horas Residuais: preservar horas do período que ainda não foram convertidas
    if residual_hours_total > 0:
        # Buscar horas positivas APENAS do período
        horas_periodo = TimeOffRecord.query.filter(
            TimeOffRecord.collaborator_id == collaborator_id,
            TimeOffRecord.record_type == 'horas',
            TimeOffRecord.hours > 0,
            TimeOffRecord.date >= period_start,
            TimeOffRecord.date <= period_end
        ).order_by(TimeOffRecord.date.desc(), TimeOffRecord.id.desc()).all()
        
        # Calcular total de horas antes do período para saber quanto já foi convertido
        horas_antes = TimeOffRecord.query.filter(
            TimeOffRecord.collaborator_id == collaborator_id,
            TimeOffRecord.record_type == 'horas',
            TimeOffRecord.hours > 0,
            TimeOffRecord.date < period_start
        ).all()
        total_horas_antes = sum(float(r.hours or 0.0) for r in horas_antes)
        
        # Calcular quantas horas já foram convertidas antes do período (múltiplos de 8h)
        dias_convertidos_antes = int(total_horas_antes // 8.0)
        horas_residuais_antes = total_horas_antes % 8.0
        
        # Horas acumuladas no período (para identificar quais são residuais)
        horas_acumuladas_periodo = 0.0
        for record in reversed(horas_periodo):  # Do mais antigo para o mais recente
            record_hours = float(record.hours or 0.0)
            horas_acumuladas_periodo += record_hours
            
            # Calcular horas residuais após adicionar esta hora
            total_horas_ate_agora = total_horas_antes + horas_acumuladas_periodo
            horas_residuais_ate_agora = total_horas_ate_agora % 8.0
            
            # Se estas horas ainda fazem parte das horas residuais pendentes, preservar
            if horas_residuais_ate_agora > 0 and horas_residuais_ate_agora <= residual_hours_total:
                pending_ids.add(record.id)
        
        # Se ainda não preservamos horas suficientes, preservar as últimas horas do período
        if len(pending_ids) == 0 and horas_periodo:
            horas_preservar = min(residual_hours_total, sum(float(r.hours or 0.0) for r in horas_periodo))
            for record in reversed(horas_periodo):
                if horas_preservar <= 0:
                    break
                record_hours = float(record.hours or 0.0)
                if record_hours > 0:
                    pending_ids.add(record.id)
                    horas_preservar -= min(horas_preservar, record_hours)
    
    # 2. Saldo de Folgas: preservar folgas adicionais manuais do período que ainda não foram usadas
    if saldo_days_total > 0:
        # Buscar folgas adicionais manuais APENAS do período
        folgas_periodo = TimeOffRecord.query.filter(
            TimeOffRecord.collaborator_id == collaborator_id,
            TimeOffRecord.record_type == 'folga_adicional',
            or_(TimeOffRecord.origin != 'horas', TimeOffRecord.origin.is_(None)),
            TimeOffRecord.date >= period_start,
            TimeOffRecord.date <= period_end
        ).order_by(TimeOffRecord.date.desc(), TimeOffRecord.id.desc()).all()
        
        # Preservar folgas do período suficientes para manter o saldo
        # Assumindo que as folgas mais recentes são as que ainda não foram usadas
        folgas_para_manter = max(0, min(saldo_days_total, sum(r.days or 0 for r in folgas_periodo)))
        for record in folgas_periodo:
            if folgas_para_manter <= 0:
                break
            days_in_record = record.days or 0
            if days_in_record > 0:
                pending_ids.add(record.id)
                folgas_para_manter -= days_in_record
    
    return pending_ids

@bp.route('/arquivar', methods=['GET', 'POST'])
@login_required
def arquivar():
    """Arquivar registros de jornada por período, preservando Horas Residuais e Saldo de Folgas"""
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Acesso negado. Apenas Administradores podem arquivar dados.', 'danger')
        return redirect(url_for('jornada.index'))
    
    if request.method == 'POST':
        # Suporta tanto período (datas) quanto meses específicos
        period_start_str = request.form.get('period_start', '').strip()
        period_end_str = request.form.get('period_end', '').strip()
        months_selected = request.form.getlist('months[]')  # Lista de meses no formato YYYY-MM
        description = request.form.get('description', '').strip()
        
        # Determinar período baseado em meses selecionados ou datas
        period_start = None
        period_end = None
        
        if months_selected:
            # Processar meses selecionados
            try:
                from calendar import monthrange
                dates = []
                for month_str in months_selected:
                    year, month = map(int, month_str.split('-'))
                    first_day = date(year, month, 1)
                    last_day_num = monthrange(year, month)[1]
                    last_day = date(year, month, last_day_num)
                    dates.append((first_day, last_day))
                
                if dates:
                    period_start = min(d[0] for d in dates)
                    period_end = max(d[1] for d in dates)
            except Exception:
                flash('Formato de mês inválido.', 'danger')
                return redirect(url_for('jornada.arquivar'))
        
        if not period_start or not period_end:
            if period_start_str and period_end_str:
                try:
                    period_start = datetime.strptime(period_start_str, '%Y-%m-%d').date()
                    period_end = datetime.strptime(period_end_str, '%Y-%m-%d').date()
                except ValueError:
                    flash('Formato de data inválido. Use o formato YYYY-MM-DD.', 'danger')
                    return redirect(url_for('jornada.arquivar'))
            else:
                flash('Período de início e fim são obrigatórios ou selecione pelo menos um mês.', 'danger')
                first_record = TimeOffRecord.query.order_by(TimeOffRecord.date.asc()).first()
                last_record = TimeOffRecord.query.order_by(TimeOffRecord.date.desc()).first()
                suggested_start = first_record.date if first_record else date.today()
                suggested_end = last_record.date if last_record else date.today()
                available_months = _get_available_months()
                return render_template('jornada/arquivar.html', active_page='jornada', 
                                     suggested_start=suggested_start, suggested_end=suggested_end,
                                     available_months=available_months)
        
        if period_start > period_end:
            flash('Data de início deve ser anterior à data de fim.', 'danger')
            first_record = TimeOffRecord.query.order_by(TimeOffRecord.date.asc()).first()
            last_record = TimeOffRecord.query.order_by(TimeOffRecord.date.desc()).first()
            suggested_start = first_record.date if first_record else date.today()
            suggested_end = last_record.date if last_record else date.today()
            available_months = _get_available_months()
            return render_template('jornada/arquivar.html', active_page='jornada', 
                                 suggested_start=suggested_start, suggested_end=suggested_end,
                                 available_months=available_months)
        
        try:
            # VALIDAÇÃO: Verificar se todos os meses do período estão em FECHADO_REVISAO
            from calendar import monthrange
            months_to_check = set()
            current_date = period_start
            while current_date <= period_end:
                months_to_check.add((current_date.year, current_date.month))
                # Avançar para o primeiro dia do próximo mês
                if current_date.month == 12:
                    current_date = date(current_date.year + 1, 1, 1)
                else:
                    current_date = date(current_date.year, current_date.month + 1, 1)
            
            # Verificar status de cada mês
            invalid_months = []
            for year, month in months_to_check:
                month_status = _get_month_status(year, month)
                if month_status.status != 'fechado':
                    invalid_months.append(f"{month:02d}/{year}")
            
            if invalid_months:
                flash(f'Não é possível arquivar. Os seguintes meses não estão em FECHADO_REVISAO: {", ".join(invalid_months)}. Feche os meses antes de arquivar.', 'danger')
                first_record = TimeOffRecord.query.order_by(TimeOffRecord.date.asc()).first()
                last_record = TimeOffRecord.query.order_by(TimeOffRecord.date.desc()).first()
                suggested_start = first_record.date if first_record else date.today()
                suggested_end = last_record.date if last_record else date.today()
                available_months = _get_available_months()
                return render_template('jornada/arquivar.html', active_page='jornada', 
                                     suggested_start=suggested_start, suggested_end=suggested_end,
                                     available_months=available_months)
            
            # Buscar todos os registros do período
            all_period_records = TimeOffRecord.query.filter(
                TimeOffRecord.date >= period_start,
                TimeOffRecord.date <= period_end
            ).all()
            
            if not all_period_records:
                flash('Nenhum registro encontrado para arquivar no período especificado.', 'warning')
                first_record = TimeOffRecord.query.order_by(TimeOffRecord.date.asc()).first()
                last_record = TimeOffRecord.query.order_by(TimeOffRecord.date.desc()).first()
                suggested_start = first_record.date if first_record else date.today()
                suggested_end = last_record.date if last_record else date.today()
                available_months = _get_available_months()
                return render_template('jornada/arquivar.html', active_page='jornada', 
                                     suggested_start=suggested_start, suggested_end=suggested_end,
                                     available_months=available_months)
            
            # Agrupar registros por colaborador para preservar saldos pendentes
            records_by_collaborator = {}
            for record in all_period_records:
                if record.collaborator_id not in records_by_collaborator:
                    records_by_collaborator[record.collaborator_id] = []
                records_by_collaborator[record.collaborator_id].append(record)
            
            # Identificar registros pendentes que NÃO devem ser arquivados
            # Estes são registros que contribuem para Horas Residuais e Saldo de Folgas
            pending_record_ids = set()
            for collaborator_id in records_by_collaborator.keys():
                pending_ids = _get_pending_records_ids(collaborator_id, period_start, period_end)
                pending_record_ids.update(pending_ids)
            
            # Separar registros para arquivar (excluindo pendentes)
            records_to_archive = [r for r in all_period_records if r.id not in pending_record_ids]
            records_preserved = [r for r in all_period_records if r.id in pending_record_ids]
            
            if not records_to_archive:
                flash('Todos os registros do período são necessários para manter Horas Residuais e Saldo de Folgas pendentes. Nenhum registro foi arquivado.', 'warning')
                return redirect(url_for('jornada.em_aberto'))
            
            archived_count = 0
            preserved_count = len(records_preserved)
            archived_at = datetime.now(ZoneInfo('America/Sao_Paulo'))
            
            # Arquivar apenas os registros que não são pendentes
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
            
            # TRANSACIONAL: Arquivar e atualizar status dos meses em uma única transação
            # Marcar meses como arquivados
            months_archived = set()
            for year, month in months_to_check:
                month_status = _get_month_status(year, month)
                if month_status.status == 'fechado' and month_status.payment_confirmed:
                    month_status.status = 'arquivado'
                    month_status.archived_at = archived_at
                    month_status.archived_by = current_user.username or current_user.name
                    months_archived.add((year, month))
            
            # Deletar apenas os registros arquivados
            for record in records_to_archive:
                db.session.delete(record)
            
            # Commit transacional - tudo ou nada
            db.session.commit()
            
            message = f'{archived_count} registro(s) arquivado(s) com sucesso.'
            if preserved_count > 0:
                message += f' {preserved_count} registro(s) foram preservados para manter Horas Residuais e Saldo de Folgas pendentes.'
            if months_archived:
                message += f' {len(months_archived)} mês(es) marcado(s) como arquivado(s).'
            
            flash(message, 'success')
            return redirect(url_for('jornada.em_aberto'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao arquivar: {e}. Todas as alterações foram revertidas.', 'danger')
    
    first_record = TimeOffRecord.query.order_by(TimeOffRecord.date.asc()).first()
    last_record = TimeOffRecord.query.order_by(TimeOffRecord.date.desc()).first()
    suggested_start = first_record.date if first_record else date.today()
    suggested_end = last_record.date if last_record else date.today()
    available_months = _get_available_months()
    return render_template('jornada/arquivar.html', active_page='jornada', 
                         suggested_start=suggested_start, suggested_end=suggested_end,
                         available_months=available_months)

def _get_available_months():
    """Retorna lista de meses disponíveis para arquivamento"""
    from calendar import monthrange
    months = set()
    
    records = TimeOffRecord.query.order_by(TimeOffRecord.date.asc()).all()
    for record in records:
        year_month = (record.date.year, record.date.month)
        months.add(year_month)
    
    # Converter para lista de strings YYYY-MM ordenadas
    months_list = [f"{year}-{month:02d}" for year, month in sorted(months)]
    return months_list


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

# Código duplicado removido - rota /arquivados já implementada acima (linha 402)

# ============================================================================
# Rotas de Transição de Estado
# ============================================================================

@bp.route('/mes/<int:year>/<int:month>/fechar', methods=['POST'], strict_slashes=False)
@login_required
def fechar_mes(year, month):
    """Fechar mês para revisão (EM ABERTO → FECHADO)"""
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Acesso negado. Apenas ADMIN e DEV podem fechar meses.', 'danger')
        return redirect(url_for('jornada.em_aberto'))
    
    try:
        month_status = _get_month_status(year, month)
        
        if month_status.status != 'aberto':
            flash(f'O mês {month_status.month_year_str} não está em aberto. Status atual: {month_status.status}.', 'warning')
            return redirect(url_for('jornada.em_aberto'))
        
        month_status.status = 'fechado'
        month_status.closed_at = datetime.now(ZoneInfo('America/Sao_Paulo'))
        month_status.closed_by = current_user.username or current_user.name
        
        db.session.commit()
        flash(f'Mês {month_status.month_year_str} fechado para revisão com sucesso.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao fechar mês: {e}', 'danger')
    
    return redirect(url_for('jornada.fechado_revisao'))

@bp.route('/mes/<int:year>/<int:month>/confirmar-pagamento', methods=['POST'], strict_slashes=False)
@login_required
def confirmar_pagamento(year, month):
    """Confirmar pagamento e arquivar mês (FECHADO → ARQUIVADO)"""
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Acesso negado. Apenas ADMIN e DEV podem confirmar pagamento.', 'danger')
        return redirect(url_for('jornada.fechado_revisao'))
    
    try:
        month_status = _get_month_status(year, month)
        
        if month_status.status != 'fechado':
            flash(f'O mês {month_status.month_year_str} não está fechado. Status atual: {month_status.status}.', 'warning')
            return redirect(url_for('jornada.fechado_revisao'))
        
        # Confirmar pagamento
        month_status.payment_confirmed = True
        month_status.payment_confirmed_at = datetime.now(ZoneInfo('America/Sao_Paulo'))
        month_status.payment_confirmed_by = current_user.username or current_user.name
        
        # Arquivar registros do mês
        from calendar import monthrange
        first_day = date(year, month, 1)
        last_day = date(year, month, monthrange(year, month)[1])
        
        records_to_archive = TimeOffRecord.query.filter(
            TimeOffRecord.date >= first_day,
            TimeOffRecord.date <= last_day
        ).all()
        
        archived_count = 0
        archived_at = datetime.now(ZoneInfo('America/Sao_Paulo'))
        
        for record in records_to_archive:
            archive_record = JornadaArchive(
                archive_period_start=first_day,
                archive_period_end=last_day,
                archived_at=archived_at,
                archived_by=current_user.username or current_user.name,
                description=f'Arquivamento automático após confirmação de pagamento - {month_status.month_year_str}',
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
        
        # Deletar registros originais
        for record in records_to_archive:
            db.session.delete(record)
        
        # Marcar mês como arquivado
        month_status.status = 'arquivado'
        month_status.archived_at = archived_at
        month_status.archived_by = current_user.username or current_user.name
        
        db.session.commit()
        flash(f'Pagamento confirmado e mês {month_status.month_year_str} arquivado. {archived_count} registro(s) arquivado(s).', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao confirmar pagamento e arquivar: {e}', 'danger')
    
    return redirect(url_for('jornada.arquivados'))

@bp.route('/mes/<int:year>/<int:month>/reabrir', methods=['POST'], strict_slashes=False)
@login_required
def reabrir_mes(year, month):
    """Reabrir mês (apenas DEV) - ARQUIVADO → FECHADO ou FECHADO → EM ABERTO"""
    if current_user.nivel != 'DEV':
        flash('Acesso negado. Apenas DEV pode reabrir meses.', 'danger')
        return redirect(url_for('jornada.arquivados'))
    
    try:
        month_status = _get_month_status(year, month)
        status_anterior = month_status.status
        
        if month_status.status == 'arquivado':
            # Reverter para fechado
            month_status.status = 'fechado'
            month_status.payment_confirmed = False
            month_status.payment_confirmed_at = None
            month_status.payment_confirmed_by = None
            month_status.archived_at = None
            month_status.archived_by = None
            flash(f'Mês {month_status.month_year_str} reaberto (ARQUIVADO → FECHADO).', 'success')
        elif month_status.status == 'fechado':
            # Reverter para aberto
            month_status.status = 'aberto'
            month_status.closed_at = None
            month_status.closed_by = None
            flash(f'Mês {month_status.month_year_str} reaberto (FECHADO → EM ABERTO).', 'success')
        else:
            flash(f'O mês {month_status.month_year_str} já está em aberto.', 'info')
            return redirect(url_for('jornada.em_aberto'))
        
        db.session.commit()
        
        # Redirecionar para página apropriada
        if month_status.status == 'aberto':
            return redirect(url_for('jornada.em_aberto'))
        else:
            return redirect(url_for('jornada.fechado_revisao'))
            
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao reabrir mês: {e}', 'danger')
        return redirect(url_for('jornada.arquivados'))

# ============================================================================
# Migração de Dados - 2025 para FECHADO_REVISAO
# ============================================================================

def _migrate_2025_to_closed():
    """
    Migração idempotente: Altera status de todos os meses de 2025 para FECHADO_REVISAO.
    Usa AppSetting para rastrear se a migração já foi executada.
    """
    migration_key = 'jornada_migration_2025_completed'
    
    # Verificar se migração já foi executada
    migration_setting = AppSetting.query.filter_by(key=migration_key).first()
    if migration_setting and migration_setting.value == 'true':
        return {
            'success': True,
            'already_completed': True,
            'message': 'Migração de 2025 já foi executada anteriormente.'
        }
    
    try:
        # Buscar todos os meses de 2025 que estão em aberto
        months_2025 = MonthStatus.query.filter(
            MonthStatus.year == 2025,
            MonthStatus.status == 'aberto'
        ).all()
        
        if not months_2025:
            # Marcar como concluída mesmo sem meses para migrar
            if not migration_setting:
                migration_setting = AppSetting(key=migration_key, value='true')
                db.session.add(migration_setting)
            else:
                migration_setting.value = 'true'
            db.session.commit()
            return {
                'success': True,
                'already_completed': False,
                'migrated_count': 0,
                'message': 'Nenhum mês de 2025 em aberto encontrado. Migração concluída.'
            }
        
        # Alterar status para fechado
        migrated_count = 0
        now = datetime.now(ZoneInfo('America/Sao_Paulo'))
        
        for month_status in months_2025:
            month_status.status = 'fechado'
            month_status.closed_at = now
            month_status.closed_by = 'Sistema - Migração 2025'
            migrated_count += 1
        
        # Marcar migração como concluída
        if not migration_setting:
            migration_setting = AppSetting(key=migration_key, value='true')
            db.session.add(migration_setting)
        else:
            migration_setting.value = 'true'
        
        db.session.commit()
        
        return {
            'success': True,
            'already_completed': False,
            'migrated_count': migrated_count,
            'message': f'Migração concluída: {migrated_count} mês(es) de 2025 alterado(s) para FECHADO_REVISAO.'
        }
        
    except Exception as e:
        db.session.rollback()
        return {
            'success': False,
            'error': str(e),
            'message': f'Erro ao executar migração: {e}'
        }

@bp.route('/migrate-2025', methods=['POST'], strict_slashes=False)
@login_required
def migrate_2025():
    """Endpoint para executar migração de dados 2025 (apenas DEV)"""
    if current_user.nivel != 'DEV':
        flash('Acesso negado. Apenas DEV pode executar migrações.', 'danger')
        return redirect(url_for('jornada.em_aberto'))
    
    result = _migrate_2025_to_closed()
    
    if result['success']:
        if result.get('already_completed'):
            flash('Migração já foi executada anteriormente.', 'info')
        else:
            flash(result['message'], 'success')
    else:
        flash(result['message'], 'danger')
    
    return redirect(url_for('jornada.em_aberto'))

@bp.route('/situacao-final', methods=['GET'], strict_slashes=False)
@login_required
def situacao_final():
    """
    Página consolidada mostrando a situação atual e real de cada colaborador.
    Mostra apenas dados ativos (não arquivados).
    """
    # Buscar todos os colaboradores
    colaboradores = _get_all_collaborators()
    
    # Calcular situação consolidada para cada colaborador
    situacoes = []
    
    for colab in colaboradores:
        # Calcular saldo apenas com registros ativos (não arquivados)
        # Registros arquivados estão em JornadaArchive, então não aparecem em TimeOffRecord
        balance = _calculate_collaborator_balance(colab.id)
        
        # Buscar registros ativos para estatísticas
        active_records = TimeOffRecord.query.filter_by(collaborator_id=colab.id).all()
        
        # Calcular totais
        total_horas = sum(float(r.hours or 0.0) for r in active_records if r.record_type == 'horas' and (r.hours or 0.0) > 0)
        total_folgas_adicionadas = sum(int(r.days or 0) for r in active_records if r.record_type == 'folga_adicional' and (not r.origin or r.origin != 'horas'))
        total_folgas_usadas = sum(int(r.days or 0) for r in active_records if r.record_type == 'folga_usada')
        total_conversoes = sum(int(r.days or 0) for r in active_records if r.record_type == 'conversao')
        
        situacoes.append({
            'collaborator': colab,
            'display_name': _get_collaborator_display_name(colab),
            'total_horas': total_horas,
            'horas_residuais': balance.get('residual_hours', 0.0),
            'dias_das_horas': balance.get('days_from_hours', 0),
            'folgas_adicionadas': total_folgas_adicionadas,
            'folgas_usadas': total_folgas_usadas,
            'conversoes': total_conversoes,
            'saldo_folgas': balance.get('saldo_days', 0),
            'total_dias_disponiveis': balance.get('saldo_days', 0) + total_folgas_adicionadas
        })
    
    # Ordenar por nome do colaborador
    situacoes.sort(key=lambda x: x['display_name'])
    
    # Calcular totais gerais
    total_geral_horas = sum(s['total_horas'] for s in situacoes)
    total_geral_folgas_adicionadas = sum(s['folgas_adicionadas'] for s in situacoes)
    total_geral_folgas_usadas = sum(s['folgas_usadas'] for s in situacoes)
    total_geral_conversoes = sum(s['conversoes'] for s in situacoes)
    total_geral_saldo = sum(s['saldo_folgas'] for s in situacoes)
    
    return render_template(
        'jornada/situacao_final.html',
        active_page='jornada',
        situacoes=situacoes,
        total_geral_horas=total_geral_horas,
        total_geral_folgas_adicionadas=total_geral_folgas_adicionadas,
        total_geral_folgas_usadas=total_geral_folgas_usadas,
        total_geral_conversoes=total_geral_conversoes,
        total_geral_saldo=total_geral_saldo
    )

@bp.route('/calendario/<int:year>/<int:month>', methods=['GET'], strict_slashes=False)
@login_required
def calendario_mes(year, month):
    """Retorna calendário do mês com dados da jornada e feriados"""
    if current_user.nivel not in ('operador', 'admin', 'DEV'):
        return jsonify({'ok': False, 'error': 'Acesso negado'}), 403
    
    try:
        from calendar import monthrange, Calendar
        import calendar as cal_module
        
        # Calcular início e fim do mês
        first_day = date(year, month, 1)
        last_day = date(year, month, monthrange(year, month)[1])
        
        # Buscar registros do mês
        records = TimeOffRecord.query.filter(
            TimeOffRecord.date >= first_day,
            TimeOffRecord.date <= last_day
        ).order_by(TimeOffRecord.date.asc()).all()
        
        # Buscar feriados do mês (da Escala)
        feriados = Holiday.query.filter(
            Holiday.date >= first_day,
            Holiday.date <= last_day
        ).order_by(Holiday.date.asc()).all()
        
        # Organizar dados por dia
        calendario = {}
        from calendar import Calendar
        cal = Calendar(firstweekday=6)  # Domingo = 6 (0=segunda)
        
        for day in cal.itermonthdates(year, month):
            if day.month == month:  # Apenas dias do mês atual
                day_records = [r for r in records if r.date == day]
                day_feriado = next((f for f in feriados if f.date == day), None)
                
                calendario[day.day] = {
                    'date': day.strftime('%Y-%m-%d'),
                    'day_of_week': day.weekday(),  # 0=segunda, 6=domingo
                    'records': [{
                        'id': r.id,
                        'collaborator_id': r.collaborator_id,
                        'collaborator_name': _get_collaborator_display_name(r.collaborator) if r.collaborator else f"ID {r.collaborator_id}",
                        'record_type': r.record_type,
                        'hours': r.hours,
                        'days': r.days,
                        'notes': r.notes
                    } for r in day_records],
                    'feriado': {
                        'name': day_feriado.name,
                        'kind': day_feriado.kind
                    } if day_feriado else None
                }
        
        return jsonify({
            'ok': True,
            'year': year,
            'month': month,
            'month_name': cal_module.month_name[month],
            'calendario': calendario,
            'feriados': [{'date': f.date.strftime('%Y-%m-%d'), 'name': f.name, 'kind': f.kind} for f in feriados]
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/config/valor-dia', methods=['GET'], strict_slashes=False)
@login_required
def get_day_value():
    """Retorna o valor configurado por dia"""
    if current_user.nivel not in ('admin', 'DEV', 'operador'):
        return jsonify({'ok': False, 'error': 'Acesso negado'}), 403
    
    day_value = _get_day_value()
    return jsonify({'ok': True, 'day_value': day_value})

@bp.route('/config/valor-dia', methods=['POST'], strict_slashes=False)
@login_required
def set_day_value():
    """Salva o valor configurado por dia"""
    if current_user.nivel not in ('admin', 'DEV', 'operador'):
        return jsonify({'ok': False, 'error': 'Acesso negado'}), 403
    
    try:
        data = request.get_json()
        if not data or 'day_value' not in data:
            return jsonify({'ok': False, 'error': 'Valor não fornecido'}), 400
        
        day_value = float(data['day_value'])
        if day_value < 0:
            return jsonify({'ok': False, 'error': 'Valor deve ser positivo'}), 400
        
        setting = AppSetting.query.filter_by(key='jornada_valor_dia').first()
        if not setting:
            setting = AppSetting(key='jornada_valor_dia', value=str(day_value))
            db.session.add(setting)
        else:
            setting.value = str(day_value)
        
        db.session.commit()
        
        # Registrar no log
        log = SystemLog()
        log.origem = 'Jornada'
        log.evento = 'configuracao_valor_dia'
        log.detalhes = f'Valor por dia atualizado para R$ {day_value:.2f} por {current_user.username}'
        log.usuario = current_user.username
        db.session.add(log)
        db.session.commit()
        
        return jsonify({'ok': True, 'day_value': day_value})
    except ValueError:
        return jsonify({'ok': False, 'error': 'Valor inválido'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500

