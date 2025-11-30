from datetime import datetime, timedelta, date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .. import db
from ..models import CleaningTask, CleaningHistory

bp = Blueprint('cronograma', __name__)

def calcular_proxima_prevista(ultima_data, frequencia, tipo):
    hoje = datetime.utcnow().date()
    if frequencia == '15 dias':
        deadline = ultima_data + timedelta(days=15)
        dia = ultima_data + timedelta(days=1)
        escolhido = None
        while dia <= deadline:
            if dia.weekday() in (1, 3) and dia.day not in (1, 2, 3, 4):
                escolhido = dia
                break
            dia += timedelta(days=1)
        if escolhido:
            return escolhido
        retro = deadline
        while retro >= ultima_data:
            if retro.weekday() in (1, 3) and retro.day not in (1, 2, 3, 4):
                return retro
            retro -= timedelta(days=1)
        return deadline
    if frequencia == '40 dias':
        return ultima_data + timedelta(days=40)
    proxima_base = datetime.combine(ultima_data, datetime.min.time())
    while True:
        if frequencia == 'Semanal':
            proxima_base += timedelta(weeks=1)
        elif frequencia == 'Mensal':
            proxima_base += timedelta(days=30)
        elif frequencia == 'Trimestral':
            proxima_base += timedelta(days=90)
        else:
            return ultima_data + timedelta(days=1)
        if proxima_base.date() > hoje:
            return proxima_base.date()
        if proxima_base.date() > hoje + timedelta(days=365*5):
            return ultima_data + timedelta(days=1)

def setup_cleaning_tasks():
    if CleaningTask.query.count() == 0:
        hoje = date.today()
        tarefas = [
            ("Limpeza Parcial da Câmara Fria", "15 dias", "Parcial", "Agendar em Terça/Quinta, evitando dias 1–4 do mês."),
            ("Limpeza Geral da Câmara Fria", "40 dias", "Geral", "Higienização completa: chão, paredes, paletes, prateleiras, barras."),
            ("Limpeza de Expositores do Açougue", "Mensal", "Mensal", "Realizar após o expediente uma vez por mês."),
        ]
        for nome, freq, tipo, obs in tarefas:
            ultima_data = hoje - timedelta(days=1)
            proxima_data = calcular_proxima_prevista(ultima_data, freq, tipo)
            new_task = CleaningTask(
                nome_limpeza=nome,
                frequencia=freq,
                tipo=tipo,
                ultima_data=ultima_data,
                proxima_data=proxima_data,
                observacao=obs,
                designados="Equipe de Limpeza"
            )
            db.session.add(new_task)
        db.session.commit()

