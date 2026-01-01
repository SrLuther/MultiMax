from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, session
from flask_login import login_required, current_user
from .. import db
from ..models import Collaborator, RegistroJornada, RegistroJornadaChange, Holiday, SystemLog, LeaveAssignment, Vacation, MedicalCertificate, HourBankEntry, LeaveCredit, LeaveConversion
from datetime import datetime, date
from zoneinfo import ZoneInfo
from uuid import uuid4
from sqlalchemy import func
import io
import csv
from openpyxl import Workbook

bp = Blueprint('jornada', __name__, url_prefix='/jornada')


# ============================================================================
# Funções auxiliares
# ============================================================================

def _log_event(evento, detalhes):
    try:
        log = SystemLog()
        log.data = datetime.now(ZoneInfo('America/Sao_Paulo'))
        log.origem = 'Jornada'
        log.evento = evento
        log.detalhes = detalhes
        log.usuario = (current_user.username if current_user.is_authenticated else '-')
        db.session.add(log)
        db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass


def _ensure_collaborator_columns():
    """Garante que as colunas matricula e departamento existem na tabela collaborator"""
    try:
        from sqlalchemy import inspect, text
        insp = inspect(db.engine)
        cols_meta = [c['name'] for c in insp.get_columns('collaborator')]
        changed = False
        if 'matricula' not in cols_meta:
            db.session.execute(text('ALTER TABLE collaborator ADD COLUMN matricula TEXT'))
            changed = True
        if 'departamento' not in cols_meta:
            db.session.execute(text('ALTER TABLE collaborator ADD COLUMN departamento TEXT'))
            changed = True
        if changed:
            db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass


def _get_pagination_params(page_param='page', default=1, per_page=10):
    """Extrai e valida parâmetros de paginação"""
    try:
        page = int(request.args.get(page_param, default))
    except Exception:
        page = default
    return max(1, page), per_page


