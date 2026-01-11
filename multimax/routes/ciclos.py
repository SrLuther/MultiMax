from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, make_response
from flask_login import login_required, current_user
from .. import db
from ..models import Collaborator, Ciclo, CicloFechamento, Vacation, MedicalCertificate, AppSetting, SystemLog, Holiday
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import func, or_, and_
from decimal import Decimal, ROUND_HALF_UP
import math
import os

try:
    from weasyprint import HTML  # type: ignore
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    HTML = None  # type: ignore

bp = Blueprint('ciclos', __name__, url_prefix='/ciclos')

# ============================================================================
# Funções auxiliares
# ============================================================================

def _get_all_collaborators():
    """Retorna todos os colaboradores ativos"""
    return Collaborator.query.filter_by(active=True).order_by(Collaborator.name.asc()).all()

def _calculate_collaborator_balance(collaborator_id):
    """Calcula saldo do colaborador (horas totais, dias completos, horas restantes, valor aproximado)"""
    # Buscar apenas registros ativos do ciclo atual
    ciclos_ativos = Ciclo.query.filter(
        Ciclo.collaborator_id == collaborator_id,
        Ciclo.status_ciclo == 'ativo'
    ).all()
    
    total_horas = Decimal('0.0')
    for ciclo in ciclos_ativos:
        total_horas += Decimal(str(ciclo.valor_horas))
    
    # Calcular dias completos (floor de total_horas / 8)
    dias_completos = int(math.floor(float(total_horas) / 8.0))
    
    # Horas restantes (< 8h não entram na conversão)
    horas_restantes = float(total_horas) % 8.0
    
    # Valor aproximado (dias_completos * valor_dia)
    valor_dia = Decimal(str(_get_valor_dia()))
    valor_aproximado = Decimal(str(dias_completos)) * valor_dia
    
    return {
        'total_horas': float(total_horas),
        'dias_completos': dias_completos,
        'horas_restantes': round(horas_restantes, 1),
        'valor_aproximado': float(valor_aproximado)
    }

def _get_valor_dia():
    """Obtém valor de 1 dia (8h) em R$"""
    try:
        setting = AppSetting.query.filter_by(key='ciclo_valor_dia').first()
        if setting and setting.value:
            return float(setting.value)
    except Exception:
        pass
    return 65.0  # Valor padrão

def _get_nome_empresa():
    """Obtém nome da empresa"""
    try:
        setting = AppSetting.query.filter_by(key='ciclo_nome_empresa').first()
        if setting and setting.value:
            return setting.value
    except Exception:
        pass
    return 'Thedo Max Supermercado'  # Valor padrão

def _validate_hours_format(value_str):
    """
    Valida formato de horas: somente múltiplos de 0.5, ponto como separador
    Retorna (valido, valor_decimal, erro)
    """
    if not value_str or not value_str.strip():
        return (False, None, 'Campo obrigatório')
    
    value_str = value_str.strip().replace(',', '.')  # Aceitar vírgula mas converter para ponto
    
    # Bloquear formatos inválidos: dois pontos, vírgula, decimais não múltiplos de 0.5
    if ':' in value_str:
        return (False, None, 'Formato inválido. Use apenas números inteiros ou decimais com ponto (ex.: 1 ou 1.5). Apenas múltiplos de 0.5 são permitidos.')
    
    if ',' in value_str and '.' in value_str:
        return (False, None, 'Formato inválido. Use apenas números inteiros ou decimais com ponto (ex.: 1 ou 1.5). Apenas múltiplos de 0.5 são permitidos.')
    
    try:
        valor = Decimal(value_str)
        
        # Verificar se é múltiplo de 0.5
        if valor < 0:
            return (False, None, 'Valor não pode ser negativo')
        
        # Verificar se é múltiplo de 0.5
        resto = float(valor) % 0.5
        if resto != 0.0:
            return (False, None, 'Formato inválido. Use apenas números inteiros ou decimais com ponto (ex.: 1 ou 1.5). Apenas múltiplos de 0.5 são permitidos.')
        
        return (True, valor, None)
    except (ValueError, TypeError):
        return (False, None, 'Formato inválido. Use apenas números inteiros ou decimais com ponto (ex.: 1 ou 1.5). Apenas múltiplos de 0.5 são permitidos.')

