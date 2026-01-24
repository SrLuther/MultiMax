"""
Serviço para gerenciar saldos de horas mensais no sistema de ciclos.

Responsabilidades:
1. Calcular e armazenar saldo ao fechar ciclo mensal
2. Recuperar e aplicar saldo anterior ao iniciar novo mês
3. Converter horas em exibição visual de dias e horas
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import and_

from .. import db
from ..models import CicloSaldo, Collaborator


def _format_mes_ano(data: Optional[datetime] = None) -> str:
    """
    Formata data como "MM-YYYY" (ex: "01-2026").
    Se data for None, usa a data atual.
    """
    if data is None:
        data = datetime.now(ZoneInfo("America/Sao_Paulo"))
    return data.strftime("%m-%Y")


def _format_mes_ano_anterior(data: Optional[datetime] = None) -> str:
    """
    Retorna o mês anterior no formato "MM-YYYY".
    Se data for None, usa a data atual.
    """
    if data is None:
        data = datetime.now(ZoneInfo("America/Sao_Paulo"))

    # Retroceder um mês
    month = data.month - 1
    year = data.year
    if month == 0:
        month = 12
        year -= 1

    # Formatar como "MM-YYYY"
    return f"{month:02d}-{year}"


def calcular_saldo_mensal(total_horas: float) -> float:
    """
    Calcula o saldo de horas (resto da divisão por 8).
    Ex: 9.5 horas -> 1.5 horas de saldo
    Ex: 16 horas -> 0 horas de saldo
    Ex: 7.5 horas -> 7.5 horas de saldo (sem dias completos)
    """
    if total_horas < 0:
        return total_horas  # Se negativo, é dívida
    return float(Decimal(str(total_horas)) % Decimal("8.0"))


def registrar_saldo(
    collaborator_id: int,
    mes_ano: str,
    saldo: float,
    usuario: Optional[str] = None,
) -> CicloSaldo:
    """
    Registra ou atualiza o saldo de horas para um colaborador em um mês específico.

    Args:
        collaborator_id: ID do colaborador
        mes_ano: Mês no formato "MM-YYYY"
        saldo: Valor do saldo em horas
        usuario: Usuário que fez a operação

    Returns:
        CicloSaldo: Registro criado ou atualizado
    """
    # Tentar encontrar saldo existente
    saldo_existente: Optional[CicloSaldo] = CicloSaldo.query.filter(
        and_(CicloSaldo.collaborator_id == collaborator_id, CicloSaldo.mes_ano == mes_ano)
    ).first()

    if saldo_existente:
        # Atualizar saldo existente
        saldo_existente.saldo = Decimal(str(round(saldo, 1)))
        saldo_existente.updated_at = datetime.now(ZoneInfo("America/Sao_Paulo"))
        saldo_existente.updated_by = usuario
        db.session.add(saldo_existente)
        return saldo_existente
    else:
        # Criar novo saldo
        novo_saldo: CicloSaldo = CicloSaldo()
        novo_saldo.collaborator_id = collaborator_id
        novo_saldo.mes_ano = mes_ano
        novo_saldo.saldo = Decimal(str(round(saldo, 1)))
        novo_saldo.created_by = usuario
        db.session.add(novo_saldo)
        return novo_saldo


def obter_saldo_anterior(collaborator_id: int, data_referencia: Optional[datetime] = None) -> float:
    """
    Obtém o saldo do mês anterior para um colaborador.

    Args:
        collaborator_id: ID do colaborador
        data_referencia: Data para calcular mês anterior (default: agora)

    Returns:
        float: Saldo anterior em horas (pode ser negativo)
    """
    mes_anterior = _format_mes_ano_anterior(data_referencia)

    saldo_record = CicloSaldo.query.filter(
        and_(CicloSaldo.collaborator_id == collaborator_id, CicloSaldo.mes_ano == mes_anterior)
    ).first()

    if saldo_record:
        return float(saldo_record.saldo)
    else:
        return 0.0  # Sem histórico = saldo zero


def aplicar_saldo_anterior(
    collaborator_id: int,
    mes_ano_atual: str,
) -> dict:
    """
    Calcula e retorna o saldo anterior que será aplicado no mês atual.
    Não modifica o banco de dados nesta função (apenas leitura).

    Args:
        collaborator_id: ID do colaborador
        mes_ano_atual: Mês atual no formato "MM-YYYY"

    Returns:
        dict com:
            - 'saldo_anterior': float - Saldo do mês anterior
            - 'mes_anterior': str - Mês anterior no formato "MM-YYYY"
    """
    # Calcular mês anterior a partir do atual
    partes = mes_ano_atual.split("-")
    mes_atual = int(partes[0])
    ano_atual = int(partes[1])

    mes_anterior = mes_atual - 1
    ano_anterior = ano_atual
    if mes_anterior == 0:
        mes_anterior = 12
        ano_anterior -= 1

    mes_anterior_str = f"{mes_anterior:02d}-{ano_anterior}"

    # Buscar saldo
    saldo_anterior = obter_saldo_anterior(collaborator_id)

    return {
        "saldo_anterior": saldo_anterior,
        "mes_anterior": mes_anterior_str,
    }


def resumo_em_dias_e_horas(total_horas: float) -> str:
    """
    Converte total de horas para exibição em "X dias e Y horas".
    Esta é uma conversão APENAS VISUAL, não altera dados.

    Exemplos:
    - 8.0 horas -> "1 dia"
    - 9.5 horas -> "1 dia e 1h30min"
    - 16.0 horas -> "2 dias"
    - 7.5 horas -> "7h30min"
    - 0 horas -> "Sem horas"
    - -8.0 horas -> "-1 dia" (dívida)

    Args:
        total_horas: Total de horas (pode ser negativo)

    Returns:
        str: String formatada para exibição
    """
    if total_horas == 0:
        return "Sem horas"

    # Verificar se é negativo (dívida)
    eh_negativo = total_horas < 0
    horas_abs = abs(total_horas)

    # Calcular dias e horas restantes
    dias_completos = int(horas_abs // 8)
    horas_restantes = horas_abs % 8

    # Converter horas restantes em "H:MM" (ex: 1.5 -> "1h30min")
    horas_int = int(horas_restantes)
    minutos = int((horas_restantes - horas_int) * 60)

    # Construir string
    partes = []

    if dias_completos > 0:
        if dias_completos == 1:
            partes.append("1 dia")
        else:
            partes.append(f"{dias_completos} dias")

    if horas_int > 0 or minutos > 0:
        if minutos == 0:
            partes.append(f"{horas_int}h")
        else:
            partes.append(f"{horas_int}h{minutos}min")

    resultado = " e ".join(partes)

    # Adicionar prefixo se for negativo
    if eh_negativo:
        resultado = f"-{resultado}"

    return resultado


def fechar_ciclo_mensal(
    colaboradores_totais: dict,
    mes_ano: str,
    usuario: Optional[str] = None,
) -> dict:
    """
    Função chamada ao fechar ciclo mensal.
    Calcula e armazena saldo de horas para cada colaborador.

    Args:
        colaboradores_totais: Dict com dados dos colaboradores (mesmo formato da função _agrupar_e_calcular_totais)
        mes_ano: Mês em formato "MM-YYYY"
        usuario: Usuário que realizou o fechamento

    Returns:
        dict com:
            - 'saldos_registrados': list de CicloSaldo criados/atualizados
            - 'resumo_saldos': dict com resumo visual dos saldos
    """
    saldos_registrados = []
    resumo_saldos = {}

    for cid, dados in colaboradores_totais.items():
        total_horas = float(dados["total_horas"])

        # Calcular saldo (resto da divisão por 8)
        saldo = calcular_saldo_mensal(total_horas)

        # Registrar no banco
        saldo_record = registrar_saldo(cid, mes_ano, saldo, usuario)
        saldos_registrados.append(saldo_record)

        # Preparar resumo visual
        resumo_saldos[cid] = {
            "nome": dados["nome"],
            "total_horas": total_horas,
            "saldo": saldo,
            "saldo_visual": resumo_em_dias_e_horas(saldo),
        }

    return {
        "saldos_registrados": saldos_registrados,
        "resumo_saldos": resumo_saldos,
    }


def obter_saldo_para_exibicao(collaborator_id: int, mes_ano: Optional[str] = None) -> dict:
    """
    Obtém informações de saldo para exibição em tela ou PDF.

    Args:
        collaborator_id: ID do colaborador
        mes_ano: Mês no formato "MM-YYYY" (default: mês atual)

    Returns:
        dict com:
            - 'saldo_horas': float - Saldo em horas
            - 'saldo_visual': str - Saldo em formato visual (dias e horas)
            - 'mes_ano': str - Mês
    """
    if mes_ano is None:
        mes_ano = _format_mes_ano()

    saldo_record = CicloSaldo.query.filter(
        and_(CicloSaldo.collaborator_id == collaborator_id, CicloSaldo.mes_ano == mes_ano)
    ).first()

    saldo_horas = float(saldo_record.saldo) if saldo_record else 0.0

    return {
        "saldo_horas": saldo_horas,
        "saldo_visual": resumo_em_dias_e_horas(saldo_horas),
        "mes_ano": mes_ano,
    }


# ==============================================================================
# Função de integração com ciclo_saldo_service
# ==============================================================================


def integrar_com_fechamento_ciclo(
    colaboradores_totais: dict,
    mes_ano: str,
    usuario: Optional[str] = None,
) -> dict:
    """
    Função completa que integra o sistema de saldo com o fechamento de ciclo.
    Deve ser chamada ao final de _registrar_fechamento_e_log().

    Args:
        colaboradores_totais: Dict com dados dos colaboradores
        mes_ano: Mês em formato "MM-YYYY"
        usuario: Usuário que realizou o fechamento

    Returns:
        dict com resultado da operação
    """
    return fechar_ciclo_mensal(colaboradores_totais, mes_ano, usuario)


def gerar_relatorio_saldos(mes_ano: Optional[str] = None) -> dict:
    """
    Gera relatório de saldos de todos os colaboradores para um mês.
    Útil para relatórios e auditoria.

    Args:
        mes_ano: Mês no formato "MM-YYYY" (default: mês atual)

    Returns:
        dict com:
            - 'mes_ano': str
            - 'saldos': list de dicts com informações de saldo
            - 'total_saldo': float
            - 'colaboradores_com_saldo': int
    """
    if mes_ano is None:
        mes_ano = _format_mes_ano()

    saldos = CicloSaldo.query.filter(CicloSaldo.mes_ano == mes_ano).all()

    total_saldo = 0.0
    saldos_list = []

    for saldo_record in saldos:
        saldo_horas = float(saldo_record.saldo)
        total_saldo += saldo_horas

        colaborador = Collaborator.query.get(saldo_record.collaborator_id)
        colaborador_nome = colaborador.name if colaborador else "Desconhecido"

        saldos_list.append(
            {
                "collaborator_id": saldo_record.collaborator_id,
                "nome": colaborador_nome,
                "saldo_horas": saldo_horas,
                "saldo_visual": resumo_em_dias_e_horas(saldo_horas),
                "created_at": saldo_record.created_at.isoformat() if saldo_record.created_at else None,
                "created_by": saldo_record.created_by,
            }
        )

    return {
        "mes_ano": mes_ano,
        "saldos": sorted(saldos_list, key=lambda x: x["nome"]),
        "total_saldo": total_saldo,
        "total_saldo_visual": resumo_em_dias_e_horas(total_saldo),
        "colaboradores_com_saldo": len(saldos_list),
    }


def aplicar_saldos_anteriores_ciclo_novo(
    colaboradores_ids: list[int],
    novo_mes_ano: Optional[str] = None,
) -> dict:
    """
    Para uso ao INICIAR novo ciclo mensal.
    Retorna informações sobre saldos anteriores que devem ser aplicados
    (Para ser usado em visualização/relatório, não modifica dados).

    Args:
        colaboradores_ids: Lista de IDs de colaboradores
        novo_mes_ano: Mês do novo ciclo (default: mês atual)

    Returns:
        dict com:
            - 'novo_mes': str
            - 'mes_anterior': str
            - 'saldos_aplicaveis': list de dicts com saldo anterior de cada colaborador
            - 'total_saldo_anterior': float
    """
    if novo_mes_ano is None:
        novo_mes_ano = _format_mes_ano()

    # Calcular mês anterior
    partes = novo_mes_ano.split("-")
    mes_novo = int(partes[0])
    ano_novo = int(partes[1])

    mes_anterior = mes_novo - 1
    ano_anterior = ano_novo
    if mes_anterior == 0:
        mes_anterior = 12
        ano_anterior -= 1

    mes_anterior_str = f"{mes_anterior:02d}-{ano_anterior}"

    saldos_aplicaveis = []
    total_saldo_anterior = 0.0

    for collab_id in colaboradores_ids:
        saldo_anterior_val = obter_saldo_anterior(collab_id)

        if saldo_anterior_val != 0:  # Só incluir se houver saldo
            colaborador = Collaborator.query.get(collab_id)
            colaborador_nome = colaborador.name if colaborador else "Desconhecido"

            saldos_aplicaveis.append(
                {
                    "collaborator_id": collab_id,
                    "nome": colaborador_nome,
                    "saldo_anterior": saldo_anterior_val,
                    "saldo_anterior_visual": resumo_em_dias_e_horas(saldo_anterior_val),
                }
            )

            total_saldo_anterior += saldo_anterior_val

    return {
        "novo_mes": novo_mes_ano,
        "mes_anterior": mes_anterior_str,
        "saldos_aplicaveis": sorted(saldos_aplicaveis, key=lambda x: x["nome"]),
        "total_saldo_anterior": total_saldo_anterior,
        "total_saldo_anterior_visual": resumo_em_dias_e_horas(total_saldo_anterior),
    }
