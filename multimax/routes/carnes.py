from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from ..models import MeatReception, MeatCarrier, MeatPart
from .. import db
from sqlalchemy import inspect, text

bp = Blueprint('carnes', __name__, url_prefix='/carnes')

def _num(val):
    try:
        s = (val or '').strip()
        s = s.replace(',', '.')
        return float(s)
    except Exception:
        return 0.0

def _ensure_tara_column():
    try:
        insp = inspect(db.engine)
        cols = [c['name'] for c in insp.get_columns('meat_part')]
        if 'tara' not in cols:
            db.session.execute(text('ALTER TABLE meat_part ADD COLUMN tara REAL DEFAULT 0'))
            db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass

@bp.route('/', strict_slashes=False)
@login_required
def index():
    if current_user.nivel not in ['operador', 'admin']:
        return redirect(url_for('estoque.index'))
    recs = MeatReception.query.order_by(MeatReception.data.desc()).limit(20).all()
    items = []
    for r in recs:
        carriers = {c.id: c for c in MeatCarrier.query.filter_by(reception_id=r.id).all()}
        parts = MeatPart.query.filter_by(reception_id=r.id).all()
        total = 0.0
        for p in parts:
            c = carriers.get(p.carrier_id)
            cw = c.peso if c else 0.0
            sub = cw if cw > 0 else (p.tara or 0.0)
            total += max(0.0, (p.peso_bruto or 0.0) - sub)
        items.append({'r': r, 'total': total, 'count': len(parts)})
    return render_template('carnes.html', items=items, active_page='carnes')

@bp.route('/nova', methods=['GET', 'POST'], strict_slashes=False)
@login_required
def nova():
    if current_user.nivel not in ['operador', 'admin']:
        return redirect(url_for('estoque.index'))
    _ensure_tara_column()
    if request.method == 'POST':
        fornecedor = request.form.get('fornecedor', '').strip()
        tipo = request.form.get('tipo', 'bovina').strip().lower()
        observacao = request.form.get('observacao', '').strip()
        if not fornecedor or tipo not in ('bovina', 'suina'):
            flash('Fornecedor e tipo são obrigatórios.', 'danger')
            return redirect(url_for('carnes.nova'))
        r = MeatReception()
        r.fornecedor = fornecedor
        r.tipo = tipo
        r.observacao = observacao
        db.session.add(r)
        db.session.flush()
        nomes = request.form.getlist('carrier_nome')
        pesos = request.form.getlist('carrier_peso')
        carrier_ids = []
        for i in range(len(nomes)):
            n = (nomes[i] or '').strip()
            w = _num(pesos[i]) if i < len(pesos) else 0.0
            if n and w > 0:
                c = MeatCarrier()
                c.reception_id = r.id
                c.nome = n
                c.peso = w
                db.session.add(c)
                db.session.flush()
                carrier_ids.append(c.id)
        animal_nums = request.form.getlist('animal_numero')
        categorias = request.form.getlist('part_categoria')
        lados = request.form.getlist('part_lado')
        pesos_brutos = request.form.getlist('part_peso_bruto')
        carriers_idx = request.form.getlist('part_carrier')
        taras = request.form.getlist('part_tara')
        total = 0.0
        for i in range(len(categorias)):
            try:
                an = int(animal_nums[i]) if i < len(animal_nums) else None
            except Exception:
                an = None
            cat = (categorias[i] or '').strip()
            lado = (lados[i] or '').strip()
            pb = _num(pesos_brutos[i]) if i < len(pesos_brutos) else 0.0
            try:
                idx = int(carriers_idx[i]) if i < len(carriers_idx) else -1
            except Exception:
                idx = -1
            cid = carrier_ids[idx] if 0 <= idx < len(carrier_ids) else None
            tara = _num(taras[i]) if i < len(taras) else 0.0
            p = MeatPart()
            p.reception_id = r.id
            p.animal_numero = an
            p.categoria = cat
            p.lado = lado
            p.peso_bruto = pb
            p.carrier_id = cid
            p.tara = tara
            db.session.add(p)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao registrar recepção: {e}', 'danger')
            return redirect(url_for('carnes.nova'))
        carriers_map = {c.id: c for c in MeatCarrier.query.filter_by(reception_id=r.id).all()}
        parts = MeatPart.query.filter_by(reception_id=r.id).all()
        for p in parts:
            c = carriers_map.get(p.carrier_id)
            cw = c.peso if c else 0.0
            sub = cw if cw > 0 else (p.tara or 0.0)
            total += max(0.0, (p.peso_bruto or 0.0) - sub)
        flash(f'Recepção registrada. Total líquido: {total:.2f} kg.', 'success')
        return redirect(url_for('carnes.index'))
    return render_template('carnes.html', items=[], active_page='carnes', nova=True)

