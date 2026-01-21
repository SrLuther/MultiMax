"""
Módulo Unificado: Estoque de Produção e Produtos
Combina:
- Gestão de produtos gerais (Modelo: Produto)
- Estoque de produção com previsão de uso (Modelo: EstoqueProducao)
"""

import io
import logging
from datetime import date, datetime
from io import BytesIO
from typing import cast
from zoneinfo import ZoneInfo

import qrcode  # type: ignore
from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from qrcode.constants import ERROR_CORRECT_L  # type: ignore
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from sqlalchemy import func, or_

from .. import db
from ..models import EstoqueProducao, Historico, HistoricoAjusteEstoque, Produto, Setor
from ..services.notificacao_service import registrar_evento

# Usar URL prefix vazio para manter retrocompat com /estoque
bp = Blueprint("estoque_producao", __name__)


# ============================================================================
# Constantes e Helpers
# ============================================================================

ALLOWED_CATEGORIES = {"CX", "PC", "VA", "AV"}


def _check_roles(allowed: tuple[str, ...], message: str, endpoint: str = "estoque_producao.index"):
    """Valida nível de acesso e retorna redirect se não autorizado."""
    if current_user.nivel not in allowed:
        flash(message, "danger")
        return redirect(url_for(endpoint))
    return None


def _parse_int_safe(value: str | None, default: int | None = 0) -> int | None:
    try:
        return int(value or "")
    except (ValueError, TypeError):
        return default


def _gerar_codigo_categoria(pref: str) -> str:
    existentes = cast(
        list[tuple[str]], Produto.query.with_entities(Produto.codigo).filter(Produto.codigo.like(f"{pref}-%")).all()
    )
    maior = 0
    for (cod,) in existentes:
        try:
            sufixo = cod.split("-", 1)[1]
            num = int(sufixo)
            if num > maior:
                maior = num
        except Exception:
            continue
    return f"{pref}-{maior+1:04d}"


def _criar_historico(produto: Produto, action: str, quantidade: int, details: str):
    try:
        hist = Historico()
        hist.product_id = produto.id
        hist.product_name = produto.nome
        hist.action = action
        hist.quantidade = quantidade
        hist.details = details
        hist.usuario = current_user.username
        db.session.add(hist)
        try:
            registrar_evento(
                "entrada de estoque" if action == "entrada" else "saída de estoque",
                produto=produto.nome,
                quantidade=quantidade,
                descricao=hist.details,
            )
        except Exception:
            pass
    except Exception as e:
        db.session.rollback()
        logging.getLogger(__name__).error(f"Erro ao registrar movimentação de estoque: {e}", exc_info=True)
        flash(f"Erro ao registrar movimentação: {e}", "danger")
    return redirect(url_for("estoque_producao.index"))


def _processar_movimentacao(produto: Produto, op: str):
    qtd_str = request.form.get("quantidade", "0") or "0"
    try:
        quantidade = int(qtd_str)
    except (ValueError, TypeError):
        flash("Quantidade inválida.", "danger")
        return redirect(url_for("estoque_producao.index"))
    if quantidade <= 0:
        flash("A quantidade deve ser maior que zero.", "warning")
        return redirect(url_for("estoque_producao.index"))
    try:
        if op == "saida" and produto.quantidade < quantidade:
            flash(f"Saída de {quantidade} excede estoque atual ({produto.quantidade}).", "warning")
            return redirect(url_for("estoque_producao.index"))
        produto.quantidade += quantidade if op == "entrada" else -quantidade
        hist = Historico()
        hist.product_id = produto.id
        hist.product_name = produto.nome
        hist.action = op
        hist.quantidade = quantidade
        hist.details = (request.form.get("detalhes") or "").strip() or (
            "Entrada de estoque" if op == "entrada" else "Saída de estoque"
        )
        hist.usuario = current_user.username
        db.session.add(hist)
        db.session.commit()
        flash(
            f"{'Entrada' if op == 'entrada' else 'Saída'} de {quantidade} unidades registrada.",
            "primary" if op == "entrada" else "warning",
        )
        try:
            registrar_evento(
                "entrada de estoque" if op == "entrada" else "saída de estoque",
                produto=produto.nome,
                quantidade=quantidade,
                descricao=hist.details,
            )
        except Exception:
            pass
    except Exception as e:
        db.session.rollback()
        logging.getLogger(__name__).error(f"Erro ao registrar movimentação de estoque: {e}", exc_info=True)
        flash(f"Erro ao registrar movimentação: {e}", "danger")
    return redirect(url_for("estoque_producao.index"))


