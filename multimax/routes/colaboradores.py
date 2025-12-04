from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .. import db
from ..models import Collaborator, Shift, AppSetting
from ..models import HourBankEntry
from ..models import LeaveCredit
from datetime import datetime, date, time
from zoneinfo import ZoneInfo

bp = Blueprint('colaboradores', __name__)

@bp.route('/colaboradores', strict_slashes=False)
@login_required
def index():
    cols = Collaborator.query.order_by(Collaborator.name.asc()).all()
    bank_balances = {}
    try:
        from sqlalchemy import func
        sums = db.session.query(HourBankEntry.collaborator_id, func.coalesce(func.sum(HourBankEntry.hours), 0.0)).group_by(HourBankEntry.collaborator_id).all()
        for cid, total in sums:
            bank_balances[int(cid)] = float(total or 0.0)
    except Exception:
        bank_balances = {}
    recent_entries = []
    try:
        recent_entries = HourBankEntry.query.order_by(HourBankEntry.date.desc()).limit(50).all()
    except Exception:
        recent_entries = []
    return render_template('colaboradores.html', colaboradores=cols, bank_balances=bank_balances, recent_entries=recent_entries, active_page='colaboradores')

@bp.route('/colaboradores/criar', methods=['POST'], strict_slashes=False)
@login_required
def criar_colaborador():
    if current_user.nivel not in ('operador', 'admin'):
        flash('Você não tem permissão para criar colaboradores.', 'danger')
        return redirect(url_for('colaboradores.index'))
    nome = request.form.get('name', '').strip()
    cargo = request.form.get('role', '').strip()
    try:
        c = Collaborator()
        c.name = nome
        c.role = cargo
        c.active = True
        c.regular_team = (request.form.get('regular_team', '').strip() or None)
        c.sunday_team = (request.form.get('sunday_team', '').strip() or None)
        c.special_team = (request.form.get('special_team', '').strip() or None)
        db.session.add(c)
        db.session.commit()
        flash(f'Colaborador "{c.name}" criado.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao criar colaborador: {e}', 'danger')
    return redirect(url_for('colaboradores.index'))

@bp.route('/colaboradores/<int:id>/editar', methods=['POST'], strict_slashes=False)
@login_required
def editar_colaborador(id: int):
    if current_user.nivel not in ('operador', 'admin'):
        flash('Você não tem permissão para editar colaboradores.', 'danger')
        return redirect(url_for('colaboradores.index'))
    c = Collaborator.query.get_or_404(id)
    try:
        c.name = ((request.form.get('name') or c.name or '').strip()) or c.name
        role_in = request.form.get('role')
        c.role = ((role_in or c.role or '').strip()) or None
        active_str = request.form.get('active', 'on') or 'on'
        c.active = True if active_str.lower() in ('on', 'true', '1') else False
        rt_in = request.form.get('regular_team') or (c.regular_team or '')
        st_in = request.form.get('sunday_team') or (c.sunday_team or '')
        xt_in = request.form.get('special_team') or (c.special_team or '')
        c.regular_team = (rt_in.strip() or None) if (rt_in.strip() in ('1','2')) else None
        c.sunday_team = (st_in.strip() or None) if (st_in.strip() in ('1','2')) else None
        c.special_team = (xt_in.strip() or None) if (xt_in.strip() in ('1','2')) else None
        db.session.commit()
        flash('Colaborador atualizado.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar colaborador: {e}', 'danger')
    return redirect(url_for('colaboradores.index'))

@bp.route('/colaboradores/<int:id>/excluir', methods=['POST'], strict_slashes=False)
@login_required
def excluir_colaborador(id: int):
    if current_user.nivel != 'admin':
        flash('Apenas Gerente pode excluir colaboradores.', 'danger')
        return redirect(url_for('colaboradores.index'))
    c = Collaborator.query.get_or_404(id)
    try:
        Shift.query.filter_by(collaborator_id=c.id).delete()
        db.session.delete(c)
        db.session.commit()
        flash('Colaborador excluído.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir colaborador: {e}', 'danger')
    return redirect(url_for('colaboradores.index'))

