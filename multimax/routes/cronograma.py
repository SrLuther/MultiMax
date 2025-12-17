from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from .. import db
from ..models import CleaningTask, CleaningHistory, CleaningChecklistTemplate, CleaningChecklistItem, CleaningHistoryPhoto

bp = Blueprint('cronograma', __name__)

def calcular_proxima_prevista(ultima_data, frequencia, tipo, nome=None):
    hoje = datetime.now(ZoneInfo('America/Sao_Paulo')).date()
    def aplicar_regras(d):
        motivos = []
        cur = d
        if cur.day in (1,2,3,4):
            motivos.append('Ajuste: início do mês (1–4)')
            while cur.day in (1,2,3,4):
                cur = cur + timedelta(days=1)
        if cur.weekday() not in (1,2,3,4):
            motivos.append('Ajuste: fora de terça–sexta')
            while cur.weekday() not in (1,2,3,4):
                cur = cur + timedelta(days=1)
        return cur, ', '.join(motivos)
    base = None
    if (nome or '').strip().lower() == 'limpeza da caixa de gordura':
        b = hoje
        wd = b.weekday()
        if wd <= 3:
            base = b + timedelta(days=(3 - wd))
        elif wd == 4:
            base = b
        else:
            base = b + timedelta(days=(7 - wd + 3))
        if base <= ultima_data:
            base = base + timedelta(days=7)
        ajustada, _mot = aplicar_regras(base)
        return ajustada
    if isinstance(frequencia, str) and frequencia.lower().startswith('personalizada'):
        try:
            num = int(''.join([c for c in frequencia if c.isdigit()]))
        except Exception:
            num = 1
        base = ultima_data + timedelta(days=max(1, num))
        ajustada, _mot = aplicar_regras(base)
        return ajustada
    if frequencia == '15 dias':
        base = ultima_data + timedelta(days=15)
        ajustada, _mot = aplicar_regras(base)
        return ajustada if ajustada > hoje else aplicar_regras(hoje + timedelta(days=1))[0]
    if frequencia == '40 dias':
        base = ultima_data + timedelta(days=40)
        ajustada, _mot = aplicar_regras(base)
        return ajustada
    proxima_base = datetime.combine(ultima_data, datetime.min.time())
    while True:
        if frequencia == 'Semanal':
            proxima_base += timedelta(weeks=1)
        elif frequencia == 'Mensal':
            proxima_base += timedelta(days=30)
        elif frequencia == 'Trimestral':
            proxima_base += timedelta(days=90)
        else:
            proxima_base += timedelta(days=1)
        cand = proxima_base.date()
        if cand > hoje:
            ajustada, _mot = aplicar_regras(cand)
            return ajustada
        if cand > hoje + timedelta(days=365*5):
            ajustada, _ = aplicar_regras(ultima_data + timedelta(days=1))
            return ajustada

def proxima_base_sem_regra(ultima_data, frequencia, tipo, nome=None):
    hoje = datetime.now(ZoneInfo('America/Sao_Paulo')).date()
    if (nome or '').strip().lower() == 'limpeza da caixa de gordura':
        b = hoje
        wd = b.weekday()
        if wd <= 3:
            base = b + timedelta(days=(3 - wd))
        elif wd == 4:
            base = b
        else:
            base = b + timedelta(days=(7 - wd + 3))
        if base <= ultima_data:
            base = base + timedelta(days=7)
        return base
    if isinstance(frequencia, str) and frequencia.lower().startswith('personalizada'):
        try:
            num = int(''.join([c for c in frequencia if c.isdigit()]))
        except Exception:
            num = 1
        return ultima_data + timedelta(days=max(1, num))
    if frequencia == '15 dias':
        return ultima_data + timedelta(days=15)
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
            proxima_base += timedelta(days=1)
        cand = proxima_base.date()
        if cand > hoje:
            return cand