def _processar_exclusao(produto: Produto):
    if current_user.nivel not in ("admin", "DEV"):
        flash("Você não tem permissão para excluir produtos.", "danger")
        return redirect(url_for("estoque_producao.index"))
    try:
        Historico.query.filter_by(product_id=produto.id).delete()
        db.session.delete(produto)
        db.session.commit()
        flash(f'Produto "{produto.nome}" excluído.', "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao excluir produto: {e}", "danger")
    return redirect(url_for("estoque_producao.index"))


def _parse_date_safe(s: str) -> date | None:
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


def _fetch_hist(prod_id: int, start_date: date | None = None) -> list[Historico]:
    query = Historico.query.filter_by(product_id=prod_id)
    if start_date:
        query = query.filter(Historico.data >= datetime.combine(start_date, datetime.min.time()))
    return query.order_by(Historico.data.asc()).all()


def _get_produtos_filtrados(search: str, cat: str, page: int, per_page: int = 12):
    query = Produto.query
    if search:
        query = query.filter(or_(Produto.nome.ilike(f"%{search}%"), Produto.codigo.ilike(f"%{search}%")))
    if cat:
        query = query.filter(Produto.categoria == cat)
    return query.order_by(Produto.nome.asc()).paginate(page=page, per_page=per_page, error_out=False)


def _get_historico_code_map(historicos):
    pids = {h.product_id for h in historicos if h.product_id}
    if not pids:
        return {}
    produtos = Produto.query.filter(Produto.id.in_(pids)).all()
    return {p.id: p.codigo for p in produtos}


def _get_produto_por_busca(busca: str, g_id: int | None):
    if g_id:
        prod = Produto.query.filter_by(id=g_id).first()
        return prod, []
    if busca:
        resultados = (
            Produto.query.filter(or_(Produto.nome.ilike(f"%{busca}%"), Produto.codigo.ilike(f"%{busca}%")))
            .limit(10)
            .all()
        )
        return None, resultados
    return None, []


def _get_produto_graficos(produto: Produto | None, g_di: date | None, g_df: date | None):
    if not produto:
        return {}
    historicos = _fetch_hist(produto.id, g_di)
    if not historicos:
        return {}
    final = {
        "labels": [],
        "entradas": [],
        "saidas": [],
        "estoque": [],
    }
    quantidade_acumulada = 0
    for h in historicos:
        if g_df and h.data.date() > g_df:
            continue
        label_data = h.data.strftime("%d/%m/%Y")
        if h.action == "entrada":
            quantidade_acumulada += h.quantidade
            final["entradas"].append({"x": label_data, "y": h.quantidade})
        elif h.action == "saida":
            quantidade_acumulada -= h.quantidade
            final["saidas"].append({"x": label_data, "y": h.quantidade})
        final["labels"].append(label_data)
        final["estoque"].append({"x": label_data, "y": quantidade_acumulada})
    return final


def _require_permission():
    if not current_user.is_authenticated:
        return False
    return current_user.nivel in ["admin", "DEV"]


def _pdf_new_page(pdf: canvas.Canvas, title: str, generated_at: str, margin: float) -> float:
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
# Rotas - Página Principal Unificada (Tudo em Uma Página)
# ============================================================================


