from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from .. import db
from ..models import TemporaryEntry, LeaveCredit, HourBankEntry, Collaborator, RegistroJornada
from uuid import uuid4
from datetime import datetime
from zoneinfo import ZoneInfo

bp = Blueprint('temporarios', __name__)

@bp.route('/temporarios', methods=['GET'], strict_slashes=False)
@login_required
def index():
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Acesso negado. Apenas Administradores podem revisar dados temporários.', 'danger')
        return redirect(url_for('home.index'))
    tipo = (request.args.get('tipo') or '').strip()
    status = (request.args.get('status') or 'pendente').strip()
    q = TemporaryEntry.query
    if tipo:
        q = q.filter(TemporaryEntry.kind == tipo)
    if status:
        q = q.filter(TemporaryEntry.status == status)
    q = q.order_by(TemporaryEntry.date.desc())
    items = q.limit(200).all()
    collabs = Collaborator.query.filter_by(active=True).order_by(Collaborator.name.asc()).all()
    colaboradores = {c.id: c.name for c in collabs}
    for it in items:
        it.collaborator_name = colaboradores.get(it.collaborator_id) or f"ID {it.collaborator_id}"
    return render_template('temporarios.html', active_page='temporarios', items=items, tipo=tipo, status=status, collab_list=collabs)