def setup_cleaning_tasks():
    if CleaningTask.query.count() == 0:
        hoje = date.today()
        tarefas = [
            ("Limpeza Parcial da Câmara Fria", "15 dias", "Parcial", "Agendar em Terça/Quinta, evitando dias 1–4 do mês."),
            ("Limpeza Geral da Câmara Fria", "40 dias", "Geral", "Higienização completa: chão, paredes, paletes, prateleiras, barras."),
            ("Limpeza de Expositores do Açougue", "Mensal", "Mensal", "Realizar após o expediente uma vez por mês."),
            ("Limpeza da Caixa de Gordura", "Semanal", "Semanal", "Agendar entre quinta e sexta-feira."),
        ]
        for nome, freq, tipo, obs in tarefas:
            ultima_data = hoje - timedelta(days=1)
            proxima_data = calcular_proxima_prevista(ultima_data, freq, tipo, nome)
            new_task = CleaningTask()
            new_task.nome_limpeza = nome
            new_task.frequencia = freq
            new_task.tipo = tipo
            new_task.ultima_data = ultima_data
            new_task.proxima_data = proxima_data
            new_task.observacao = obs
            new_task.designados = "Equipe de Limpeza"
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
            tarefa.proxima_data = calcular_proxima_prevista(tarefa.ultima_data, tarefa.frequencia, tarefa.tipo, tarefa.nome_limpeza)
            atualizados = True
    padroes = {
        'Limpeza Parcial da Câmara Fria': ('15 dias', 'Parcial', 'Agendar em Terça/Quinta, evitando dias 1–4 do mês.'),
        'Limpeza Geral da Câmara Fria': ('40 dias', 'Geral', 'Higienização completa: chão, paredes, paletes, prateleiras, barras.'),
        'Limpeza de Expositores do Açougue': ('Mensal', 'Mensal', 'Realizar após o expediente uma vez por mês.'),
        'Limpeza da Caixa de Gordura': ('Semanal', 'Semanal', 'Agendar entre quinta e sexta-feira.'),
    }
    for nome, defs in padroes.items():
        tarefa = CleaningTask.query.filter_by(nome_limpeza=nome).first()
        if not tarefa:
            hoje = date.today()
            nova = CleaningTask()
            nova.nome_limpeza = nome
            nova.frequencia = defs[0]
            nova.tipo = defs[1]
            nova.ultima_data = hoje - timedelta(days=1)
            nova.proxima_data = calcular_proxima_prevista(nova.ultima_data, nova.frequencia, nova.tipo, nome)
            nova.observacao = defs[2]
            nova.designados = 'Equipe de Limpeza'
            db.session.add(nova)
            atualizados = True
        else:
            # não sobrescrever frequência escolhida manualmente; apenas preencher observação se faltando
            if not tarefa.observacao:
                tarefa.observacao = defs[2]
    if atualizados:
        db.session.commit()
    tipo_sel = request.args.get('tipo', '').strip()
    tarefas_q = CleaningTask.query
    allowed_types = {'Parcial','Geral','Mensal','Semanal'}
    if tipo_sel in allowed_types:
        tarefas_q = tarefas_q.filter(CleaningTask.tipo == tipo_sel)
    tarefas = tarefas_q.order_by(CleaningTask.proxima_data.asc()).all()
    ajustes = {}
    for t in tarefas:
        base = proxima_base_sem_regra(t.ultima_data, t.frequencia, t.tipo, t.nome_limpeza)
        parts = []
        if base.day in (1,2,3,4):
            parts.append('ajuste: início do mês (1–4)')
        if base.weekday() not in (1,2,3,4):
            parts.append('ajuste: fora de terça–sexta')
        if parts:
            ajustes[t.id] = ' • '.join(parts)
    page_hist = request.args.get('hpage', 1, type=int)
    htipo = request.args.get('htipo', '').strip()
    allowed_types = {'Parcial','Geral','Mensal','Semanal'}
    q = CleaningHistory.query
    if htipo in allowed_types:
        nomes_por_tipo = [n for n, defs in padroes.items() if defs[1] == htipo]
        if nomes_por_tipo:
            q = q.filter(CleaningHistory.nome_limpeza.in_(nomes_por_tipo))
    hist_pag = q.order_by(CleaningHistory.data_conclusao.desc()).paginate(page=page_hist, per_page=5, error_out=False)
    
    hoje = date.today()
    total_tarefas = CleaningTask.query.count()
    tarefas_atrasadas = CleaningTask.query.filter(CleaningTask.proxima_data < hoje).count()
    tarefas_proximas = CleaningTask.query.filter(
        CleaningTask.proxima_data >= hoje,
        CleaningTask.proxima_data <= hoje + timedelta(days=7)
    ).count()
    
    primeiro_dia_mes = hoje.replace(day=1)
    if hoje.month == 12:
        ultimo_dia_mes = hoje.replace(year=hoje.year+1, month=1, day=1) - timedelta(days=1)
    else:
        ultimo_dia_mes = hoje.replace(month=hoje.month+1, day=1) - timedelta(days=1)
    
    concluidas_mes = CleaningHistory.query.filter(
        CleaningHistory.data_conclusao >= datetime.combine(primeiro_dia_mes, datetime.min.time()),
        CleaningHistory.data_conclusao <= datetime.combine(ultimo_dia_mes, datetime.max.time())
    ).count()
    
    taxa_cumprimento = round((concluidas_mes / max(total_tarefas, 1)) * 100) if total_tarefas > 0 else 0
    
    kpis = {
        'total': total_tarefas,
        'atrasadas': tarefas_atrasadas,
        'proximas': tarefas_proximas,
        'concluidas_mes': concluidas_mes,
        'taxa': min(taxa_cumprimento, 100)
    }
    
    for t in tarefas:
        t.status = 'normal'
        if t.proxima_data < hoje:
            t.status = 'atrasada'
        elif t.proxima_data <= hoje + timedelta(days=3):
            t.status = 'urgente'
    
    return render_template('cronograma.html', cronograma_tarefas=tarefas, historico_limpezas=hist_pag.items, historico_pagination=hist_pag, active_page='cronograma', htipo=htipo, ajustes=ajustes, tipo=tipo_sel, kpis=kpis, hoje=hoje)