def _calculate_days_and_remaining(hours_decimal):
    """Calcula dias fechados e horas restantes a partir de horas"""
    hours_float = float(hours_decimal)
    dias_fechados = int(math.floor(hours_float / 8.0))
    horas_restantes = hours_float % 8.0
    return dias_fechados, round(horas_restantes, 1)

# ============================================================================
# Rotas principais
# ============================================================================

@bp.route('/', methods=['GET'], strict_slashes=False)
@login_required
def index():
    """Página principal de Ciclos com cards de colaboradores"""
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('home.index'))
    
    # Buscar todos os colaboradores ativos
    colaboradores = _get_all_collaborators()
    
    # Calcular saldos para cada colaborador
    colaboradores_stats = []
    for colab in colaboradores:
        balance = _calculate_collaborator_balance(colab.id)
        colaboradores_stats.append({
            'collaborator': colab,
            'balance': balance
        })
    
    # Buscar configurações
    nome_empresa = _get_nome_empresa()
    valor_dia = _get_valor_dia()
    
    # Totais gerais
    total_horas_geral = sum(s['balance']['total_horas'] for s in colaboradores_stats)
    total_dias_geral = sum(s['balance']['dias_completos'] for s in colaboradores_stats)
    total_horas_restantes_geral = sum(s['balance']['horas_restantes'] for s in colaboradores_stats)
    total_valor_geral = sum(s['balance']['valor_aproximado'] for s in colaboradores_stats)
    
    # Verificar se há registros ativos para mostrar botão de fechamento
    tem_registros_ativos = any(s['balance']['total_horas'] > 0 for s in colaboradores_stats)
    
    return render_template(
        'ciclos/index.html',
        active_page='ciclos',
        colaboradores_stats=colaboradores_stats,
        nome_empresa=nome_empresa,
        valor_dia=valor_dia,
        total_horas_geral=total_horas_geral,
        total_dias_geral=total_dias_geral,
        total_horas_restantes_geral=total_horas_restantes_geral,
        total_valor_geral=total_valor_geral,
        tem_registros_ativos=tem_registros_ativos,
        can_edit=current_user.nivel in ['admin', 'DEV']
    )

