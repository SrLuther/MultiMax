"""
Rotas para Estoque de Produção com Previsão de Uso
Controla produtos produzidos e estocados internamente com previsão de uso futuro
"""

from datetime import datetime
from io import BytesIO
from zoneinfo import ZoneInfo

from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from sqlalchemy import func, or_

from .. import db
from ..models import EstoqueProducao, HistoricoAjusteEstoque, Produto, Setor

bp = Blueprint("estoque_producao", __name__, url_prefix="/estoque-producao")


def _require_permission():
    """Verifica se o usuário tem permissão para acessar o módulo"""
    if not current_user.is_authenticated:
        return False
    return current_user.nivel in ["admin", "DEV"]


def _pdf_new_page(pdf: canvas.Canvas, title: str, generated_at: str, margin: float) -> float:
    """Renderiza cabeçalho padrão e retorna o Y inicial da página."""
    width, height = A4
    pdf.setFillColor(colors.HexColor("#0f172a"))
    pdf.rect(0, height - 52, width, 52, stroke=0, fill=1)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(margin, height - 22, title)
    pdf.setFont("Helvetica", 10)
    pdf.drawString(margin, height - 38, generated_at)
    pdf.setStrokeColor(colors.HexColor("#10b981"))
    pdf.setLineWidth(2)
    pdf.line(margin, height - 54, width - margin, height - 54)
    return height - 72


# ============================================================================
# Rota Principal - Listagem
# ============================================================================


@bp.route("/", methods=["GET"])
@login_required
def index():
    """Página principal do estoque de produção"""
    if not _require_permission():
        flash("Você não tem permissão para acessar este módulo.", "danger")
        return redirect(url_for("home.index"))

    # Filtros
    filtro_produto = request.args.get("produto", "").strip()
    filtro_setor = request.args.get("setor", "").strip()
    filtro_previsao = request.args.get("previsao", "").strip()
    filtro_data_ini = request.args.get("data_ini", "").strip()
    filtro_data_fim = request.args.get("data_fim", "").strip()

    # Query base
    query = EstoqueProducao.query.filter_by(ativo=True)

    # Aplicar filtros
    if filtro_produto:
        query = query.join(Produto).filter(
            or_(Produto.nome.ilike(f"%{filtro_produto}%"), Produto.codigo.ilike(f"%{filtro_produto}%"))
        )

    if filtro_setor:
        query = query.filter_by(setor_id=int(filtro_setor))

    if filtro_previsao:
        query = query.filter(EstoqueProducao.previsao_uso.ilike(f"%{filtro_previsao}%"))

    if filtro_data_ini:
        try:
            data_ini = datetime.strptime(filtro_data_ini, "%Y-%m-%d").date()
            query = query.filter(func.date(EstoqueProducao.data_registro) >= data_ini)
        except ValueError:
            pass

    if filtro_data_fim:
        try:
            data_fim = datetime.strptime(filtro_data_fim, "%Y-%m-%d").date()
            query = query.filter(func.date(EstoqueProducao.data_registro) <= data_fim)
        except ValueError:
            pass

    # Ordenação
    estoques = query.order_by(EstoqueProducao.data_registro.desc()).all()

    # Buscar produtos e setores para os selects
    produtos = Produto.query.filter_by(ativo=True).order_by(Produto.nome).all()
    setores = Setor.query.filter_by(ativo=True).order_by(Setor.nome).all()

    # Estatísticas rápidas
    total_registros = len(estoques)
    total_quantidade = sum(e.quantidade for e in estoques)
    produtos_unicos = len(set(e.produto_id for e in estoques))

    return render_template(
        "estoque_producao.html",
        estoques=estoques,
        produtos=produtos,
        setores=setores,
        total_registros=total_registros,
        total_quantidade=total_quantidade,
        produtos_unicos=produtos_unicos,
        filtro_produto=filtro_produto,
        filtro_setor=filtro_setor,
        filtro_previsao=filtro_previsao,
        filtro_data_ini=filtro_data_ini,
        filtro_data_fim=filtro_data_fim,
    )


