from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, session
from flask_login import login_required, current_user
from .. import db
from ..models import Collaborator, RegistroJornada, RegistroJornadaChange, Holiday, SystemLog, LeaveAssignment, Vacation, MedicalCertificate
from datetime import datetime, date
from zoneinfo import ZoneInfo
from uuid import uuid4
from sqlalchemy import func
import io
import csv
from openpyxl import Workbook

bp = Blueprint('jornada', __name__, url_prefix='/jornada')


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


@bp.route('/', methods=['GET'], strict_slashes=False)
@login_required
def index():
    if current_user.nivel not in ['operador', 'admin']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('home.index'))
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
    q_colab = (request.args.get('colaborador') or '').strip()
    tipo = (request.args.get('tipo') or '').strip()
    data_inicio = (request.args.get('inicio') or '').strip()
    data_fim = (request.args.get('fim') or '').strip()
    sort = (request.args.get('sort') or 'data desc').strip()
    try:
        page = int(request.args.get('page', '1'))
    except Exception:
        page = 1
    if page < 1:
        page = 1

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
        orders.append(sort_map.get(part.lower()))
    if not orders:
        orders = [RegistroJornada.data.desc()]
    query = query.order_by(*orders)

    per_page = 50
    total = query.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    if page > total_pages:
        page = total_pages
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    colaboradores = Collaborator.query.filter_by(active=True).order_by(Collaborator.name.asc()).all()
    selected_tipo = session.get('jornada_tipo', '')

    resumo_horas = 0.0
    resumo_dias = 0.0
    resumo_colab_nome = ''
    if q_colab:
        base = db.session.query(func.sum(RegistroJornada.valor)).join(Collaborator, RegistroJornada.collaborator_id == Collaborator.id)
        try:
            cid = int(q_colab)
            base = base.filter(Collaborator.id == cid)
            col_obj = Collaborator.query.filter_by(id=cid).first()
            if col_obj:
                resumo_colab_nome = col_obj.name
            else:
                resumo_colab_nome = f"ID {cid}"
        except Exception:
            base = base.filter(Collaborator.name.ilike(f"%{q_colab}%"))
            resumo_colab_nome = q_colab
        if data_inicio:
            try:
                di = datetime.strptime(data_inicio, '%Y-%m-%d').date()
                base = base.filter(RegistroJornada.data >= di)
            except Exception:
                pass
        if data_fim:
            try:
                df = datetime.strptime(data_fim, '%Y-%m-%d').date()
                base = base.filter(RegistroJornada.data <= df)
            except Exception:
                pass
        sh = base.filter(RegistroJornada.tipo_registro == 'horas').scalar()
        sd = base.filter(RegistroJornada.tipo_registro == 'dias').scalar()
        resumo_horas = float(sh or 0.0)
        resumo_dias = float(sd or 0.0)

    # Folgas (Uso)
    try:
        la_collab_id = request.args.get('la_collaborator_id', type=int)
    except Exception:
        la_collab_id = None
    try:
        la_page = int(request.args.get('la_page', '1'))
    except Exception:
        la_page = 1
    if la_page < 1:
        la_page = 1
    la_q = LeaveAssignment.query.order_by(LeaveAssignment.date.desc())
    if la_collab_id:
        la_q = la_q.filter(LeaveAssignment.collaborator_id == la_collab_id)
    leave_assignments_all = la_q.all()
    sub_per_page = 10
    la_total_pages = max(1, (len(leave_assignments_all) + sub_per_page - 1) // sub_per_page)
    if la_page > la_total_pages:
        la_page = la_total_pages
    la_start = (la_page - 1) * sub_per_page
    la_end = la_start + sub_per_page
    leave_assignments_page = leave_assignments_all[la_start:la_end]

    # Férias
    try:
        ferias_collab_id = request.args.get('ferias_collaborator_id', type=int)
    except Exception:
        ferias_collab_id = None
    try:
        ferias_page = int(request.args.get('ferias_page', '1'))
    except Exception:
        ferias_page = 1
    if ferias_page < 1:
        ferias_page = 1
    ferias_q = Vacation.query.order_by(Vacation.data_inicio.desc())
    if ferias_collab_id:
        ferias_q = ferias_q.filter(Vacation.collaborator_id == ferias_collab_id)
    ferias_all = ferias_q.all()
    ferias_total_pages = max(1, (len(ferias_all) + sub_per_page - 1) // sub_per_page)
    if ferias_page > ferias_total_pages:
        ferias_page = ferias_total_pages
    ferias_start = (ferias_page - 1) * sub_per_page
    ferias_end = ferias_start + sub_per_page
    ferias_page_items = ferias_all[ferias_start:ferias_end]

    # Atestados
    try:
        at_collab_id = request.args.get('at_collaborator_id', type=int)
    except Exception:
        at_collab_id = None
    try:
        at_page = int(request.args.get('at_page', '1'))
    except Exception:
        at_page = 1
    if at_page < 1:
        at_page = 1
    at_q = MedicalCertificate.query.order_by(MedicalCertificate.data_inicio.desc())
    if at_collab_id:
        at_q = at_q.filter(MedicalCertificate.collaborator_id == at_collab_id)
    atestados_all = at_q.all()
    at_total_pages = max(1, (len(atestados_all) + sub_per_page - 1) // sub_per_page)
    if at_page > at_total_pages:
        at_page = at_total_pages
    at_start = (at_page - 1) * sub_per_page
    at_end = at_start + sub_per_page
    atestados_page = atestados_all[at_start:at_end]

    # Agregação por colaborador (horas/dias)
    cards_stats = []
    try:
        h_rows = db.session.query(RegistroJornada.collaborator_id, func.sum(RegistroJornada.valor))\
            .filter(RegistroJornada.tipo_registro == 'horas')\
            .group_by(RegistroJornada.collaborator_id).all()
        d_rows = db.session.query(RegistroJornada.collaborator_id, func.sum(RegistroJornada.valor))\
            .filter(RegistroJornada.tipo_registro == 'dias')\
            .group_by(RegistroJornada.collaborator_id).all()
        h_map = {cid: float(s or 0.0) for cid, s in h_rows or []}
        d_map = {cid: float(s or 0.0) for cid, s in d_rows or []}
        for c in colaboradores:
            cards_stats.append({
                'id': c.id,
                'name': c.name,
                'horas': h_map.get(c.id, 0.0),
                'dias': d_map.get(c.id, 0.0)
            })
    except Exception:
        cards_stats = []

    # Filtro e paginação para cards (um por página)
    try:
        cs_collab_id = request.args.get('cs_collaborator_id', type=int)
    except Exception:
        cs_collab_id = None
    try:
        cs_page = int(request.args.get('cs_page', '1'))
    except Exception:
        cs_page = 1
    cs_list = cards_stats
    if cs_collab_id:
        cs_list = [s for s in cards_stats if s.get('id') == cs_collab_id]
    cs_total_pages = max(1, len(cs_list) if cs_list else 1)
    if cs_page < 1:
        cs_page = 1
    if cs_page > cs_total_pages:
        cs_page = cs_total_pages
    cs_item = (cs_list[cs_page - 1] if cs_list and len(cs_list) >= cs_page else None)

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
    if current_user.nivel != 'admin':
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
        w = RegistroJornada()
        w.id = str(uuid4())
        w.collaborator_id = cid
        w.tipo_registro = tipo
        w.valor = val
        w.data = dt
        w.created_at = datetime.now(ZoneInfo('America/Sao_Paulo'))
        w.updated_at = w.created_at
        db.session.add(w)
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
    if current_user.nivel != 'admin':
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
        w.collaborator_id = cid
        w.tipo_registro = tipo
        w.valor = val
        w.data = dt
        w.updated_at = datetime.now(ZoneInfo('America/Sao_Paulo'))
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
    if current_user.nivel != 'admin':
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
    if current_user.nivel not in ['operador', 'admin']:
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
        ws.append(['ID', 'Colaborador', 'Tipo', 'Valor', 'Data', 'Criado em'])
        for w, c in rows:
            ws.append([w.id, c.name, w.tipo_registro, float(w.valor or 0), w.data.strftime('%Y-%m-%d'), (w.created_at.strftime('%Y-%m-%d %H:%M') if w.created_at else '')])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return send_file(buf, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='registro_jornada.xlsx')
    else:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(['ID', 'Colaborador', 'Tipo', 'Valor', 'Data', 'Criado em'])
        for w, c in rows:
            writer.writerow([w.id, c.name, w.tipo_registro, f"{float(w.valor or 0):.2f}", w.data.strftime('%Y-%m-%d'), (w.created_at.strftime('%Y-%m-%d %H:%M') if w.created_at else '')])
        data_str = buf.getvalue().encode('utf-8')
        return send_file(io.BytesIO(data_str), mimetype='text/csv', as_attachment=True, download_name='registro_jornada.csv')


@bp.route('/migrar', methods=['POST'], strict_slashes=False)
@login_required
def migrar():
    if current_user.nivel != 'admin':
        flash('Apenas Administradores podem migrar.', 'danger')
        return redirect(url_for('jornada.index'))
    from ..models import HourBankEntry, LeaveCredit
    created = 0
    try:
        entries = HourBankEntry.query.all()
        for e in entries:
            w = RegistroJornada()
            w.id = str(uuid4())
            w.collaborator_id = e.collaborator_id
            w.tipo_registro = 'horas'
            w.valor = float(e.hours or 0.0)
            w.data = e.date
            w.created_at = datetime.now(ZoneInfo('America/Sao_Paulo'))
            w.updated_at = w.created_at
            db.session.add(w)
            created += 1
        credits = LeaveCredit.query.all()
        for c in credits:
            w = RegistroJornada()
            w.id = str(uuid4())
            w.collaborator_id = c.collaborator_id
            w.tipo_registro = 'dias'
            w.valor = float(c.amount_days or 0)
            w.data = c.date
            w.created_at = datetime.now(ZoneInfo('America/Sao_Paulo'))
            w.updated_at = w.created_at
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