@bp.route("/")
@bp.route("/estoque")
@bp.route("/estoque-unificado")
@login_required
def index():
    """Página unificada: Produtos + Estoque Geral + Estoque de Produção em abas"""
    search_term = request.args.get("busca", "")
    page = request.args.get("page", 1, type=int)
    ppage = request.args.get("ppage", 1, type=int)
    cat = request.args.get("cat", "").strip().upper()

    # Dados de Produtos e Histórico
    produtos_pag = _get_produtos_filtrados(search_term, cat, ppage, per_page=12)
    produtos_all = Produto.query.order_by(Produto.nome.asc()).limit(100).all() if not search_term and not cat else []
    historico = Historico.query.order_by(Historico.data.desc()).paginate(page=page, per_page=10, error_out=False)
    code_map = _get_historico_code_map(historico.items)

    # Gráficos
    gq = request.args.get("gq", "").strip()
    g_produto_id = request.args.get("g_produto_id", type=int)
    g_data_inicio_str = request.args.get("g_data_inicio", "").strip()
    g_data_fim_str = request.args.get("g_data_fim", "").strip()

    g_produto, g_resultados = _get_produto_por_busca(gq, g_produto_id)
    g_di = _parse_date_safe(g_data_inicio_str)
    g_df = _parse_date_safe(g_data_fim_str)
    if g_di and g_df and g_di > g_df:
        g_di, g_df = g_df, g_di

    charts_g = _get_produto_graficos(g_produto, g_di, g_df)

    # Dados de Estoque de Produção (para aba adicional)
    filtro_produto_prod = request.args.get("produto_prod", "").strip()
    filtro_setor = request.args.get("setor", "").strip()

    query_producao = EstoqueProducao.query.filter_by(ativo=True)
    if filtro_produto_prod:
        query_producao = query_producao.join(Produto).filter(
            or_(Produto.nome.ilike(f"%{filtro_produto_prod}%"), Produto.codigo.ilike(f"%{filtro_produto_prod}%"))
        )
    if filtro_setor:
        query_producao = query_producao.filter_by(setor_id=int(filtro_setor))

    estoques_producao = query_producao.order_by(EstoqueProducao.data_registro.desc()).limit(50).all()
    setores = Setor.query.filter_by(ativo=True).order_by(Setor.nome).all()

    total_producao = sum(e.quantidade for e in estoques_producao) if estoques_producao else 0

    return render_template(
        "index.html",
        produtos_pag=produtos_pag,
        produtos_all=produtos_all,
        historico=historico,
        busca=search_term,
        cat=cat,
        hist_code_map=code_map,
        active_page="index",
        gq=gq,
        g_resultados=g_resultados,
        g_produto=g_produto,
        charts_g=charts_g,
        g_data_inicio=g_data_inicio_str,
        g_data_fim=g_data_fim_str,
        # Dados do Estoque de Produção
        estoques_producao=estoques_producao,
        setores=setores,
        total_producao=total_producao,
        filtro_produto_prod=filtro_produto_prod,
        filtro_setor=filtro_setor,
    )


# ============================================================================
# Rotas - Produtos (Listagem e Gestão Completa)
# ============================================================================


@bp.route("/produtos")
@login_required
def lista_produtos():
    produtos: list[Produto] = Produto.query.order_by(Produto.nome.asc()).all()
    return render_template("produtos.html", produtos=produtos, active_page="index")


@bp.route("/produtos/adicionar", methods=["POST"])
@login_required
def adicionar_produto():
    if current_user.nivel == "visualizador":
        flash("Visualizadores não têm permissão para fazer alterações no sistema.", "danger")
        return redirect(url_for("estoque_producao.lista_produtos"))
    categoria = request.form.get("categoria", "AV").strip().upper()
    prefix_map = {"CX": "CX", "PC": "PC", "VA": "VA", "AV": "AV"}
    prefix = prefix_map.get(categoria, "AV")
    codigo = _gerar_codigo_categoria(prefix)
    nome = request.form.get("nome")
    try:
        quantidade = int(request.form.get("quantidade", "0"))
    except Exception:
        quantidade = 0
    estoque_minimo = int(request.form.get("estoque_minimo", "0"))
    preco_custo = float(request.form.get("preco_custo", "0"))
    preco_venda = float(request.form.get("preco_venda", "0"))
    novo = Produto()
    novo.codigo = codigo
    novo.nome = nome
    novo.quantidade = quantidade
    novo.estoque_minimo = estoque_minimo
    novo.preco_custo = preco_custo
    novo.preco_venda = preco_venda
    db.session.add(novo)
    db.session.commit()
    if quantidade > 0:
        hist = Historico()
        hist.product_id = novo.id
        hist.product_name = novo.nome
        hist.action = "entrada"
        hist.quantidade = quantidade
        hist.details = "Cadastro inicial"
        hist.usuario = current_user.username
        db.session.add(hist)
        db.session.commit()
        registrar_evento("entrada de estoque", produto=novo.nome, quantidade=quantidade, descricao="Cadastro inicial")
    flash("Produto cadastrado com sucesso!", "success")
    return redirect(url_for("estoque_producao.lista_produtos"))


