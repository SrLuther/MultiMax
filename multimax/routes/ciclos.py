import math
import os
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from flask import Blueprint, flash, jsonify, make_response, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from .. import db
from ..models import AppSetting, Ciclo, CicloFechamento, Collaborator, MedicalCertificate, SystemLog, Vacation

try:
    from weasyprint import HTML

    WEASYPRINT_AVAILABLE = True
except Exception:
    # Captura ImportError, OSError e outros erros de inicialização do WeasyPrint
    # (especialmente no Windows onde DLLs podem não estar disponíveis)
    WEASYPRINT_AVAILABLE = False
    HTML = None  # type: ignore

bp = Blueprint("ciclos", __name__, url_prefix="/ciclos")

# ============================================================================
# Funções auxiliares
# ============================================================================


def _get_all_collaborators():
    """Retorna todos os colaboradores ativos"""
    return Collaborator.query.filter_by(active=True).order_by(Collaborator.name.asc()).all()


def _get_active_ciclos_query(collaborator_id):
    """Helper para buscar registros ativos de um colaborador"""
    return Ciclo.query.filter(Ciclo.collaborator_id == collaborator_id, Ciclo.status_ciclo == "ativo")


def _calculate_collaborator_balance(collaborator_id):
    """
    FUNÇÃO CENTRAL: Calcula saldo do colaborador a partir dos registros ativos
    NÃO confia em valores armazenados - sempre recalcula a partir das horas
    Otimizado: usa sum() do SQLAlchemy para melhor performance
    """
    # Buscar soma de todas as horas usando sum() do SQLAlchemy (mais eficiente)
    total_horas_decimal = _get_active_ciclos_query(collaborator_id).with_entities(
        func.coalesce(func.sum(Ciclo.valor_horas), 0)
    ).scalar() or Decimal("0.0")

    # Converter para Decimal se necessário
    if not isinstance(total_horas_decimal, Decimal):
        total_horas = Decimal(str(total_horas_decimal))
    else:
        total_horas = total_horas_decimal

    # Calcular dias completos (floor de total_horas / 8)
    # Apenas dias completos entram na conversão para R$
    # Se horas totais são negativas (folgas utilizadas), dias = 0
    total_horas_float = float(total_horas)
    if total_horas_float < 0:
        dias_completos = 0
        horas_restantes = 0.0  # Horas negativas não geram horas restantes
    else:
        dias_completos = int(math.floor(total_horas_float / 8.0))
        horas_restantes = total_horas_float % 8.0

    # Valor aproximado (dias_completos * valor_dia)
    # Apenas dias completos têm valor em R$
    valor_dia = Decimal(str(_get_valor_dia()))
    valor_aproximado = Decimal(str(dias_completos)) * valor_dia

    return {
        "total_horas": float(total_horas),
        "dias_completos": dias_completos,
        "horas_restantes": round(horas_restantes, 1),
        "valor_aproximado": float(valor_aproximado),
    }


def _get_valor_dia():
    """Obtém valor de 1 dia (8h) em R$"""
    try:
        setting = AppSetting.query.filter_by(key="ciclo_valor_dia").first()
        if setting and setting.value:
            return float(setting.value)
    except Exception:
        pass
    return 65.0  # Valor padrão


def _get_nome_empresa():
    """Obtém nome da empresa"""
    try:
        setting = AppSetting.query.filter_by(key="ciclo_nome_empresa").first()
        if setting and setting.value:
            return setting.value
    except Exception:
        pass
    return "MultiMax | Controle inteligente"  # Valor padrão


def _get_ciclo_atual():
    """Calcula o ciclo atual (ciclo_id e mês de início)"""
    # Buscar primeiro ciclo_id disponível (próximo ciclo ou 1 se não houver fechamentos)
    ultimo_fechamento = CicloFechamento.query.order_by(CicloFechamento.ciclo_id.desc()).first()
    ciclo_id = (ultimo_fechamento.ciclo_id + 1) if ultimo_fechamento else 1

    # Buscar primeira data de lançamento dos registros ativos para determinar mês de início
    primeiro_registro = Ciclo.query.filter(Ciclo.status_ciclo == "ativo").order_by(Ciclo.data_lancamento.asc()).first()
    if primeiro_registro:
        mes_inicio = primeiro_registro.data_lancamento.strftime("%B")
    else:
        mes_inicio = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%B")

    # Converter para português
    meses_pt = {
        "January": "Janeiro",
        "February": "Fevereiro",
        "March": "Março",
        "April": "Abril",
        "May": "Maio",
        "June": "Junho",
        "July": "Julho",
        "August": "Agosto",
        "September": "Setembro",
        "October": "Outubro",
        "November": "Novembro",
        "December": "Dezembro",
    }
    mes_inicio = meses_pt.get(mes_inicio, mes_inicio)

    return {"ciclo_id": ciclo_id, "mes_inicio": mes_inicio}


def _validate_hours_format(value_str, allow_negative=False):
    """
    Valida formato de horas: somente múltiplos de 0.5, ponto como separador
    NÃO aceita vírgula (bloqueia completamente)
    Retorna (valido, valor_decimal, erro)
    """
    if not value_str or not value_str.strip():
        return (False, None, "Campo obrigatório")

    value_str = value_str.strip()

    # Bloquear vírgula completamente (NÃO converter)
    if "," in value_str:
        return (
            False,
            None,
            (
                "Formato inválido. Use apenas números inteiros ou decimais com ponto "
                "(ex.: 1 ou 1.5). Apenas múltiplos de 0.5 são permitidos."
            ),
        )

    # Bloquear dois pontos (formato 2:30)
    if ":" in value_str:
        return (
            False,
            None,
            (
                "Formato inválido. Use apenas números inteiros ou decimais com ponto "
                "(ex.: 1 ou 1.5). Apenas múltiplos de 0.5 são permitidos."
            ),
        )

    try:
        valor = Decimal(value_str)

        # Verificar se é negativo (exceto se permitido)
        if valor < 0 and not allow_negative:
            return (False, None, "Valor não pode ser negativo")

        # Verificar se é múltiplo de 0.5
        resto = abs(float(valor)) % 0.5
        if resto > 0.001 and resto < 0.499:  # Tolerância para erros de ponto flutuante
            return (
                False,
                None,
                (
                "Formato inválido. Use apenas números inteiros ou decimais com ponto "
                "(ex.: 1 ou 1.5). Apenas múltiplos de 0.5 são permitidos."
            ),
            )

        return (True, valor, None)
    except (ValueError, TypeError):
        return (
            False,
            None,
            (
                "Formato inválido. Use apenas números inteiros ou decimais com ponto "
                "(ex.: 1 ou 1.5). Apenas múltiplos de 0.5 são permitidos."
            ),
        )