@bp.route('/temporarios/update', methods=['POST'], strict_slashes=False)
@login_required
def update():
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('temporarios.index'))
    tid = request.form.get('id', type=int)
    if not tid:
        flash('Item inválido.', 'warning')
        return redirect(url_for('temporarios.index'))
    item = TemporaryEntry.query.get(tid)
    if not item:
        flash('Item não encontrado.', 'warning')
        return redirect(url_for('temporarios.index'))
    action = (request.form.get('action') or '').strip()
    try:
        date_str = (request.form.get('date') or '').strip()
        if date_str:
            try:
                item.date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except Exception:
                pass
        collab_id = request.form.get('collaborator_id', type=int)
        if collab_id:
            try:
                c = Collaborator.query.get(int(collab_id))
                if c and c.active:
                    item.collaborator_id = int(collab_id)
                else:
                    flash('Colaborador inválido ou inativo.', 'warning')
            except Exception:
                pass
        kind = (request.form.get('kind') or '').strip()
        if kind in ('folga_credit','hour_bank','folga_hour_both'):
            item.kind = kind
        amount_days = request.form.get('amount_days')
        hours = request.form.get('hours')
        reason = (request.form.get('reason') or '').strip()
        source = (request.form.get('source') or '').strip()
        if amount_days is not None:
            try:
                item.amount_days = int(amount_days or 0)
            except Exception:
                pass
        if hours is not None:
            try:
                item.hours = float(hours or 0)
            except Exception:
                pass
        item.reason = reason
        if source:
            item.source = source
        item.updated_at = datetime.now(ZoneInfo('America/Sao_Paulo'))
        if action == 'approve':
            # aplicar ao banco definitivo e registrar na jornada
            try:
                created_days = False
                created_hours = False
                if item.kind == 'folga_credit':
                    lc = LeaveCredit()
                    lc.collaborator_id = item.collaborator_id
                    lc.date = item.date
                    lc.amount_days = max(1, int(item.amount_days or 1))
                    lc.origin = item.source or 'temporario'
                    lc.notes = item.reason or ''
                    db.session.add(lc)
                    w = RegistroJornada()
                    w.id = str(uuid4())
                    w.collaborator_id = item.collaborator_id
                    w.tipo_registro = 'dias'
                    w.valor = float(item.amount_days or 1)
                    w.data = item.date
                    w.observacao = item.reason or ''
                    db.session.add(w)
                    created_days = True
                elif item.kind == 'hour_bank':
                    hb = HourBankEntry()
                    hb.collaborator_id = item.collaborator_id
                    hb.date = item.date
                    hb.hours = float(item.hours or 0)
                    hb.reason = item.reason or ''
                    db.session.add(hb)
                    w = RegistroJornada()
                    w.id = str(uuid4())
                    w.collaborator_id = item.collaborator_id
                    w.tipo_registro = 'horas'
                    w.valor = float(item.hours or 0)
                    w.data = item.date
                    w.observacao = item.reason or ''
                    db.session.add(w)
                    created_hours = True
                elif item.kind == 'folga_hour_both':
                    lc = LeaveCredit()
                    lc.collaborator_id = item.collaborator_id
                    lc.date = item.date
                    lc.amount_days = max(1, int(item.amount_days or 1))
                    lc.origin = item.source or 'temporario'
                    lc.notes = item.reason or ''
                    db.session.add(lc)
                    hb = HourBankEntry()
                    hb.collaborator_id = item.collaborator_id
                    hb.date = item.date
                    hb.hours = float(item.hours or 1.0)
                    hb.reason = item.reason or 'Hora extra combinada'
                    db.session.add(hb)
                    w1 = RegistroJornada()
                    w1.id = str(uuid4())
                    w1.collaborator_id = item.collaborator_id
                    w1.tipo_registro = 'dias'
                    w1.valor = float(item.amount_days or 1)
                    w1.data = item.date
                    w1.observacao = item.reason or ''
                    db.session.add(w1)
                    w2 = RegistroJornada()
                    w2.id = str(uuid4())
                    w2.collaborator_id = item.collaborator_id
                    w2.tipo_registro = 'horas'
                    w2.valor = float(item.hours or 1.0)
                    w2.data = item.date
                    w2.observacao = item.reason or 'Hora extra combinada'
                    db.session.add(w2)
                    created_days = True
                    created_hours = True
                # se houver dias e horas informados juntos, garantir duas linhas na jornada e créditos correspondentes
                if (float(item.hours or 0) > 0) and not created_hours:
                    exists_h = RegistroJornada.query.filter_by(collaborator_id=item.collaborator_id, tipo_registro='horas', data=item.date).first()
                    if not exists_h:
                        w = RegistroJornada()
                        w.id = str(uuid4())
                        w.collaborator_id = item.collaborator_id
                        w.tipo_registro = 'horas'
                        w.valor = float(item.hours or 0)
                        w.data = item.date
                        w.observacao = item.reason or ''
                        db.session.add(w)
                    exists_hb = HourBankEntry.query.filter_by(collaborator_id=item.collaborator_id, date=item.date).first()
                    if not exists_hb:
                        hb = HourBankEntry()
                        hb.collaborator_id = item.collaborator_id
                        hb.date = item.date
                        hb.hours = float(item.hours or 0)
                        hb.reason = item.reason or ''
                        db.session.add(hb)
                if (int(item.amount_days or 0) > 0) and not created_days:
                    exists_d = RegistroJornada.query.filter_by(collaborator_id=item.collaborator_id, tipo_registro='dias', data=item.date).first()
                    if not exists_d:
                        w = RegistroJornada()
                        w.id = str(uuid4())
                        w.collaborator_id = item.collaborator_id
                        w.tipo_registro = 'dias'
                        w.valor = float(item.amount_days or 1)
                        w.data = item.date
                        w.observacao = item.reason or ''
                        db.session.add(w)
                    exists_lc = LeaveCredit.query.filter_by(collaborator_id=item.collaborator_id, date=item.date).first()
                    if not exists_lc:
                        lc = LeaveCredit()
                        lc.collaborator_id = item.collaborator_id
                        lc.date = item.date
                        lc.amount_days = max(1, int(item.amount_days or 1))
                        lc.origin = item.source or 'temporario'
                        lc.notes = item.reason or ''
                        db.session.add(lc)
                item.status = 'aprovado'
                item.updated_at = datetime.now(ZoneInfo('America/Sao_Paulo'))
                db.session.commit()
                flash('Item aprovado e aplicado ao banco definitivo.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao aprovar: {e}', 'danger')
        elif action == 'reject':
            try:
                item.status = 'rejeitado'
                item.updated_at = datetime.now(ZoneInfo('America/Sao_Paulo'))
                db.session.commit()
                flash('Item rejeitado.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao rejeitar: {e}', 'danger')
        else:
            db.session.commit()
            flash('Item atualizado.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar: {e}', 'danger')
    return redirect(url_for('temporarios.index'))