@bp.route('/colaboradores/horas/adicionar', methods=['POST'], strict_slashes=False)
@login_required
def horas_adicionar():
    if current_user.nivel not in ('operador', 'admin'):
        flash('Você não tem permissão para registrar horas.', 'danger')
        return redirect(url_for('colaboradores.index'))
    cid_str = (request.form.get('collaborator_id', '').strip() or '')
    date_str = (request.form.get('date', '').strip() or '')
    hours_str = (request.form.get('hours', '0').strip() or '0')
    reason = (request.form.get('reason', '').strip() or '')
    try:
        cid = int(cid_str)
        d = datetime.strptime(date_str, '%Y-%m-%d').date()
        h = float(hours_str)
    except Exception:
        flash('Dados inválidos para banco de horas.', 'warning')
        return redirect(url_for('colaboradores.index'))
    try:
        e = HourBankEntry()
        e.collaborator_id = cid
        e.date = d
        e.hours = h
        e.reason = reason
        db.session.add(e)
        db.session.commit()
        flash('Horas registradas.', 'success')
    except Exception as ex:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f'Erro ao registrar horas: {ex}', 'danger')
    return redirect(url_for('colaboradores.index'))

@bp.route('/colaboradores/horas/excluir/<int:id>', methods=['POST'], strict_slashes=False)
@login_required
def horas_excluir(id: int):
    if current_user.nivel != 'admin':
        flash('Apenas Gerente pode excluir lançamentos.', 'danger')
        return redirect(url_for('colaboradores.index'))
    e = HourBankEntry.query.get_or_404(id)
    try:
        db.session.delete(e)
        db.session.commit()
        flash('Lançamento excluído.', 'danger')
    except Exception as ex:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f'Erro ao excluir lançamento: {ex}', 'danger')
    return redirect(url_for('colaboradores.index'))

