from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from zoneinfo import ZoneInfo
from ..models import SupplierEvaluation, Fornecedor, MeatReception, db
from sqlalchemy import func, desc

bp = Blueprint('fornecedores_avaliacao', __name__, url_prefix='/fornecedores-avaliacao')

@bp.route('/', methods=['GET'])
@login_required
def index():
    fornecedor_id = request.args.get('fornecedor_id', type=int)
    
    query = SupplierEvaluation.query
    if fornecedor_id:
        query = query.filter_by(fornecedor_id=fornecedor_id)
    
    avaliacoes = query.order_by(desc(SupplierEvaluation.data_avaliacao)).limit(100).all()
    
    # Calcular médias por fornecedor
    fornecedores = Fornecedor.query.filter_by(ativo=True).all()
    medias = {}
    for forn in fornecedores:
        avals = SupplierEvaluation.query.filter_by(fornecedor_id=forn.id).all()
        if avals:
            medias[forn.id] = {
                'qualidade': sum(a.nota_qualidade for a in avals) / len(avals),
                'preco': sum(a.nota_preco for a in avals) / len(avals),
                'pontualidade': sum(a.nota_pontualidade for a in avals) / len(avals),
                'atendimento': sum(a.nota_atendimento for a in avals) / len(avals),
                'total': sum(a.nota_qualidade + a.nota_preco + a.nota_pontualidade + a.nota_atendimento for a in avals) / (len(avals) * 4)
            }
    
    return render_template('fornecedores_avaliacao/index.html',
                         avaliacoes=avaliacoes,
                         fornecedor_id=fornecedor_id,
                         fornecedores=fornecedores,
                         medias=medias,
                         active_page='fornecedores_avaliacao')

@bp.route('/nova', methods=['GET', 'POST'])
@login_required
def nova():
    if current_user.nivel == 'visualizador':
        flash('Visualizadores não têm permissão para fazer alterações.', 'danger')
        return redirect(url_for('fornecedores_avaliacao.index'))
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Você não tem permissão para criar avaliações.', 'danger')
        return redirect(url_for('fornecedores_avaliacao.index'))
    
    if request.method == 'POST':
        fornecedor_id = int(request.form.get('fornecedor_id', '0') or '0')
        reception_id = int(request.form.get('reception_id', '0') or '0') if request.form.get('reception_id') else None
        nota_qualidade = int(request.form.get('nota_qualidade', '5') or '5')
        nota_preco = int(request.form.get('nota_preco', '5') or '5')
        nota_pontualidade = int(request.form.get('nota_pontualidade', '5') or '5')
        nota_atendimento = int(request.form.get('nota_atendimento', '5') or '5')
        observacao = request.form.get('observacao', '').strip()
        
        if not fornecedor_id:
            flash('Fornecedor é obrigatório.', 'warning')
            return redirect(url_for('fornecedores_avaliacao.nova'))
        
        aval = SupplierEvaluation()
        aval.fornecedor_id = fornecedor_id
        aval.reception_id = reception_id
        aval.nota_qualidade = max(1, min(10, nota_qualidade))
        aval.nota_preco = max(1, min(10, nota_preco))
        aval.nota_pontualidade = max(1, min(10, nota_pontualidade))
        aval.nota_atendimento = max(1, min(10, nota_atendimento))
        aval.observacao = observacao
        aval.avaliador = current_user.name
        
        try:
            db.session.add(aval)
            db.session.commit()
            flash('Avaliação registrada!', 'success')
            return redirect(url_for('fornecedores_avaliacao.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao registrar avaliação: {e}', 'danger')
    
    fornecedores = Fornecedor.query.filter_by(ativo=True).order_by(Fornecedor.nome).all()
    recepcoes = MeatReception.query.order_by(desc(MeatReception.data)).limit(50).all()
    
    return render_template('fornecedores_avaliacao/nova.html',
                         fornecedores=fornecedores,
                         recepcoes=recepcoes,
                         active_page='fornecedores_avaliacao')

