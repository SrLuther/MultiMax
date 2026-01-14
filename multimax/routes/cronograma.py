import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from .. import db
from ..filename_utils import secure_filename
from ..models import (
    CleaningChecklistItem,
    CleaningChecklistTemplate,
    CleaningHistory,
    CleaningHistoryPhoto,
    CleaningTask,
)

bp = Blueprint("cronograma", __name__)

# ============================================================================
# Constantes
# ============================================================================

TASK_PADROES = {
    "Limpeza Parcial da Câmara Fria": ("15 dias", "Parcial", "Agendar em Terça/Quinta, evitando dias 1–4 do mês."),
    "Limpeza Geral da Câmara Fria": (
        "40 dias",
        "Geral",
        "Higienização completa: chão, paredes, paletes, prateleiras, barras.",
    ),
    "Limpeza de Expositores do Açougue": ("Mensal", "Mensal", "Realizar após o expediente uma vez por mês."),
    "Limpeza da Caixa de Gordura": ("Semanal", "Semanal", "Agendar entre quinta e sexta-feira."),
}

TASK_MAPPING = {
    "Limpeza Diária Geral": (
        "Limpeza Parcial da Câmara Fria",
        "15 dias",
        "Parcial",
        "Agendar em Terça/Quinta, evitando dias 1–4 do mês.",
    ),
    "Limpeza Parcial (Máquinas e Bancadas)": (
        "Limpeza Geral da Câmara Fria",
        "40 dias",
        "Geral",
        "Higienização completa: chão, paredes, paletes, prateleiras, barras.",
    ),
    "Limpeza Completa da Unidade": (
        "Limpeza de Expositores do Açougue",
        "Mensal",
        "Mensal",
        "Realizar após o expediente uma vez por mês.",
    ),
}

ALLOWED_TYPES = {"Parcial", "Geral", "Mensal", "Semanal"}
ALLOWED_FREQUENCIES = {"Semanal", "15 dias", "Mensal", "40 dias", "Trimestral", "Personalizada"}

# ============================================================================
# Funções auxiliares - Cálculo de datas
# ============================================================================


def aplicar_regras_data(d):
    """Aplica regras de ajuste de data (evitar dias 1-4 e fora de terça-sexta)"""
    motivos = []
    cur = d
    if cur.day in (1, 2, 3, 4):
        motivos.append("Ajuste: início do mês (1–4)")
        while cur.day in (1, 2, 3, 4):
            cur = cur + timedelta(days=1)
    if cur.weekday() not in (1, 2, 3, 4):  # 1=Terça, 2=Quarta, 3=Quinta, 4=Sexta
        motivos.append("Ajuste: fora de terça–sexta")
        while cur.weekday() not in (1, 2, 3, 4):
            cur = cur + timedelta(days=1)
    return cur, ", ".join(motivos)


def calcular_caixa_gordura(hoje, ultima_data):
    """Calcula próxima data para limpeza da caixa de gordura (quinta/sexta)"""
    wd = hoje.weekday()
    if wd <= 3:
        base = hoje + timedelta(days=(3 - wd))
    elif wd == 4:
        base = hoje
    else:
        base = hoje + timedelta(days=(7 - wd + 3))
    if base <= ultima_data:
        base = base + timedelta(days=7)
    return base


def calcular_frequencia_padrao(ultima_data, frequencia):
    """Calcula próxima data baseada em frequência padrão (sem regras especiais)"""
    if frequencia == "15 dias":
        return ultima_data + timedelta(days=15)
    elif frequencia == "40 dias":
        return ultima_data + timedelta(days=40)
    elif frequencia == "Semanal":
        return ultima_data + timedelta(weeks=1)
    elif frequencia == "Mensal":
        return ultima_data + timedelta(days=30)
    elif frequencia == "Trimestral":
        return ultima_data + timedelta(days=90)
    else:
        return ultima_data + timedelta(days=1)