@bp.route('/escala', strict_slashes=False)
@login_required
def escala():
    cols = Collaborator.query.filter_by(active=True).order_by(Collaborator.name.asc()).all()
    from datetime import timedelta
    today = date.today()
    current_monday = today - timedelta(days=today.weekday())
    try:
        ref_monday_setting = AppSetting.query.filter_by(key='rodizio_ref_monday').first()
        ref_open_setting = AppSetting.query.filter_by(key='rodizio_open_team_ref').first()
        ref_monday = None
        if ref_monday_setting and (ref_monday_setting.value or '').strip():
            try:
                ref_monday = datetime.strptime(ref_monday_setting.value.strip(), '%Y-%m-%d').date()
            except Exception:
                ref_monday = None
        if not ref_monday:
            if not ref_monday_setting:
                ref_monday_setting = AppSetting()
                ref_monday_setting.key = 'rodizio_ref_monday'
                db.session.add(ref_monday_setting)
            ref_monday_setting.value = current_monday.strftime('%Y-%m-%d')
            db.session.commit()
            ref_monday = current_monday
        open_ref = (ref_open_setting.value.strip() if ref_open_setting and ref_open_setting.value else '1')
        if open_ref not in ('1','2'):
            open_ref = '1'
        # auto-avance semanal: se referência ficou para trás, atualiza e alterna
        if ref_monday < current_monday:
            weeks_diff = (current_monday - ref_monday).days // 7
            if weeks_diff % 2 == 1:
                open_ref = '2' if open_ref == '1' else '1'
            ref_monday = current_monday
            if not ref_monday_setting:
                ref_monday_setting = AppSetting()
                ref_monday_setting.key = 'rodizio_ref_monday'
                db.session.add(ref_monday_setting)
            ref_monday_setting.value = current_monday.strftime('%Y-%m-%d')
            if not ref_open_setting:
                ref_open_setting = AppSetting()
                ref_open_setting.key = 'rodizio_open_team_ref'
                db.session.add(ref_open_setting)
            ref_open_setting.value = open_ref
            db.session.commit()
        weeks = []
        for i in range(5):
            ws = current_monday + timedelta(days=7*i)
            we = ws + timedelta(days=5)
            open_team = open_ref if (i % 2 == 0) else ('2' if open_ref == '1' else '1')
            close_team = '2' if open_team == '1' else '1'
            weeks.append({
                'start': ws,
                'end': we,
                'open': f"Equipe {open_team}",
                'close': f"Equipe {close_team}",
            })
    except Exception:
        weeks = []
    try:
        sun_team_setting = AppSetting.query.filter_by(key='domingo_team_ref').first()
        sun_ref_setting = AppSetting.query.filter_by(key='domingo_ref_sunday').first()
        domingo_team = (sun_team_setting.value.strip() if sun_team_setting and sun_team_setting.value else None)
        if domingo_team not in ('1','2'):
            sun_m = AppSetting.query.filter_by(key='domingo_manha_team').first()
            domingo_team = (sun_m.value.strip() if sun_m and sun_m.value else '1')
            if domingo_team not in ('1','2'):
                domingo_team = '1'
        domingo_ref_date = (sun_ref_setting.value.strip() if sun_ref_setting and sun_ref_setting.value else '')
    except Exception:
        domingo_team = '1'
        domingo_ref_date = ''
    events = []
    try:
        from datetime import timedelta
        for i in range(5):
            ws = current_monday + timedelta(days=7*i)
            we = ws + timedelta(days=5)
            open_team = open_ref if (i % 2 == 0) else ('2' if open_ref == '1' else '1')
            close_team = '2' if open_team == '1' else '1'
            d = ws
            while d <= we:
                events.append({
                    'title': f"EQUIPE ABERTURA '{open_team}'",
                    'start': d.strftime('%Y-%m-%d'),
                    'color': '#0d6efd',
                    'url': url_for('colaboradores.escala'),
                    'kind': 'rodizio-open',
                    'team': open_team,
                })
                events.append({
                    'title': f"EQUIPE FECHAMENTO '{close_team}'",
                    'start': d.strftime('%Y-%m-%d'),
                    'color': '#0b5ed7',
                    'url': url_for('colaboradores.escala'),
                    'kind': 'rodizio-close',
                    'team': close_team,
                })
                d = d + timedelta(days=1)
            sunday = ws + timedelta(days=6)
            events.append({
                'title': f"DOMINGO EQUIPE '{domingo_team}' (5h–13h)",
                'start': sunday.strftime('%Y-%m-%d'),
                'color': '#fd7e14',
                'url': url_for('colaboradores.escala'),
                'kind': 'rodizio-sunday',
                'team': domingo_team,
            })
    except Exception:
        pass
    return render_template('escala.html', colaboradores=cols, weeks=weeks, ref_open=open_ref, domingo_team=domingo_team, domingo_ref_date=domingo_ref_date, events=events, active_page='escala')

@bp.route('/escala/novo', methods=['POST'], strict_slashes=False)
@login_required
def nova_escala():
    if current_user.nivel not in ('operador', 'admin'):
        flash('Você não tem permissão para criar escalas.', 'danger')
        return redirect(url_for('colaboradores.escala'))
    col_id = request.form.get('collaborator_id', '').strip()
    data_str = request.form.get('date', '').strip()
    turno = request.form.get('turno', '').strip()
    obs = request.form.get('observacao', '').strip()
    try:
        cid = int(col_id)
        d = datetime.strptime(data_str, '%Y-%m-%d').date()
    except Exception:
        flash('Dados inválidos para nova escala.', 'warning')
        return redirect(url_for('colaboradores.escala'))
    try:
        s = Shift()
        s.collaborator_id = cid
        s.date = d
        s.turno = turno
        s.observacao = obs
        db.session.add(s)
        db.session.commit()
        flash('Escala adicionada.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao adicionar escala: {e}', 'danger')
    return redirect(url_for('colaboradores.escala'))