@bp.route('/cronograma', methods=['GET'])
@login_required
def cronograma():
    if current_user.nivel not in ['operador', 'admin']:
        flash('Acesso negado. Apenas Operadores e Administradores podem visualizar o cronograma.', 'danger')
        return redirect(url_for('estoque.index'))
    mapping = {
        'Limpeza Diária Geral': (
            'Limpeza Parcial da Câmara Fria', '15 dias', 'Parcial',
            'Agendar em Terça/Quinta, evitando dias 1–4 do mês.'
        ),
        'Limpeza Parcial (Máquinas e Bancadas)': (
            'Limpeza Geral da Câmara Fria', '40 dias', 'Geral',
            'Higienização completa: chão, paredes, paletes, prateleiras, barras.'
        ),
        'Limpeza Completa da Unidade': (
            'Limpeza de Expositores do Açougue', 'Mensal', 'Mensal',
            'Realizar após o expediente uma vez por mês.'
        ),
    }
    atualizados = False
    for antigo, novo in mapping.items():
        tarefa = CleaningTask.query.filter_by(nome_limpeza=antigo).first()
        if tarefa:
            tarefa.nome_limpeza = novo[0]
            tarefa.frequencia = novo[1]
            tarefa.tipo = novo[2]
            tarefa.observacao = novo[3]
            tarefa.proxima_data = calcular_proxima_prevista(tarefa.ultima_data, tarefa.frequencia, tarefa.tipo)
            atualizados = True
    padroes = {
        'Limpeza Parcial da Câmara Fria': ('15 dias', 'Parcial', 'Agendar em Terça/Quinta, evitando dias 1–4 do mês.'),
        'Limpeza Geral da Câmara Fria': ('40 dias', 'Geral', 'Higienização completa: chão, paredes, paletes, prateleiras, barras.'),
        'Limpeza de Expositores do Açougue': ('Mensal', 'Mensal', 'Realizar após o expediente uma vez por mês.'),
    }
    for nome, defs in padroes.items():
        tarefa = CleaningTask.query.filter_by(nome_limpeza=nome).first()
        if tarefa and tarefa.frequencia != defs[0]:
            tarefa.frequencia = defs[0]
            tarefa.tipo = defs[1]
            tarefa.observacao = tarefa.observacao or defs[2]
            tarefa.proxima_data = calcular_proxima_prevista(tarefa.ultima_data, tarefa.frequencia, tarefa.tipo)
            atualizados = True
    if atualizados:
        db.session.commit()
    tarefas = CleaningTask.query.order_by(CleaningTask.proxima_data.asc()).all()
    historico_limpezas = CleaningHistory.query.order_by(CleaningHistory.data_conclusao.desc()).limit(10).all()
    return render_template('cronograma.html', cronograma_tarefas=tarefas, historico_limpezas=historico_limpezas, active_page='cronograma')

@bp.route('/cronograma/salvar', methods=['POST'])
@login_required
def salvar_cronograma():
    if current_user.nivel != 'admin':
        flash('Apenas Gerente (Admin) pode concluir e atualizar o cronograma.', 'danger')
        return redirect(url_for('cronograma.cronograma'))
    concluir_id = request.form.get('concluir_id')
    if concluir_id:
        try:
            task_id = int(concluir_id)
            tarefa = CleaningTask.query.get_or_404(task_id)
            observacao = request.form.get(f'obs_{task_id}', '').strip()
            designados = request.form.get(f'participantes_{task_id}', current_user.name).strip()
            hist = CleaningHistory(
                nome_limpeza=tarefa.nome_limpeza,
                observacao=observacao if observacao else "Sem observações.",
                designados=designados if designados else current_user.name,
                usuario_conclusao=current_user.name
            )
            db.session.add(hist)
            tarefa.ultima_data = datetime.utcnow().date()
            tarefa.proxima_data = calcular_proxima_prevista(tarefa.ultima_data, tarefa.frequencia, tarefa.tipo)
            tarefa.observacao = observacao if observacao else tarefa.observacao
            tarefa.designados = designados if designados else tarefa.designados
            db.session.commit()
            flash(f'Limpeza "{tarefa.nome_limpeza}" marcada como concluída e reagendada para {tarefa.proxima_data.strftime("%d/%m/%Y")}.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao concluir a tarefa de limpeza: {e}', 'danger')
    return redirect(url_for('cronograma.cronograma'))

@bp.route('/cronograma/changelog')
@login_required
def changelog():
    if current_user.nivel not in ['operador', 'admin']:
        flash('Acesso negado. Apenas Operadores e Administradores podem visualizar o changelog.', 'danger')
        return redirect(url_for('estoque.index'))
    page = request.args.get('page', 1, type=int)
    hist = CleaningHistory.query.order_by(CleaningHistory.data_conclusao.desc()).paginate(page=page, per_page=10, error_out=False)
    items = []
    for h in hist.items:
        items.append({
            'data': h.data_conclusao,
            'tipo': h.nome_limpeza,
            'observacao': h.observacao,
            'designados': h.designados,
        })
    return render_template('changelog.html', active_page='cronograma', history=hist, items=items)
