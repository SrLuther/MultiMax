"""
Rotas para Estoque de Produção com Previsão de Uso
Controla produtos produzidos e estocados internamente com previsão de uso futuro
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, or_

from .. import db
from ..models import EstoqueProducao, HistoricoAjusteEstoque, Produto, Setor

bp = Blueprint("estoque_producao", __name__, url_prefix="/estoque-producao")


def _require_permission():
    """Verifica se o usuário tem permissão para acessar o módulo"""
    if not current_user.is_authenticated:
        return False
    return current_user.nivel in ["admin", "DEV"]


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