@bp.route("/pdf", methods=["GET"])
@login_required
def exportar_pdf():
    """Gera um PDF com visão profissional do estoque de produção."""
    if not _require_permission():
        flash("Você não tem permissão para acessar este recurso.", "danger")
        return redirect(url_for("estoque_producao.index"))

    estoques = (
        EstoqueProducao.query.filter_by(ativo=True)
        .join(Produto)
        .order_by(Produto.nome.asc(), EstoqueProducao.data_previsao.asc())
        .all()
    )
    setores = {s.id: s.nome for s in Setor.query.filter_by(ativo=True).all()}

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    margin = 18 * mm
    width, _ = A4
    generated_at = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("Gerado em %d/%m/%Y %H:%M")
    y = _pdf_new_page(pdf, "Estoque de Produção", generated_at, margin)

    def _maybe_paginate(y_pos: float) -> float:
        if y_pos < margin + 40:
            pdf.showPage()
            return _pdf_new_page(pdf, "Estoque de Produção", generated_at, margin)
        return y_pos

    def _draw_stats(y_pos: float) -> float:
        total_registros = len(estoques)
        total_quantidade = sum(e.quantidade for e in estoques)
        produtos_unicos = len({e.produto_id for e in estoques})
        pdf.setFillColor(colors.HexColor("#10b981"))
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(margin, y_pos, "Visão Geral")
        pdf.setFont("Helvetica", 10)
        pdf.setFillColor(colors.black)
        y_line = y_pos - 14
        pdf.drawString(margin, y_line, f"Registros ativos: {total_registros}")
        pdf.drawString(margin + 180, y_line, f"Quantidade total: {total_quantidade:0.2f}")
        pdf.drawString(margin + 360, y_line, f"Produtos únicos: {produtos_unicos}")
        return y_line - 18

    def _draw_table_header(y_pos: float) -> float:
        headers = ["Produto", "Setor", "Qtd", "Previsão", "Data Prev.", "Observação"]
        col_widths = [150, 90, 40, 90, 70, 120]
        pdf.setFillColor(colors.HexColor("#0f172a"))
        pdf.rect(margin, y_pos - 14, sum(col_widths), 18, fill=1, stroke=0)
        pdf.setFont("Helvetica-Bold", 10)
        pdf.setFillColor(colors.white)
        x = margin + 4
        for header, w in zip(headers, col_widths):
            pdf.drawString(x, y_pos - 2, header)
            x += w
        return y_pos - 24

    def _draw_row(y_pos: float, estoque: EstoqueProducao) -> float:
        pdf.setFont("Helvetica", 9)
        pdf.setFillColor(colors.black)
        col_widths = [150, 90, 40, 90, 70, 120]
        values = [
            estoque.produto.nome if estoque.produto else "-",
            setores.get(estoque.setor_id, "-"),
            f"{estoque.quantidade:0.2f}",
            estoque.previsao_uso or "-",
            estoque.data_previsao.strftime("%d/%m/%Y") if estoque.data_previsao else "-",
            (estoque.observacao or "").strip(),
        ]

        def _short(text: str, limit: int = 70) -> str:
            t = (text or "").strip()
            return (t[: limit - 3] + "...") if len(t) > limit else t

        values[-1] = _short(values[-1])

        x = margin + 4
        for val, w in zip(values, col_widths):
            pdf.drawString(x, y_pos, val)
            x += w
        pdf.setStrokeColor(colors.HexColor("#e5e7eb"))
        pdf.line(margin, y_pos - 4, margin + sum(col_widths), y_pos - 4)
        return y_pos - 18

    y = _draw_stats(_maybe_paginate(y))
    y = _draw_table_header(_maybe_paginate(y))

    if not estoques:
        pdf.setFillColor(colors.black)
        pdf.setFont("Helvetica", 11)
        pdf.drawString(margin, y, "Nenhum registro ativo encontrado.")
    else:
        for estoque in estoques:
            y = _maybe_paginate(y)
            y = _draw_row(y, estoque)

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    filename = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("estoque-producao-%Y%m%d-%H%M.pdf")
    return send_file(buffer, download_name=filename, mimetype="application/pdf", as_attachment=True)


# ============================================================================
# Criar Registro
# ============================================================================