def calcular_proxima_prevista(ultima_data, frequencia, tipo, nome=None):
    """Calcula a próxima data prevista para uma tarefa aplicando regras especiais"""
    hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).date()

    # Caso especial: Limpeza da Caixa de Gordura
    if (nome or "").strip().lower() == "limpeza da caixa de gordura":
        base = calcular_caixa_gordura(hoje, ultima_data)
        ajustada, _mot = aplicar_regras_data(base)
        return ajustada

    # Frequência personalizada
    if isinstance(frequencia, str) and frequencia.lower().startswith("personalizada"):
        try:
            num = int("".join([c for c in frequencia if c.isdigit()]))
        except Exception:
            num = 1
        base = ultima_data + timedelta(days=max(1, num))
        ajustada, _mot = aplicar_regras_data(base)
        return ajustada

    # Frequências padrão
    if frequencia == "15 dias":
        base = ultima_data + timedelta(days=15)
        ajustada, _mot = aplicar_regras_data(base)
        return ajustada if ajustada > hoje else aplicar_regras_data(hoje + timedelta(days=1))[0]

    if frequencia == "40 dias":
        base = ultima_data + timedelta(days=40)
        ajustada, _mot = aplicar_regras_data(base)
        return ajustada

    # Frequências que precisam de loop (Semanal, Mensal, Trimestral)
    proxima_base = datetime.combine(ultima_data, datetime.min.time())
    while True:
        if frequencia == "Semanal":
            proxima_base += timedelta(weeks=1)
        elif frequencia == "Mensal":
            proxima_base += timedelta(days=30)
        elif frequencia == "Trimestral":
            proxima_base += timedelta(days=90)
        else:
            proxima_base += timedelta(days=1)

        cand = proxima_base.date()
        if cand > hoje:
            ajustada, _mot = aplicar_regras_data(cand)
            return ajustada
        if cand > hoje + timedelta(days=365 * 5):
            ajustada, _ = aplicar_regras_data(ultima_data + timedelta(days=1))
            return ajustada


def proxima_base_sem_regra(ultima_data, frequencia, tipo, nome=None):
    """Calcula próxima data base sem aplicar regras de ajuste"""
    hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).date()

    if (nome or "").strip().lower() == "limpeza da caixa de gordura":
        return calcular_caixa_gordura(hoje, ultima_data)

    if isinstance(frequencia, str) and frequencia.lower().startswith("personalizada"):
        try:
            num = int("".join([c for c in frequencia if c.isdigit()]))
        except Exception:
            num = 1
        return ultima_data + timedelta(days=max(1, num))

    if frequencia in ("15 dias", "40 dias", "Semanal", "Mensal", "Trimestral"):
        return calcular_frequencia_padrao(ultima_data, frequencia)

    # Fallback
    proxima_base = datetime.combine(ultima_data, datetime.min.time())
    while True:
        proxima_base += timedelta(days=1)
        cand = proxima_base.date()
        if cand > hoje:
            return cand


# ============================================================================
# Funções auxiliares - Setup e migração
# ============================================================================


def _ensure_default_tasks():
    """Garante que as tarefas padrão existam no banco"""
    atualizados = False

    # Migração de nomes antigos para novos
    for antigo, novo in TASK_MAPPING.items():
        tarefa = CleaningTask.query.filter_by(nome_limpeza=antigo).first()
        if tarefa:
            tarefa.nome_limpeza = novo[0]
            tarefa.frequencia = novo[1]
            tarefa.tipo = novo[2]
            tarefa.observacao = novo[3]
            tarefa.proxima_data = calcular_proxima_prevista(
                tarefa.ultima_data, tarefa.frequencia, tarefa.tipo, tarefa.nome_limpeza
            )
            atualizados = True

    # Criar tarefas padrão se não existirem
    hoje = date.today()
    for nome, (freq, tipo, obs) in TASK_PADROES.items():
        tarefa = CleaningTask.query.filter_by(nome_limpeza=nome).first()
        if not tarefa:
            nova = CleaningTask()
            nova.nome_limpeza = nome
            nova.frequencia = freq
            nova.tipo = tipo
            nova.ultima_data = hoje - timedelta(days=1)
            nova.proxima_data = calcular_proxima_prevista(nova.ultima_data, freq, tipo, nome)
            nova.observacao = obs
            nova.designados = "Equipe de Limpeza"
            db.session.add(nova)
            atualizados = True
        else:
            # Preencher observação se faltando
            if not tarefa.observacao:
                tarefa.observacao = obs

    if atualizados:
        db.session.commit()

    return atualizados


def _calcular_ajustes_tarefas(tarefas):
    """Calcula ajustes aplicados às datas das tarefas"""
    ajustes = {}
    for t in tarefas:
        base = proxima_base_sem_regra(t.ultima_data, t.frequencia, t.tipo, t.nome_limpeza)
        parts = []
        if base.day in (1, 2, 3, 4):
            parts.append("ajuste: início do mês (1–4)")
        if base.weekday() not in (1, 2, 3, 4):
            parts.append("ajuste: fora de terça–sexta")
        if parts:
            ajustes[t.id] = " • ".join(parts)
    return ajustes


