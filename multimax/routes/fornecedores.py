from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .. import db
from ..models import Fornecedor, Produto

bp = Blueprint('fornecedores', __name__, url_prefix='/fornecedores')

@bp.route('/')
@login_required
def index():
    if current_user.nivel not in ['operador', 'admin']:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('home.index'))
    search = request.args.get('busca', '').strip()
    query = Fornecedor.query
    if search:
        query = query.filter(
            (Fornecedor.nome.contains(search)) | 
            (Fornecedor.cnpj.contains(search)) |
            (Fornecedor.email.contains(search))
        )
    fornecedores = query.order_by(Fornecedor.nome.asc()).all()
    return render_template('fornecedores.html', fornecedores=fornecedores, busca=search, active_page='fornecedores')

@bp.route('/adicionar', methods=['GET', 'POST'])
@login_required
def adicionar():
    if current_user.nivel not in ['operador', 'admin']:
        flash('Você não tem permissão para adicionar fornecedores.', 'danger')
        return redirect(url_for('fornecedores.index'))
    if request.method == 'POST':
        try:
            nome = request.form.get('nome', '').strip()
            if not nome:
                flash('O nome do fornecedor é obrigatório.', 'warning')
                return redirect(url_for('fornecedores.adicionar'))
            cnpj = request.form.get('cnpj', '').strip()
            if cnpj:
                existe = Fornecedor.query.filter_by(cnpj=cnpj).first()
                if existe:
                    flash('Já existe um fornecedor com este CNPJ.', 'danger')
                    return redirect(url_for('fornecedores.adicionar'))
            fornecedor = Fornecedor()
            fornecedor.nome = nome
            fornecedor.cnpj = cnpj if cnpj else None
            fornecedor.telefone = request.form.get('telefone', '').strip() or None
            fornecedor.email = request.form.get('email', '').strip() or None
            fornecedor.endereco = request.form.get('endereco', '').strip() or None
            fornecedor.observacao = request.form.get('observacao', '').strip() or None
            fornecedor.ativo = request.form.get('ativo') == 'on'
            db.session.add(fornecedor)
            db.session.commit()
            flash(f'Fornecedor "{nome}" cadastrado com sucesso!', 'success')
            return redirect(url_for('fornecedores.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar fornecedor: {e}', 'danger')
            return redirect(url_for('fornecedores.adicionar'))
    return render_template('fornecedor_form.html', fornecedor=None, active_page='fornecedores')

@bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id: int):
    if current_user.nivel not in ['operador', 'admin']:
        flash('Você não tem permissão para editar fornecedores.', 'danger')
        return redirect(url_for('fornecedores.index'))
    fornecedor = Fornecedor.query.get_or_404(id)
    if request.method == 'POST':
        try:
            nome = request.form.get('nome', '').strip()
            if not nome:
                flash('O nome do fornecedor é obrigatório.', 'warning')
                return redirect(url_for('fornecedores.editar', id=id))
            cnpj = request.form.get('cnpj', '').strip()
            if cnpj and cnpj != fornecedor.cnpj:
                existe = Fornecedor.query.filter_by(cnpj=cnpj).first()
                if existe and existe.id != id:
                    flash('Já existe um fornecedor com este CNPJ.', 'danger')
                    return redirect(url_for('fornecedores.editar', id=id))
            fornecedor.nome = nome
            fornecedor.cnpj = cnpj if cnpj else None
            fornecedor.telefone = request.form.get('telefone', '').strip() or None
            fornecedor.email = request.form.get('email', '').strip() or None
            fornecedor.endereco = request.form.get('endereco', '').strip() or None
            fornecedor.observacao = request.form.get('observacao', '').strip() or None
            fornecedor.ativo = request.form.get('ativo') == 'on'
            db.session.commit()
            flash(f'Fornecedor "{nome}" atualizado com sucesso!', 'success')
            return redirect(url_for('fornecedores.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar fornecedor: {e}', 'danger')
            return redirect(url_for('fornecedores.editar', id=id))
    return render_template('fornecedor_form.html', fornecedor=fornecedor, active_page='fornecedores')

@bp.route('/excluir/<int:id>')
@login_required
def excluir(id: int):
    if current_user.nivel != 'admin':
        flash('Você não tem permissão para excluir fornecedores.', 'danger')
        return redirect(url_for('fornecedores.index'))
    fornecedor = Fornecedor.query.get_or_404(id)
    try:
        produtos_vinculados = Produto.query.filter_by(fornecedor_id=id).count()
        if produtos_vinculados > 0:
            flash(f'Não é possível excluir: há {produtos_vinculados} produtos vinculados a este fornecedor.', 'danger')
            return redirect(url_for('fornecedores.index'))
        db.session.delete(fornecedor)
        db.session.commit()
        flash(f'Fornecedor "{fornecedor.nome}" excluído com sucesso!', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir fornecedor: {e}', 'danger')
    return redirect(url_for('fornecedores.index'))

@bp.route('/detalhes/<int:id>')
@login_required
def detalhes(id: int):
    if current_user.nivel not in ['operador', 'admin']:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('home.index'))
    fornecedor = Fornecedor.query.get_or_404(id)
    produtos = Produto.query.filter_by(fornecedor_id=id).order_by(Produto.nome.asc()).all()
    return render_template('fornecedor_detalhes.html', fornecedor=fornecedor, produtos=produtos, active_page='fornecedores')