@bp.route('/relatorio/<int:id>', methods=['GET'], strict_slashes=False)
@login_required
def relatorio(id: int):
    if current_user.nivel not in ['operador', 'admin']:
        return redirect(url_for('estoque.index'))
    r = MeatReception.query.get_or_404(id)
    carriers = MeatCarrier.query.filter_by(reception_id=r.id).all()
    carriers_map = {c.id: c for c in carriers}
    parts = MeatPart.query.filter_by(reception_id=r.id).order_by(MeatPart.id.asc()).all()
    animais = {}
    total_bruto = 0.0
    total_liquido = 0.0
    group_size = 4 if (r.tipo or 'bovina') == 'bovina' else 2
    for idx, p in enumerate(parts):
        c = carriers_map.get(p.carrier_id)
        cw = c.peso if c else 0.0
        bruto = float(p.peso_bruto or 0.0)
        sub = cw if cw > 0 else (p.tara or 0.0)
        liquido = max(0.0, bruto - sub)
        total_bruto += bruto
        total_liquido += liquido
        fallback_num = (idx // group_size) + 1
        an = p.animal_numero if p.animal_numero is not None else fallback_num
        if an not in animais:
            animais[an] = []
        animais[an].append({
            'categoria': p.categoria,
            'lado': p.lado,
            'peso_bruto': bruto,
            'carrier_nome': (c.nome if c else None),
            'carrier_peso': cw if cw > 0 else None,
            'tara': (p.tara or None),
            'peso_liquido': liquido,
        })
    filtered_animais = {an: ps for an, ps in animais.items() if (sum((p.get('peso_bruto') or 0.0) for p in ps) > 0.0) or (sum((p.get('peso_liquido') or 0.0) for p in ps) > 0.0)}
    included_bruto = sum((p.get('peso_bruto') or 0.0) for ps in filtered_animais.values() for p in ps)
    included_liquido = sum((p.get('peso_liquido') or 0.0) for ps in filtered_animais.values() for p in ps)
    included_partes = sum(len(ps) for ps in filtered_animais.values())
    totals = {
        'bruto': included_bruto,
        'liquido': included_liquido,
        'desconto': max(0.0, included_bruto - included_liquido),
        'qtd_partes': included_partes,
        'qtd_animais': len(filtered_animais),
        'funcionarios_peso_total': sum((c.peso or 0.0) for c in carriers),
    }
    return render_template('carnes_relatorio.html', r=r, carriers=carriers, animais=filtered_animais, totals=totals, active_page='carnes')

@bp.route('/excluir/<int:id>', methods=['POST'], strict_slashes=False)
@login_required
def excluir(id: int):
    if current_user.nivel != 'admin':
        flash('Você não tem permissão para excluir recepções.', 'danger')
        return redirect(url_for('carnes.index'))
    r = MeatReception.query.get_or_404(id)
    try:
        MeatPart.query.filter_by(reception_id=r.id).delete()
        MeatCarrier.query.filter_by(reception_id=r.id).delete()
        db.session.delete(r)
        db.session.commit()
        flash('Recepção excluída com sucesso.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir recepção: {e}', 'danger')
    return redirect(url_for('carnes.index'))