@bp.route('/escala/excluir/<int:id>', methods=['POST'], strict_slashes=False)
@login_required
def excluir_escala(id: int):
    if current_user.nivel != 'admin':
        flash('Apenas Gerente pode excluir escalas.', 'danger')
        return redirect(url_for('colaboradores.escala'))
    s = Shift.query.get_or_404(id)
    try:
        db.session.delete(s)
        db.session.commit()
        flash('Escala excluída.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir escala: {e}', 'danger')
    return redirect(url_for('colaboradores.escala'))

@bp.route('/escala/gerar', methods=['POST'], strict_slashes=False)
@login_required
def gerar_semana():
    if current_user.nivel not in ('operador', 'admin'):
        flash('Você não tem permissão para gerar escalas.', 'danger')
        return redirect(url_for('colaboradores.escala'))
    di_str = request.form.get('data_inicio', '').strip()
    df_str = request.form.get('data_fim', '').strip()
    limpar = request.form.get('limpar', '') in ('on','true','1')
    tipo = (request.form.get('tipo', 'regular') or 'regular').strip().lower()
    abertura_sel = (request.form.get('abertura_equipe', '1') or '1').strip()
    fechamento_sel = (request.form.get('fechamento_equipe', '2') or '2').strip()
    def parse_date_safe(s: str):
        try:
            return datetime.strptime(s, '%Y-%m-%d').date()
        except Exception:
            return None
    di = parse_date_safe(di_str)
    df = parse_date_safe(df_str)
    if not di or not df:
        flash('Informe período válido para geração.', 'warning')
        return redirect(url_for('colaboradores.escala'))
    if di > df:
        di, df = df, di
    try:
        if limpar:
            Shift.query.filter(Shift.date >= di, Shift.date <= df).delete()
            db.session.commit()
        cols = Collaborator.query.filter_by(active=True).all()
        reg1 = [c for c in cols if (c.regular_team or '') == '1']
        reg2 = [c for c in cols if (c.regular_team or '') == '2']
        sun1 = [c for c in cols if (c.sunday_team or '') == '1']
        sun2 = [c for c in cols if (c.sunday_team or '') == '2']
        sp1 = [c for c in cols if (c.special_team or '') == '1']
        sp2 = [c for c in cols if (c.special_team or '') == '2']
        cur = di
        from datetime import timedelta
        while cur <= df:
            wk = cur.isocalendar()[1]
            if tipo in ('domingo', 'todos') and cur.weekday() == 6:
                sun_m = AppSetting.query.filter_by(key='domingo_manha_team').first()
                domingo_team_val = (sun_m.value.strip() if sun_m and sun_m.value else '1')
                domingo_team_val = domingo_team_val if domingo_team_val in ('1','2') else '1'
                domingo_team = sun1 if domingo_team_val == '1' else sun2
                for c in domingo_team:
                    s = Shift()
                    s.collaborator_id = c.id
                    s.date = cur
                    s.turno = 'Domingo'
                    s.start_dt = datetime.combine(cur, time(5, 0)).replace(tzinfo=ZoneInfo('America/Sao_Paulo'))
                    s.end_dt = datetime.combine(cur, time(13, 0)).replace(tzinfo=ZoneInfo('America/Sao_Paulo'))
                    db.session.add(s)
                    exists = LeaveCredit.query.filter_by(collaborator_id=c.id, date=cur, origin='domingo').first()
                    if not exists:
                        lc = LeaveCredit()
                        lc.collaborator_id = c.id
                        lc.date = cur
                        lc.amount_days = 1
                        lc.origin = 'domingo'
                        lc.notes = 'Domingo trabalhado'
                        db.session.add(lc)
            if cur.weekday() in (0,1,2,3,4,5):
                if tipo in ('regular', 'todos'):
                    open_team = reg1 if abertura_sel == '1' else reg2
                    close_team = reg1 if fechamento_sel == '1' else reg2
                    for c in open_team:
                        s1 = Shift()
                        s1.collaborator_id = c.id
                        s1.date = cur
                        s1.turno = 'Abertura (Manhã)'
                        s1.start_dt = datetime.combine(cur, time(5, 0)).replace(tzinfo=ZoneInfo('America/Sao_Paulo'))
                        s1.end_dt = datetime.combine(cur, time(11, 0)).replace(tzinfo=ZoneInfo('America/Sao_Paulo'))
                        db.session.add(s1)
                        s2 = Shift()
                        s2.collaborator_id = c.id
                        s2.date = cur
                        s2.turno = 'Abertura (Tarde)'
                        s2.start_dt = datetime.combine(cur, time(13, 0)).replace(tzinfo=ZoneInfo('America/Sao_Paulo'))
                        s2.end_dt = datetime.combine(cur, time(15, 0)).replace(tzinfo=ZoneInfo('America/Sao_Paulo'))
                        db.session.add(s2)
                    for c in close_team:
                        s1 = Shift()
                        s1.collaborator_id = c.id
                        s1.date = cur
                        s1.turno = 'Fechamento (Manhã)'
                        s1.start_dt = datetime.combine(cur, time(9, 30)).replace(tzinfo=ZoneInfo('America/Sao_Paulo'))
                        s1.end_dt = datetime.combine(cur, time(13, 0)).replace(tzinfo=ZoneInfo('America/Sao_Paulo'))
                        db.session.add(s1)
                        s2 = Shift()
                        s2.collaborator_id = c.id
                        s2.date = cur
                        s2.turno = 'Fechamento (Tarde)'
                        s2.start_dt = datetime.combine(cur, time(15, 0)).replace(tzinfo=ZoneInfo('America/Sao_Paulo'))
                        s2.end_dt = datetime.combine(cur, time(19, 30)).replace(tzinfo=ZoneInfo('America/Sao_Paulo'))
                        db.session.add(s2)
                if tipo in ('especial', 'todos'):
                    for c in sp1:
                        s1 = Shift()
                        s1.collaborator_id = c.id
                        s1.date = cur
                        s1.turno = 'Abertura (Especial-Manhã)'
                        s1.start_dt = datetime.combine(cur, time(5, 0)).replace(tzinfo=ZoneInfo('America/Sao_Paulo'))
                        s1.end_dt = datetime.combine(cur, time(11, 0)).replace(tzinfo=ZoneInfo('America/Sao_Paulo'))
                        db.session.add(s1)
                        s2 = Shift()
                        s2.collaborator_id = c.id
                        s2.date = cur
                        s2.turno = 'Abertura (Especial-Tarde)'
                        s2.start_dt = datetime.combine(cur, time(13, 0)).replace(tzinfo=ZoneInfo('America/Sao_Paulo'))
                        s2.end_dt = datetime.combine(cur, time(15, 0)).replace(tzinfo=ZoneInfo('America/Sao_Paulo'))
                        db.session.add(s2)
                    for c in sp2:
                        s1 = Shift()
                        s1.collaborator_id = c.id
                        s1.date = cur
                        s1.turno = 'Fechamento (Especial-Manhã)'
                        s1.start_dt = datetime.combine(cur, time(9, 30)).replace(tzinfo=ZoneInfo('America/Sao_Paulo'))
                        s1.end_dt = datetime.combine(cur, time(13, 0)).replace(tzinfo=ZoneInfo('America/Sao_Paulo'))
                        db.session.add(s1)
                        s2 = Shift()
                        s2.collaborator_id = c.id
                        s2.date = cur
                        s2.turno = 'Fechamento (Especial-Tarde)'
                        s2.start_dt = datetime.combine(cur, time(15, 0)).replace(tzinfo=ZoneInfo('America/Sao_Paulo'))
                        s2.end_dt = datetime.combine(cur, time(19, 30)).replace(tzinfo=ZoneInfo('America/Sao_Paulo'))
                        db.session.add(s2)
            cur += timedelta(days=1)
        db.session.commit()
        flash('Escalas geradas para o período.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao gerar escalas: {e}', 'danger')
    return redirect(url_for('colaboradores.escala'))