@bp.route("/produtos/editar/<int:id>", methods=["POST"])
@login_required
def editar_produto(id: int):
    if current_user.nivel == "visualizador":
        flash("Visualizadores não têm permissão para fazer alterações no sistema.", "danger")
        return redirect(url_for("estoque_producao.lista_produtos"))
    produto = Produto.query.get_or_404(id)
    produto.nome = request.form.get("nome")
    produto.estoque_minimo = int(request.form.get("estoque_minimo", "0"))
    produto.preco_custo = float(request.form.get("preco_custo", str(produto.preco_custo)))
    produto.preco_venda = float(request.form.get("preco_venda", str(produto.preco_venda)))
    try:
        if produto.quantidade == 0:
            novo_codigo = request.form.get("codigo")
            if novo_codigo:
                produto.codigo = novo_codigo
    except Exception:
        pass
    db.session.commit()
    flash("Produto atualizado!", "success")
    return redirect(url_for("estoque_producao.lista_produtos"))


@bp.route("/produtos/excluir/<int:id>", methods=["POST"])
@login_required
def excluir_produto(id: int):
    if current_user.nivel == "visualizador":
        flash("Visualizadores não têm permissão para fazer alterações no sistema.", "danger")
        return redirect(url_for("estoque_producao.lista_produtos"))
    if current_user.nivel not in ("admin", "DEV", "operador"):
        flash("Você não tem permissão para excluir produtos.", "danger")
        return redirect(url_for("estoque_producao.lista_produtos"))
    produto = Produto.query.get_or_404(id)
    try:
        Historico.query.filter_by(product_id=id).delete()
        db.session.delete(produto)
        db.session.commit()
        flash(f'Produto "{produto.nome}" excluído com sucesso!', "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao excluir produto: {e}", "danger")
    return redirect(url_for("estoque_producao.lista_produtos"))


@bp.route("/produtos/entrada/<int:id>", methods=["POST"])
@login_required
def entrada_produto(id: int):
    if current_user.nivel == "visualizador":
        flash("Visualizadores não têm permissão para fazer alterações no sistema.", "danger")
        return redirect(url_for("estoque_producao.lista_produtos"))
    produto = Produto.query.get_or_404(id)
    qtd = int(request.form.get("quantidade", "0"))
    produto.quantidade += qtd
    db.session.commit()
    hist = Historico()
    hist.product_id = produto.id
    hist.product_name = produto.nome
    hist.action = "entrada"
    hist.quantidade = qtd
    hist.details = request.form.get("detalhes")
    hist.usuario = current_user.username
    db.session.add(hist)
    db.session.commit()
    registrar_evento(
        "entrada de estoque",
        produto=produto.nome,
        quantidade=qtd,
        descricao=(request.form.get("detalhes") or "").strip(),
    )
    flash("Entrada registrada!", "success")
    return redirect(url_for("estoque_producao.lista_produtos"))


@bp.route("/produtos/saida/<int:id>", methods=["POST"])
@login_required
def saida_produto(id: int):
    if current_user.nivel == "visualizador":
        flash("Visualizadores não têm permissão para fazer alterações no sistema.", "danger")
        return redirect(url_for("estoque_producao.lista_produtos"))
    produto = Produto.query.get_or_404(id)
    qtd = int(request.form.get("quantidade", "0"))
    if produto.quantidade < qtd:
        flash("Quantidade insuficiente em estoque.", "danger")
        return redirect(url_for("estoque_producao.lista_produtos"))
    produto.quantidade -= qtd
    db.session.commit()
    hist = Historico()
    hist.product_id = produto.id
    hist.product_name = produto.nome
    hist.action = "saida"
    hist.quantidade = qtd
    hist.details = request.form.get("detalhes")
    hist.usuario = current_user.username
    db.session.add(hist)
    db.session.commit()
    registrar_evento(
        "saída de estoque", produto=produto.nome, quantidade=qtd, descricao=(request.form.get("detalhes") or "").strip()
    )
    if produto.quantidade == 0:
        registrar_evento("produto zerado", produto=produto.nome, quantidade=0)
    flash("Saída registrada!", "warning")
    return redirect(url_for("estoque_producao.lista_produtos"))