def _calcular_status_tarefas(tarefas):
    """Calcula status (normal, urgente, atrasada) para cada tarefa"""
    hoje = date.today()
    for t in tarefas:
        t.status = "normal"
        if t.proxima_data < hoje:
            t.status = "atrasada"
        elif t.proxima_data <= hoje + timedelta(days=3):
            t.status = "urgente"


def _calcular_kpis():
    """Calcula KPIs para o dashboard"""
    hoje = date.today()

    total_tarefas = CleaningTask.query.count()
    tarefas_atrasadas = CleaningTask.query.filter(CleaningTask.proxima_data < hoje).count()
    tarefas_proximas = CleaningTask.query.filter(
        CleaningTask.proxima_data >= hoje, CleaningTask.proxima_data <= hoje + timedelta(days=7)
    ).count()

    # Calcular concluídas no mês
    primeiro_dia_mes = hoje.replace(day=1)
    if hoje.month == 12:
        ultimo_dia_mes = hoje.replace(year=hoje.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        ultimo_dia_mes = hoje.replace(month=hoje.month + 1, day=1) - timedelta(days=1)

    concluidas_mes = CleaningHistory.query.filter(
        CleaningHistory.data_conclusao >= datetime.combine(primeiro_dia_mes, datetime.min.time()),
        CleaningHistory.data_conclusao <= datetime.combine(ultimo_dia_mes, datetime.max.time()),
    ).count()

    taxa_cumprimento = round((concluidas_mes / max(total_tarefas, 1)) * 100) if total_tarefas > 0 else 0

    return {
        "total": total_tarefas,
        "atrasadas": tarefas_atrasadas,
        "proximas": tarefas_proximas,
        "concluidas_mes": concluidas_mes,
        "taxa": min(taxa_cumprimento, 100),
    }


def _get_tarefas_filtradas(tipo_sel=None):
    """Busca tarefas com filtro opcional por tipo"""
    query = CleaningTask.query
    if tipo_sel and tipo_sel in ALLOWED_TYPES:
        query = query.filter(CleaningTask.tipo == tipo_sel)
    return query.order_by(CleaningTask.proxima_data.asc()).all()


def _get_historico_filtrado(page=1, htipo=None, per_page=5):
    """Busca histórico com filtros e paginação"""
    query = CleaningHistory.query

    if htipo and htipo in ALLOWED_TYPES:
        nomes_por_tipo = [n for n, (_, tipo, _) in TASK_PADROES.items() if tipo == htipo]
        if nomes_por_tipo:
            query = query.filter(CleaningHistory.nome_limpeza.in_(nomes_por_tipo))

    return query.order_by(CleaningHistory.data_conclusao.desc()).paginate(page=page, per_page=per_page, error_out=False)


def setup_cleaning_tasks():
    """Função legada - usar _ensure_default_tasks()"""
    return _ensure_default_tasks()


@bp.route("/cronograma", methods=["GET"])
@login_required
def cronograma():
    if current_user.nivel not in ["operador", "admin", "DEV"]:
        flash("Acesso negado. Apenas Operadores e Administradores podem visualizar o cronograma.", "danger")
        return redirect(url_for("estoque.index"))

    # Garantir que tarefas padrão existam
    _ensure_default_tasks()

    # Parâmetros de filtro
    tipo_sel = request.args.get("tipo", "").strip()
    page_hist = request.args.get("hpage", 1, type=int)
    htipo = request.args.get("htipo", "").strip()

    # Buscar dados
    tarefas = _get_tarefas_filtradas(tipo_sel)
    ajustes = _calcular_ajustes_tarefas(tarefas)
    _calcular_status_tarefas(tarefas)

    # Histórico
    hist_pag = _get_historico_filtrado(page_hist, htipo, per_page=5)

    # KPIs
    kpis = _calcular_kpis()

    hoje = date.today()

    return render_template(
        "cronograma.html",
        cronograma_tarefas=tarefas,
        historico_limpezas=hist_pag.items,
        historico_pagination=hist_pag,
        active_page="cronograma",
        htipo=htipo,
        ajustes=ajustes,
        tipo=tipo_sel,
        kpis=kpis,
        hoje=hoje,
    )


@bp.route("/cronograma/salvar", methods=["POST"])
@login_required
def salvar_cronograma():
    if current_user.nivel not in ("admin", "DEV"):
        flash("Apenas Gerente (Admin) pode concluir e atualizar o cronograma.", "danger")
        return redirect(url_for("cronograma.cronograma"))
    concluir_id = request.form.get("concluir_id")
    alterar_id = request.form.get("alterar_id")
    nova_freq = request.form.get("nova_frequencia", "").strip()
    nova_dias = request.form.get("nova_dias", "").strip()
    if alterar_id and nova_freq:
        try:
            task_id = int(alterar_id)
            tarefa = CleaningTask.query.get_or_404(task_id)
            allowed = {"Semanal", "15 dias", "Mensal", "40 dias", "Trimestral", "Personalizada"}
            if nova_freq not in allowed:
                flash("Frequência inválida.", "danger")
                return redirect(url_for("cronograma.cronograma"))
            if nova_freq == "Personalizada":
                try:
                    nd = int(nova_dias)
                except Exception:
                    nd = 0
                if nd <= 0:
                    flash("Dias personalizados inválidos.", "danger")
                    return redirect(url_for("cronograma.cronograma"))
                tarefa.frequencia = f"Personalizada {nd} dias"
            else:
                tarefa.frequencia = nova_freq
            tarefa.proxima_data = calcular_proxima_prevista(
                tarefa.ultima_data, tarefa.frequencia, tarefa.tipo, tarefa.nome_limpeza
            )
            db.session.commit()
            flash("Frequência atualizada.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao atualizar frequência: {e}", "danger")
        return redirect(url_for("cronograma.cronograma"))
    if concluir_id:
        try:
            task_id = int(concluir_id)
            tarefa = CleaningTask.query.get_or_404(task_id)
            observacao = (request.form.get(f"obs_{task_id}", "") or "").strip()
            designados = (request.form.get(f"participantes_{task_id}", None) or current_user.name or "").strip()
            data_conclusao_str = (request.form.get("data_conclusao", "") or "").strip()
            hist = CleaningHistory()
            hist.nome_limpeza = tarefa.nome_limpeza
            hist.observacao = observacao if observacao else "Sem observações."
            hist.designados = designados if designados else (current_user.name or "")
            hist.usuario_conclusao = current_user.name
            if data_conclusao_str:
                try:
                    dtc = datetime.strptime(data_conclusao_str, "%Y-%m-%d").replace(
                        tzinfo=ZoneInfo("America/Sao_Paulo")
                    )
                    hist.data_conclusao = dtc
                    tarefa.ultima_data = dtc.date()
                except Exception:
                    tarefa.ultima_data = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
            else:
                tarefa.ultima_data = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
            db.session.add(hist)
            tarefa.proxima_data = calcular_proxima_prevista(
                tarefa.ultima_data, tarefa.frequencia, tarefa.tipo, tarefa.nome_limpeza
            )
            tarefa.observacao = observacao if observacao else tarefa.observacao
            tarefa.designados = designados if designados else tarefa.designados
            db.session.commit()
            msg = (
                f'Limpeza "{tarefa.nome_limpeza}" marcada como concluída e reagendada para '
                f'{tarefa.proxima_data.strftime("%d/%m/%Y")}.'
            )
            flash(
                msg,
                "success",
            )
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao concluir a tarefa de limpeza: {e}", "danger")
    return redirect(url_for("cronograma.cronograma"))


@bp.route("/cronograma/historico/excluir/<int:id>", methods=["POST"])
@login_required
def excluir_historico(id: int):
    if current_user.nivel not in ("admin", "DEV"):
        flash("Apenas Gerente pode excluir histórico.", "danger")
        return redirect(url_for("cronograma.cronograma"))
    h = CleaningHistory.query.get_or_404(id)
    try:
        db.session.delete(h)
        db.session.commit()
        flash("Histórico excluído.", "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao excluir histórico: {e}", "danger")
    return redirect(url_for("cronograma.cronograma"))


@bp.route("/cronograma/api/calendario", methods=["GET"])
@login_required
def api_calendario():
    ano = request.args.get("ano", date.today().year, type=int)
    mes = request.args.get("mes", date.today().month, type=int)

    primeiro_dia = date(ano, mes, 1)
    if mes == 12:
        ultimo_dia = date(ano + 1, 1, 1) - timedelta(days=1)
    else:
        ultimo_dia = date(ano, mes + 1, 1) - timedelta(days=1)

    tarefas = CleaningTask.query.filter(
        CleaningTask.proxima_data >= primeiro_dia, CleaningTask.proxima_data <= ultimo_dia
    ).all()

    historico = CleaningHistory.query.filter(
        CleaningHistory.data_conclusao >= datetime.combine(primeiro_dia, datetime.min.time()),
        CleaningHistory.data_conclusao <= datetime.combine(ultimo_dia, datetime.max.time()),
    ).all()

    eventos = []
    cores = {"Parcial": "#3b82f6", "Geral": "#ef4444", "Mensal": "#f59e0b", "Semanal": "#22c55e"}
    hoje = date.today()

    for t in tarefas:
        cor = cores.get(t.tipo, "#6b7280")
        if t.proxima_data < hoje:
            cor = "#dc2626"
        eventos.append(
            {
                "id": f"task_{t.id}",
                "title": t.nome_limpeza,
                "start": t.proxima_data.isoformat(),
                "color": cor,
                "tipo": t.tipo,
                "status": "atrasada" if t.proxima_data < hoje else "pendente",
            }
        )

    for h in historico:
        eventos.append(
            {
                "id": f"hist_{h.id}",
                "title": f"✓ {h.nome_limpeza}",
                "start": h.data_conclusao.date().isoformat(),
                "color": "#10b981",
                "status": "concluida",
            }
        )

    return jsonify({"eventos": eventos, "ano": ano, "mes": mes})


@bp.route("/cronograma/api/checklist/<tipo>", methods=["GET"])
@login_required
def api_checklist(tipo):
    items = CleaningChecklistTemplate.query.filter_by(tipo=tipo).order_by(CleaningChecklistTemplate.ordem).all()
    return jsonify({"items": [{"id": i.id, "texto": i.item_texto, "obrigatorio": i.obrigatorio} for i in items]})


@bp.route("/cronograma/concluir-completo", methods=["POST"])
@login_required
def concluir_completo():
    if current_user.nivel not in ("operador", "admin", "DEV"):
        flash("Sem permissão.", "danger")
        return redirect(url_for("cronograma.cronograma"))

    task_id = request.form.get("task_id", type=int)
    tarefa = CleaningTask.query.get_or_404(task_id)

    observacao = (request.form.get("observacao", "") or "").strip()
    designados = (request.form.get("designados", "") or current_user.name).strip()
    duracao = request.form.get("duracao", type=int)
    qualidade = request.form.get("qualidade", 5, type=int)
    data_str = request.form.get("data_conclusao", "").strip()

    try:
        hist = CleaningHistory()
        hist.task_id = task_id
        hist.nome_limpeza = tarefa.nome_limpeza
        hist.observacao = observacao or "Sem observações"
        hist.designados = designados
        hist.usuario_conclusao = current_user.name
        hist.duracao_minutos = duracao
        hist.qualidade = qualidade

        if data_str:
            try:
                dt = datetime.strptime(data_str, "%Y-%m-%d").replace(tzinfo=ZoneInfo("America/Sao_Paulo"))
                hist.data_conclusao = dt
                tarefa.ultima_data = dt.date()
            except Exception:
                tarefa.ultima_data = date.today()
        else:
            tarefa.ultima_data = date.today()

        db.session.add(hist)
        db.session.flush()

        checklist_items = request.form.getlist("checklist")
        templates = CleaningChecklistTemplate.query.filter_by(tipo=tarefa.tipo).all()
        for tmpl in templates:
            item = CleaningChecklistItem()
            item.history_id = hist.id
            item.item_texto = tmpl.item_texto
            item.concluido = str(tmpl.id) in checklist_items
            if item.concluido:
                item.concluido_por = current_user.name
                item.concluido_em = datetime.now(ZoneInfo("America/Sao_Paulo"))
            db.session.add(item)

        upload_folder = os.path.join("static", "uploads", "limpeza")
        os.makedirs(upload_folder, exist_ok=True)

        for tipo_foto in ["antes", "depois"]:
            files = request.files.getlist(f"foto_{tipo_foto}")
            for f in files:
                if f and f.filename:
                    filename = secure_filename(
                        f'{hist.id}_{tipo_foto}_{datetime.now().strftime("%Y%m%d%H%M%S")}_{f.filename}'
                    )
                    filepath = os.path.join(upload_folder, filename)
                    f.save(filepath)

                    photo = CleaningHistoryPhoto()
                    photo.history_id = hist.id
                    photo.filename = filename
                    photo.tipo = tipo_foto
                    photo.uploaded_by = current_user.name
                    db.session.add(photo)

        tarefa.proxima_data = calcular_proxima_prevista(
            tarefa.ultima_data, tarefa.frequencia, tarefa.tipo, tarefa.nome_limpeza
        )
        db.session.commit()

        flash(f'Limpeza "{tarefa.nome_limpeza}" concluída com sucesso!', "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao concluir: {e}", "danger")

    return redirect(url_for("cronograma.cronograma"))


@bp.route("/cronograma/api/estatisticas", methods=["GET"])
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
            CleaningHistory.data_conclusao <= datetime.combine(ultimo, datetime.max.time()),
        ).count()

        meses.append({"mes": primeiro.strftime("%b"), "concluidas": concluidas})

    return jsonify({"meses": meses})