@bp.route('/escala/rodizio/atualizar', methods=['POST'], strict_slashes=False)
@login_required
def rodizio_atualizar():
    if current_user.nivel not in ('operador', 'admin'):
        flash('Você não tem permissão para configurar rodízio.', 'danger')
        return redirect(url_for('colaboradores.escala'))
    open_sel = (request.form.get('abertura_equipe', '1') or '1').strip()
    close_sel = (request.form.get('fechamento_equipe', '2') or '2').strip()
    if open_sel not in ('1','2') or close_sel not in ('1','2') or open_sel == close_sel:
        flash('Seleção inválida: equipes devem ser 1 e 2, distintas.', 'warning')
        return redirect(url_for('colaboradores.escala'))
    from datetime import timedelta
    today = date.today()
    current_monday = today - timedelta(days=today.weekday())
    try:
        rms = AppSetting.query.filter_by(key='rodizio_ref_monday').first()
        ros = AppSetting.query.filter_by(key='rodizio_open_team_ref').first()
        if not rms:
            rms = AppSetting()
            rms.key = 'rodizio_ref_monday'
            db.session.add(rms)
        if not ros:
            ros = AppSetting()
            ros.key = 'rodizio_open_team_ref'
            db.session.add(ros)
        rms.value = current_monday.strftime('%Y-%m-%d')
        ros.value = open_sel
        db.session.commit()
        flash('Rodízio atualizado para a semana atual.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar rodízio: {e}', 'danger')
    return redirect(url_for('colaboradores.escala'))