@bp.route('/lançar', methods=['POST'], strict_slashes=False)
@login_required
def lancar_horas():
    """Lançar horas para um colaborador"""
    if current_user.nivel not in ['admin', 'DEV']:
        flash('Acesso negado. Apenas administradores podem lançar horas.', 'danger')
        return redirect(url_for('ciclos.index'))
    
    try:
        collaborator_id = int(request.form.get('collaborator_id', 0))
        data_lancamento_str = request.form.get('data_lancamento', '').strip()
        origem = request.form.get('origem', '').strip()
        descricao = request.form.get('descricao', '').strip()
        valor_horas_str = request.form.get('valor_horas', '').strip()
        
        # Validações obrigatórias
        if not collaborator_id or not data_lancamento_str or not origem or not valor_horas_str:
            flash('Dados obrigatórios ausentes.', 'warning')
            return redirect(url_for('ciclos.index'))
        
        # Validar colaborador
        collaborator = Collaborator.query.get(collaborator_id)
        if not collaborator:
            flash('Colaborador não encontrado.', 'danger')
            return redirect(url_for('ciclos.index'))
        
        # Validar origem
        origens_validas = ['Domingo', 'Feriado', 'Horas adicionais', 'Outro']
        if origem not in origens_validas:
            flash('Origem inválida.', 'warning')
            return redirect(url_for('ciclos.index'))
        
        # Validar descrição se necessário
        if origem in ['Horas adicionais', 'Outro'] and not descricao:
            flash('Descrição é obrigatória para origem "Horas adicionais" ou "Outro".', 'warning')
            return redirect(url_for('ciclos.index'))
        
        # Validar formato de horas
        valido, valor_horas_decimal, erro = _validate_hours_format(valor_horas_str)
        if not valido:
            flash(erro or 'Formato inválido.', 'warning')
            return redirect(url_for('ciclos.index'))
        
        # Validar e converter data
        try:
            data_lancamento = datetime.strptime(data_lancamento_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Data inválida.', 'warning')
            return redirect(url_for('ciclos.index'))
        
        # Calcular dias fechados e horas restantes
        dias_fechados, horas_restantes = _calculate_days_and_remaining(valor_horas_decimal)
        
        # Calcular valor aproximado
        valor_dia = Decimal(str(_get_valor_dia()))
        valor_aproximado = Decimal(str(dias_fechados)) * valor_dia
        
        # Criar registro
        ciclo = Ciclo()
        ciclo.collaborator_id = collaborator_id
        ciclo.nome_colaborador = collaborator.name  # Cópia do nome
        ciclo.data_lancamento = data_lancamento
        ciclo.origem = origem
        ciclo.descricao = descricao if descricao else None
        ciclo.valor_horas = valor_horas_decimal
        ciclo.dias_fechados = dias_fechados
        ciclo.horas_restantes = Decimal(str(horas_restantes))
        ciclo.ciclo_id = None  # Será preenchido no fechamento
        ciclo.status_ciclo = 'ativo'
        ciclo.valor_aproximado = valor_aproximado
        ciclo.created_by = current_user.name or current_user.username
        
        db.session.add(ciclo)
        
        # Log
        log = SystemLog()
        log.origem = 'Ciclos'
        log.evento = 'lançamento_horas'
        log.detalhes = f'Lançamento de {valor_horas_decimal}h para {collaborator.name} - Origem: {origem}'
        log.usuario = current_user.name or current_user.username
        db.session.add(log)
        
        db.session.commit()
        flash(f'Horas lançadas com sucesso: {valor_horas_decimal}h para {collaborator.name}', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao lançar horas: {str(e)}', 'danger')
        import traceback
        print(traceback.format_exc())
    
    return redirect(url_for('ciclos.index'))

@bp.route('/historico/<int:collaborator_id>', methods=['GET'], strict_slashes=False)
@login_required
def historico(collaborator_id):
    """Retorna histórico paginado de um colaborador (JSON)"""
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        return jsonify({'ok': False, 'error': 'Acesso negado'}), 403
    
    try:
        page = int(request.args.get('page', 1))
        per_page = 5  # 5 linhas por página
        
        # Buscar colaborador
        collaborator = Collaborator.query.get_or_404(collaborator_id)
        
        # Buscar registros ativos do colaborador
        query = Ciclo.query.filter(
            Ciclo.collaborator_id == collaborator_id,
            Ciclo.status_ciclo == 'ativo'
        ).order_by(Ciclo.data_lancamento.desc(), Ciclo.id.desc())
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        registros = pagination.items
        
        # Calcular saldo atual
        balance = _calculate_collaborator_balance(collaborator_id)
        
        # Formatar registros
        registros_data = []
        for reg in registros:
            registros_data.append({
                'id': reg.id,
                'data': reg.data_lancamento.strftime('%d/%m/%Y'),
                'origem': reg.origem,
                'descricao': reg.descricao or '-',
                'horas': float(reg.valor_horas),
                'dias_fechados': reg.dias_fechados or 0,
                'horas_restantes': float(reg.horas_restantes) if reg.horas_restantes else 0.0
            })
        
        return jsonify({
            'ok': True,
            'collaborator_name': collaborator.name,
            'registros': registros_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            },
            'balance': balance
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/ajustar/<int:ciclo_id>', methods=['POST'], strict_slashes=False)
@login_required
def ajustar(ciclo_id):
    """Ajustar registro manualmente (apenas admin/dev)"""
    if current_user.nivel not in ['admin', 'DEV']:
        flash('Acesso negado. Apenas administradores podem ajustar registros.', 'danger')
        return redirect(url_for('ciclos.index'))
    
    try:
        ciclo = Ciclo.query.get_or_404(ciclo_id)
        
        valor_horas_str = request.form.get('valor_horas', '').strip()
        descricao = request.form.get('descricao', '').strip()
        
        # Validar formato de horas
        valido, valor_horas_decimal, erro = _validate_hours_format(valor_horas_str)
        if not valido:
            flash(erro or 'Formato inválido.', 'warning')
            return redirect(url_for('ciclos.index'))
        
        # Calcular dias fechados e horas restantes
        dias_fechados, horas_restantes = _calculate_days_and_remaining(valor_horas_decimal)
        
        # Calcular valor aproximado
        valor_dia = Decimal(str(_get_valor_dia()))
        valor_aproximado = Decimal(str(dias_fechados)) * valor_dia
        
        # Atualizar registro
        ciclo.valor_horas = valor_horas_decimal
        ciclo.dias_fechados = dias_fechados
        ciclo.horas_restantes = Decimal(str(horas_restantes))
        ciclo.valor_aproximado = valor_aproximado
        if descricao:
            ciclo.descricao = descricao
        ciclo.updated_at = datetime.now(ZoneInfo('America/Sao_Paulo'))
        ciclo.updated_by = current_user.name or current_user.username
        
        # Log
        log = SystemLog()
        log.origem = 'Ciclos'
        log.evento = 'ajuste_manual'
        log.detalhes = f'Ajuste manual de registro {ciclo_id}: {valor_horas_decimal}h'
        log.usuario = current_user.name or current_user.username
        db.session.add(log)
        
        db.session.commit()
        flash('Registro ajustado com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao ajustar registro: {str(e)}', 'danger')
    
    return redirect(url_for('ciclos.index'))

@bp.route('/fechamento/resumo', methods=['GET'], strict_slashes=False)
@login_required
def resumo_fechamento():
    """Retorna resumo para fechamento do ciclo (JSON)"""
    if current_user.nivel not in ['admin', 'DEV']:
        return jsonify({'ok': False, 'error': 'Acesso negado'}), 403
    
    try:
        colaboradores = _get_all_collaborators()
        colaboradores_resumo = []
        
        valor_dia = _get_valor_dia()
        
        for colab in colaboradores:
            balance = _calculate_collaborator_balance(colab.id)
            
            # Buscar registros ativos
            registros = Ciclo.query.filter(
                Ciclo.collaborator_id == colab.id,
                Ciclo.status_ciclo == 'ativo'
            ).all()
            
            # Calcular totais
            total_horas = sum(float(r.valor_horas) for r in registros)
            dias_completos = balance['dias_completos']
            horas_restantes = balance['horas_restantes']
            valor_total = balance['valor_aproximado']
            
            if total_horas > 0:  # Só incluir se tiver horas
                colaboradores_resumo.append({
                    'collaborator_id': colab.id,
                    'nome': colab.name,
                    'total_horas': round(total_horas, 1),
                    'dias_completos': dias_completos,
                    'horas_restantes': horas_restantes,
                    'valor': round(valor_total, 2),
                    'registros_count': len(registros)
                })
        
        # Totais gerais
        total_geral_horas = sum(r['total_horas'] for r in colaboradores_resumo)
        total_geral_dias = sum(r['dias_completos'] for r in colaboradores_resumo)
        total_geral_horas_restantes = sum(r['horas_restantes'] for r in colaboradores_resumo)
        total_geral_valor = sum(r['valor'] for r in colaboradores_resumo)
        
        # Avisos: horas < 8h não entram na conversão
        avisos = []
        for resumo in colaboradores_resumo:
            if resumo['total_horas'] < 8.0:
                avisos.append(f"{resumo['nome']}: {resumo['total_horas']}h (< 8h) - não entrará na conversão automática")
        
        return jsonify({
            'ok': True,
            'colaboradores': colaboradores_resumo,
            'totais': {
                'total_horas': round(total_geral_horas, 1),
                'total_dias': total_geral_dias,
                'total_horas_restantes': round(total_geral_horas_restantes, 1),
                'total_valor': round(total_geral_valor, 2),
                'valor_dia': valor_dia
            },
            'avisos': avisos
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/fechamento/confirmar', methods=['POST'], strict_slashes=False)
@login_required
def confirmar_fechamento():
    """Confirma fechamento do ciclo, arquiva e move horas restantes para próximo ciclo"""
    if current_user.nivel not in ['admin', 'DEV']:
        flash('Acesso negado. Apenas administradores podem fechar ciclos.', 'danger')
        return redirect(url_for('ciclos.index'))
    
    try:
        # Buscar próximo ciclo_id disponível
        ultimo_fechamento = CicloFechamento.query.order_by(CicloFechamento.ciclo_id.desc()).first()
        proximo_ciclo_id = (ultimo_fechamento.ciclo_id + 1) if ultimo_fechamento else 1
        
        # Buscar todos os registros ativos
        registros_ativos = Ciclo.query.filter(Ciclo.status_ciclo == 'ativo').all()
        
        if not registros_ativos:
            flash('Nenhum registro ativo encontrado para fechamento.', 'warning')
            return redirect(url_for('ciclos.index'))
        
        # Agrupar por colaborador para calcular totais
        colaboradores_totais = {}
        for reg in registros_ativos:
            cid = reg.collaborator_id
            if cid not in colaboradores_totais:
                colaboradores_totais[cid] = {
                    'nome': reg.nome_colaborador,
                    'total_horas': Decimal('0.0'),
                    'total_dias': 0,
                    'total_valor': Decimal('0.0'),
                    'horas_restantes': Decimal('0.0'),
                    'registros': []
                }
            
            colaboradores_totais[cid]['total_horas'] += Decimal(str(reg.valor_horas))
            colaboradores_totais[cid]['total_dias'] += (reg.dias_fechados or 0)
            colaboradores_totais[cid]['total_valor'] += Decimal(str(reg.valor_aproximado)) if reg.valor_aproximado else Decimal('0.0')
            colaboradores_totais[cid]['registros'].append(reg)
        
        # Calcular totais gerais
        total_horas_geral = sum(float(c['total_horas']) for c in colaboradores_totais.values())
        total_dias_geral = sum(c['total_dias'] for c in colaboradores_totais.values())
        total_valor_geral = sum(float(c['total_valor']) for c in colaboradores_totais.values())
        
        # Processar cada colaborador: fechar registros e manter horas restantes
        horas_restantes_processadas = []
        
        for cid, dados in colaboradores_totais.items():
            horas_restantes_colab = float(dados['total_horas']) % 8.0
            
            if horas_restantes_colab > 0:
                # Criar novo registro com horas restantes para próximo ciclo
                ultimo_reg = dados['registros'][0]  # Pegar um registro como referência
                novo_ciclo_restante = Ciclo()
                novo_ciclo_restante.collaborator_id = cid
                novo_ciclo_restante.nome_colaborador = dados['nome']
                novo_ciclo_restante.data_lancamento = date.today()
                novo_ciclo_restante.origem = 'Horas restantes do ciclo anterior'
                novo_ciclo_restante.descricao = f'Horas restantes do ciclo {proximo_ciclo_id - 1}'
                novo_ciclo_restante.valor_horas = Decimal(str(round(horas_restantes_colab, 1)))
                novo_ciclo_restante.dias_fechados = 0  # < 8h não entram na conversão
                novo_ciclo_restante.horas_restantes = Decimal(str(round(horas_restantes_colab, 1)))
                novo_ciclo_restante.ciclo_id = None  # Será preenchido no próximo fechamento
                novo_ciclo_restante.status_ciclo = 'ativo'
                novo_ciclo_restante.valor_aproximado = Decimal('0.0')  # < 8h não tem valor
                novo_ciclo_restante.created_by = current_user.name or current_user.username
                horas_restantes_processadas.append(novo_ciclo_restante)
                db.session.add(novo_ciclo_restante)
            
            # Marcar registros como fechados
            for reg in dados['registros']:
                reg.ciclo_id = proximo_ciclo_id
                reg.status_ciclo = 'fechado'
                reg.updated_at = datetime.now(ZoneInfo('America/Sao_Paulo'))
                reg.updated_by = current_user.name or current_user.username
        
        # Criar registro de fechamento
        fechamento = CicloFechamento()
        fechamento.ciclo_id = proximo_ciclo_id
        fechamento.fechado_por = current_user.name or current_user.username
        fechamento.valor_total = Decimal(str(total_valor_geral))
        fechamento.total_horas = Decimal(str(round(total_horas_geral, 1)))
        fechamento.total_dias = total_dias_geral
        fechamento.colaboradores_envolvidos = len(colaboradores_totais)
        observacoes = request.form.get('observacoes', '').strip()
        fechamento.observacoes = observacoes if observacoes else None
        db.session.add(fechamento)
        
        # Log
        log = SystemLog()
        log.origem = 'Ciclos'
        log.evento = 'fechamento_ciclo'
        log.detalhes = f'Fechamento do ciclo {proximo_ciclo_id}: {total_dias_geral} dias, {total_horas_geral}h, R$ {total_valor_geral:.2f}'
        log.usuario = current_user.name or current_user.username
        db.session.add(log)
        
        db.session.commit()
        
        flash(f'Ciclo {proximo_ciclo_id} fechado com sucesso! {total_dias_geral} dias completos, {round(total_horas_geral, 1)}h totais, R$ {total_valor_geral:.2f}', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao fechar ciclo: {str(e)}', 'danger')
        import traceback
        print(traceback.format_exc())
    
    return redirect(url_for('ciclos.index'))

@bp.route('/config', methods=['GET', 'POST'], strict_slashes=False)
@login_required
def config():
    """Página de configurações (nome empresa, valor dia)"""
    if current_user.nivel not in ['admin', 'DEV']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('ciclos.index'))
    
    nome_empresa = _get_nome_empresa()
    valor_dia = _get_valor_dia()
    
    if request.method == 'POST':
        try:
            novo_nome = request.form.get('nome_empresa', '').strip()
            novo_valor_str = request.form.get('valor_dia', '').strip()
            
            if not novo_nome:
                flash('Nome da empresa é obrigatório.', 'warning')
                return redirect(url_for('ciclos.config'))
            
            try:
                novo_valor = float(novo_valor_str)
                if novo_valor <= 0:
                    flash('Valor do dia deve ser maior que zero.', 'warning')
                    return redirect(url_for('ciclos.config'))
            except (ValueError, TypeError):
                flash('Valor do dia inválido.', 'warning')
                return redirect(url_for('ciclos.config'))
            
            # Salvar nome da empresa
            setting_nome = AppSetting.query.filter_by(key='ciclo_nome_empresa').first()
            if not setting_nome:
                setting_nome = AppSetting()
                setting_nome.key = 'ciclo_nome_empresa'
                db.session.add(setting_nome)
            setting_nome.value = novo_nome
            
            # Salvar valor do dia
            setting_valor = AppSetting.query.filter_by(key='ciclo_valor_dia').first()
            if not setting_valor:
                setting_valor = AppSetting()
                setting_valor.key = 'ciclo_valor_dia'
                db.session.add(setting_valor)
            setting_valor.value = str(novo_valor)
            
            # Log
            log = SystemLog()
            log.origem = 'Ciclos'
            log.evento = 'config_atualizada'
            log.detalhes = f'Configuração atualizada: Empresa={novo_nome}, Valor dia=R$ {novo_valor}'
            log.usuario = current_user.name or current_user.username
            db.session.add(log)
            
            db.session.commit()
            flash('Configurações salvas com sucesso!', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao salvar configurações: {str(e)}', 'danger')
        
        return redirect(url_for('ciclos.config'))
    
    return render_template(
        'ciclos/config.html',
        active_page='ciclos',
        nome_empresa=nome_empresa,
        valor_dia=valor_dia
    )

# ============================================================================
# Rotas de Férias e Atestados (movidas para Ciclos)
# ============================================================================

@bp.route('/ferias/adicionar', methods=['POST'], strict_slashes=False)
@login_required
def ferias_adicionar():
    """Adicionar férias para um colaborador"""
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('ciclos.index'))
    try:
        cid_str = (request.form.get('collaborator_id') or '').strip()
        di_str = (request.form.get('data_inicio') or '').strip()
        df_str = (request.form.get('data_fim') or '').strip()
        if not cid_str or not di_str or not df_str:
            flash('Dados obrigatórios ausentes.', 'warning')
            return redirect(url_for('ciclos.index'))
        cid = int(cid_str)
        data_inicio = datetime.strptime(di_str, '%Y-%m-%d').date()
        data_fim = datetime.strptime(df_str, '%Y-%m-%d').date()
        observacao = request.form.get('observacao', '').strip()
        
        if data_fim < data_inicio:
            flash('Data final deve ser maior ou igual à data inicial.', 'warning')
            return redirect(url_for('ciclos.index'))
        
        v = Vacation()
        v.collaborator_id = cid
        v.data_inicio = data_inicio
        v.data_fim = data_fim
        v.observacao = observacao
        v.criado_por = current_user.name or current_user.username
        db.session.add(v)
        db.session.commit()
        flash('Férias registradas com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao registrar férias: {e}', 'danger')
    return redirect(url_for('ciclos.index'))

@bp.route('/ferias/<int:id>/excluir', methods=['POST'], strict_slashes=False)
@login_required
def ferias_excluir(id: int):
    """Excluir férias"""
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('ciclos.index'))
    v = Vacation.query.get_or_404(id)
    try:
        db.session.delete(v)
        db.session.commit()
        flash('Férias excluídas.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir: {e}', 'danger')
    return redirect(url_for('ciclos.index'))

@bp.route('/atestado/adicionar', methods=['POST'], strict_slashes=False)
@login_required
def atestado_adicionar():
    """Adicionar atestado médico para um colaborador"""
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('ciclos.index'))
    try:
        from ..filename_utils import secure_filename
        
        cid_str = (request.form.get('collaborator_id') or '').strip()
        di_str = (request.form.get('data_inicio') or '').strip()
        df_str = (request.form.get('data_fim') or '').strip()
        if not cid_str or not di_str or not df_str:
            flash('Dados obrigatórios ausentes.', 'warning')
            return redirect(url_for('ciclos.index'))
        cid = int(cid_str)
        data_inicio = datetime.strptime(di_str, '%Y-%m-%d').date()
        data_fim = datetime.strptime(df_str, '%Y-%m-%d').date()
        motivo = request.form.get('motivo', '').strip()
        cid_code = request.form.get('cid', '').strip()
        medico = request.form.get('medico', '').strip()
        
        if data_fim < data_inicio:
            flash('Data final deve ser maior ou igual à data inicial.', 'warning')
            return redirect(url_for('ciclos.index'))
        
        dias = (data_fim - data_inicio).days + 1
        
        foto_filename = None
        if 'foto_atestado' in request.files:
            foto = request.files['foto_atestado']
            if foto and foto.filename:
                ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}
                MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
                
                if '.' not in foto.filename or foto.filename.rsplit('.', 1)[1].lower() not in ALLOWED_IMAGE_EXTENSIONS:
                    flash('Tipo de arquivo não permitido. Use imagens (PNG, JPG, JPEG, GIF).', 'warning')
                    return redirect(url_for('ciclos.index'))
                
                foto.seek(0, 2)
                size = foto.tell()
                foto.seek(0)
                if size > MAX_UPLOAD_SIZE:
                    flash('Arquivo muito grande. Máximo 10MB.', 'warning')
                    return redirect(url_for('ciclos.index'))
                
                upload_dir = os.path.join('static', 'uploads', 'atestados')
                os.makedirs(upload_dir, exist_ok=True)
                safe_name = secure_filename(foto.filename)
                ext = safe_name.rsplit('.', 1)[1].lower() if '.' in safe_name else 'jpg'
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
        flash('Atestado registrado com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao registrar atestado: {e}', 'danger')
    return redirect(url_for('ciclos.index'))

@bp.route('/atestado/<int:id>/excluir', methods=['POST'], strict_slashes=False)
@login_required
def atestado_excluir(id: int):
    """Excluir atestado médico"""
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('ciclos.index'))
    m = MedicalCertificate.query.get_or_404(id)
    try:
        if m.foto_atestado:
            path = os.path.join('static', 'uploads', 'atestados', m.foto_atestado)
            if os.path.exists(path):
                os.remove(path)
        db.session.delete(m)
        db.session.commit()
        flash('Atestado excluído.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir: {e}', 'danger')
    return redirect(url_for('ciclos.index'))

@bp.route('/ferias/listar/<int:collaborator_id>', methods=['GET'], strict_slashes=False)
@login_required
def ferias_listar(collaborator_id):
    """Retorna lista de férias de um colaborador (JSON)"""
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        return jsonify({'ok': False, 'error': 'Acesso negado'}), 403
    
    try:
        ferias = Vacation.query.filter_by(collaborator_id=collaborator_id, ativo=True).order_by(Vacation.data_inicio.desc()).all()
        
        ferias_data = []
        for f in ferias:
            ferias_data.append({
                'id': f.id,
                'data_inicio': f.data_inicio.strftime('%d/%m/%Y'),
                'data_fim': f.data_fim.strftime('%d/%m/%Y'),
                'observacao': f.observacao or '-'
            })
        
        return jsonify({'ok': True, 'ferias': ferias_data})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/atestado/listar/<int:collaborator_id>', methods=['GET'], strict_slashes=False)
@login_required
def atestado_listar(collaborator_id):
    """Retorna lista de atestados de um colaborador (JSON)"""
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        return jsonify({'ok': False, 'error': 'Acesso negado'}), 403
    
    try:
        atestados = MedicalCertificate.query.filter_by(collaborator_id=collaborator_id).order_by(MedicalCertificate.data_inicio.desc()).all()
        
        atestados_data = []
        for a in atestados:
            atestados_data.append({
                'id': a.id,
                'data_inicio': a.data_inicio.strftime('%d/%m/%Y'),
                'data_fim': a.data_fim.strftime('%d/%m/%Y'),
                'dias': a.dias,
                'motivo': a.motivo or '-',
                'cid': a.cid or '-',
                'medico': a.medico or '-',
                'foto_atestado': a.foto_atestado
            })
        
        return jsonify({'ok': True, 'atestados': atestados_data})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500
