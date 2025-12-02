from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import current_user
from datetime import datetime
from .. import db
from ..models import Historico, CleaningTask, CleaningHistory, MeatReception, SystemLog, AppSetting

bp = Blueprint('home', __name__, url_prefix='/home')

@bp.route('/', strict_slashes=False)
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    events = []
    try:
        hist = Historico.query.order_by(Historico.data.desc()).limit(200).all()
        for h in hist:
            t = 'Entrada' if (h.action or '').lower() == 'entrada' else 'Saída'
            qty = h.quantidade or 0
            sign = '+' if t == 'Entrada' else '-' 
            events.append({
                'title': f"{t}: {h.product_name} {sign}{qty}",
                'start': (h.data or datetime.utcnow()).isoformat(),
                'color': '#0d6efd',
                'url': url_for('estoque.editar', id=h.product_id) if h.product_id else None,
            })
    except Exception:
        pass
    try:
        tasks = CleaningTask.query.all()
        for t in tasks:
            if t.proxima_data:
                events.append({
                    'title': f"Limpeza prevista: {t.nome_limpeza}",
                    'start': t.proxima_data.strftime('%Y-%m-%d'),
                    'color': '#20c997',
                    'url': url_for('cronograma.cronograma'),
                })
    except Exception:
        pass
    try:
        ch = CleaningHistory.query.order_by(CleaningHistory.data_conclusao.desc()).limit(100).all()
        for c in ch:
            events.append({
                'title': f"Limpeza concluída: {c.nome_limpeza}",
                'start': (c.data_conclusao or datetime.utcnow()).isoformat(),
                'color': '#198754',
                'url': url_for('cronograma.cronograma'),
            })
    except Exception:
        pass
    try:
        recs = MeatReception.query.order_by(MeatReception.data.desc()).limit(100).all()
        for r in recs:
            events.append({
                'title': f"Recepção de carnes: {r.fornecedor} ({r.tipo})",
                'start': (r.data or datetime.utcnow()).isoformat(),
                'color': '#6c757d',
                'url': url_for('carnes.index'),
            })
    except Exception:
        pass
    try:
        logs = SystemLog.query.order_by(SystemLog.data.desc()).limit(100).all()
        for lg in logs:
            events.append({
                'title': f"{lg.origem}: {lg.evento}",
                'start': (lg.data or datetime.utcnow()).isoformat(),
                'color': '#6610f2',
                'url': url_for('usuarios.monitor') if lg.origem in ('Usuarios', 'Sistema') else None,
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
    return render_template('home.html', active_page='home', events=events, mural_html=mural_html, mural_text=mural_text)

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