# ============================================================================
# Rotas principais
# ============================================================================


@bp.route("/", methods=["GET"], strict_slashes=False)
@login_required
def index():
    """Página principal de Ciclos com cards de colaboradores"""
    if current_user.nivel not in ["operador", "admin", "DEV"]:
        flash("Acesso negado.", "danger")
        return redirect(url_for("home.index"))

    try:
        # Buscar todos os colaboradores ativos
        colaboradores = _get_all_collaborators()

        # Calcular saldos para cada colaborador
        colaboradores_stats = []
        for colab in colaboradores:
            balance = _calculate_collaborator_balance(colab.id)
            colaboradores_stats.append({"collaborator": colab, "balance": balance})

        # Buscar configurações
        nome_empresa = _get_nome_empresa()
        valor_dia = _get_valor_dia()

        # Calcular ciclo atual
        ciclo_atual = _get_ciclo_atual()

        # Totais gerais
        total_horas_geral = sum(s["balance"]["total_horas"] for s in colaboradores_stats)
        total_dias_geral = sum(s["balance"]["dias_completos"] for s in colaboradores_stats)
        total_horas_restantes_geral = sum(s["balance"]["horas_restantes"] for s in colaboradores_stats)
        total_valor_geral = sum(s["balance"]["valor_aproximado"] for s in colaboradores_stats)

        # Verificar se há registros ativos para mostrar botão de fechamento
        tem_registros_ativos = any(s["balance"]["total_horas"] > 0 for s in colaboradores_stats)

        # Buscar colaborador selecionado (se houver) para exibir férias e atestados
        selected_collaborator_id = request.args.get("collaborator_id", type=int)
        selected_collaborator = None
        ferias = []
        atestados = []

        if selected_collaborator_id and current_user.nivel in ("admin", "DEV"):
            selected_collaborator = Collaborator.query.get(selected_collaborator_id)
            if selected_collaborator:
                ferias = (
                    Vacation.query.filter_by(collaborator_id=selected_collaborator.id)
                    .order_by(Vacation.data_inicio.desc())
                    .all()
                )
                atestados = (
                    MedicalCertificate.query.filter_by(collaborator_id=selected_collaborator.id)
                    .order_by(MedicalCertificate.data_inicio.desc())
                    .all()
                )

        return render_template(
            "ciclos/index.html",
            active_page="ciclos",
            colaboradores_stats=colaboradores_stats,
            nome_empresa=nome_empresa,
            valor_dia=valor_dia,
            ciclo_atual=ciclo_atual,
            total_horas_geral=total_horas_geral,
            total_dias_geral=total_dias_geral,
            total_horas_restantes_geral=total_horas_restantes_geral,
            total_valor_geral=total_valor_geral,
            tem_registros_ativos=tem_registros_ativos,
            can_edit=current_user.nivel in ["admin", "DEV"],
            selected_collaborator=selected_collaborator,
            ferias=ferias,
            atestados=atestados,
        )
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f"Erro ao carregar Ciclos: {str(e)}", "danger")
        # Retornar página vazia em caso de erro para evitar erro 500
        ciclo_atual_default = {"ciclo_id": 1, "mes_inicio": datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%B")}
        meses_pt = {
            "January": "Janeiro",
            "February": "Fevereiro",
            "March": "Março",
            "April": "Abril",
            "May": "Maio",
            "June": "Junho",
            "July": "Julho",
            "August": "Agosto",
            "September": "Setembro",
            "October": "Outubro",
            "November": "Novembro",
            "December": "Dezembro",
        }
        ciclo_atual_default["mes_inicio"] = meses_pt.get(
            ciclo_atual_default["mes_inicio"], ciclo_atual_default["mes_inicio"]
        )
        return render_template(
            "ciclos/index.html",
            active_page="ciclos",
            colaboradores_stats=[],
            nome_empresa="MultiMax | Controle inteligente",
            valor_dia=65.0,
            ciclo_atual=ciclo_atual_default,
            total_horas_geral=0.0,
            total_dias_geral=0,
            total_horas_restantes_geral=0.0,
            total_valor_geral=0.0,
            tem_registros_ativos=False,
            can_edit=current_user.nivel in ["admin", "DEV"],
            selected_collaborator=None,
            ferias=[],
            atestados=[],
        )


@bp.route("/lançar", methods=["POST"], strict_slashes=False)
@login_required
def lancar_horas():
    """Lançar horas para um colaborador"""
    if current_user.nivel not in ["admin", "DEV"]:
        flash("Acesso negado. Apenas administradores podem lançar horas.", "danger")
        return redirect(url_for("ciclos.index"))

    try:
        collaborator_id = int(request.form.get("collaborator_id", 0))
        data_lancamento_str = request.form.get("data_lancamento", "").strip()
        origem = request.form.get("origem", "").strip()
        descricao = request.form.get("descricao", "").strip()
        valor_horas_str = request.form.get("valor_horas", "").strip()

        # Validações obrigatórias
        if not collaborator_id or not data_lancamento_str or not origem or not valor_horas_str:
            flash("Dados obrigatórios ausentes.", "warning")
            return redirect(url_for("ciclos.index"))

        # Validar colaborador
        collaborator = Collaborator.query.get(collaborator_id)
        if not collaborator:
            flash("Colaborador não encontrado.", "danger")
            return redirect(url_for("ciclos.index"))

        # Validar origem
        origens_validas = ["Domingo", "Feriado", "Horas adicionais", "Outro", "Folga utilizada"]
        if origem not in origens_validas:
            flash("Origem inválida.", "warning")
            return redirect(url_for("ciclos.index"))

        # Validar descrição se necessário
        if origem in ["Horas adicionais", "Outro"] and not descricao:
            flash('Descrição é obrigatória para origem "Horas adicionais" ou "Outro".', "warning")
            return redirect(url_for("ciclos.index"))

        # Validar formato de horas (permitir negativo apenas para Folga utilizada)
        allow_negative = origem == "Folga utilizada"
        valido, valor_horas_decimal, erro = _validate_hours_format(valor_horas_str, allow_negative=allow_negative)
        if not valido:
            flash(erro or "Formato inválido.", "warning")
            return redirect(url_for("ciclos.index"))

        # Validar Folga utilizada: deve ser exatamente -8h
        if origem == "Folga utilizada":
            if valor_horas_decimal != Decimal("-8.0"):
                flash("Folga utilizada deve ser exatamente -8 horas.", "warning")
                return redirect(url_for("ciclos.index"))

        # Validar e converter data
        try:
            data_lancamento = datetime.strptime(data_lancamento_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Data inválida.", "warning")
            return redirect(url_for("ciclos.index"))

        # NÃO calcular dias no lançamento - sempre 0
        # Conversão de horas em dias acontece APENAS no fechamento

        # Criar registro
        ciclo = Ciclo()
        ciclo.collaborator_id = collaborator_id
        ciclo.nome_colaborador = collaborator.name  # Cópia do nome
        ciclo.data_lancamento = data_lancamento
        ciclo.origem = origem
        ciclo.descricao = descricao if descricao else None
        ciclo.valor_horas = valor_horas_decimal
        ciclo.dias_fechados = 0  # Sempre 0 no lançamento
        ciclo.horas_restantes = Decimal("0.0")  # Sempre 0 no lançamento
        ciclo.ciclo_id = None  # Será preenchido no fechamento
        ciclo.status_ciclo = "ativo"
        ciclo.valor_aproximado = Decimal("0.0")  # Sempre 0 no lançamento
        ciclo.created_by = current_user.name or current_user.username

        db.session.add(ciclo)

        # Log
        log = SystemLog()
        log.origem = "Ciclos"
        log.evento = "lançamento_horas"
        log.detalhes = f"Lançamento de {valor_horas_decimal}h para {collaborator.name} - Origem: {origem}"
        log.usuario = current_user.name or current_user.username
        db.session.add(log)

        db.session.commit()
        flash(f"Horas lançadas com sucesso: {valor_horas_decimal}h para {collaborator.name}", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao lançar horas: {str(e)}", "danger")
        import traceback

        print(traceback.format_exc())

    return redirect(url_for("ciclos.index"))


@bp.route("/historico/<int:collaborator_id>", methods=["GET"], strict_slashes=False)
@login_required
def historico(collaborator_id):
    """Retorna histórico paginado de um colaborador (JSON)"""
    if current_user.nivel not in ["operador", "admin", "DEV"]:
        return jsonify({"ok": False, "error": "Acesso negado"}), 403

    try:
        page = int(request.args.get("page", 1))
        per_page = 5  # 5 linhas por página

        # Buscar colaborador
        collaborator = Collaborator.query.get_or_404(collaborator_id)

        # Buscar registros ativos do colaborador
        query = _get_active_ciclos_query(collaborator_id).order_by(Ciclo.data_lancamento.desc(), Ciclo.id.desc())

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        registros = pagination.items

        # Calcular saldo atual
        balance = _calculate_collaborator_balance(collaborator_id)

        # Formatar registros
        registros_data = []
        for reg in registros:
            registros_data.append(
                {
                    "id": reg.id,
                    "data": reg.data_lancamento.strftime("%d/%m/%Y"),
                    "origem": reg.origem,
                    "descricao": reg.descricao or "-",
                    "horas": float(reg.valor_horas),
                    "dias_fechados": reg.dias_fechados or 0,
                    "horas_restantes": float(reg.horas_restantes) if reg.horas_restantes else 0.0,
                }
            )

        return jsonify(
            {
                "ok": True,
                "collaborator_name": collaborator.name,
                "registros": registros_data,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": pagination.total,
                    "pages": pagination.pages,
                    "has_next": pagination.has_next,
                    "has_prev": pagination.has_prev,
                },
                "balance": balance,
            }
        )
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.route("/ajustar/<int:ciclo_id>", methods=["POST"], strict_slashes=False)
@login_required
def ajustar(ciclo_id):
    """Ajustar registro manualmente (apenas admin/dev)"""
    if current_user.nivel not in ["admin", "DEV"]:
        return jsonify({"ok": False, "error": "Acesso negado. Apenas administradores podem ajustar registros."}), 403

    try:
        ciclo = Ciclo.query.get_or_404(ciclo_id)

        valor_horas_str = request.form.get("valor_horas", "").strip()
        descricao = request.form.get("descricao", "").strip()

        # Validar formato de horas (permitir negativo para ajustes de folgas)
        allow_negative = ciclo.origem == "Folga utilizada"
        valido, valor_horas_decimal, erro = _validate_hours_format(valor_horas_str, allow_negative=allow_negative)
        if not valido:
            return jsonify({"ok": False, "error": erro or "Formato inválido."}), 400

        # NÃO calcular dias no ajuste - sempre 0
        # Conversão de horas em dias acontece APENAS no fechamento

        # Atualizar registro
        ciclo.valor_horas = valor_horas_decimal
        ciclo.dias_fechados = 0  # Sempre 0
        ciclo.horas_restantes = Decimal("0.0")  # Sempre 0
        ciclo.valor_aproximado = Decimal("0.0")  # Sempre 0
        if descricao:
            ciclo.descricao = descricao
        ciclo.updated_at = datetime.now(ZoneInfo("America/Sao_Paulo"))
        ciclo.updated_by = current_user.name or current_user.username

        # Log
        log = SystemLog()
        log.origem = "Ciclos"
        log.evento = "ajuste_manual"
        log.detalhes = f"Ajuste manual de registro {ciclo_id}: {valor_horas_decimal}h"
        log.usuario = current_user.name or current_user.username
        db.session.add(log)

        db.session.commit()
        return jsonify({"ok": True, "message": "Registro ajustado com sucesso!"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.route("/excluir/<int:ciclo_id>", methods=["POST"], strict_slashes=False)
@login_required
def excluir(ciclo_id):
    """Excluir registro do histórico (apenas admin/dev)"""
    if current_user.nivel not in ["admin", "DEV"]:
        return jsonify({"ok": False, "error": "Acesso negado. Apenas administradores podem excluir registros."}), 403

    try:
        ciclo = Ciclo.query.get_or_404(ciclo_id)

        # Verificar se o registro está ativo (só pode excluir registros ativos)
        if ciclo.status_ciclo != "ativo":
            return jsonify({"ok": False, "error": "Apenas registros ativos podem ser excluídos."}), 400

        colaborador_nome = ciclo.nome_colaborador
        horas_excluidas = float(ciclo.valor_horas)

        # Excluir registro
        db.session.delete(ciclo)

        # Log
        log = SystemLog()
        log.origem = "Ciclos"
        log.evento = "exclusao_registro"
        log.detalhes = f"Exclusão de registro {ciclo_id}: {horas_excluidas}h de {colaborador_nome}"
        log.usuario = current_user.name or current_user.username
        db.session.add(log)

        db.session.commit()

        return jsonify(
            {
                "ok": True,
                "message": f"Registro excluído com sucesso! {horas_excluidas}h removidas de {colaborador_nome}",
            }
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": f"Erro ao excluir registro: {str(e)}"}), 500


@bp.route("/fechamento/resumo", methods=["GET"], strict_slashes=False)
@login_required
def resumo_fechamento():
    """Retorna resumo para fechamento do ciclo (JSON)"""
    if current_user.nivel not in ["admin", "DEV"]:
        return jsonify({"ok": False, "error": "Acesso negado"}), 403

    try:
        colaboradores = _get_all_collaborators()
        colaboradores_resumo = []

        valor_dia = _get_valor_dia()

        for colab in colaboradores:
            balance = _calculate_collaborator_balance(colab.id)

            # Buscar registros ativos
            registros = _get_active_ciclos_query(colab.id).all()

            # Calcular totais usando balance (já calculado acima, mais eficiente)
            total_horas = balance["total_horas"]
            dias_completos = balance["dias_completos"]
            horas_restantes = balance["horas_restantes"]
            valor_total = balance["valor_aproximado"]

            if total_horas > 0:  # Só incluir se tiver horas
                colaboradores_resumo.append(
                    {
                        "collaborator_id": colab.id,
                        "nome": colab.name,
                        "total_horas": round(total_horas, 1),
                        "dias_completos": dias_completos,
                        "horas_restantes": horas_restantes,
                        "valor": round(valor_total, 2),
                        "registros_count": len(registros),
                    }
                )

        # Totais gerais
        total_geral_horas = sum(r["total_horas"] for r in colaboradores_resumo)
        total_geral_dias = sum(r["dias_completos"] for r in colaboradores_resumo)
        total_geral_horas_restantes = sum(r["horas_restantes"] for r in colaboradores_resumo)
        total_geral_valor = sum(r["valor"] for r in colaboradores_resumo)

        # Avisos: horas < 8h não entram na conversão
        avisos = []
        for resumo in colaboradores_resumo:
            if resumo["total_horas"] < 8.0:
                avisos.append(
                    f"{resumo['nome']}: {resumo['total_horas']}h (< 8h) - não entrará na conversão automática"
                )

        return jsonify(
            {
                "ok": True,
                "colaboradores": colaboradores_resumo,
                "totais": {
                    "total_horas": round(total_geral_horas, 1),
                    "total_dias": total_geral_dias,
                    "total_horas_restantes": round(total_geral_horas_restantes, 1),
                    "total_valor": round(total_geral_valor, 2),
                    "valor_dia": valor_dia,
                },
                "avisos": avisos,
            }
        )
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.route("/fechamento/confirmar", methods=["POST"], strict_slashes=False)
@login_required
def confirmar_fechamento():
    """Confirma fechamento do ciclo, arquiva e move horas restantes para próximo ciclo"""
    if current_user.nivel not in ["admin", "DEV"]:
        flash("Acesso negado. Apenas administradores podem fechar ciclos.", "danger")
        return redirect(url_for("ciclos.index"))

    try:
        # Buscar próximo ciclo_id disponível
        ultimo_fechamento = CicloFechamento.query.order_by(CicloFechamento.ciclo_id.desc()).first()
        proximo_ciclo_id = (ultimo_fechamento.ciclo_id + 1) if ultimo_fechamento else 1

        # Buscar todos os registros ativos
        registros_ativos = Ciclo.query.filter(Ciclo.status_ciclo == "ativo").all()

        if not registros_ativos:
            flash("Nenhum registro ativo encontrado para fechamento.", "warning")
            return redirect(url_for("ciclos.index"))

        # Agrupar por colaborador e calcular usando função central
        colaboradores_totais = {}
        colaboradores_list = list(set(reg.collaborator_id for reg in registros_ativos))

        total_horas_geral = Decimal("0.0")
        total_dias_geral = 0
        total_valor_geral = Decimal("0.0")

        # Calcular totais usando função central (NÃO usar valores armazenados)
        for cid in colaboradores_list:
            balance = _calculate_collaborator_balance(cid)

            # Buscar registros do colaborador
            registros_colab = [r for r in registros_ativos if r.collaborator_id == cid]

            # Usar valores calculados (não armazenados)
            total_horas_colab = Decimal(str(balance["total_horas"]))
            dias_completos_colab = balance["dias_completos"]
            valor_total_colab = Decimal(str(balance["valor_aproximado"]))
            horas_restantes_colab = balance["horas_restantes"]

            colaboradores_totais[cid] = {
                "nome": registros_colab[0].nome_colaborador,
                "total_horas": total_horas_colab,
                "total_dias": dias_completos_colab,
                "total_valor": valor_total_colab,
                "horas_restantes": horas_restantes_colab,
                "registros": registros_colab,
            }

            total_horas_geral += total_horas_colab
            total_dias_geral += dias_completos_colab
            total_valor_geral += valor_total_colab

        # Processar cada colaborador: fechar registros e criar carryover
        for cid, dados in colaboradores_totais.items():
            horas_restantes_colab = dados["horas_restantes"]

            # Criar carryover apenas se houver horas restantes (> 0 e < 8h)
            if horas_restantes_colab > 0 and horas_restantes_colab < 8.0:
                # CARRYOVER: Horas restantes do ciclo anterior
                novo_ciclo_carryover = Ciclo()
                novo_ciclo_carryover.collaborator_id = cid
                novo_ciclo_carryover.nome_colaborador = dados["nome"]
                novo_ciclo_carryover.data_lancamento = date.today()
                novo_ciclo_carryover.origem = "Carryover"  # Tipo específico para carryover
                novo_ciclo_carryover.descricao = f"Horas restantes do ciclo {proximo_ciclo_id - 1} transportadas"
                novo_ciclo_carryover.valor_horas = Decimal(str(round(horas_restantes_colab, 1)))
                novo_ciclo_carryover.dias_fechados = 0  # Sempre 0
                novo_ciclo_carryover.horas_restantes = Decimal("0.0")  # Sempre 0
                novo_ciclo_carryover.ciclo_id = None  # Será preenchido no próximo fechamento
                novo_ciclo_carryover.status_ciclo = "ativo"
                novo_ciclo_carryover.valor_aproximado = Decimal("0.0")  # Sempre 0
                novo_ciclo_carryover.created_by = current_user.name or current_user.username
                db.session.add(novo_ciclo_carryover)

            # Marcar registros como fechados
            for reg in dados["registros"]:
                reg.ciclo_id = proximo_ciclo_id
                reg.status_ciclo = "fechado"
                reg.updated_at = datetime.now(ZoneInfo("America/Sao_Paulo"))
                reg.updated_by = current_user.name or current_user.username

        # Criar registro de fechamento
        fechamento = CicloFechamento()
        fechamento.ciclo_id = proximo_ciclo_id
        fechamento.fechado_por = current_user.name or current_user.username
        fechamento.valor_total = total_valor_geral
        fechamento.total_horas = Decimal(str(round(float(total_horas_geral), 1)))
        fechamento.total_dias = total_dias_geral
        fechamento.colaboradores_envolvidos = len(colaboradores_totais)
        observacoes = request.form.get("observacoes", "").strip()
        fechamento.observacoes = observacoes if observacoes else None
        db.session.add(fechamento)

        # Log
        log = SystemLog()
        log.origem = "Ciclos"
        log.evento = "fechamento_ciclo"
        log.detalhes = (
            f"Fechamento do ciclo {proximo_ciclo_id}: {total_dias_geral} dias, "
            f"{total_horas_geral}h, R$ {total_valor_geral:.2f}"
        )
        log.usuario = current_user.name or current_user.username
        db.session.add(log)

        db.session.commit()

        msg = (
            f"Ciclo {proximo_ciclo_id} fechado com sucesso! {total_dias_geral} dias completos, "
            f"{round(total_horas_geral, 1)}h totais, R$ {total_valor_geral:.2f}"
        )
        flash(msg, "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao fechar ciclo: {str(e)}", "danger")
        import traceback

        print(traceback.format_exc())

    return redirect(url_for("ciclos.index"))


@bp.route("/config", methods=["GET", "POST"], strict_slashes=False)
@login_required
def config():
    """Página de configurações (nome empresa, valor dia)"""
    if current_user.nivel not in ["admin", "DEV"]:
        flash("Acesso negado.", "danger")
        return redirect(url_for("ciclos.index"))

    nome_empresa = _get_nome_empresa()
    valor_dia = _get_valor_dia()

    if request.method == "POST":
        try:
            novo_nome = request.form.get("nome_empresa", "").strip()
            novo_valor_str = request.form.get("valor_dia", "").strip()

            if not novo_nome:
                flash("Nome da empresa é obrigatório.", "warning")
                return redirect(url_for("ciclos.config"))

            try:
                novo_valor = float(novo_valor_str)
                if novo_valor <= 0:
                    flash("Valor do dia deve ser maior que zero.", "warning")
                    return redirect(url_for("ciclos.config"))
            except (ValueError, TypeError):
                flash("Valor do dia inválido.", "warning")
                return redirect(url_for("ciclos.config"))

            # Salvar nome da empresa
            setting_nome = AppSetting.query.filter_by(key="ciclo_nome_empresa").first()
            if not setting_nome:
                setting_nome = AppSetting()
                setting_nome.key = "ciclo_nome_empresa"
                db.session.add(setting_nome)
            setting_nome.value = novo_nome

            # Salvar valor do dia
            setting_valor = AppSetting.query.filter_by(key="ciclo_valor_dia").first()
            if not setting_valor:
                setting_valor = AppSetting()
                setting_valor.key = "ciclo_valor_dia"
                db.session.add(setting_valor)
            setting_valor.value = str(novo_valor)

            # Log
            log = SystemLog()
            log.origem = "Ciclos"
            log.evento = "config_atualizada"
            log.detalhes = f"Configuração atualizada: Empresa={novo_nome}, Valor dia=R$ {novo_valor}"
            log.usuario = current_user.name or current_user.username
            db.session.add(log)

            db.session.commit()
            flash("Configurações salvas com sucesso!", "success")

        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao salvar configurações: {str(e)}", "danger")

        return redirect(url_for("ciclos.config"))

    return render_template("ciclos/config.html", active_page="ciclos", nome_empresa=nome_empresa, valor_dia=valor_dia)


# ============================================================================
# Rotas de Férias e Atestados (movidas para Ciclos)
# ============================================================================


@bp.route("/ferias/adicionar", methods=["POST"], strict_slashes=False)
@login_required
def ferias_adicionar():
    """Adicionar férias para um colaborador"""
    if current_user.nivel not in ("admin", "DEV"):
        flash("Acesso negado.", "danger")
        return redirect(url_for("ciclos.index"))
    try:
        cid_str = (request.form.get("collaborator_id") or "").strip()
        di_str = (request.form.get("data_inicio") or "").strip()
        df_str = (request.form.get("data_fim") or "").strip()
        if not cid_str or not di_str or not df_str:
            flash("Dados obrigatórios ausentes.", "warning")
            return redirect(url_for("ciclos.index", collaborator_id=cid_str if cid_str else None))
        cid = int(cid_str)
        data_inicio = datetime.strptime(di_str, "%Y-%m-%d").date()
        data_fim = datetime.strptime(df_str, "%Y-%m-%d").date()
        observacao = request.form.get("observacao", "").strip()

        if data_fim < data_inicio:
            flash("Data final deve ser maior ou igual à data inicial.", "warning")
            return redirect(url_for("ciclos.index", collaborator_id=cid))

        v = Vacation()
        v.collaborator_id = cid
        v.data_inicio = data_inicio
        v.data_fim = data_fim
        v.observacao = observacao
        v.criado_por = current_user.name or current_user.username
        db.session.add(v)
        db.session.commit()
        flash("Férias registradas com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao registrar férias: {e}", "danger")
        # Em caso de erro, tentar manter collaborator_id se disponível
        try:
            cid = int(request.form.get("collaborator_id", 0))
            if cid:
                return redirect(url_for("ciclos.index", collaborator_id=cid))
        except Exception:
            pass
    # Manter collaborator_id na URL para exibir os cards
    return redirect(url_for("ciclos.index", collaborator_id=cid))


@bp.route("/ferias/<int:id>/excluir", methods=["POST"], strict_slashes=False)
@login_required
def ferias_excluir(id: int):
    """Excluir férias"""
    if current_user.nivel not in ("admin", "DEV"):
        flash("Acesso negado.", "danger")
        return redirect(url_for("ciclos.index"))
    v = Vacation.query.get_or_404(id)
    collaborator_id = v.collaborator_id
    try:
        db.session.delete(v)
        db.session.commit()
        flash("Férias excluídas.", "info")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao excluir: {e}", "danger")
    # Manter collaborator_id na URL para exibir os cards
    return redirect(url_for("ciclos.index", collaborator_id=collaborator_id))


@bp.route("/atestado/adicionar", methods=["POST"], strict_slashes=False)
@login_required
def atestado_adicionar():
    """Adicionar atestado médico para um colaborador"""
    if current_user.nivel not in ("admin", "DEV"):
        flash("Acesso negado.", "danger")
        return redirect(url_for("ciclos.index"))
    try:
        from ..filename_utils import secure_filename

        cid_str = (request.form.get("collaborator_id") or "").strip()
        di_str = (request.form.get("data_inicio") or "").strip()
        df_str = (request.form.get("data_fim") or "").strip()
        if not cid_str or not di_str or not df_str:
            flash("Dados obrigatórios ausentes.", "warning")
            return redirect(url_for("ciclos.index", collaborator_id=cid_str if cid_str else None))
        cid = int(cid_str)
        data_inicio = datetime.strptime(di_str, "%Y-%m-%d").date()
        data_fim = datetime.strptime(df_str, "%Y-%m-%d").date()
        motivo = request.form.get("motivo", "").strip()
        cid_code = request.form.get("cid", "").strip()
        medico = request.form.get("medico", "").strip()

        if data_fim < data_inicio:
            flash("Data final deve ser maior ou igual à data inicial.", "warning")
            return redirect(url_for("ciclos.index", collaborator_id=cid))

        dias = (data_fim - data_inicio).days + 1

        foto_filename = None
        if "foto_atestado" in request.files:
            foto = request.files["foto_atestado"]
            if foto and foto.filename:
                ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "bmp"}
                MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB

                if "." not in foto.filename or foto.filename.rsplit(".", 1)[1].lower() not in ALLOWED_IMAGE_EXTENSIONS:
                    flash("Tipo de arquivo não permitido. Use imagens (PNG, JPG, JPEG, GIF).", "warning")
                    return redirect(url_for("ciclos.index", collaborator_id=cid))

                foto.seek(0, 2)
                size = foto.tell()
                foto.seek(0)
                if size > MAX_UPLOAD_SIZE:
                    flash("Arquivo muito grande. Máximo 10MB.", "warning")
                    return redirect(url_for("ciclos.index", collaborator_id=cid))

                upload_dir = os.path.join("static", "uploads", "atestados")
                os.makedirs(upload_dir, exist_ok=True)
                safe_name = secure_filename(foto.filename)
                ext = safe_name.rsplit(".", 1)[1].lower() if "." in safe_name else "jpg"
                foto_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{cid}.{ext}"
                foto.save(os.path.join(upload_dir, foto_filename))

        m = MedicalCertificate()
        m.collaborator_id = cid
        m.data_inicio = data_inicio
        m.data_fim = data_fim
        m.dias = dias
        m.motivo = motivo
        m.cid = cid_code
        m.medico = medico
        m.foto_atestado = foto_filename
        m.criado_por = current_user.name or current_user.username
        db.session.add(m)
        db.session.commit()
        flash("Atestado registrado com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao registrar atestado: {e}", "danger")
        # Em caso de erro, tentar manter collaborator_id se disponível
        try:
            cid = int(request.form.get("collaborator_id", 0))
            if cid:
                return redirect(url_for("ciclos.index", collaborator_id=cid))
        except Exception:
            pass
    # Manter collaborator_id na URL para exibir os cards
    return redirect(url_for("ciclos.index", collaborator_id=cid))


@bp.route("/atestado/<int:id>/excluir", methods=["POST"], strict_slashes=False)
@login_required
def atestado_excluir(id: int):
    """Excluir atestado médico"""
    if current_user.nivel not in ("admin", "DEV"):
        flash("Acesso negado.", "danger")
        return redirect(url_for("ciclos.index"))
    m = MedicalCertificate.query.get_or_404(id)
    collaborator_id = m.collaborator_id
    try:
        if m.foto_atestado:
            path = os.path.join("static", "uploads", "atestados", m.foto_atestado)
            if os.path.exists(path):
                os.remove(path)
        db.session.delete(m)
        db.session.commit()
        flash("Atestado excluído.", "info")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao excluir: {e}", "danger")
    # Manter collaborator_id na URL para exibir os cards
    return redirect(url_for("ciclos.index", collaborator_id=collaborator_id))


@bp.route("/ferias/listar/<int:collaborator_id>", methods=["GET"], strict_slashes=False)
@login_required
def ferias_listar(collaborator_id):
    """Retorna lista de férias de um colaborador (JSON)"""
    if current_user.nivel not in ["operador", "admin", "DEV"]:
        return jsonify({"ok": False, "error": "Acesso negado"}), 403

    try:
        ferias = (
            Vacation.query.filter_by(collaborator_id=collaborator_id, ativo=True)
            .order_by(Vacation.data_inicio.desc())
            .all()
        )

        ferias_data = []
        for f in ferias:
            ferias_data.append(
                {
                    "id": f.id,
                    "data_inicio": f.data_inicio.strftime("%d/%m/%Y"),
                    "data_fim": f.data_fim.strftime("%d/%m/%Y"),
                    "observacao": f.observacao or "-",
                }
            )

        return jsonify({"ok": True, "ferias": ferias_data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.route("/atestado/listar/<int:collaborator_id>", methods=["GET"], strict_slashes=False)
@login_required
def atestado_listar(collaborator_id):
    """Retorna lista de atestados de um colaborador (JSON)"""
    if current_user.nivel not in ["operador", "admin", "DEV"]:
        return jsonify({"ok": False, "error": "Acesso negado"}), 403

    try:
        atestados = (
            MedicalCertificate.query.filter_by(collaborator_id=collaborator_id)
            .order_by(MedicalCertificate.data_inicio.desc())
            .all()
        )

        atestados_data = []
        for a in atestados:
            atestados_data.append(
                {
                    "id": a.id,
                    "data_inicio": a.data_inicio.strftime("%d/%m/%Y"),
                    "data_fim": a.data_fim.strftime("%d/%m/%Y"),
                    "dias": a.dias,
                    "motivo": a.motivo or "-",
                    "cid": a.cid or "-",
                    "medico": a.medico or "-",
                    "foto_atestado": a.foto_atestado,
                }
            )

        return jsonify({"ok": True, "atestados": atestados_data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ============================================================================
# Rotas de PDF
# ============================================================================


@bp.route("/pdf/individual/<int:collaborator_id>", methods=["GET"], strict_slashes=False)
@login_required
def pdf_individual(collaborator_id):
    """Gera PDF individual do histórico completo do colaborador"""
    if not WEASYPRINT_AVAILABLE:
        flash("WeasyPrint não está disponível.", "danger")
        return redirect(url_for("ciclos.index"))

    if current_user.nivel not in ["operador", "admin", "DEV"]:
        flash("Acesso negado.", "danger")
        return redirect(url_for("ciclos.index"))

    try:
        import sys

        base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

        collaborator = Collaborator.query.get_or_404(collaborator_id)

        # Buscar todos os registros ativos do colaborador
        registros = (
            _get_active_ciclos_query(collaborator_id).order_by(Ciclo.data_lancamento.desc(), Ciclo.id.desc()).all()
        )

        # Calcular saldo
        balance = _calculate_collaborator_balance(collaborator_id)

        # Configurações
        nome_empresa = _get_nome_empresa()
        valor_dia = _get_valor_dia()

        # Buscar primeiro ciclo_id disponível (próximo ciclo ou 1 se não houver fechamentos)
        ultimo_fechamento = CicloFechamento.query.order_by(CicloFechamento.ciclo_id.desc()).first()
        ciclo_id = (ultimo_fechamento.ciclo_id + 1) if ultimo_fechamento else 1

        # Buscar primeira data de lançamento dos registros ativos para determinar mês de início
        if registros:
            primeira_data = min(reg.data_lancamento for reg in registros)
            mes_inicio = primeira_data.strftime("%B")
            # Converter para português
            meses_pt = {
                "January": "Janeiro",
                "February": "Fevereiro",
                "March": "Março",
                "April": "Abril",
                "May": "Maio",
                "June": "Junho",
                "July": "Julho",
                "August": "Agosto",
                "September": "Setembro",
                "October": "Outubro",
                "November": "Novembro",
                "December": "Dezembro",
            }
            mes_inicio = meses_pt.get(mes_inicio, mes_inicio)
        else:
            mes_inicio = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%B")
            meses_pt = {
                "January": "Janeiro",
                "February": "Fevereiro",
                "March": "Março",
                "April": "Abril",
                "May": "Maio",
                "June": "Junho",
                "July": "Julho",
                "August": "Agosto",
                "September": "Setembro",
                "October": "Outubro",
                "November": "Novembro",
                "December": "Dezembro",
            }
            mes_inicio = meses_pt.get(mes_inicio, mes_inicio)

        # Caminhos das logos - usar caminhos relativos ao base_dir
        logo_header_path = os.path.join(base_dir, "static", "icons", "logo black.png")
        # Usar caminho relativo ao base_dir para o WeasyPrint
        if os.path.exists(logo_header_path):
            # Caminho relativo ao base_dir (ex: static/icons/logo black.png)
            logo_header = os.path.relpath(logo_header_path, base_dir).replace("\\", "/")
        else:
            logo_header = None
        logo_footer = None  # Removido por questões judiciais

        html = render_template(
            "ciclos/pdf_individual.html",
            collaborator=collaborator,
            registros=registros,
            balance=balance,
            nome_empresa=nome_empresa,
            valor_dia=valor_dia,
            ciclo_id=ciclo_id,
            mes_inicio=mes_inicio,
            logo_header=logo_header,
            logo_footer=logo_footer,
            data_geracao=datetime.now(ZoneInfo("America/Sao_Paulo")),
        )

        # Passar base_url para o WeasyPrint resolver caminhos relativos corretamente
        if not WEASYPRINT_AVAILABLE or HTML is None:
            flash("WeasyPrint não está disponível. Não é possível gerar PDF.", "danger")
            return redirect(url_for("ciclos.index"))
        base_url = str(base_dir) if base_dir else os.getcwd()
        pdf = HTML(string=html, base_url=base_url).write_pdf()

        response = make_response(pdf)
        response.headers["Content-Type"] = "application/pdf"
        response.headers[
            "Content-Disposition"
        ] = f'inline; filename=ciclo_individual_{collaborator.name.replace(" ", "_")}.pdf'

        return response

    except Exception as e:
        flash(f"Erro ao gerar PDF: {str(e)}", "danger")
        return redirect(url_for("ciclos.index"))


@bp.route("/pdf/geral", methods=["GET"], strict_slashes=False)
@login_required
def pdf_geral():
    """Gera PDF geral com resumo de todos os colaboradores do ciclo"""
    if not WEASYPRINT_AVAILABLE:
        flash("WeasyPrint não está disponível.", "danger")
        return redirect(url_for("ciclos.index"))

    if current_user.nivel not in ["operador", "admin", "DEV"]:
        flash("Acesso negado.", "danger")
        return redirect(url_for("ciclos.index"))

    try:
        import sys

        base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

        colaboradores = _get_all_collaborators()
        colaboradores_resumo = []

        valor_dia = _get_valor_dia()

        # Buscar primeiro ciclo_id disponível (próximo ciclo ou 1 se não houver fechamentos)
        ultimo_fechamento = CicloFechamento.query.order_by(CicloFechamento.ciclo_id.desc()).first()
        ciclo_id = (ultimo_fechamento.ciclo_id + 1) if ultimo_fechamento else 1

        # Buscar primeira data de lançamento dos registros ativos para determinar mês de início
        primeira_data = Ciclo.query.filter(Ciclo.status_ciclo == "ativo").order_by(Ciclo.data_lancamento.asc()).first()
        if primeira_data:
            mes_inicio = primeira_data.data_lancamento.strftime("%B")
            # Converter para português
            meses_pt = {
                "January": "Janeiro",
                "February": "Fevereiro",
                "March": "Março",
                "April": "Abril",
                "May": "Maio",
                "June": "Junho",
                "July": "Julho",
                "August": "Agosto",
                "September": "Setembro",
                "October": "Outubro",
                "November": "Novembro",
                "December": "Dezembro",
            }
            mes_inicio = meses_pt.get(mes_inicio, mes_inicio)
        else:
            mes_inicio = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%B")
            meses_pt = {
                "January": "Janeiro",
                "February": "Fevereiro",
                "March": "Março",
                "April": "Abril",
                "May": "Maio",
                "June": "Junho",
                "July": "Julho",
                "August": "Agosto",
                "September": "Setembro",
                "October": "Outubro",
                "November": "Novembro",
                "December": "Dezembro",
            }
            mes_inicio = meses_pt.get(mes_inicio, mes_inicio)

        for colab in colaboradores:
            balance = _calculate_collaborator_balance(colab.id)

            # Buscar registros ativos usando helper (ordenados por data)
            registros = _get_active_ciclos_query(colab.id).order_by(Ciclo.data_lancamento.asc(), Ciclo.id.asc()).all()

            if len(registros) > 0:  # Só incluir se tiver registros
                colaboradores_resumo.append(
                    {
                        "collaborator": colab,
                        "balance": balance,
                        "registros": registros,  # Incluir registros detalhados
                        "registros_count": len(registros),
                    }
                )

        # Totais gerais
        total_horas_geral = sum(r["balance"]["total_horas"] for r in colaboradores_resumo)
        total_dias_geral = sum(r["balance"]["dias_completos"] for r in colaboradores_resumo)
        total_horas_restantes_geral = sum(r["balance"]["horas_restantes"] for r in colaboradores_resumo)
        total_valor_geral = sum(r["balance"]["valor_aproximado"] for r in colaboradores_resumo)

        # Configurações
        nome_empresa = _get_nome_empresa()

        # Caminhos das logos - usar caminhos relativos ao base_dir
        logo_header_path = os.path.join(base_dir, "static", "icons", "logo black.png")
        # Usar caminho relativo ao base_dir para o WeasyPrint
        if os.path.exists(logo_header_path):
            # Caminho relativo ao base_dir (ex: static/icons/logo black.png)
            logo_header = os.path.relpath(logo_header_path, base_dir).replace("\\", "/")
        else:
            logo_header = None
        logo_footer = None  # Removido por questões judiciais

        html = render_template(
            "ciclos/pdf_geral.html",
            colaboradores_resumo=colaboradores_resumo,
            total_horas_geral=total_horas_geral,
            total_dias_geral=total_dias_geral,
            total_horas_restantes_geral=total_horas_restantes_geral,
            total_valor_geral=total_valor_geral,
            nome_empresa=nome_empresa,
            valor_dia=valor_dia,
            ciclo_id=ciclo_id,
            mes_inicio=mes_inicio,
            logo_header=logo_header,
            logo_footer=logo_footer,
            data_geracao=datetime.now(ZoneInfo("America/Sao_Paulo")),
        )

        # Passar base_url para o WeasyPrint resolver caminhos relativos corretamente
        if not WEASYPRINT_AVAILABLE or HTML is None:
            flash("WeasyPrint não está disponível. Não é possível gerar PDF.", "danger")
            return redirect(url_for("ciclos.index"))
        base_url = str(base_dir) if base_dir else os.getcwd()
        pdf = HTML(string=html, base_url=base_url).write_pdf()

        response = make_response(pdf)
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = "inline; filename=ciclo_geral.pdf"

        return response

    except Exception as e:
        flash(f"Erro ao gerar PDF: {str(e)}", "danger")
        return redirect(url_for("ciclos.index"))
