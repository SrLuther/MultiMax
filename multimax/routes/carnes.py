from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from ..models import MeatReception, MeatCarrier, MeatPart
from .. import db

bp = Blueprint('carnes', __name__, url_prefix='/carnes')

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
            cw = carriers.get(p.carrier_id).peso if p.carrier_id in carriers else 0.0
            total += max(0.0, (p.peso_bruto or 0.0) - cw)
        items.append({'r': r, 'total': total, 'count': len(parts)})
    return render_template('carnes.html', items=items, active_page='carnes')

@bp.route('/nova', methods=['GET', 'POST'], strict_slashes=False)
@login_required
def nova():
    if current_user.nivel not in ['operador', 'admin']:
        return redirect(url_for('estoque.index'))
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
            try:
                w = float(pesos[i]) if i < len(pesos) else 0.0
            except Exception:
                w = 0.0
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
        total = 0.0
        for i in range(len(categorias)):
            try:
                an = int(animal_nums[i]) if i < len(animal_nums) else None
            except Exception:
                an = None
            cat = (categorias[i] or '').strip()
            lado = (lados[i] or '').strip()
            try:
                pb = float(pesos_brutos[i]) if i < len(pesos_brutos) else 0.0
            except Exception:
                pb = 0.0
            try:
                idx = int(carriers_idx[i]) if i < len(carriers_idx) else -1
            except Exception:
                idx = -1
            cid = carrier_ids[idx] if 0 <= idx < len(carrier_ids) else None
            p = MeatPart()
            p.reception_id = r.id
            p.animal_numero = an
            p.categoria = cat
            p.lado = lado
            p.peso_bruto = pb
            p.carrier_id = cid
            db.session.add(p)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash('Erro ao registrar recepção.', 'danger')
            return redirect(url_for('carnes.nova'))
        carriers_map = {c.id: c for c in MeatCarrier.query.filter_by(reception_id=r.id).all()}
        parts = MeatPart.query.filter_by(reception_id=r.id).all()
        for p in parts:
            cw = carriers_map.get(p.carrier_id).peso if p.carrier_id in carriers_map else 0.0
            total += max(0.0, (p.peso_bruto or 0.0) - cw)
        flash(f'Recepção registrada. Total líquido: {total:.2f} kg.', 'success')
        return redirect(url_for('carnes.index'))
    return render_template('carnes.html', items=[], active_page='carnes', nova=True)