def _parse_date_filter(date_str):
    """Converte string de data em objeto date ou retorna None"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except Exception:
        return None


def _build_registros_query(q_colab=None, tipo=None, data_inicio=None, data_fim=None, sort='data desc'):
    """Constrói query para buscar registros de jornada com filtros"""
    query = db.session.query(RegistroJornada, Collaborator).join(
        Collaborator, RegistroJornada.collaborator_id == Collaborator.id
    )
    
    # Filtro por colaborador
    if q_colab:
        try:
            cid = int(q_colab)
            query = query.filter(Collaborator.id == cid)
        except Exception:
            query = query.filter(Collaborator.name.ilike(f"%{q_colab}%"))
    
    # Filtro por tipo
    if tipo in ('horas', 'dias'):
        query = query.filter(RegistroJornada.tipo_registro == tipo)
    
    # Filtros de data
    di = _parse_date_filter(data_inicio)
    df = _parse_date_filter(data_fim)
    if di:
        query = query.filter(RegistroJornada.data >= di)
    if df:
        query = query.filter(RegistroJornada.data <= df)
    
    # Ordenação
    sort_map = {
        'data asc': RegistroJornada.data.asc(),
        'data desc': RegistroJornada.data.desc(),
        'valor asc': RegistroJornada.valor.asc(),
        'valor desc': RegistroJornada.valor.desc(),
        'tipo asc': RegistroJornada.tipo_registro.asc(),
        'tipo desc': RegistroJornada.tipo_registro.desc(),
        'colaborador asc': Collaborator.name.asc(),
        'colaborador desc': Collaborator.name.desc(),
    }
    orders = []
    for part in [p.strip() for p in sort.split(',') if p.strip()]:
        if part.lower() in sort_map:
            orders.append(sort_map[part.lower()])
    if not orders:
        orders = [RegistroJornada.data.desc()]
    
    return query.order_by(*orders)


def _get_resumo_periodo(q_colab=None, data_inicio=None, data_fim=None):
    """Calcula resumo de horas e dias para um colaborador no período"""
    if not q_colab:
        return 0.0, 0.0, ''
    
    base = db.session.query(func.sum(RegistroJornada.valor)).join(
        Collaborator, RegistroJornada.collaborator_id == Collaborator.id
    )
    
    try:
        cid = int(q_colab)
        base = base.filter(Collaborator.id == cid)
        col_obj = Collaborator.query.filter_by(id=cid).first()
        resumo_colab_nome = col_obj.name if col_obj else f"ID {cid}"
    except Exception:
        base = base.filter(Collaborator.name.ilike(f"%{q_colab}%"))
        resumo_colab_nome = q_colab
    
    di = _parse_date_filter(data_inicio)
    df = _parse_date_filter(data_fim)
    if di:
        base = base.filter(RegistroJornada.data >= di)
    if df:
        base = base.filter(RegistroJornada.data <= df)
    
    sh = base.filter(RegistroJornada.tipo_registro == 'horas').scalar()
    sd = base.filter(RegistroJornada.tipo_registro == 'dias').scalar()
    
    return float(sh or 0.0), float(sd or 0.0), resumo_colab_nome


def _calculate_collaborator_stats(colaboradores, data_inicio=None, data_fim=None):
    """Calcula estatísticas (horas residuais e saldo de dias) para cada colaborador"""
    cards_stats = []
    if not colaboradores:
        return cards_stats
    
    try:
        di = _parse_date_filter(data_inicio)
        df = _parse_date_filter(data_fim)
        colab_ids = [c.id for c in colaboradores]
        
        # Agregar horas
        horas_query = db.session.query(
            HourBankEntry.collaborator_id,
            func.coalesce(func.sum(HourBankEntry.hours), 0.0).label('total_horas')
        ).filter(HourBankEntry.collaborator_id.in_(colab_ids))
        if di:
            horas_query = horas_query.filter(HourBankEntry.date >= di)
        if df:
            horas_query = horas_query.filter(HourBankEntry.date <= df)
        horas_dict = {r.collaborator_id: float(r.total_horas) for r in horas_query.group_by(HourBankEntry.collaborator_id).all()}
        
        # Agregar créditos
        creditos_query = db.session.query(
            LeaveCredit.collaborator_id,
            func.coalesce(func.sum(LeaveCredit.amount_days), 0).label('total')
        ).filter(LeaveCredit.collaborator_id.in_(colab_ids))
        if di:
            creditos_query = creditos_query.filter(LeaveCredit.date >= di)
        if df:
            creditos_query = creditos_query.filter(LeaveCredit.date <= df)
        creditos_dict = {r.collaborator_id: int(r.total) for r in creditos_query.group_by(LeaveCredit.collaborator_id).all()}
        
        # Agregar atribuições
        atribuicoes_query = db.session.query(
            LeaveAssignment.collaborator_id,
            func.coalesce(func.sum(LeaveAssignment.days_used), 0).label('total')
        ).filter(LeaveAssignment.collaborator_id.in_(colab_ids))
        if di:
            atribuicoes_query = atribuicoes_query.filter(LeaveAssignment.date >= di)
        if df:
            atribuicoes_query = atribuicoes_query.filter(LeaveAssignment.date <= df)
        atribuicoes_dict = {r.collaborator_id: int(r.total) for r in atribuicoes_query.group_by(LeaveAssignment.collaborator_id).all()}
        
        # Agregar conversões
        conversoes_query = db.session.query(
            LeaveConversion.collaborator_id,
            func.coalesce(func.sum(LeaveConversion.amount_days), 0).label('total')
        ).filter(LeaveConversion.collaborator_id.in_(colab_ids))
        if di:
            conversoes_query = conversoes_query.filter(LeaveConversion.date >= di)
        if df:
            conversoes_query = conversoes_query.filter(LeaveConversion.date <= df)
        conversoes_dict = {r.collaborator_id: int(r.total) for r in conversoes_query.group_by(LeaveConversion.collaborator_id).all()}
        
        # Processar resultados
        for c in colaboradores:
            try:
                hsum = horas_dict.get(c.id, 0.0)
                residual_hours = (hsum % 8.0) if hsum >= 0.0 else -((-hsum) % 8.0)
                credits_sum = creditos_dict.get(c.id, 0)
                assigned_sum = atribuicoes_dict.get(c.id, 0)
                converted_sum = conversoes_dict.get(c.id, 0)
                saldo_days = credits_sum - assigned_sum - converted_sum
                cards_stats.append({
                    'id': c.id,
                    'name': c.name,
                    'residual_hours': residual_hours,
                    'saldo_days': saldo_days,
                    'assigned_days': assigned_sum
                })
            except Exception:
                pass
    except Exception:
        pass
    
    return cards_stats


def _paginate_query(query, page, per_page):
    """Aplica paginação a uma query"""
    total = query.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    if page > total_pages:
        page = total_pages
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return items, page, total_pages, total


def _paginate_list(items, page, per_page):
    """Pagina uma lista Python"""
    total = len(items)
    total_pages = max(1, (total + per_page - 1) // per_page)
    if page > total_pages:
        page = total_pages
    start = (page - 1) * per_page
    end = start + per_page
    return items[start:end], page, total_pages, total


# ============================================================================
# Rotas
# ============================================================================

@bp.route('/', methods=['GET'], strict_slashes=False)
@login_required
def index():
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('home.index'))
    
    _ensure_collaborator_columns()
    
    # Parâmetros de filtro
    q_colab = (request.args.get('colaborador') or '').strip()
    tipo = (request.args.get('tipo') or '').strip()
    data_inicio = (request.args.get('inicio') or '').strip()
    data_fim = (request.args.get('fim') or '').strip()
    sort = (request.args.get('sort') or 'data desc').strip()
    
    # Paginação principal
    page, per_page = _get_pagination_params('page', 1, 10)
    
    # Query e paginação de registros
    query = _build_registros_query(q_colab, tipo, data_inicio, data_fim, sort)
    items, page, total_pages, total = _paginate_query(query, page, per_page)
    
    # Colaboradores e resumo
    colaboradores = Collaborator.query.filter_by(active=True).order_by(Collaborator.name.asc()).all()
    selected_tipo = session.get('jornada_tipo', '')
    resumo_horas, resumo_dias, resumo_colab_nome = _get_resumo_periodo(q_colab, data_inicio, data_fim)
    
    # Estatísticas dos colaboradores
    cards_stats = _calculate_collaborator_stats(colaboradores, data_inicio, data_fim)
    
    # Paginação dos cards
    try:
        cs_collab_id = request.args.get('cs_collaborator_id', type=int)
    except Exception:
        cs_collab_id = None
    cs_page, _ = _get_pagination_params('cs_page', 1, 1)
    cs_list = [s for s in cards_stats if s.get('id') == cs_collab_id] if cs_collab_id else cards_stats
    cs_item, cs_page, cs_total_pages, _ = _paginate_list(cs_list, cs_page, 1)
    cs_item = cs_item[0] if cs_item else None
    
    # Folgas (Uso)
    try:
        la_collab_id = request.args.get('la_collaborator_id', type=int)
    except Exception:
        la_collab_id = None
    la_q = LeaveAssignment.query.order_by(LeaveAssignment.date.desc())
    if la_collab_id:
        la_q = la_q.filter(LeaveAssignment.collaborator_id == la_collab_id)
    leave_assignments_all = la_q.all()
    leave_assignments_page, la_page, la_total_pages, _ = _paginate_list(leave_assignments_all, _get_pagination_params('la_page', 1, 10)[0], 10)
    
    # Férias
    try:
        ferias_collab_id = request.args.get('ferias_collaborator_id', type=int)
    except Exception:
        ferias_collab_id = None
    ferias_q = Vacation.query.order_by(Vacation.data_inicio.desc())
    if ferias_collab_id:
        ferias_q = ferias_q.filter(Vacation.collaborator_id == ferias_collab_id)
    ferias_all = ferias_q.all()
    ferias_page_items, ferias_page, ferias_total_pages, _ = _paginate_list(ferias_all, _get_pagination_params('ferias_page', 1, 10)[0], 10)
    
    # Atestados
    try:
        at_collab_id = request.args.get('at_collaborator_id', type=int)
    except Exception:
        at_collab_id = None
    at_q = MedicalCertificate.query.order_by(MedicalCertificate.data_inicio.desc())
    if at_collab_id:
        at_q = at_q.filter(MedicalCertificate.collaborator_id == at_collab_id)
    atestados_all = at_q.all()
    atestados_page, at_page, at_total_pages, _ = _paginate_list(atestados_all, _get_pagination_params('at_page', 1, 10)[0], 10)

    return render_template(
        'jornada.html',
        registros=items,
        colaboradores=colaboradores,
        page=page,
        total_pages=total_pages,
        total=total,
        q_colab=q_colab,
        tipo=(tipo or selected_tipo),
        data_inicio=data_inicio,
        data_fim=data_fim,
        sort=sort,
        resumo_horas=resumo_horas,
        resumo_dias=resumo_dias,
        resumo_colab_nome=resumo_colab_nome,
        active_page='jornada'
        , leave_assignments_page=leave_assignments_page, la_page=la_page, la_total_pages=la_total_pages, la_collab_id=la_collab_id
        , ferias_page_items=ferias_page_items, ferias_page=ferias_page, ferias_total_pages=ferias_total_pages, ferias_collab_id=ferias_collab_id
        , atestados_page=atestados_page, at_page=at_page, at_total_pages=at_total_pages, at_collab_id=at_collab_id
        , cards_stats=cards_stats, cs_item=cs_item, cs_page=cs_page, cs_total_pages=cs_total_pages, cs_collab_id=cs_collab_id
    )


@bp.route('/search_collaborators', methods=['GET'], strict_slashes=False)
@login_required
def search_collaborators():
    q = (request.args.get('q') or '').strip()
    items = []
    base = Collaborator.query.filter_by(active=True)
    if q:
        base = base.filter(Collaborator.name.ilike(f"%{q}%"))
    cols = base.order_by(Collaborator.name.asc()).limit(20).all()
    for c in cols:
        items.append({'id': c.id, 'name': c.name})
    return jsonify({'ok': True, 'items': items})


@bp.route('/is_holiday', methods=['GET'], strict_slashes=False)
@login_required
def is_holiday():
    d = (request.args.get('date') or '').strip()
    try:
        dt = datetime.strptime(d, '%Y-%m-%d').date()
    except Exception:
        return jsonify({'ok': False, 'holiday': False})
    h = Holiday.query.filter_by(date=dt).first()
    return jsonify({'ok': True, 'holiday': bool(h), 'name': (h.name if h else '')})


@bp.route('/create', methods=['POST'], strict_slashes=False)
@login_required
def create():
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Apenas Administradores podem criar.', 'danger')
        return redirect(url_for('jornada.index'))
    tipo = (request.form.get('tipo') or '').strip()
    session['jornada_tipo'] = tipo
    colab_id = (request.form.get('collaborator_id') or '').strip()
    valor = (request.form.get('valor') or '').strip()
    data_str = (request.form.get('data') or '').strip()
    try:
        cid = int(colab_id)
    except Exception:
        flash('Colaborador inválido.', 'danger')
        return redirect(url_for('jornada.index'))
    if tipo not in ('horas', 'dias'):
        flash('Tipo inválido.', 'danger')
        return redirect(url_for('jornada.index'))
    try:
        val = float(valor)
    except Exception:
        flash('Valor inválido.', 'danger')
        return redirect(url_for('jornada.index'))
    if tipo == 'horas' and (val < 0 or val > 24):
        flash('Horas fora do intervalo.', 'danger')
        return redirect(url_for('jornada.index'))
    if tipo == 'dias' and (val < 1 or val > 365):
        flash('Dias fora do intervalo.', 'danger')
        return redirect(url_for('jornada.index'))
    try:
        dt = datetime.strptime(data_str, '%Y-%m-%d').date()
    except Exception:
        flash('Data inválida.', 'danger')
        return redirect(url_for('jornada.index'))
    if dt > date.today():
        flash('Data futura não permitida.', 'danger')
        return redirect(url_for('jornada.index'))
    try:
        obs = (request.form.get('observacao') or '').strip()
        
        # Criar registro em RegistroJornada
        w = RegistroJornada()
        w.id = str(uuid4())
        w.collaborator_id = cid
        w.tipo_registro = tipo
        w.valor = val
        w.data = dt
        w.created_at = datetime.now(ZoneInfo('America/Sao_Paulo'))
        w.updated_at = w.created_at
        w.observacao = obs
        db.session.add(w)
        
        # Também criar nas tabelas antigas para manter compatibilidade
        if tipo == 'horas':
            # Criar em HourBankEntry para manter compatibilidade com cálculos
            hb = HourBankEntry()
            hb.collaborator_id = cid
            hb.date = dt
            hb.hours = val
            hb.reason = obs
            db.session.add(hb)
            
            # Aplicar conversão automática 8h -> 1 dia (se necessário)
            try:
                from sqlalchemy import func
                total_hours = db.session.query(func.coalesce(func.sum(HourBankEntry.hours), 0.0)).filter(HourBankEntry.collaborator_id == cid).scalar() or 0.0
                total_hours = float(total_hours)
                auto_credits = db.session.query(func.coalesce(func.sum(LeaveCredit.amount_days), 0)).filter(LeaveCredit.collaborator_id == cid, LeaveCredit.origin == 'horas').scalar() or 0
                auto_credits = int(auto_credits)
                desired_credits = int(total_hours // 8.0)
                missing = max(0, desired_credits - auto_credits)
                if missing > 0:
                    for _ in range(missing):
                        lc = LeaveCredit()
                        lc.collaborator_id = cid
                        lc.date = date.today()
                        lc.amount_days = 1
                        lc.origin = 'horas'
                        lc.notes = 'Crédito automático por 8h no banco de horas'
                        db.session.add(lc)
                    for _ in range(missing):
                        adj = HourBankEntry()
                        adj.collaborator_id = cid
                        adj.date = date.today()
                        adj.hours = -8.0
                        adj.reason = 'Conversão automática: -8h por +1 dia de folga'
                        db.session.add(adj)
            except Exception:
                pass  # Se der erro na conversão, continua mesmo assim
        
        elif tipo == 'dias':
            # Criar em LeaveCredit para manter compatibilidade
            lc = LeaveCredit()
            lc.collaborator_id = cid
            lc.date = dt
            lc.amount_days = int(val)
            lc.origin = 'manual'
            lc.notes = obs
            db.session.add(lc)
        
        db.session.commit()
        _log_event('create', f"{tipo} {val} em {dt} para colaborador {cid}")
        flash('Registro criado.', 'success')
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f'Erro ao criar: {e}', 'danger')
    return redirect(url_for('jornada.index'))


@bp.route('/update/<worklog_id>', methods=['POST'], strict_slashes=False)
@login_required
def update(worklog_id):
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Apenas Administradores podem editar.', 'danger')
        return redirect(url_for('jornada.index'))
    w = RegistroJornada.query.filter_by(id=worklog_id).first()
    if not w:
        flash('Registro não encontrado.', 'danger')
        return redirect(url_for('jornada.index'))
    old = {'tipo': w.tipo_registro, 'valor': float(w.valor or 0), 'data': w.data}
    tipo = (request.form.get('tipo') or '').strip()
    colab_id = (request.form.get('collaborator_id') or '').strip()
    valor = (request.form.get('valor') or '').strip()
    data_str = (request.form.get('data') or '').strip()
    try:
        cid = int(colab_id)
    except Exception:
        flash('Colaborador inválido.', 'danger')
        return redirect(url_for('jornada.index'))
    try:
        val = float(valor)
    except Exception:
        flash('Valor inválido.', 'danger')
        return redirect(url_for('jornada.index'))
    try:
        dt = datetime.strptime(data_str, '%Y-%m-%d').date()
    except Exception:
        flash('Data inválida.', 'danger')
        return redirect(url_for('jornada.index'))
    if dt > date.today():
        flash('Data futura não permitida.', 'danger')
        return redirect(url_for('jornada.index'))
    try:
        obs = (request.form.get('observacao') or '').strip()
        w.collaborator_id = cid
        w.tipo_registro = tipo
        w.valor = val
        w.data = dt
        w.updated_at = datetime.now(ZoneInfo('America/Sao_Paulo'))
        w.observacao = obs
        ch = RegistroJornadaChange()
        ch.worklog_id = w.id
        ch.changed_by = current_user.id
        ch.old_tipo = old['tipo']
        ch.old_valor = old['valor']
        ch.old_data = old['data']
        ch.new_tipo = tipo
        ch.new_valor = val
        ch.new_data = dt
        db.session.add(ch)
        db.session.commit()
        _log_event('update', f"{tipo} {val} em {dt} para colaborador {cid}")
        flash('Registro atualizado.', 'success')
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f'Erro ao atualizar: {e}', 'danger')
    return redirect(url_for('jornada.index'))


@bp.route('/delete/<worklog_id>', methods=['POST'], strict_slashes=False)
@login_required
def delete(worklog_id):
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Apenas Administradores podem excluir.', 'danger')
        return redirect(url_for('jornada.index'))
    w = RegistroJornada.query.filter_by(id=worklog_id).first()
    if not w:
        flash('Registro não encontrado.', 'danger')
        return redirect(url_for('jornada.index'))
    try:
        db.session.delete(w)
        db.session.commit()
        _log_event('delete', f"registro {worklog_id}")
        flash('Registro excluído.', 'success')
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f'Erro ao excluir: {e}', 'danger')
    return redirect(url_for('jornada.index'))


@bp.route('/history/<worklog_id>', methods=['GET'], strict_slashes=False)
@login_required
def history(worklog_id):
    w = RegistroJornada.query.filter_by(id=worklog_id).first()
    if not w:
        return jsonify({'ok': False, 'items': []})
    items = []
    for ch in RegistroJornadaChange.query.filter_by(worklog_id=worklog_id).order_by(RegistroJornadaChange.changed_at.desc()).limit(20).all():
        items.append({
            'changed_at': ch.changed_at.strftime('%Y-%m-%d %H:%M') if ch.changed_at else '',
            'by': current_user.username if current_user.is_authenticated else '',
            'old_tipo': ch.old_tipo,
            'old_valor': float(ch.old_valor or 0),
            'old_data': ch.old_data.strftime('%Y-%m-%d') if ch.old_data else '',
            'new_tipo': ch.new_tipo,
            'new_valor': float(ch.new_valor or 0),
            'new_data': ch.new_data.strftime('%Y-%m-%d') if ch.new_data else ''
        })
    return jsonify({'ok': True, 'items': items})

@bp.route('/export', methods=['GET'], strict_slashes=False)
@login_required
def export():
    if current_user.nivel not in ('operador', 'admin', 'DEV'):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('jornada.index'))
    fmt = (request.args.get('fmt') or 'csv').strip().lower()
    q_colab = (request.args.get('colaborador') or '').strip()
    tipo = (request.args.get('tipo') or '').strip()
    data_inicio = (request.args.get('inicio') or '').strip()
    data_fim = (request.args.get('fim') or '').strip()
    query = db.session.query(RegistroJornada, Collaborator).join(Collaborator, RegistroJornada.collaborator_id == Collaborator.id)
    if q_colab:
        try:
            cid = int(q_colab)
            query = query.filter(Collaborator.id == cid)
        except Exception:
            query = query.filter(Collaborator.name.ilike(f"%{q_colab}%"))
    if tipo in ('horas', 'dias'):
        query = query.filter(RegistroJornada.tipo_registro == tipo)
    if data_inicio:
        try:
            di = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            query = query.filter(RegistroJornada.data >= di)
        except Exception:
            pass
    if data_fim:
        try:
            df = datetime.strptime(data_fim, '%Y-%m-%d').date()
            query = query.filter(RegistroJornada.data <= df)
        except Exception:
            pass
    rows = query.order_by(RegistroJornada.data.desc()).all()
    if fmt == 'xlsx':
        wb = Workbook()
        ws = wb.active
        if not ws:
            ws = wb.create_sheet(title='Jornada')
        else:
            ws.title = 'Jornada'
        ws.append(['ID', 'Colaborador', 'Tipo', 'Valor', 'Data', 'Observações', 'Criado em'])
        for w, c in rows:
            ws.append([w.id, c.name, w.tipo_registro, float(w.valor or 0), w.data.strftime('%Y-%m-%d'), (w.observacao or ''), (w.created_at.strftime('%Y-%m-%d %H:%M') if w.created_at else '')])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return send_file(buf, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='registro_jornada.xlsx')
    else:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(['ID', 'Colaborador', 'Tipo', 'Valor', 'Data', 'Observações', 'Criado em'])
        for w, c in rows:
            writer.writerow([w.id, c.name, w.tipo_registro, f"{float(w.valor or 0):.2f}", w.data.strftime('%Y-%m-%d'), (w.observacao or ''), (w.created_at.strftime('%Y-%m-%d %H:%M') if w.created_at else '')])
        data_str = buf.getvalue().encode('utf-8')
        return send_file(io.BytesIO(data_str), mimetype='text/csv', as_attachment=True, download_name='registro_jornada.csv')

@bp.route('/relatorio', methods=['GET'], strict_slashes=False)
@login_required
def relatorio():
    if current_user.nivel not in ('operador', 'admin', 'DEV'):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('jornada.index'))
    collab_id = request.args.get('collaborator_id', type=int)
    inicio = (request.args.get('inicio') or '').strip()
    fim = (request.args.get('fim') or '').strip()
    di = None
    df = None
    try:
        if inicio:
            di = datetime.strptime(inicio, '%Y-%m-%d').date()
    except Exception:
        di = None
    try:
        if fim:
            df = datetime.strptime(fim, '%Y-%m-%d').date()
    except Exception:
        df = None
    colaboradores = Collaborator.query.filter_by(active=True).order_by(Collaborator.name.asc()).all()
    def _range_filter(q, col):
        if di and df:
            return q.filter(col.between(di, df))
        if di:
            return q.filter(col >= di)
        if df:
            return q.filter(col <= df)
        return q
    resumo = []
    eventos = []
    targets = colaboradores if not collab_id else [c for c in colaboradores if c.id == collab_id]
    for c in targets:
        try:
            hq = _range_filter(HourBankEntry.query.filter(HourBankEntry.collaborator_id == c.id), HourBankEntry.date)
            cq = _range_filter(LeaveCredit.query.filter(LeaveCredit.collaborator_id == c.id), LeaveCredit.date)
            aq = _range_filter(LeaveAssignment.query.filter(LeaveAssignment.collaborator_id == c.id), LeaveAssignment.date)
            vq = _range_filter(LeaveConversion.query.filter(LeaveConversion.collaborator_id == c.id), LeaveConversion.date)
            rjq = _range_filter(RegistroJornada.query.filter(RegistroJornada.collaborator_id == c.id), RegistroJornada.data)
            rj_obs_map = {}
            rj_obs_date_map = {}
            for w in rjq.all():
                try:
                    k = (w.data, (w.tipo_registro or ''))
                    if k not in rj_obs_map and (w.observacao or ''):
                        rj_obs_map[k] = (w.observacao or '')
                    if (w.data not in rj_obs_date_map) and (w.observacao or ''):
                        rj_obs_date_map[w.data] = (w.observacao or '')
                except Exception:
                    pass
            hsum = float(db.session.query(func.coalesce(func.sum(HourBankEntry.hours), 0.0)).filter(HourBankEntry.collaborator_id == c.id).scalar() or 0.0)
            if di or df:
                hsum = float(hq.with_entities(func.coalesce(func.sum(HourBankEntry.hours), 0.0)).scalar() or 0.0)
            residual_hours = (hsum % 8.0) if hsum >= 0.0 else - ((-hsum) % 8.0)
            credits_sum = int(db.session.query(func.coalesce(func.sum(LeaveCredit.amount_days), 0)).filter(LeaveCredit.collaborator_id == c.id).scalar() or 0)
            assigned_sum = int(db.session.query(func.coalesce(func.sum(LeaveAssignment.days_used), 0)).filter(LeaveAssignment.collaborator_id == c.id).scalar() or 0)
            converted_sum = int(db.session.query(func.coalesce(func.sum(LeaveConversion.amount_days), 0)).filter(LeaveConversion.collaborator_id == c.id).scalar() or 0)
            if di or df:
                credits_sum = int(cq.with_entities(func.coalesce(func.sum(LeaveCredit.amount_days), 0)).scalar() or 0)
                assigned_sum = int(aq.with_entities(func.coalesce(func.sum(LeaveAssignment.days_used), 0)).scalar() or 0)
                converted_sum = int(vq.with_entities(func.coalesce(func.sum(LeaveConversion.amount_days), 0)).scalar() or 0)
            saldo_days = credits_sum - assigned_sum - converted_sum
            resumo.append({'id': c.id, 'name': c.name, 'residual_hours': residual_hours, 'saldo_days': saldo_days})
            for e in hq.order_by(HourBankEntry.date.desc()).all():
                if e.date:
                    desc = (e.reason or '')
                    eventos.append({'collab_id': c.id, 'collab_name': c.name, 'date': e.date, 'tipo': 'horas', 'valor': float(e.hours or 0.0), 'descricao': desc})
            for cr in cq.order_by(LeaveCredit.date.desc()).all():
                if cr.date:
                    desc = (cr.notes or '')
                    eventos.append({'collab_id': c.id, 'collab_name': c.name, 'date': cr.date, 'tipo': 'dias_add', 'valor': int(cr.amount_days or 0), 'descricao': desc})
            for a in aq.order_by(LeaveAssignment.date.desc()).all():
                if a.date:
                    desc = (a.notes or '')
                    if not desc:
                        desc = (rj_obs_map.get((a.date, 'dias')) or '')
                    if not desc:
                        desc = (rj_obs_date_map.get(a.date) or '')
                    eventos.append({'collab_id': c.id, 'collab_name': c.name, 'date': a.date, 'tipo': 'dias_uso', 'valor': -int(a.days_used or 0), 'descricao': desc})
            for v in vq.order_by(LeaveConversion.date.desc()).all():
                if v.date:
                    notes = (v.notes or '')
                    if not notes:
                        notes = (rj_obs_map.get((v.date, 'dias')) or '')
                    if not notes:
                        notes = (rj_obs_date_map.get(v.date) or '')
                    eventos.append({'collab_id': c.id, 'collab_name': c.name, 'date': v.date, 'tipo': 'dias_pago', 'valor': int(v.amount_days or 0), 'descricao': f"R$ {float(v.amount_paid or 0):.2f} — {notes}"})
        except Exception as e:
            _log_event('relatorio_error', f"collab {c.id} {c.name}: {e}")
    eventos.sort(key=lambda it: ((it.get('collab_name') or ''), (it.get('date') or date.min)), reverse=True)
    return render_template('relatorio_jornada.html', resumo=resumo, eventos=eventos, colaboradores=colaboradores, inicio=inicio, fim=fim, collab_id=collab_id, active_page='jornada')

@bp.route('/relatorio/export', methods=['GET'], strict_slashes=False)
@login_required
def relatorio_export():
    if current_user.nivel not in ('operador', 'admin', 'DEV'):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('jornada.index'))
    collab_id = request.args.get('collaborator_id', type=int)
    inicio = (request.args.get('inicio') or '').strip()
    fim = (request.args.get('fim') or '').strip()
    di = None
    df = None
    try:
        if inicio:
            di = datetime.strptime(inicio, '%Y-%m-%d').date()
    except Exception:
        di = None
    try:
        if fim:
            df = datetime.strptime(fim, '%Y-%m-%d').date()
    except Exception:
        df = None
    colaboradores = Collaborator.query.filter_by(active=True).order_by(Collaborator.name.asc()).all()
    def _range_filter(q, col):
        if di and df:
            return q.filter(col.between(di, df))
        if di:
            return q.filter(col >= di)
        if df:
            return q.filter(col <= df)
        return q
    resumo = []
    eventos = []
    targets = colaboradores if not collab_id else [c for c in colaboradores if c.id == collab_id]
    for c in targets:
        try:
            hq = _range_filter(HourBankEntry.query.filter(HourBankEntry.collaborator_id == c.id), HourBankEntry.date)
            cq = _range_filter(LeaveCredit.query.filter(LeaveCredit.collaborator_id == c.id), LeaveCredit.date)
            aq = _range_filter(LeaveAssignment.query.filter(LeaveAssignment.collaborator_id == c.id), LeaveAssignment.date)
            vq = _range_filter(LeaveConversion.query.filter(LeaveConversion.collaborator_id == c.id), LeaveConversion.date)
            rjq = _range_filter(RegistroJornada.query.filter(RegistroJornada.collaborator_id == c.id), RegistroJornada.data)
            rj_obs_map = {}
            rj_obs_date_map = {}
            for w in rjq.all():
                try:
                    k = (w.data, (w.tipo_registro or ''))
                    if k not in rj_obs_map and (w.observacao or ''):
                        rj_obs_map[k] = (w.observacao or '')
                    if (w.data not in rj_obs_date_map) and (w.observacao or ''):
                        rj_obs_date_map[w.data] = (w.observacao or '')
                except Exception:
                    pass
            hsum = float(hq.with_entities(func.coalesce(func.sum(HourBankEntry.hours), 0.0)).scalar() or 0.0)
            residual_hours = (hsum % 8.0) if hsum >= 0.0 else - ((-hsum) % 8.0)
            credits_sum = int(cq.with_entities(func.coalesce(func.sum(LeaveCredit.amount_days), 0)).scalar() or 0)
            assigned_sum = int(aq.with_entities(func.coalesce(func.sum(LeaveAssignment.days_used), 0)).scalar() or 0)
            converted_sum = int(vq.with_entities(func.coalesce(func.sum(LeaveConversion.amount_days), 0)).scalar() or 0)
            saldo_days = credits_sum - assigned_sum - converted_sum
            resumo.append({'id': c.id, 'name': c.name, 'residual_hours': residual_hours, 'saldo_days': saldo_days})
            for e in hq.order_by(HourBankEntry.date.desc()).all():
                if e.date:
                    desc = (e.reason or '')
                    eventos.append({'date': e.date, 'collab': c.name, 'tipo': 'Horas', 'valor': float(e.hours or 0.0), 'obs': desc})
            for cr in cq.order_by(LeaveCredit.date.desc()).all():
                if cr.date:
                    desc = (cr.notes or '')
                    eventos.append({'date': cr.date, 'collab': c.name, 'tipo': 'Dias acrescentados', 'valor': int(cr.amount_days or 0), 'obs': desc})
            for a in aq.order_by(LeaveAssignment.date.desc()).all():
                if a.date:
                    desc = (a.notes or '')
                    if not desc:
                        desc = (rj_obs_map.get((a.date, 'dias')) or '')
                    if not desc:
                        desc = (rj_obs_date_map.get(a.date) or '')
                    eventos.append({'date': a.date, 'collab': c.name, 'tipo': 'Dias usados', 'valor': -int(a.days_used or 0), 'obs': desc})
            for v in vq.order_by(LeaveConversion.date.desc()).all():
                if v.date:
                    notes = (v.notes or '')
                    if not notes:
                        notes = (rj_obs_map.get((v.date, 'dias')) or '')
                    if not notes:
                        notes = (rj_obs_date_map.get(v.date) or '')
                    eventos.append({'date': v.date, 'collab': c.name, 'tipo': 'Dias convertidos em R$', 'valor': int(v.amount_days or 0), 'obs': f"R$ {float(v.amount_paid or 0):.2f} — {notes}"})
        except Exception as e:
            _log_event('relatorio_export_error', f"collab {c.id} {c.name}: {e}")
    eventos.sort(key=lambda it: ((it.get('collab') or ''), (it.get('date') or date.min)), reverse=True)
    wb = Workbook()
    ws_resumo = wb.active
    if not ws_resumo:
        ws_resumo = wb.create_sheet(title='Resumo')
    else:
        ws_resumo.title = 'Resumo'
    ws_resumo.append(['Colaborador', 'Horas restantes', 'Dias restantes'])
    for r in resumo:
        ws_resumo.append([r['name'], float(r['residual_hours'] or 0.0), int(r['saldo_days'] or 0)])
    ws_eventos = wb.create_sheet(title='Eventos')
    ws_eventos.append(['Data', 'Colaborador', 'Tipo', 'Valor', 'Observações'])
    for e in eventos:
        ws_eventos.append([(e.get('date').strftime('%Y-%m-%d') if e.get('date') else ''), e.get('collab') or '', e.get('tipo') or '', e.get('valor'), e.get('obs') or ''])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(buf, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='relatorio_jornada.xlsx')


@bp.route('/migrar', methods=['POST'], strict_slashes=False)
@login_required
def migrar():
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Apenas Administradores podem migrar.', 'danger')
        return redirect(url_for('jornada.index'))
    from ..models import HourBankEntry, LeaveCredit
    created = 0
    try:
        entries = HourBankEntry.query.all()
        for e in entries:
            exists = RegistroJornada.query.filter_by(
                collaborator_id=e.collaborator_id,
                tipo_registro='horas',
                data=e.date
            ).first()
            if exists:
                continue
            w = RegistroJornada()
            w.id = str(uuid4())
            w.collaborator_id = e.collaborator_id
            w.tipo_registro = 'horas'
            w.valor = float(e.hours or 0.0)
            w.data = e.date
            w.created_at = datetime.now(ZoneInfo('America/Sao_Paulo'))
            w.updated_at = w.created_at
            w.observacao = (e.reason or '')
            db.session.add(w)
            created += 1
        credits = LeaveCredit.query.all()
        for c in credits:
            exists = RegistroJornada.query.filter_by(
                collaborator_id=c.collaborator_id,
                tipo_registro='dias',
                data=c.date
            ).first()
            if exists:
                continue
            w = RegistroJornada()
            w.id = str(uuid4())
            w.collaborator_id = c.collaborator_id
            w.tipo_registro = 'dias'
            w.valor = float(c.amount_days or 0)
            w.data = c.date
            w.created_at = datetime.now(ZoneInfo('America/Sao_Paulo'))
            w.updated_at = w.created_at
            w.observacao = (c.notes or '')
            db.session.add(w)
            created += 1
        db.session.commit()
        _log_event('migrate', f"{created} registros migrados")
        flash(f'{created} registros migrados.', 'success')
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f'Erro na migração: {e}', 'danger')
    return redirect(url_for('jornada.index'))

@bp.route('/sincronizar-observacoes', methods=['POST'], strict_slashes=False)
@login_required
def sincronizar_observacoes():
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Apenas Administradores podem sincronizar.', 'danger')
        return redirect(url_for('jornada.index'))
    updated = 0
    try:
        horas_regs = RegistroJornada.query.filter(RegistroJornada.tipo_registro == 'horas').all()
        for w in horas_regs:
            try:
                src = HourBankEntry.query.filter_by(collaborator_id=w.collaborator_id, date=w.data).order_by(HourBankEntry.id.asc()).first()
                val = (src.reason if src and src.reason else '')
                if val and not (w.observacao or '').strip():
                    w.observacao = val
                    updated += 1
            except Exception:
                pass
        dias_regs = RegistroJornada.query.filter(RegistroJornada.tipo_registro == 'dias').all()
        for w in dias_regs:
            try:
                src = LeaveCredit.query.filter_by(collaborator_id=w.collaborator_id, date=w.data).order_by(LeaveCredit.id.asc()).first()
                val = (src.notes if src and src.notes else '')
                if val and not (w.observacao or '').strip():
                    w.observacao = val
                    updated += 1
            except Exception:
                pass
        db.session.commit()
        _log_event('sync_obs', f"{updated} observações sincronizadas")
        flash(f'Observações sincronizadas: {updated}', 'success')
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f'Erro na sincronização: {e}', 'danger')
    return redirect(url_for('jornada.index'))

@bp.route('/delete_by_date', methods=['POST'], strict_slashes=False)
@login_required
def delete_by_date():
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Apenas Administradores podem excluir em massa.', 'danger')
        return redirect(url_for('jornada.index'))
    date_str = (request.form.get('data') or '').strip()
    d_start_str = (request.form.get('del_inicio') or '').strip()
    d_end_str = (request.form.get('del_fim') or '').strip()
    di = None
    df = None
    dt = None
    try:
        if d_start_str:
            di = datetime.strptime(d_start_str, '%Y-%m-%d').date()
    except Exception:
        di = None
    try:
        if d_end_str:
            df = datetime.strptime(d_end_str, '%Y-%m-%d').date()
    except Exception:
        df = None
    if not (di and df):
        try:
            if date_str:
                dt = datetime.strptime(date_str, '%Y-%m-%d').date()
        except Exception:
            dt = None
    if not ((di and df) or dt):
        flash('Período ou data inválidos para exclusão.', 'warning')
        return redirect(url_for('jornada.index'))
    try:
        if di and df:
            q = RegistroJornada.query.filter(RegistroJornada.data.between(di, df))
        else:
            q = RegistroJornada.query.filter(RegistroJornada.data == dt)
        count = q.count()
        for w in q.all():
            db.session.delete(w)
        db.session.commit()
        if di and df:
            _log_event('bulk_delete', f"{count} registros removidos no período {di} a {df}")
        else:
            _log_event('bulk_delete', f"{count} registros removidos em {dt}")
        if count > 0:
            if di and df:
                ps = (f"{di.strftime('%d/%m/%Y')} a {df.strftime('%d/%m/%Y')}" if (di and df) else '')
                flash(f'{count} registro(s) removido(s) no período {ps}.', 'success')
            else:
                ds = (dt.strftime('%d/%m/%Y') if dt else '')
                flash(f'{count} registro(s) removido(s) na data {ds}.', 'success')
        else:
            flash('Nenhum registro para remover no intervalo informado.', 'info')
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f'Erro ao excluir registros: {e}', 'danger')
    # Preservar filtros do usuário ao redirecionar
    args = {
        'colaborador': (request.form.get('colaborador') or '').strip() or None,
        'tipo': (request.form.get('tipo') or '').strip() or None,
        'inicio': (request.form.get('inicio') or '').strip() or None,
        'fim': (request.form.get('fim') or '').strip() or None,
        'sort': (request.form.get('sort') or '').strip() or None,
        'cs_collaborator_id': (request.form.get('cs_collaborator_id') or '').strip() or None,
        'cs_page': (request.form.get('cs_page') or '').strip() or None,
    }
    args = {k: v for k, v in args.items() if v is not None}
    try:
        from urllib.parse import urlencode
        base = url_for('jornada.index')
        qs = urlencode(args) if args else ''
        url = f"{base}?{qs}" if qs else base
        return redirect(url, code=303)
    except Exception:
        return redirect(url_for('jornada.index'))