@bp.route('/cronograma/salvar', methods=['POST'])
@login_required
def salvar_cronograma():
    if current_user.nivel != 'admin':
        flash('Apenas Gerente (Admin) pode concluir e atualizar o cronograma.', 'danger')
        return redirect(url_for('cronograma.cronograma'))
    concluir_id = request.form.get('concluir_id')
    alterar_id = request.form.get('alterar_id')
    nova_freq = request.form.get('nova_frequencia', '').strip()
    nova_dias = request.form.get('nova_dias', '').strip()
    if alterar_id and nova_freq:
        try:
            task_id = int(alterar_id)
            tarefa = CleaningTask.query.get_or_404(task_id)
            allowed = {'Semanal','15 dias','Mensal','40 dias','Trimestral','Personalizada'}
            if nova_freq not in allowed:
                flash('Frequência inválida.', 'danger')
                return redirect(url_for('cronograma.cronograma'))
            if nova_freq == 'Personalizada':
                try:
                    nd = int(nova_dias)
                except Exception:
                    nd = 0
                if nd <= 0:
                    flash('Dias personalizados inválidos.', 'danger')
                    return redirect(url_for('cronograma.cronograma'))
                tarefa.frequencia = f'Personalizada {nd} dias'
            else:
                tarefa.frequencia = nova_freq
            tarefa.proxima_data = calcular_proxima_prevista(tarefa.ultima_data, tarefa.frequencia, tarefa.tipo, tarefa.nome_limpeza)
            db.session.commit()
            flash('Frequência atualizada.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar frequência: {e}', 'danger')
        return redirect(url_for('cronograma.cronograma'))
    if concluir_id:
        try:
            task_id = int(concluir_id)
            tarefa = CleaningTask.query.get_or_404(task_id)
            observacao = (request.form.get(f'obs_{task_id}', '') or '').strip()
            designados = (request.form.get(f'participantes_{task_id}', None) or current_user.name or '').strip()
            data_conclusao_str = (request.form.get('data_conclusao', '') or '').strip()
            hist = CleaningHistory()
            hist.nome_limpeza = tarefa.nome_limpeza
            hist.observacao = observacao if observacao else "Sem observações."
            hist.designados = designados if designados else (current_user.name or '')
            hist.usuario_conclusao = current_user.name
            if data_conclusao_str:
                try:
                    dtc = datetime.strptime(data_conclusao_str, '%Y-%m-%d').replace(tzinfo=ZoneInfo('America/Sao_Paulo'))
                    hist.data_conclusao = dtc
                    tarefa.ultima_data = dtc.date()
                except Exception:
                    tarefa.ultima_data = datetime.now(ZoneInfo('America/Sao_Paulo')).date()
            else:
                tarefa.ultima_data = datetime.now(ZoneInfo('America/Sao_Paulo')).date()
            db.session.add(hist)
            tarefa.proxima_data = calcular_proxima_prevista(tarefa.ultima_data, tarefa.frequencia, tarefa.tipo, tarefa.nome_limpeza)
            tarefa.observacao = observacao if observacao else tarefa.observacao
            tarefa.designados = designados if designados else tarefa.designados
            db.session.commit()
            flash(f'Limpeza "{tarefa.nome_limpeza}" marcada como concluída e reagendada para {tarefa.proxima_data.strftime("%d/%m/%Y")}.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao concluir a tarefa de limpeza: {e}', 'danger')
    return redirect(url_for('cronograma.cronograma'))


