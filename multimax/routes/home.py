from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import current_user
from datetime import datetime
from .. import db
from ..models import Historico, CleaningTask, CleaningHistory, MeatReception, SystemLog, AppSetting
from ..models import LeaveCredit

bp = Blueprint('home', __name__, url_prefix='/home')

@bp.route('/', strict_slashes=False)
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    db_diag = None
    try:
        from flask import current_app
        from sqlalchemy import text
        uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
        host = None
        try:
            if '://' in uri:
                after = uri.split('://', 1)[1]
                hostpart = after.split('@', 1)[1] if '@' in after else after
                host = hostpart.split('/', 1)[0]
        except Exception:
            host = None
        ok = True
        err = ''
        try:
            db.session.execute(text('select 1'))
        except Exception as e:
            ok = False
            err = str(e)
            try:
                db.session.rollback()
            except Exception:
                pass
        db_diag = {'ok': ok, 'uri': uri, 'host': host, 'err': err}
    except Exception:
        db_diag = {'ok': False, 'uri': '', 'host': None, 'err': ''}
    events = []
    # Estoque (Histórico)
    try:
        hist = Historico.query.order_by(Historico.data.desc()).limit(100).all()
        for h in hist:
            t = 'Entrada' if (h.action or '').lower() == 'entrada' else 'Saída'
            qty = h.quantidade or 0
            sign = '+' if t == 'Entrada' else '-'
            events.append({
                'title': f"📦 {t}: {h.product_name} {sign}{qty}",
                'start': (h.data or datetime.utcnow()).isoformat(),
                'color': '#0d6efd',
                'url': url_for('estoque.editar', id=h.product_id) if h.product_id else None,
            })
    except Exception:
        pass
    try:
        from datetime import date, timedelta
        today = date.today()
        current_monday = today - timedelta(days=today.weekday())
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
                ref_monday_setting = AppSetting(); ref_monday_setting.key = 'rodizio_ref_monday'; db.session.add(ref_monday_setting)
            ref_monday_setting.value = current_monday.strftime('%Y-%m-%d')
            db.session.commit()
            ref_monday = current_monday
        open_ref = (ref_open_setting.value.strip() if ref_open_setting and ref_open_setting.value else '1')
        if open_ref not in ('1','2'):
            open_ref = '1'
        if ref_monday < current_monday:
            weeks_diff = (current_monday - ref_monday).days // 7
            if weeks_diff % 2 == 1:
                open_ref = '2' if open_ref == '1' else '1'
            ref_monday = current_monday
            if not ref_monday_setting:
                ref_monday_setting = AppSetting(); ref_monday_setting.key = 'rodizio_ref_monday'; db.session.add(ref_monday_setting)
            ref_monday_setting.value = current_monday.strftime('%Y-%m-%d')
            if not ref_open_setting:
                ref_open_setting = AppSetting(); ref_open_setting.key = 'rodizio_open_team_ref'; db.session.add(ref_open_setting)
            ref_open_setting.value = open_ref
            db.session.commit()
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
            try:
                sun_ref_setting = AppSetting.query.filter_by(key='domingo_ref_sunday').first()
                sun_team_setting = AppSetting.query.filter_by(key='domingo_team_ref').first()
                base_team = (sun_team_setting.value.strip() if sun_team_setting and sun_team_setting.value else None)
                if base_team not in ('1', '2'):
                    # fallback para configuração antiga, se existir
                    sun_m = AppSetting.query.filter_by(key='domingo_manha_team').first()
                    base_team = (sun_m.value.strip() if sun_m and sun_m.value else '1')
                    if base_team not in ('1','2'):
                        base_team = '1'
                    if not sun_team_setting:
                        sun_team_setting = AppSetting(); sun_team_setting.key = 'domingo_team_ref'; db.session.add(sun_team_setting)
                    sun_team_setting.value = base_team
                # definir domingo de referência se não existir
                ref_sunday = None
                if sun_ref_setting and (sun_ref_setting.value or '').strip():
                    try:
                        ref_sunday = datetime.strptime(sun_ref_setting.value.strip(), '%Y-%m-%d').date()
                    except Exception:
                        ref_sunday = None
                if not ref_sunday:
                    last_sunday = (current_monday - timedelta(days=1))
                    if not sun_ref_setting:
                        sun_ref_setting = AppSetting(); sun_ref_setting.key = 'domingo_ref_sunday'; db.session.add(sun_ref_setting)
                    sun_ref_setting.value = last_sunday.strftime('%Y-%m-%d')
                    db.session.commit()
                    ref_sunday = last_sunday
                # calcular equipe do domingo pelo número de semanas desde a referência
                weeks_since_ref = max(0, (sunday - ref_sunday).days // 7)
                domingo_val = base_team if (weeks_since_ref % 2 == 0) else ('2' if base_team == '1' else '1')
                events.append({
                    'title': f"DOMINGO EQUIPE '{domingo_val}' (5h–13h)",
                    'start': sunday.strftime('%Y-%m-%d'),
                    'color': '#fd7e14',
                    'url': url_for('colaboradores.escala'),
                    'kind': 'rodizio-sunday',
                    'team': domingo_val,
                })
            except Exception:
                pass
    except Exception:
        pass
    # Limpeza prevista
    try:
        tasks = CleaningTask.query.all()
        for t in tasks:
            if t.proxima_data:
                events.append({
                    'title': f"🧼 Limpeza prevista: {t.nome_limpeza}",
                    'start': t.proxima_data.strftime('%Y-%m-%d'),
                    'color': '#20c997',
                    'url': url_for('cronograma.cronograma'),
                })
    except Exception:
        pass
    # Limpeza concluída
    try:
        ch = CleaningHistory.query.order_by(CleaningHistory.data_conclusao.desc()).limit(50).all()
        for c in ch:
            events.append({
                'title': f"✅ Limpeza concluída: {c.nome_limpeza}",
                'start': (c.data_conclusao or datetime.utcnow()).isoformat(),
                'color': '#198754',
                'url': url_for('cronograma.cronograma'),
            })
    except Exception:
        pass
    # Carnes
    try:
        recs = MeatReception.query.order_by(MeatReception.data.desc()).limit(50).all()
        for r in recs:
            events.append({
                'title': f"🥩 Recepção de carnes: {r.fornecedor} ({r.tipo})",
                'start': (r.data or datetime.utcnow()).isoformat(),
                'color': '#6c757d',
                'url': url_for('carnes.index'),
            })
    except Exception:
        pass
    # Sistema
    try:
        logs = SystemLog.query.order_by(SystemLog.data.desc()).limit(50).all()
        for lg in logs:
            events.append({
                'title': f"⚙️ {lg.origem}: {lg.evento}",
                'start': (lg.data or datetime.utcnow()).isoformat(),
                'color': '#6610f2',
                'url': url_for('usuarios.monitor') if lg.origem in ('Usuarios', 'Sistema') else None,
            })
    except Exception:
        pass
    # Feriados
    try:
        from datetime import date as _date
        def _fixed(mm: int, dd: int, yy: int):
            return _date(yy, mm, dd).strftime('%Y-%m-%d')
        def _easter_date(yy: int):
            a = yy % 19
            b = yy // 100
            c = yy % 100
            d = (19 * a + b - (b // 4) - ((b + 8) // 25) + 15) % 30
            e = (32 + 2 * (b % 4) + 2 * (c // 4) - d - (c % 4)) % 7
            m = (d + e + 114) // 31
            p = ((d + e + 114) % 31) + 1
            return _date(yy, m, p)
        def _movable_holidays(yy: int):
            from datetime import timedelta as _td
            easter = _easter_date(yy)
            carnival = easter - _td(days=47)
            good_friday = easter - _td(days=2)
            corpus_christi = easter + _td(days=60)
            return [
                {'title': '🎉 Carnaval', 'start': carnival.strftime('%Y-%m-%d'), 'color': '#dc3545', 'kind': 'holiday'},
                {'title': '✝️ Paixão de Cristo', 'start': good_friday.strftime('%Y-%m-%d'), 'color': '#dc3545', 'kind': 'holiday'},
                {'title': '✝️ Corpus Christi', 'start': corpus_christi.strftime('%Y-%m-%d'), 'color': '#dc3545', 'kind': 'holiday'},
            ]
        def _federal_holidays(yy: int):
            return [
                {'title': '🎉 Feriado Nacional: Confraternização Universal', 'start': _fixed(1, 1, yy), 'color': '#dc3545', 'kind': 'holiday'},
                {'title': '🎉 Feriado Nacional: Tiradentes', 'start': _fixed(4, 21, yy), 'color': '#dc3545', 'kind': 'holiday'},
                {'title': '🎉 Feriado Nacional: Dia do Trabalho', 'start': _fixed(5, 1, yy), 'color': '#dc3545', 'kind': 'holiday'},
                {'title': '🎉 Feriado Nacional: Independência do Brasil', 'start': _fixed(9, 7, yy), 'color': '#dc3545', 'kind': 'holiday'},
                {'title': '🎉 Feriado Nacional: Nossa Senhora Aparecida', 'start': _fixed(10, 12, yy), 'color': '#dc3545', 'kind': 'holiday'},
                {'title': '🎉 Feriado Nacional: Finados', 'start': _fixed(11, 2, yy), 'color': '#dc3545', 'kind': 'holiday'},
                {'title': '🎉 Feriado Nacional: Proclamação da República', 'start': _fixed(11, 15, yy), 'color': '#dc3545', 'kind': 'holiday'},
                {'title': '🎉 Feriado Nacional: Natal', 'start': _fixed(12, 25, yy), 'color': '#dc3545', 'kind': 'holiday'},
            ]
        years = []
        try:
            y0 = _date.today().year
            years = [y0-1, y0, y0+1]
        except Exception:
            years = []
        hols = []
        for yy in years:
            hols.extend(_federal_holidays(yy))
            hols.extend(_movable_holidays(yy))
        events.extend(hols)
    except Exception:
        pass
    try:
        credits = LeaveCredit.query.order_by(LeaveCredit.date.desc()).limit(100).all()
        for lc in credits:
            events.append({
                'title': f"🏖️ Crédito de Folga: +{lc.amount_days}",
                'start': lc.date.strftime('%Y-%m-%d'),
                'color': '#ffa94d',
                'url': url_for('colaboradores.escala'),
            })
    except Exception:
        pass
    
    mural_text = ''
    try:
        s = AppSetting.query.filter_by(key='mural_text').first()
        mural_text = (s.value or '') if s else ''
    except Exception:
        mural_text = ''
    def _to_html(txt: str) -> str:
        import html
        esc = html.escape(txt or '')
        esc = esc.replace("\n", "<br>")
        return esc
    mural_html = _to_html(mural_text)
    return render_template('home.html', active_page='home', events=events, mural_html=mural_html, mural_text=mural_text, db_diag=db_diag)

@bp.route('/mural', methods=['POST'], strict_slashes=False)
def update_mural():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    if current_user.nivel != 'admin':
        flash('Apenas Gerente pode editar o mural.', 'danger')
        return redirect(url_for('home.index'))
    txt = request.form.get('mural_text', '').strip()
    try:
        s = AppSetting.query.filter_by(key='mural_text').first()
        if not s:
            s = AppSetting()
            s.key = 'mural_text'
            db.session.add(s)
        s.value = txt
        db.session.commit()
        flash('Mural atualizado.', 'success')
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f'Erro ao atualizar mural: {e}', 'danger')
    return redirect(url_for('home.index'))