@bp.route('/escala/rodizio/gerar', methods=['POST'], strict_slashes=False)
@login_required
def rodizio_gerar():
    if current_user.nivel not in ('operador', 'admin'):
        flash('Você não tem permissão para gerar rodízio.', 'danger')
        return redirect(url_for('colaboradores.escala'))
    limpar = request.form.get('limpar', '') in ('on','true','1')
    from datetime import timedelta
    today = date.today()
    current_monday = today - timedelta(days=today.weekday())
    rms = AppSetting.query.filter_by(key='rodizio_ref_monday').first()
    ros = AppSetting.query.filter_by(key='rodizio_open_team_ref').first()
    open_ref = (ros.value.strip() if ros and ros.value else '1')
    if open_ref not in ('1','2'):
        open_ref = '1'
    try:
        cols = Collaborator.query.filter_by(active=True).all()
        reg1 = [c for c in cols if (c.regular_team or '') == '1']
        reg2 = [c for c in cols if (c.regular_team or '') == '2']
        start_range = current_monday
        end_range = current_monday + timedelta(days=7*5 - 1)
        if limpar:
            Shift.query.filter(Shift.date >= start_range, Shift.date <= end_range).delete()
            db.session.commit()
        for i in range(5):
            ws = current_monday + timedelta(days=7*i)
            we = ws + timedelta(days=5)
            open_team = reg1 if (open_ref == '1' and i % 2 == 0) or (open_ref == '2' and i % 2 == 1) else reg2
            close_team = reg2 if open_team is reg1 else reg1
            d = ws
            while d <= we:
                for c in open_team:
                    s1 = Shift()
                    s1.collaborator_id = c.id
                    s1.date = d
                    s1.turno = 'Abertura (Manhã)'
                    s1.start_dt = datetime.combine(d, time(5, 0)).replace(tzinfo=ZoneInfo('America/Sao_Paulo'))
                    s1.end_dt = datetime.combine(d, time(11, 0)).replace(tzinfo=ZoneInfo('America/Sao_Paulo'))
                    db.session.add(s1)
                    s2 = Shift()
                    s2.collaborator_id = c.id
                    s2.date = d
                    s2.turno = 'Abertura (Tarde)'
                    s2.start_dt = datetime.combine(d, time(13, 0)).replace(tzinfo=ZoneInfo('America/Sao_Paulo'))
                    s2.end_dt = datetime.combine(d, time(15, 0)).replace(tzinfo=ZoneInfo('America/Sao_Paulo'))
                    db.session.add(s2)
                for c in close_team:
                    c1 = Shift()
                    c1.collaborator_id = c.id
                    c1.date = d
                    c1.turno = 'Fechamento (Manhã)'
                    c1.start_dt = datetime.combine(d, time(9, 30)).replace(tzinfo=ZoneInfo('America/Sao_Paulo'))
                    c1.end_dt = datetime.combine(d, time(13, 0)).replace(tzinfo=ZoneInfo('America/Sao_Paulo'))
                    db.session.add(c1)
                    c2 = Shift()
                    c2.collaborator_id = c.id
                    c2.date = d
                    c2.turno = 'Fechamento (Tarde)'
                    c2.start_dt = datetime.combine(d, time(15, 0)).replace(tzinfo=ZoneInfo('America/Sao_Paulo'))
                    c2.end_dt = datetime.combine(d, time(19, 30)).replace(tzinfo=ZoneInfo('America/Sao_Paulo'))
                    db.session.add(c2)
                d += timedelta(days=1)
        db.session.commit()
        flash('Rodízio gerado para as próximas 5 semanas.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao gerar rodízio: {e}', 'danger')
    return redirect(url_for('colaboradores.escala'))