@bp.route("/produtos/<int:id>/minimo", methods=["POST"])
@login_required
def atualizar_minimo(id: int):
    if current_user.nivel == "visualizador":
        flash("Visualizadores não têm permissão para fazer alterações no sistema.", "danger")
        return redirect(url_for("estoque_producao.index"))
    if current_user.nivel not in ["operador", "admin", "DEV"]:
        flash("Você não tem permissão para atualizar estoque mínimo.", "danger")
        return redirect(url_for("estoque_producao.index"))
    produto = Produto.query.get_or_404(id)
    try:
        novo_min = int(request.form.get("novo_minimo", str(produto.estoque_minimo)))
        if novo_min < 0:
            novo_min = 0
        produto.estoque_minimo = novo_min
        db.session.commit()
        flash(f'Estoque mínimo de "{produto.nome}" atualizado para {novo_min}.', "info")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao atualizar estoque mínimo: {e}", "danger")
    return redirect(request.form.get("next") or url_for("estoque_producao.index"))


@bp.route("/produtos/<int:id>/qrcode")
@login_required
def qrcode_produto(id: int):
    produto = Produto.query.get_or_404(id)
    qr = qrcode.QRCode(version=1, error_correction=ERROR_CORRECT_L, box_size=10, border=4)
    qr_data = f"MULTIMAX|{produto.codigo}|{produto.nome}|{produto.id}"
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf)
    buf.seek(0)
    return send_file(buf, mimetype="image/png", download_name=f"qrcode_{produto.codigo}.png")


@bp.route("/produtos/<int:id>/qrcode/view")
@login_required
def qrcode_view(id: int):
    produto = Produto.query.get_or_404(id)
    return render_template("qrcode_produto.html", produto=produto, active_page="index")


# ============================================================================
# Rotas - Estoque Legado (compatibilidade)
# ============================================================================


@bp.route("/estoque/adicionar", methods=["POST"])
@bp.route("/adicionar", methods=["POST"])
@login_required
def adicionar():
    deny = _check_roles(("operador", "admin", "DEV"), "Você não tem permissão para adicionar produtos.")
    if deny:
        return deny
    try:
        nome = request.form.get("nome", "").strip()
        if not nome:
            flash("O nome do produto é obrigatório.", "danger")
            return redirect(url_for("estoque_producao.index"))
        if Produto.query.filter_by(nome=nome).first():
            flash(f'Produto com o nome "{nome}" já existe.', "danger")
            return redirect(url_for("estoque_producao.index"))
        categoria = request.form.get("categoria", "AV").strip().upper()
        prefix = categoria if categoria in ALLOWED_CATEGORIES else "AV"
        proximo_codigo = _gerar_codigo_categoria(prefix)
        new_produto = Produto()
        new_produto.codigo = proximo_codigo
        new_produto.nome = nome
        new_produto.quantidade = int(_parse_int_safe(request.form.get("quantidade"), 0) or 0)
        new_produto.estoque_minimo = max(0, int(_parse_int_safe(request.form.get("estoque_minimo"), 0) or 0))
        new_produto.preco_custo = float(request.form.get("preco_custo", "0"))
        new_produto.preco_venda = float(request.form.get("preco_venda", "0"))
        db.session.add(new_produto)
        db.session.flush()
        if (new_produto.quantidade or 0) > 0:
            _criar_historico(new_produto, "entrada", new_produto.quantidade, "Estoque inicial adicionado")
        db.session.commit()
        flash(f'Produto "{new_produto.nome}" adicionado com sucesso!', "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao adicionar produto: {e}", "danger")
    return redirect(url_for("estoque_producao.index"))