@bp.route("/criar", methods=["POST"])
@login_required
def criar():
    """Cria um novo registro de estoque de produção"""
    if not _require_permission():
        flash("Você não tem permissão para realizar esta ação.", "danger")
        return redirect(url_for("estoque_producao.index"))

    try:
        produto_id = int(request.form.get("produto_id", 0))
        quantidade = float(request.form.get("quantidade", 0))
        setor_id = int(request.form.get("setor_id", 0))
        previsao_uso = request.form.get("previsao_uso", "").strip()
        data_previsao = request.form.get("data_previsao", "").strip()
        observacao = request.form.get("observacao", "").strip()

        # Validações
        if not produto_id or not setor_id:
            flash("Produto e setor são obrigatórios.", "warning")
            return redirect(url_for("estoque_producao.index"))

        if quantidade < 0:
            flash("A quantidade não pode ser negativa.", "warning")
            return redirect(url_for("estoque_producao.index"))

        # Criar registro
        estoque = EstoqueProducao()
        estoque.produto_id = produto_id
        estoque.quantidade = quantidade
        estoque.setor_id = setor_id
        estoque.previsao_uso = previsao_uso or None
        estoque.data_previsao = datetime.strptime(data_previsao, "%Y-%m-%d").date() if data_previsao else None
        estoque.observacao = observacao or None
        estoque.criado_por = current_user.name
        estoque.data_registro = datetime.now(ZoneInfo("America/Sao_Paulo"))

        db.session.add(estoque)
        db.session.flush()  # Para obter o ID

        # Criar histórico inicial
        historico = HistoricoAjusteEstoque()
        historico.estoque_id = estoque.id
        historico.tipo_ajuste = "entrada"
        historico.quantidade_anterior = 0
        historico.quantidade_ajuste = quantidade
        historico.quantidade_nova = quantidade
        historico.motivo = "Registro inicial de estoque"
        historico.ajustado_por = current_user.name
        db.session.add(historico)
        db.session.commit()

        flash("Registro de estoque criado com sucesso!", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao criar registro: {str(e)}", "danger")

    return redirect(url_for("estoque_producao.index"))


# ============================================================================
# Ajustar Quantidade
# ============================================================================


@bp.route("/<int:id>/ajustar", methods=["POST"])
@login_required
def ajustar(id):
    """Ajusta a quantidade de um registro de estoque"""
    if not _require_permission():
        flash("Você não tem permissão para realizar esta ação.", "danger")
        return redirect(url_for("estoque_producao.index"))

    estoque = EstoqueProducao.query.get_or_404(id)

    try:
        tipo_ajuste = request.form.get("tipo_ajuste", "").strip()
        quantidade_ajuste = float(request.form.get("quantidade_ajuste", 0))
        motivo = request.form.get("motivo", "").strip()

        # Validações
        if tipo_ajuste not in ["entrada", "saida", "correcao"]:
            flash("Tipo de ajuste inválido.", "warning")
            return redirect(url_for("estoque_producao.index"))

        if not motivo:
            flash("Motivo do ajuste é obrigatório.", "warning")
            return redirect(url_for("estoque_producao.index"))

        # Calcula nova quantidade
        quantidade_anterior = estoque.quantidade

        if tipo_ajuste == "entrada":
            quantidade_nova = quantidade_anterior + quantidade_ajuste
        elif tipo_ajuste == "saida":
            quantidade_nova = quantidade_anterior - quantidade_ajuste
        else:  # correcao
            quantidade_nova = quantidade_ajuste

        # Verifica se não fica negativo
        if quantidade_nova < 0:
            flash("A quantidade não pode ficar negativa.", "warning")
            return redirect(url_for("estoque_producao.index"))

        # Atualiza estoque
        estoque.quantidade = quantidade_nova

        # Registra histórico
        historico = HistoricoAjusteEstoque()
        historico.estoque_id = estoque.id
        historico.tipo_ajuste = tipo_ajuste
        historico.quantidade_anterior = quantidade_anterior
        historico.quantidade_ajuste = (
            quantidade_ajuste if tipo_ajuste != "correcao" else (quantidade_nova - quantidade_anterior)
        )
        historico.quantidade_nova = quantidade_nova
        historico.motivo = motivo
        historico.ajustado_por = current_user.name
        db.session.add(historico)
        db.session.commit()

        flash(f"Ajuste de {tipo_ajuste} realizado com sucesso!", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao ajustar quantidade: {str(e)}", "danger")

    return redirect(url_for("estoque_producao.index"))


# ============================================================================
# Editar Registro
# ============================================================================


@bp.route("/<int:id>/editar", methods=["POST"])
@login_required
def editar(id):
    """Edita as informações de um registro (exceto quantidade)"""
    if not _require_permission():
        flash("Você não tem permissão para realizar esta ação.", "danger")
        return redirect(url_for("estoque_producao.index"))

    estoque = EstoqueProducao.query.get_or_404(id)

    try:
        estoque.previsao_uso = request.form.get("previsao_uso", "").strip() or None
        data_previsao = request.form.get("data_previsao", "").strip()
        estoque.data_previsao = datetime.strptime(data_previsao, "%Y-%m-%d").date() if data_previsao else None
        estoque.observacao = request.form.get("observacao", "").strip() or None

        db.session.commit()
        flash("Registro atualizado com sucesso!", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao editar registro: {str(e)}", "danger")

    return redirect(url_for("estoque_producao.index"))


# ============================================================================
# Excluir Registro
# ============================================================================


@bp.route("/<int:id>/excluir", methods=["POST"])
@login_required
def excluir(id):
    """Marca um registro como inativo (soft delete)"""
    if not _require_permission():
        flash("Você não tem permissão para realizar esta ação.", "danger")
        return redirect(url_for("estoque_producao.index"))

    estoque = EstoqueProducao.query.get_or_404(id)

    try:
        estoque.ativo = False
        db.session.commit()
        flash("Registro removido com sucesso!", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao remover registro: {str(e)}", "danger")

    return redirect(url_for("estoque_producao.index"))


# ============================================================================
# Histórico de Ajustes
# ============================================================================


@bp.route("/<int:id>/historico", methods=["GET"])
@login_required
def historico(id):
    """Retorna o histórico de ajustes de um registro"""
    if not _require_permission():
        flash("Você não tem permissão para acessar este recurso.", "danger")
        return redirect(url_for("estoque_producao.index"))

    estoque = EstoqueProducao.query.get_or_404(id)
    historicos = (
        HistoricoAjusteEstoque.query.filter_by(estoque_id=id).order_by(HistoricoAjusteEstoque.data_ajuste.desc()).all()
    )

    return render_template(
        "estoque_producao_historico.html",
        estoque=estoque,
        historicos=historicos,
    )
