from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .. import db
from ..models import Collaborator, Shift, AppSetting, User, Holiday
from ..models import LeaveAssignment
from ..models import HourBankEntry
from ..models import LeaveCredit, LeaveAssignment, LeaveConversion
from ..services.notificacao_service import registrar_evento
from datetime import datetime, date, time
from zoneinfo import ZoneInfo

bp = Blueprint('colaboradores', __name__)


@bp.route('/escala', strict_slashes=False)
@login_required
def escala():
    try:
        from sqlalchemy import inspect, text
        insp = inspect(db.engine)
        cols_meta = [c['name'] for c in insp.get_columns('collaborator')]
        changed = False
        if 'name' not in cols_meta:
            db.session.execute(text('ALTER TABLE collaborator ADD COLUMN name TEXT'))
            changed = True
            if 'nome' in cols_meta:
                try:
                    db.session.execute(text('UPDATE collaborator SET name = nome WHERE name IS NULL'))
                except Exception:
                    pass
            else:
                try:
                    db.session.execute(text("UPDATE collaborator SET name = '' WHERE name IS NULL"))
                except Exception:
                    pass
        if changed:
            db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
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
        base_team = domingo_team if domingo_team in ('1','2') else '1'
        ref_sun = None
        if domingo_ref_date:
            try:
                ref_sun = datetime.strptime(domingo_ref_date, '%Y-%m-%d').date()
            except Exception:
                ref_sun = None
        for i in range(5):
            ws = current_monday + timedelta(days=7*i)
            sunday = ws + timedelta(days=6)
            team_i = base_team
            if ref_sun:
                weeks_diff = ((sunday - ref_sun).days // 7)
                if weeks_diff % 2 == 1:
                    team_i = '2' if base_team == '1' else '1'
            else:
                if i % 2 == 1:
                    team_i = '2' if base_team == '1' else '1'
            events.append({
                'title': f"DOMINGO EQUIPE '{team_i}' (5h–13h)",
                'start': sunday.strftime('%Y-%m-%d'),
                'color': '#fd7e14',
                'url': url_for('colaboradores.escala'),
                'kind': 'rodizio-sunday',
                'team': team_i,
            })
    except Exception:
        pass
    try:
        y = today.year
        fixed = [
            (date(y, 2, 2), 'Padroeiro de Umbaúba'),
            (date(y, 2, 6), 'Aniversário de Umbaúba'),
            (date(y + 1, 2, 2), 'Padroeiro de Umbaúba'),
            (date(y + 1, 2, 6), 'Aniversário de Umbaúba'),
        ]
        for dt, nm in fixed:
            h = Holiday.query.filter_by(date=dt).first()
            if h:
                h.name = nm
                h.kind = 'municipal-Umbaúba'
            else:
                hh = Holiday(); hh.date = dt; hh.name = nm; hh.kind = 'municipal-Umbaúba'; db.session.add(hh)
        db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
    try:
        ano = 2026
        fixes = [
            (date(ano,1,1), 'Confraternização Universal'),
            (date(ano,4,21), 'Tiradentes'),
            (date(ano,5,1), 'Dia do Trabalho'),
            (date(ano,9,7), 'Independência do Brasil'),
            (date(ano,10,12), 'Nossa Senhora Aparecida'),
            (date(ano,11,2), 'Finados'),
            (date(ano,11,15), 'Proclamação da República'),
            (date(ano,11,20), 'Consciência Negra'),
            (date(ano,12,25), 'Natal'),
        ]
        def easter(y):
            a = y % 19
            b = y // 100
            c = y % 100
            d = (19*a + b - (b//4) - ((b - ((b+8)//25) + 1)//3) + 15) % 30
            e = (32 + 2*(b%4) + 2*(c//4) - d - (c%4)) % 7
            f = d + e - 7*((a + 11*d + 22*e)//451) + 114
            month = f // 31
            day = (f % 31) + 1
            return date(y, month, day)
        gf = easter(ano)
        try:
            from datetime import timedelta as _timedelta
            gf = gf - _timedelta(days=2)
            fixes.append((gf, 'Sexta-Feira Santa'))
            cc = easter(ano) + _timedelta(days=60)
            fixes.append((cc, 'Corpus Christi'))
        except Exception:
            pass
        for dt, nm in fixes:
            h = Holiday.query.filter_by(date=dt).first()
            if h:
                h.name = nm
                h.kind = 'nacional'
            else:
                hh = Holiday(); hh.date = dt; hh.name = nm; hh.kind = 'nacional'; db.session.add(hh)
        db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
    try:
        hs = Holiday.query.order_by(Holiday.date.asc()).all()
        color_map = {
            'nacional': '#20c997',
            'movel': '#198754',
            'estadual-SE': '#0dcaf0',
            'municipal-Umbaúba': '#0d6efd',
            'facultativo': '#adb5bd',
            'municipal': '#0d6efd',
            'estadual': '#0dcaf0',
        }
        for h in hs:
            kind = (h.kind or 'feriado').strip()
            events.append({
                'title': h.name,
                'start': h.date.strftime('%Y-%m-%d'),
                'color': color_map.get(kind, '#20c997'),
                'url': url_for('colaboradores.escala'),
                'kind': kind,
            })
    except Exception:
        pass
    try:
        las = LeaveAssignment.query.order_by(LeaveAssignment.date.asc()).all()
        name_by_id = {c.id: c.name for c in cols}
        from datetime import timedelta
        for la in las:
            base = la.date
            days = max(1, int(la.days_used or 1))
            nm = name_by_id.get(la.collaborator_id) or f"ID {la.collaborator_id}"
            for i in range(days):
                d = base + timedelta(days=i)
                events.append({
                    'title': f"FOLGA: {nm}",
                    'start': d.strftime('%Y-%m-%d'),
                    'color': '#6f42c1',
                    'url': url_for('colaboradores.escala'),
                    'kind': 'folga',
                })
    except Exception:
        pass
    return render_template('escala.html', colaboradores=cols, weeks=weeks, ref_open=open_ref, domingo_team=domingo_team, domingo_ref_date=domingo_ref_date, events=events, feriados=hs if 'hs' in locals() else [], active_page='escala')
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

@bp.route('/escala/feriado/criar', methods=['POST'], strict_slashes=False)
@login_required
def feriado_criar():
    if current_user.nivel != 'admin':
        flash('Apenas Gerente pode configurar feriados.', 'danger')
        return redirect(url_for('colaboradores.escala'))
    date_str = (request.form.get('date', '').strip() or '')
    name = (request.form.get('name', '').strip() or '')
    kind = (request.form.get('kind', '').strip() or '')
    try:
        d = datetime.strptime(date_str, '%Y-%m-%d').date()
    except Exception:
        flash('Data inválida para feriado.', 'warning')
        return redirect(url_for('colaboradores.escala'))
    if not name:
        flash('Nome do feriado é obrigatório.', 'warning')
        return redirect(url_for('colaboradores.escala'))
    try:
        existing = Holiday.query.filter_by(date=d).first()
        if existing:
            existing.name = name
            existing.kind = kind or existing.kind
        else:
            h = Holiday()
            h.date = d
            h.name = name
            h.kind = kind or None
            db.session.add(h)
        db.session.commit()
        flash('Feriado salvo.', 'success')
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f'Erro ao salvar feriado: {e}', 'danger')
    return redirect(url_for('colaboradores.escala'))

@bp.route('/escala/feriado/excluir/<int:id>', methods=['POST'], strict_slashes=False)
@login_required
def feriado_excluir(id: int):
    if current_user.nivel != 'admin':
        flash('Apenas Gerente pode excluir feriados.', 'danger')
        return redirect(url_for('colaboradores.escala'))
    h = Holiday.query.get_or_404(id)
    try:
        db.session.delete(h)
        db.session.commit()
        flash('Feriado excluído.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir feriado: {e}', 'danger')
    return redirect(url_for('colaboradores.escala'))


@bp.route('/gestao/folga/credito', methods=['POST'], strict_slashes=False)
@login_required
def folga_credito_registrar_gestao():
    if current_user.nivel not in ('operador', 'admin'):
        flash('Você não tem permissão para registrar créditos.', 'danger')
        return redirect(url_for('usuarios.gestao'))
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
        return redirect(url_for('usuarios.gestao'))
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
    return redirect(url_for('usuarios.gestao'))

@bp.route('/gestao/folga/credito/domingo', methods=['POST'], strict_slashes=False)
@login_required
def folga_credito_domingo():
    if current_user.nivel not in ('operador', 'admin'):
        flash('Você não tem permissão para registrar créditos.', 'danger')
        return redirect(url_for('usuarios.gestao'))
    cid_str = (request.form.get('collaborator_id', '').strip() or '')
    date_str = (request.form.get('date', '').strip() or '')
    amount_str = (request.form.get('amount', '1').strip() or '1')
    notes = (request.form.get('notes', '').strip() or 'Domingo trabalhado')
    try:
        cid = int(cid_str)
        d = datetime.strptime(date_str, '%Y-%m-%d').date()
        amount = max(1, int(amount_str))
    except Exception:
        flash('Dados inválidos para crédito de domingo.', 'warning')
        return redirect(url_for('usuarios.gestao'))
    try:
        exists = LeaveCredit.query.filter_by(collaborator_id=cid, date=d, origin='domingo').first()
        if not exists:
            lc = LeaveCredit()
            lc.collaborator_id = cid
            lc.date = d
            lc.amount_days = amount
            lc.origin = 'domingo'
            lc.notes = notes
            db.session.add(lc)
            db.session.commit()
            flash('Crédito de domingo registrado.', 'success')
        else:
            flash('Crédito de domingo já existe para essa data.', 'info')
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f'Erro ao registrar crédito: {e}', 'danger')
    return redirect(url_for('usuarios.gestao'))

@bp.route('/gestao/folga/credito/reduzir', methods=['POST'], strict_slashes=False)
@login_required
def folga_credito_reduzir():
    if current_user.nivel not in ('operador', 'admin'):
        flash('Você não tem permissão para ajustar créditos.', 'danger')
        return redirect(url_for('usuarios.gestao'))
    cid_str = (request.form.get('collaborator_id', '').strip() or '')
    amount_str = (request.form.get('amount', '1').strip() or '1')
    notes = (request.form.get('notes', '').strip() or 'Ajuste negativo')
    try:
        cid = int(cid_str)
        amount = max(1, int(amount_str))
    except Exception:
        flash('Dados inválidos para ajuste.', 'warning')
        return redirect(url_for('usuarios.gestao'))
    try:
        from datetime import date as _date
        lc = LeaveCredit()
        lc.collaborator_id = cid
        lc.date = _date.today()
        lc.amount_days = -amount
        lc.origin = 'ajuste'
        lc.notes = notes
        db.session.add(lc)
        db.session.commit()
        flash('Ajuste aplicado: dias reduzidos.', 'warning')
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f'Erro ao ajustar créditos: {e}', 'danger')
    return redirect(url_for('usuarios.gestao'))

@bp.route('/gestao/folga/agendar', methods=['POST'], strict_slashes=False)
@login_required
def folga_agendar():
    if current_user.nivel not in ('operador', 'admin'):
        flash('Você não tem permissão para agendar folga.', 'danger')
        return redirect(url_for('usuarios.gestao'))
    cid_str = (request.form.get('collaborator_id', '').strip() or '')
    date_str = (request.form.get('date', '').strip() or '')
    days_str = (request.form.get('days', '1').strip() or '1')
    notes = (request.form.get('notes', '').strip() or '')
    try:
        cid = int(cid_str)
        d = datetime.strptime(date_str, '%Y-%m-%d').date()
        days = max(1, int(days_str))
    except Exception:
        flash('Dados inválidos para agendamento.', 'warning')
        return redirect(url_for('usuarios.gestao'))
    try:
        la = LeaveAssignment()
        la.collaborator_id = cid
        la.date = d
        la.days_used = days
        la.notes = notes
        db.session.add(la)
        db.session.commit()
        try:
            col = Collaborator.query.get(cid)
            nome = col.name if col and col.name else f'ID {cid}'
        except Exception:
            nome = f'ID {cid}'
        registrar_evento('folga cadastrada', produto=nome, quantidade=days, descricao=notes)
        flash('Folga agendada.', 'success')
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f'Erro ao agendar folga: {e}', 'danger')
    return redirect(url_for('usuarios.gestao'))

@bp.route('/gestao/folga/converter', methods=['POST'], strict_slashes=False)
@login_required
def folga_converter():
    if current_user.nivel not in ('operador', 'admin'):
        flash('Você não tem permissão para converter folga.', 'danger')
        return redirect(url_for('usuarios.gestao'))
    cid_str = (request.form.get('collaborator_id', '').strip() or '')
    date_str = (request.form.get('date', '').strip() or '')
    days_str = (request.form.get('days', '1').strip() or '1')
    amount_str = (request.form.get('amount_paid', '').strip() or '')
    rate_str = (request.form.get('rate_per_day', '65').strip() or '65')
    notes = (request.form.get('notes', '').strip() or '')
    try:
        cid = int(cid_str)
        d = datetime.strptime(date_str, '%Y-%m-%d').date()
        days = max(1, int(days_str))
        rate = float(rate_str)
        amount_paid = float(amount_str) if amount_str else (rate * days)
    except Exception:
        flash('Dados inválidos para conversão.', 'warning')
        return redirect(url_for('usuarios.gestao'))
    try:
        conv = LeaveConversion()
        conv.collaborator_id = cid
        conv.date = d
        conv.amount_days = days
        conv.amount_paid = amount_paid
        conv.rate_per_day = rate
        conv.notes = notes
        db.session.add(conv)
        db.session.commit()
        flash('Conversão registrada.', 'success')
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f'Erro ao registrar conversão: {e}', 'danger')
    return redirect(url_for('usuarios.gestao'))