@bp.route("/estoque/entrada/<int:id>", methods=["POST"])
@bp.route("/entrada/<int:id>", methods=["POST"])
@login_required
def entrada(id: int):
    if current_user.nivel == "visualizador":
        flash("Visualizadores não têm permissão para fazer alterações no sistema.", "danger")
        return redirect(url_for("estoque_producao.index"))
    if current_user.nivel not in ["operador", "admin", "DEV"]:
        flash("Você não tem permissão para registrar entrada.", "danger")
        return redirect(url_for("estoque_producao.index"))
    produto = Produto.query.get_or_404(id)
    try:
        quantidade_str = request.form.get("quantidade", "0") or "0"
        try:
            quantidade = int(quantidade_str)
        except (ValueError, TypeError):
            flash("Quantidade inválida.", "danger")
            return redirect(url_for("estoque_producao.index"))
        if quantidade <= 0:
            flash("A quantidade deve ser positiva.", "warning")
            return redirect(url_for("estoque_producao.index"))
        produto.quantidade += quantidade
        hist = Historico()
        hist.product_id = produto.id
        hist.product_name = produto.nome
        hist.action = "entrada"
        hist.quantidade = quantidade
        hist.details = "Entrada de estoque"
        hist.usuario = current_user.username
        db.session.add(hist)
        db.session.commit()
        flash(f'Registrada entrada de {quantidade} unidades de "{produto.nome}".', "primary")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao registrar entrada: {e}", "danger")
    return redirect(url_for("estoque_producao.index"))


@bp.route("/estoque/saida/<int:id>", methods=["POST"])
@bp.route("/saida/<int:id>", methods=["POST"])
@login_required
def saida(id: int):
    if current_user.nivel == "visualizador":
        flash("Visualizadores não têm permissão para fazer alterações no sistema.", "danger")
        return redirect(url_for("estoque_producao.index"))
    if current_user.nivel not in ["operador", "admin", "DEV"]:
        flash("Você não tem permissão para registrar saída.", "danger")
        return redirect(url_for("estoque_producao.index"))
    produto = Produto.query.get_or_404(id)
    try:
        quantidade_str = request.form.get("quantidade", "0") or "0"
        try:
            quantidade = int(quantidade_str)
        except (ValueError, TypeError):
            flash("Quantidade inválida.", "danger")
            return redirect(url_for("estoque_producao.index"))
        if quantidade <= 0:
            flash("A quantidade deve ser positiva.", "warning")
            return redirect(url_for("estoque_producao.index"))
        if quantidade > produto.quantidade:
            flash(f"Saída de {quantidade} unidades excede o estoque atual ({produto.quantidade}).", "warning")
            return redirect(url_for("estoque_producao.index"))
        produto.quantidade -= quantidade
        hist = Historico()
        hist.product_id = produto.id
        hist.product_name = produto.nome
        hist.action = "saida"
        hist.quantidade = quantidade
        hist.details = "Saída de estoque (Venda/Uso)"
        hist.usuario = current_user.username
        db.session.add(hist)
        db.session.commit()
        flash(f'Registrada saída de {quantidade} unidades de "{produto.nome}".', "warning")
        if produto.quantidade <= produto.estoque_minimo:
            flash(f'ALERTA: O estoque de "{produto.nome}" está abaixo do nível mínimo!', "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao registrar saída: {e}", "danger")
    return redirect(url_for("estoque_producao.index"))


