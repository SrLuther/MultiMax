"""
Rotas para gerenciar Escalas Especiais/Futuras
Permite criar, editar, deletar e visualizar escalas especiais como:
- Limpeza fora do horário normal
- Horários redistribuídos em feriados
- Eventos especiais
- Redistribuições de equipe
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from .. import db
from ..models import Collaborator, EscalaEspecial

bp = Blueprint("escala_especial", __name__, url_prefix="/escala-especial")


@bp.route("/", methods=["GET"])
@login_required
def pagina_escala_especial():
    """Renderiza a página de escalas especiais"""
    return render_template("escala_especial.html")


# ============================================================================
# ROTAS DE API
# ============================================================================

api_bp = Blueprint("escala_especial_api", __name__, url_prefix="/api/escala-especial")


@api_bp.route("/", methods=["GET"])
@login_required
def listar_escalas_especiais():
    """Lista todas as escalas especiais"""
    try:
        # Filtros opcionais
        ativo = request.args.get("ativo", type=lambda x: x.lower() == "true", default=None)
        tipo = request.args.get("tipo", type=str, default=None)
        data_inicio = request.args.get("data_inicio", type=str, default=None)

        query = EscalaEspecial.query

        if ativo is not None:
            query = query.filter_by(ativo=ativo)

        if tipo:
            query = query.filter_by(tipo=tipo)

        if data_inicio:
            try:
                data_inicio_obj = datetime.fromisoformat(data_inicio).date()
                query = query.filter(EscalaEspecial.data_inicio >= data_inicio_obj)
            except ValueError:
                pass

        # Ordena por data de início (mais próximas primeiro)
        escalas = query.order_by(EscalaEspecial.data_inicio).all()

        return jsonify({"status": "success", "data": [e.to_dict() for e in escalas], "total": len(escalas)})

    except Exception as e:
        return jsonify({"status": "error", "message": f"Erro ao listar escalas: {str(e)}"}), 500


@api_bp.route("/", methods=["POST"])
@login_required
def criar_escala_especial():
    """Cria uma nova escala especial"""
    try:
        data = request.get_json()

        # Validações
        if not data.get("nome"):
            return jsonify({"status": "error", "message": "Nome é obrigatório"}), 400

        if not data.get("tipo"):
            return jsonify({"status": "error", "message": "Tipo é obrigatório"}), 400

        if not data.get("data_inicio") or not data.get("data_fim"):
            return jsonify({"status": "error", "message": "Data início e fim são obrigatórias"}), 400

        try:
            data_inicio = datetime.fromisoformat(data["data_inicio"]).date()
            data_fim = datetime.fromisoformat(data["data_fim"]).date()
        except ValueError:
            return jsonify({"status": "error", "message": "Formato de data inválido"}), 400

        if data_inicio > data_fim:
            return jsonify({"status": "error", "message": "Data início não pode ser após data fim"}), 400

        # Cria a escala especial
        escala = EscalaEspecial(
            nome=data.get("nome"),
            descricao=data.get("descricao", ""),
            tipo=data.get("tipo"),
            data_inicio=data_inicio,
            data_fim=data_fim,
            turno_customizado=data.get("turno_customizado"),
            criterio_atribuicao=data.get("criterio_atribuicao", "todos"),
            equipe_id=data.get("equipe_id"),
            numero_pessoas=data.get("numero_pessoas"),
            colaboradores_selecionados=data.get("colaboradores_selecionados"),
            ativo=data.get("ativo", True),
            criado_por=current_user.username if hasattr(current_user, "username") else "sistema",
        )

        db.session.add(escala)
        db.session.commit()

        return (
            jsonify({"status": "success", "message": "Escala especial criada com sucesso", "data": escala.to_dict()}),
            201,
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Erro ao criar escala: {str(e)}"}), 500


@api_bp.route("/<int:escala_id>", methods=["GET"])
@login_required
def obter_escala_especial(escala_id):
    """Obtém detalhes de uma escala especial"""
    try:
        escala = EscalaEspecial.query.get(escala_id)

        if not escala:
            return jsonify({"status": "error", "message": "Escala não encontrada"}), 404

        return jsonify({"status": "success", "data": escala.to_dict()})

    except Exception as e:
        return jsonify({"status": "error", "message": f"Erro ao obter escala: {str(e)}"}), 500


@api_bp.route("/<int:escala_id>", methods=["PUT"])
@login_required
def atualizar_escala_especial(escala_id):
    """Atualiza uma escala especial existente"""
    try:
        escala = EscalaEspecial.query.get(escala_id)

        if not escala:
            return jsonify({"status": "error", "message": "Escala não encontrada"}), 404

        data = request.get_json()

        # Atualiza campos
        if "nome" in data:
            escala.nome = data["nome"]

        if "descricao" in data:
            escala.descricao = data["descricao"]

        if "tipo" in data:
            escala.tipo = data["tipo"]

        if "data_inicio" in data:
            try:
                escala.data_inicio = datetime.fromisoformat(data["data_inicio"]).date()
            except ValueError:
                return jsonify({"status": "error", "message": "Formato de data_inicio inválido"}), 400

        if "data_fim" in data:
            try:
                escala.data_fim = datetime.fromisoformat(data["data_fim"]).date()
            except ValueError:
                return jsonify({"status": "error", "message": "Formato de data_fim inválido"}), 400

        if escala.data_inicio > escala.data_fim:
            return jsonify({"status": "error", "message": "Data início não pode ser após data fim"}), 400

        if "turno_customizado" in data:
            escala.turno_customizado = data["turno_customizado"]

        if "criterio_atribuicao" in data:
            escala.criterio_atribuicao = data["criterio_atribuicao"]

        if "equipe_id" in data:
            escala.equipe_id = data.get("equipe_id")

        if "numero_pessoas" in data:
            escala.numero_pessoas = data.get("numero_pessoas")

        if "colaboradores_selecionados" in data:
            escala.colaboradores_selecionados = data.get("colaboradores_selecionados")

        if "ativo" in data:
            escala.ativo = data["ativo"]

        escala.atualizado_em = datetime.now(ZoneInfo("America/Sao_Paulo"))
        db.session.commit()

        return jsonify(
            {"status": "success", "message": "Escala especial atualizada com sucesso", "data": escala.to_dict()}
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Erro ao atualizar escala: {str(e)}"}), 500


@api_bp.route("/<int:escala_id>", methods=["DELETE"])
@login_required
def deletar_escala_especial(escala_id):
    """Deleta uma escala especial"""
    try:
        escala = EscalaEspecial.query.get(escala_id)

        if not escala:
            return jsonify({"status": "error", "message": "Escala não encontrada"}), 404

        db.session.delete(escala)
        db.session.commit()

        return jsonify({"status": "success", "message": "Escala especial deletada com sucesso"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Erro ao deletar escala: {str(e)}"}), 500


@api_bp.route("/tipos", methods=["GET"])
@login_required
def get_tipos_escala():
    """Retorna os tipos de escala disponíveis"""
    tipos = [
        {"id": "limpeza", "nome": "Limpeza Especial", "descricao": "Limpeza fora do horário normal"},
        {"id": "feriado", "nome": "Feriado", "descricao": "Horários redistribuídos para feriado"},
        {"id": "redistribuicao", "nome": "Redistribuição", "descricao": "Redistribuição de horários"},
        {"id": "evento", "nome": "Evento Especial", "descricao": "Evento que afeta a escala"},
        {"id": "manutencao", "nome": "Manutenção", "descricao": "Período de manutenção/parada"},
        {"id": "outro", "nome": "Outro", "descricao": "Outro tipo de escala especial"},
    ]

    return jsonify({"status": "success", "data": tipos})


@api_bp.route("/criterios", methods=["GET"])
@login_required
def get_criterios_atribuicao():
    """Retorna os critérios de atribuição disponíveis"""
    criterios = [
        {"id": "todos", "nome": "Todos os Colaboradores", "descricao": "Aplica a toda equipe"},
        {"id": "por_equipe", "nome": "Por Equipe", "descricao": "Aplica apenas a uma equipe/setor"},
        {"id": "por_numero", "nome": "Por Número", "descricao": "Seleciona N colaboradores"},
        {"id": "manual", "nome": "Manual", "descricao": "Seleciona colaboradores específicos"},
    ]

    return jsonify({"status": "success", "data": criterios})


@api_bp.route("/aplicar/<int:escala_id>", methods=["POST"])
@login_required
def aplicar_escala_especial(escala_id):
    """
    Aplica uma escala especial aos colaboradores
    Cria as entradas de turno (Shift) baseado na escala especial
    """
    try:
        from ..models import Shift

        escala = EscalaEspecial.query.get(escala_id)

        if not escala:
            return jsonify({"status": "error", "message": "Escala não encontrada"}), 404

        # Determina quais colaboradores serão afetados
        colaboradores = _obter_colaboradores_para_escala(escala)

        if not colaboradores:
            return jsonify({"status": "error", "message": "Nenhum colaborador selecionado"}), 400

        # Cria turnos para cada dia do período
        shifts_criados = 0
        data_atual = escala.data_inicio

        while data_atual <= escala.data_fim:
            for colab in colaboradores:
                # Verifica se já existe turno nesse dia para este colaborador
                turno_existente = Shift.query.filter_by(collaborator_id=colab.id, date=data_atual).first()

                if turno_existente:
                    # Atualiza o turno existente
                    turno_existente.shift_type = escala.turno_customizado or "especial"
                    turno_existente.descricao = f"[{escala.tipo.upper()}] {escala.nome}"
                else:
                    # Cria novo turno
                    novo_turno = Shift(
                        collaborator_id=colab.id,
                        date=data_atual,
                        shift_type=escala.turno_customizado or "especial",
                        turno=escala.turno_customizado or "Especial",
                        descricao=f"[{escala.tipo.upper()}] {escala.nome}",
                    )
                    db.session.add(novo_turno)

                shifts_criados += 1

            data_atual = data_atual + timedelta(days=1)

        db.session.commit()

        return jsonify(
            {
                "status": "success",
                "message": f"Escala aplicada com sucesso! {shifts_criados} turnos criados/atualizados",
                "turnos_criados": shifts_criados,
            }
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Erro ao aplicar escala: {str(e)}"}), 500


@api_bp.route("/remover/<int:escala_id>", methods=["POST"])
@login_required
def remover_aplicacao_escala(escala_id):
    """
    Remove a aplicação de uma escala especial
    Deleta os turnos criados pela escala
    """
    try:
        from ..models import Shift

        escala = EscalaEspecial.query.get(escala_id)

        if not escala:
            return jsonify({"status": "error", "message": "Escala não encontrada"}), 404

        # Obtém colaboradores da escala
        colaboradores = _obter_colaboradores_para_escala(escala)

        # Remove os turnos criados pela escala
        turnos_removidos = 0
        data_atual = escala.data_inicio

        while data_atual <= escala.data_fim:
            for colab in colaboradores:
                turno = Shift.query.filter_by(collaborator_id=colab.id, date=data_atual).first()

                if turno and f"[{escala.tipo.upper()}]" in (turno.descricao or ""):
                    db.session.delete(turno)
                    turnos_removidos += 1

            data_atual = data_atual + timedelta(days=1)

        db.session.commit()

        return jsonify(
            {"status": "success", "message": f"Aplicação removida com sucesso! {turnos_removidos} turnos removidos"}
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Erro ao remover aplicação: {str(e)}"}), 500


def _obter_colaboradores_para_escala(escala):
    """Helper para determinar quais colaboradores serão afetados pela escala"""
    colaboradores = []

    if escala.criterio_atribuicao == "todos":
        # Todos os colaboradores ativos
        colaboradores = Collaborator.query.filter_by(ativo=True).all()

    elif escala.criterio_atribuicao == "por_equipe":
        # Colaboradores de uma equipe específica
        if escala.equipe_id:
            colaboradores = Collaborator.query.filter_by(ativo=True, setor_id=escala.equipe_id).all()

    elif escala.criterio_atribuicao == "por_numero":
        # Primeiros N colaboradores
        if escala.numero_pessoas:
            colaboradores = Collaborator.query.filter_by(ativo=True).limit(escala.numero_pessoas).all()

    elif escala.criterio_atribuicao == "manual":
        # Colaboradores selecionados manualmente
        if escala.colaboradores_selecionados:
            colaboradores = Collaborator.query.filter(Collaborator.id.in_(escala.colaboradores_selecionados)).all()

    return colaboradores