@bp.route('/temporarios/approve', methods=['POST'], strict_slashes=False)
@login_required
def approve():
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('temporarios.index'))
    tid = request.form.get('id', type=int)
    item = TemporaryEntry.query.get(tid) if tid else None
    if not item or item.status != 'pendente':
        flash('Item inválido ou já processado.', 'warning')
        return redirect(url_for('temporarios.index'))
    try:
        if item.kind == 'folga_credit':
            lc = LeaveCredit()
            lc.collaborator_id = item.collaborator_id
            lc.date = item.date
            lc.amount_days = max(1, int(item.amount_days or 1))
            lc.origin = item.source or 'temporario'
            lc.notes = item.reason or ''
            db.session.add(lc)
            w = RegistroJornada()
            w.id = str(uuid4())
            w.collaborator_id = item.collaborator_id
            w.tipo_registro = 'dias'
            w.valor = float(item.amount_days or 1)
            w.data = item.date
            w.observacao = item.reason or ''
            db.session.add(w)
        elif item.kind == 'hour_bank':
            hb = HourBankEntry()
            hb.collaborator_id = item.collaborator_id
            hb.date = item.date
            hb.hours = float(item.hours or 0)
            hb.reason = item.reason or ''
            db.session.add(hb)
            w = RegistroJornada()
            w.id = str(uuid4())
            w.collaborator_id = item.collaborator_id
            w.tipo_registro = 'horas'
            w.valor = float(item.hours or 0)
            w.data = item.date
            w.observacao = item.reason or ''
            db.session.add(w)
        elif item.kind == 'folga_hour_both':
            lc = LeaveCredit()
            lc.collaborator_id = item.collaborator_id
            lc.date = item.date
            lc.amount_days = max(1, int(item.amount_days or 1))
            lc.origin = item.source or 'temporario'
            lc.notes = item.reason or ''
            db.session.add(lc)
            hb = HourBankEntry()
            hb.collaborator_id = item.collaborator_id
            hb.date = item.date
            hb.hours = float(item.hours or 1.0)
            hb.reason = item.reason or 'Hora extra combinada'
            db.session.add(hb)
            w1 = RegistroJornada()
            w1.id = str(uuid4())
            w1.collaborator_id = item.collaborator_id
            w1.tipo_registro = 'dias'
            w1.valor = float(item.amount_days or 1)
            w1.data = item.date
            w1.observacao = item.reason or ''
            db.session.add(w1)
            w2 = RegistroJornada()
            w2.id = str(uuid4())
            w2.collaborator_id = item.collaborator_id
            w2.tipo_registro = 'horas'
            w2.valor = float(item.hours or 1.0)
            w2.data = item.date
            w2.observacao = item.reason or 'Hora extra combinada'
            db.session.add(w2)
        item.status = 'aprovado'
        item.updated_at = datetime.now(ZoneInfo('America/Sao_Paulo'))
        db.session.commit()
        flash('Item aprovado e aplicado ao banco definitivo.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao aprovar: {e}', 'danger')
    return redirect(url_for('temporarios.index'))

@bp.route('/temporarios/reject', methods=['POST'], strict_slashes=False)
@login_required
def reject():
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('temporarios.index'))
    tid = request.form.get('id', type=int)
    item = TemporaryEntry.query.get(tid) if tid else None
    if not item or item.status != 'pendente':
        flash('Item inválido ou já processado.', 'warning')
        return redirect(url_for('temporarios.index'))
    try:
        item.status = 'rejeitado'
        item.updated_at = datetime.now(ZoneInfo('America/Sao_Paulo'))
        db.session.commit()
        flash('Item rejeitado.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao rejeitar: {e}', 'danger')
    return redirect(url_for('temporarios.index'))