@bp.route('/escala/domingo/configurar', methods=['POST'], strict_slashes=False)
@login_required
def domingo_configurar():
    if current_user.nivel not in ('operador', 'admin'):
        flash('Você não tem permissão para configurar domingos.', 'danger')
        return redirect(url_for('colaboradores.escala'))
    team = (request.form.get('domingo_team', '1') or '1').strip()
    date_str = (request.form.get('domingo_data', '').strip() or '')
    if team not in ('1','2'):
        flash('Seleção inválida para domingos.', 'warning')
        return redirect(url_for('colaboradores.escala'))
    try:
        sm = AppSetting.query.filter_by(key='domingo_manha_team').first()
        if not sm:
            sm = AppSetting()
            sm.key = 'domingo_manha_team'
            db.session.add(sm)
        sm.value = team
        stm = AppSetting.query.filter_by(key='domingo_team_ref').first()
        rs = AppSetting.query.filter_by(key='domingo_ref_sunday').first()
        if not stm:
            stm = AppSetting()
            stm.key = 'domingo_team_ref'
            db.session.add(stm)
        if date_str:
            try:
                d = datetime.strptime(date_str, '%Y-%m-%d').date()
                if not rs:
                    rs = AppSetting()
                    rs.key = 'domingo_ref_sunday'
                    db.session.add(rs)
                rs.value = d.strftime('%Y-%m-%d')
            except Exception:
                pass
        stm.value = team
        db.session.commit()
        flash('Configuração de domingos atualizada.', 'success')
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f'Erro ao salvar configuração de domingos: {e}', 'danger')
    return redirect(url_for('colaboradores.escala'))

@bp.route('/escala/folga/credito', methods=['POST'], strict_slashes=False)
@login_required
def folga_credito_registrar():
    if current_user.nivel not in ('operador', 'admin'):
        flash('Você não tem permissão para registrar créditos.', 'danger')
        return redirect(url_for('colaboradores.escala'))
    cid_str = (request.form.get('collaborator_id', '').strip() or '')
    date_str = (request.form.get('date', '').strip() or '')
    amount_str = (request.form.get('amount', '1').strip() or '1')
    notes = (request.form.get('notes', '').strip() or '')
    try:
        cid = int(cid_str)
        d = datetime.strptime(date_str, '%Y-%m-%d').date()
        amount = max(1, int(amount_str))
    except Exception:
        flash('Dados inválidos para crédito de folga.', 'warning')
        return redirect(url_for('colaboradores.escala'))
    try:
        lc = LeaveCredit()
        lc.collaborator_id = cid
        lc.date = d
        lc.amount_days = amount
        lc.origin = 'manual'
        lc.notes = notes
        db.session.add(lc)
        db.session.commit()
        flash('Crédito de folga registrado.', 'success')
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f'Erro ao registrar crédito: {e}', 'danger')
    return redirect(url_for('colaboradores.escala'))
