from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from zoneinfo import ZoneInfo
from ..models import MeatCut, MeatCutExecution, MeatReception, MeatPart, db
from sqlalchemy import func

bp = Blueprint('cortes', __name__, url_prefix='/cortes')

@bp.route('/', methods=['GET'])
@login_required
def index():
    if current_user.nivel == 'visualizador':
        flash('Visualizadores não têm permissão para acessar esta página.', 'danger')
        return redirect(url_for('home.index'))
    
    categoria = request.args.get('categoria', '').strip()
    busca = request.args.get('busca', '').strip()
    
    query = MeatCut.query.filter_by(ativo=True)
    if categoria:
        query = query.filter_by(categoria=categoria)
    if busca:
        query = query.filter(MeatCut.nome.ilike(f'%{busca}%'))
    
    cortes = query.order_by(MeatCut.categoria, MeatCut.nome).all()
    
    # Estatísticas
    total_cortes = MeatCut.query.filter_by(ativo=True).count()
    execucoes_hoje = MeatCutExecution.query.filter(
        func.date(MeatCutExecution.data_corte) == datetime.now(ZoneInfo('America/Sao_Paulo')).date()
    ).count()
    
    return render_template('cortes/index.html', 
                         cortes=cortes, 
                         categoria=categoria,
                         busca=busca,
                         total_cortes=total_cortes,
                         execucoes_hoje=execucoes_hoje,
                         active_page='cortes')

@bp.route('/novo', methods=['GET', 'POST'])
@login_required
def novo():
    if current_user.nivel == 'visualizador':
        flash('Visualizadores não têm permissão para fazer alterações.', 'danger')
        return redirect(url_for('cortes.index'))
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Você não tem permissão para criar cortes.', 'danger')
        return redirect(url_for('cortes.index'))
    
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        categoria = request.form.get('categoria', '').strip()
        tipo_corte = request.form.get('tipo_corte', '').strip()
        rendimento_esperado = float(request.form.get('rendimento_esperado', '0') or '0')
        preco_base_kg = float(request.form.get('preco_base_kg', '0') or '0')
        tempo_preparo = int(request.form.get('tempo_preparo_minutos', '0') or '0')
        instrucoes = request.form.get('instrucoes', '').strip()
        equipamentos = request.form.get('equipamentos', '').strip()
        
        if not nome or not categoria:
            flash('Nome e categoria são obrigatórios.', 'warning')
            return redirect(url_for('cortes.novo'))
        
        corte = MeatCut()
        corte.nome = nome
        corte.categoria = categoria
        corte.tipo_corte = tipo_corte
        corte.rendimento_esperado = rendimento_esperado
        corte.preco_base_kg = preco_base_kg
        corte.tempo_preparo_minutos = tempo_preparo
        corte.instrucoes = instrucoes
        corte.equipamentos = equipamentos
        
        try:
            db.session.add(corte)
            db.session.commit()
            flash(f'Corte "{nome}" cadastrado com sucesso!', 'success')
            return redirect(url_for('cortes.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar corte: {e}', 'danger')
    
    return render_template('cortes/novo.html', active_page='cortes')

@bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar(id):
    if current_user.nivel == 'visualizador':
        flash('Visualizadores não têm permissão para fazer alterações.', 'danger')
        return redirect(url_for('cortes.index'))
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Você não tem permissão para editar cortes.', 'danger')
        return redirect(url_for('cortes.index'))
    
    corte = MeatCut.query.get_or_404(id)
    
    if request.method == 'POST':
        corte.nome = request.form.get('nome', '').strip()
        corte.categoria = request.form.get('categoria', '').strip()
        corte.tipo_corte = request.form.get('tipo_corte', '').strip()
        corte.rendimento_esperado = float(request.form.get('rendimento_esperado', '0') or '0')
        corte.preco_base_kg = float(request.form.get('preco_base_kg', '0') or '0')
        corte.tempo_preparo_minutos = int(request.form.get('tempo_preparo_minutos', '0') or '0')
        corte.instrucoes = request.form.get('instrucoes', '').strip()
        corte.equipamentos = request.form.get('equipamentos', '').strip()
        
        try:
            db.session.commit()
            flash('Corte atualizado com sucesso!', 'success')
            return redirect(url_for('cortes.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar corte: {e}', 'danger')
    
    return render_template('cortes/editar.html', corte=corte, active_page='cortes')

@bp.route('/executar', methods=['POST'])
@login_required
def executar():
    if current_user.nivel == 'visualizador':
        flash('Visualizadores não têm permissão para fazer alterações.', 'danger')
        return redirect(url_for('cortes.index'))
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Você não tem permissão para executar cortes.', 'danger')
        return redirect(url_for('cortes.index'))
    
    reception_id = int(request.form.get('reception_id', '0') or '0')
    cut_id = int(request.form.get('cut_id', '0') or '0')
    part_id = int(request.form.get('part_id', '0') or '0') if request.form.get('part_id') else None
    peso_entrada = float(request.form.get('peso_entrada', '0') or '0')
    peso_saida = float(request.form.get('peso_saida', '0') or '0')
    observacao = request.form.get('observacao', '').strip()
    
    if not reception_id or not cut_id or peso_entrada <= 0 or peso_saida <= 0:
        flash('Dados inválidos para execução do corte.', 'warning')
        return redirect(url_for('carnes.index'))
    
    rendimento_real = (peso_saida / peso_entrada * 100) if peso_entrada > 0 else 0
    
    execucao = MeatCutExecution()
    execucao.reception_id = reception_id
    execucao.cut_id = cut_id
    execucao.part_id = part_id
    execucao.peso_entrada = peso_entrada
    execucao.peso_saida = peso_saida
    execucao.rendimento_real = rendimento_real
    execucao.responsavel = current_user.name
    execucao.observacao = observacao
    
    try:
        db.session.add(execucao)
        db.session.commit()
        flash(f'Corte executado! Rendimento: {rendimento_real:.2f}%', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao registrar corte: {e}', 'danger')
    
    return redirect(url_for('carnes.index'))

@bp.route('/rendimento/<int:reception_id>')
@login_required
def rendimento(reception_id):
    reception = MeatReception.query.get_or_404(reception_id)
    execucoes = MeatCutExecution.query.filter_by(reception_id=reception_id).all()
    
    total_entrada = sum(e.peso_entrada for e in execucoes)
    total_saida = sum(e.peso_saida for e in execucoes)
    rendimento_geral = (total_saida / total_entrada * 100) if total_entrada > 0 else 0
    
    return render_template('cortes/rendimento.html',
                         reception=reception,
                         execucoes=execucoes,
                         total_entrada=total_entrada,
                         total_saida=total_saida,
                         rendimento_geral=rendimento_geral,
                         active_page='cortes')