@bp.route("/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar(id: int):
    deny = _check_roles(("operador", "admin", "DEV"), "Você não tem permissão para editar produtos.")
    if deny:
        return deny
    produto = Produto.query.get_or_404(id)
    if request.method == "POST":
        deny_post = _check_roles(("operador", "admin", "DEV"), "Você não tem permissão para editar produtos.")
        if deny_post:
            return deny_post
        try:
            novo_nome = request.form.get("nome", produto.nome)
            novo_codigo = request.form.get("codigo", produto.codigo)
            novo_minimo = max(
                0, int(_parse_int_safe(request.form.get("estoque_minimo"), produto.estoque_minimo or 0) or 0)
            )
            ajuste = int(_parse_int_safe(request.form.get("ajuste"), 0) or 0)
            detalhes = (request.form.get("detalhes") or "").strip()
            data_validade = _parse_date_safe(request.form.get("data_validade", "").strip())
            lote = (request.form.get("lote", "") or "").strip() or None
            produto.nome = novo_nome
            produto.codigo = novo_codigo
            produto.estoque_minimo = novo_minimo
            produto.data_validade = data_validade
            produto.lote = lote
            fornecedor_id_str = request.form.get("fornecedor_id", "").strip()
            produto.fornecedor_id = _parse_int_safe(fornecedor_id_str, None) if fornecedor_id_str else None
            if ajuste != 0:
                if ajuste < 0 and (produto.quantidade or 0) < abs(ajuste):
                    flash(f"Ajuste de {-ajuste} excede estoque atual ({produto.quantidade}).", "warning")
                    return redirect(url_for("estoque_producao.editar", id=id))
                produto.quantidade = (produto.quantidade or 0) + ajuste
                _criar_historico(
                    produto, "entrada" if ajuste > 0 else "saida", abs(ajuste), detalhes or "Ajuste via edição"
                )
            db.session.commit()
            if ajuste != 0:
                registrar_evento(
                    "entrada de estoque" if ajuste > 0 else "saída de estoque",
                    produto=produto.nome,
                    quantidade=abs(ajuste),
                    descricao=detalhes or "Ajuste via edição",
                )
            flash(f'Produto "{produto.nome}" atualizado com sucesso!', "info")
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao editar produto: {e}", "danger")
        return redirect(url_for("estoque_producao.index"))
    return render_template("editar_produto.html", produto=produto, active_page="index", today=date.today())


@bp.route("/excluir/<int:id>")
@login_required
def excluir(id: int):
    if current_user.nivel == "visualizador":
        flash("Visualizadores não têm permissão para fazer alterações no sistema.", "danger")
        return redirect(url_for("estoque_producao.index"))
    if current_user.nivel not in ("admin", "DEV"):
        flash("Você não tem permissão para excluir produtos.", "danger")
        return redirect(url_for("estoque_producao.index"))
    produto = Produto.query.get_or_404(id)
    try:
        Historico.query.filter_by(product_id=id).delete()
        db.session.delete(produto)
        db.session.commit()
        flash(f'Produto "{produto.nome}" excluído com sucesso!', "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao excluir produto: {e}", "danger")
    return redirect(url_for("estoque_producao.index"))


@bp.route("/gerenciar", methods=["POST"])
@login_required
def gerenciar():
    deny = _check_roles(("operador", "admin", "DEV"), "Você não tem permissão para gerenciar estoque.")
    if deny:
        return deny
    op = (request.form.get("op") or "").strip().lower()
    pid = _parse_int_safe(request.form.get("product_id"), 0) or 0
    if pid <= 0:
        flash("Produto inválido.", "danger")
        return redirect(url_for("estoque_producao.index"))
    produto = Produto.query.get_or_404(pid)
    if op in ("entrada", "saida"):
        return _processar_movimentacao(produto, op)
    if op == "excluir":
        return _processar_exclusao(produto)
    flash("Operação inválida.", "danger")
    return redirect(url_for("estoque_producao.index"))


# ============================================================================
# Rotas - Estoque de Produção (com previsão de uso)
# ============================================================================


@bp.route("/estoque-producao", methods=["GET"])
@login_required
def estoque_producao_index():
    """Página principal do estoque de produção"""
    if not _require_permission():
        flash("Você não tem permissão para acessar este módulo.", "danger")
        return redirect(url_for("home.index"))

    filtro_produto = request.args.get("produto", "").strip()
    filtro_setor = request.args.get("setor", "").strip()
    filtro_previsao = request.args.get("previsao", "").strip()
    filtro_data_ini = request.args.get("data_ini", "").strip()
    filtro_data_fim = request.args.get("data_fim", "").strip()

    query = EstoqueProducao.query.filter_by(ativo=True)

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

    estoques = query.order_by(EstoqueProducao.data_registro.desc()).all()
    produtos = Produto.query.filter_by(ativo=True).order_by(Produto.nome).all()
    setores = Setor.query.filter_by(ativo=True).order_by(Setor.nome).all()

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


@bp.route("/estoque-producao/pdf", methods=["GET"])
@login_required
def exportar_pdf():
    """Gera PDF do estoque de produção."""
    if not _require_permission():
        flash("Você não tem permissão para acessar este recurso.", "danger")
        return redirect(url_for("estoque_producao.estoque_producao_index"))
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


@bp.route("/estoque-producao/criar", methods=["POST"])
@login_required
def criar():
    """Cria registro de estoque de produção"""
    if not _require_permission():
        flash("Você não tem permissão para realizar esta ação.", "danger")
        return redirect(url_for("estoque_producao.estoque_producao_index"))
    try:
        produto_id = int(request.form.get("produto_id", 0))
        quantidade = float(request.form.get("quantidade", 0))
        setor_id = int(request.form.get("setor_id", 0))
        previsao_uso = request.form.get("previsao_uso", "").strip()
        data_previsao = request.form.get("data_previsao", "").strip()
        observacao = request.form.get("observacao", "").strip()
        if not produto_id or not setor_id:
            flash("Produto e setor são obrigatórios.", "warning")
            return redirect(url_for("estoque_producao.estoque_producao_index"))
        if quantidade < 0:
            flash("A quantidade não pode ser negativa.", "warning")
            return redirect(url_for("estoque_producao.estoque_producao_index"))
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
        db.session.flush()
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
    return redirect(url_for("estoque_producao.estoque_producao_index"))


@bp.route("/estoque-producao/<int:id>/ajustar", methods=["POST"])
@login_required
def ajustar(id):
    """Ajusta quantidade do estoque de produção"""
    if not _require_permission():
        flash("Você não tem permissão para realizar esta ação.", "danger")
        return redirect(url_for("estoque_producao.estoque_producao_index"))
    estoque = EstoqueProducao.query.get_or_404(id)
    try:
        tipo_ajuste = request.form.get("tipo_ajuste", "").strip()
        quantidade_ajuste = float(request.form.get("quantidade_ajuste", 0))
        motivo = request.form.get("motivo", "").strip()
        if tipo_ajuste not in ["entrada", "saida", "correcao"]:
            flash("Tipo de ajuste inválido.", "warning")
            return redirect(url_for("estoque_producao.estoque_producao_index"))
        if not motivo:
            flash("Motivo do ajuste é obrigatório.", "warning")
            return redirect(url_for("estoque_producao.estoque_producao_index"))
        quantidade_anterior = estoque.quantidade
        if tipo_ajuste == "entrada":
            quantidade_nova = quantidade_anterior + quantidade_ajuste
        elif tipo_ajuste == "saida":
            quantidade_nova = quantidade_anterior - quantidade_ajuste
        else:
            quantidade_nova = quantidade_ajuste
        if quantidade_nova < 0:
            flash("A quantidade não pode ficar negativa.", "warning")
            return redirect(url_for("estoque_producao.estoque_producao_index"))
        estoque.quantidade = quantidade_nova
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
    return redirect(url_for("estoque_producao.estoque_producao_index"))


@bp.route("/estoque-producao/<int:id>/editar", methods=["POST"])
@login_required
def editar_estoque_producao(id):
    """Edita informações do estoque de produção"""
    if not _require_permission():
        flash("Você não tem permissão para realizar esta ação.", "danger")
        return redirect(url_for("estoque_producao.estoque_producao_index"))
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
    return redirect(url_for("estoque_producao.estoque_producao_index"))


@bp.route("/estoque-producao/<int:id>/excluir", methods=["POST"])
@login_required
def excluir_estoque_producao(id):
    """Soft delete no estoque de produção"""
    if not _require_permission():
        flash("Você não tem permissão para realizar esta ação.", "danger")
        return redirect(url_for("estoque_producao.estoque_producao_index"))
    estoque = EstoqueProducao.query.get_or_404(id)
    try:
        estoque.ativo = False
        db.session.commit()
        flash("Registro removido com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao remover registro: {str(e)}", "danger")
    return redirect(url_for("estoque_producao.estoque_producao_index"))


@bp.route("/estoque-producao/<int:id>/historico", methods=["GET"])
@login_required
def historico(id):
    """Histórico de ajustes do estoque de produção"""
    if not _require_permission():
        flash("Você não tem permissão para acessar este recurso.", "danger")
        return redirect(url_for("estoque_producao.estoque_producao_index"))
    estoque = EstoqueProducao.query.get_or_404(id)
    historicos = (
        HistoricoAjusteEstoque.query.filter_by(estoque_id=id).order_by(HistoricoAjusteEstoque.data_ajuste.desc()).all()
    )
    return render_template("estoque_producao_historico.html", estoque=estoque, historicos=historicos)