@bp.route('/cronograma/historico/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_historico(id: int):
    if current_user.nivel != 'admin':
        flash('Apenas Gerente pode excluir histórico.', 'danger')
        return redirect(url_for('cronograma.cronograma'))
    h = CleaningHistory.query.get_or_404(id)
    try:
        db.session.delete(h)
        db.session.commit()
        flash('Histórico excluído.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir histórico: {e}', 'danger')
    return redirect(url_for('cronograma.cronograma'))


@bp.route('/cronograma/api/calendario', methods=['GET'])
@login_required
def api_calendario():
    ano = request.args.get('ano', date.today().year, type=int)
    mes = request.args.get('mes', date.today().month, type=int)
    
    primeiro_dia = date(ano, mes, 1)
    if mes == 12:
        ultimo_dia = date(ano + 1, 1, 1) - timedelta(days=1)
    else:
        ultimo_dia = date(ano, mes + 1, 1) - timedelta(days=1)
    
    tarefas = CleaningTask.query.filter(
        CleaningTask.proxima_data >= primeiro_dia,
        CleaningTask.proxima_data <= ultimo_dia
    ).all()
    
    historico = CleaningHistory.query.filter(
        CleaningHistory.data_conclusao >= datetime.combine(primeiro_dia, datetime.min.time()),
        CleaningHistory.data_conclusao <= datetime.combine(ultimo_dia, datetime.max.time())
    ).all()
    
    eventos = []
    cores = {'Parcial': '#3b82f6', 'Geral': '#ef4444', 'Mensal': '#f59e0b', 'Semanal': '#22c55e'}
    hoje = date.today()
    
    for t in tarefas:
        cor = cores.get(t.tipo, '#6b7280')
        if t.proxima_data < hoje:
            cor = '#dc2626'
        eventos.append({
            'id': f'task_{t.id}',
            'title': t.nome_limpeza,
            'start': t.proxima_data.isoformat(),
            'color': cor,
            'tipo': t.tipo,
            'status': 'atrasada' if t.proxima_data < hoje else 'pendente'
        })
    
    for h in historico:
        eventos.append({
            'id': f'hist_{h.id}',
            'title': f'✓ {h.nome_limpeza}',
            'start': h.data_conclusao.date().isoformat(),
            'color': '#10b981',
            'status': 'concluida'
        })
    
    return jsonify({'eventos': eventos, 'ano': ano, 'mes': mes})


@bp.route('/cronograma/api/checklist/<tipo>', methods=['GET'])
@login_required
def api_checklist(tipo):
    items = CleaningChecklistTemplate.query.filter_by(tipo=tipo).order_by(CleaningChecklistTemplate.ordem).all()
    return jsonify({'items': [{'id': i.id, 'texto': i.item_texto, 'obrigatorio': i.obrigatorio} for i in items]})


@bp.route('/cronograma/concluir-completo', methods=['POST'])
@login_required
def concluir_completo():
    if current_user.nivel not in ('operador', 'admin'):
        flash('Sem permissão.', 'danger')
        return redirect(url_for('cronograma.cronograma'))
    
    task_id = request.form.get('task_id', type=int)
    tarefa = CleaningTask.query.get_or_404(task_id)
    
    observacao = (request.form.get('observacao', '') or '').strip()
    designados = (request.form.get('designados', '') or current_user.name).strip()
    duracao = request.form.get('duracao', type=int)
    qualidade = request.form.get('qualidade', 5, type=int)
    data_str = request.form.get('data_conclusao', '').strip()
    
    try:
        hist = CleaningHistory()
        hist.task_id = task_id
        hist.nome_limpeza = tarefa.nome_limpeza
        hist.observacao = observacao or 'Sem observações'
        hist.designados = designados
        hist.usuario_conclusao = current_user.name
        hist.duracao_minutos = duracao
        hist.qualidade = qualidade
        
        if data_str:
            try:
                dt = datetime.strptime(data_str, '%Y-%m-%d').replace(tzinfo=ZoneInfo('America/Sao_Paulo'))
                hist.data_conclusao = dt
                tarefa.ultima_data = dt.date()
            except:
                tarefa.ultima_data = date.today()
        else:
            tarefa.ultima_data = date.today()
        
        db.session.add(hist)
        db.session.flush()
        
        checklist_items = request.form.getlist('checklist')
        templates = CleaningChecklistTemplate.query.filter_by(tipo=tarefa.tipo).all()
        for tmpl in templates:
            item = CleaningChecklistItem()
            item.history_id = hist.id
            item.item_texto = tmpl.item_texto
            item.concluido = str(tmpl.id) in checklist_items
            if item.concluido:
                item.concluido_por = current_user.name
                item.concluido_em = datetime.now(ZoneInfo('America/Sao_Paulo'))
            db.session.add(item)
        
        upload_folder = os.path.join('static', 'uploads', 'limpeza')
        os.makedirs(upload_folder, exist_ok=True)
        
        for tipo_foto in ['antes', 'depois']:
            files = request.files.getlist(f'foto_{tipo_foto}')
            for f in files:
                if f and f.filename:
                    filename = secure_filename(f'{hist.id}_{tipo_foto}_{datetime.now().strftime("%Y%m%d%H%M%S")}_{f.filename}')
                    filepath = os.path.join(upload_folder, filename)
                    f.save(filepath)
                    
                    photo = CleaningHistoryPhoto()
                    photo.history_id = hist.id
                    photo.filename = filename
                    photo.tipo = tipo_foto
                    photo.uploaded_by = current_user.name
                    db.session.add(photo)
        
        tarefa.proxima_data = calcular_proxima_prevista(tarefa.ultima_data, tarefa.frequencia, tarefa.tipo, tarefa.nome_limpeza)
        db.session.commit()
        
        flash(f'Limpeza "{tarefa.nome_limpeza}" concluída com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao concluir: {e}', 'danger')
    
    return redirect(url_for('cronograma.cronograma'))


@bp.route('/cronograma/api/estatisticas', methods=['GET'])
@login_required
def api_estatisticas():
    hoje = date.today()
    
    meses = []
    for i in range(5, -1, -1):
        if hoje.month - i <= 0:
            ano = hoje.year - 1
            mes = 12 + (hoje.month - i)
        else:
            ano = hoje.year
            mes = hoje.month - i
        
        primeiro = date(ano, mes, 1)
        if mes == 12:
            ultimo = date(ano + 1, 1, 1) - timedelta(days=1)
        else:
            ultimo = date(ano, mes + 1, 1) - timedelta(days=1)
        
        concluidas = CleaningHistory.query.filter(
            CleaningHistory.data_conclusao >= datetime.combine(primeiro, datetime.min.time()),
            CleaningHistory.data_conclusao <= datetime.combine(ultimo, datetime.max.time())
        ).count()
        
        meses.append({
            'mes': primeiro.strftime('%b'),
            'concluidas': concluidas
        })
    
    return jsonify({'meses': meses})
