"""Rotas de PDF para o módulo Jornada usando WeasyPrint"""
from flask import Blueprint, render_template, make_response, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, date
from zoneinfo import ZoneInfo
from sqlalchemy import func
from .. import db
from ..models import MonthStatus, TimeOffRecord, JornadaArchive, Collaborator
try:
    from .jornada import (
        _get_all_collaborators, _calculate_simple_balance,
        _get_collaborator_display_name
    )
except ImportError:
    # Se importação falhar, definir funções stub para evitar erro 502
    _get_all_collaborators = None
    _calculate_simple_balance = None
    _get_collaborator_display_name = None

try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

bp = Blueprint('jornada_pdf', __name__, url_prefix='/jornada/pdf')

@bp.route('/em-aberto', methods=['GET'], strict_slashes=False)
@login_required
def em_aberto():
    """Gera PDF da página principal de Jornada"""
    if not WEASYPRINT_AVAILABLE:
        flash('WeasyPrint não está disponível. Instale com: pip install weasyprint', 'danger')
        return redirect(url_for('jornada.index'))
    
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('home.index'))
    
    if _get_all_collaborators is None or _calculate_simple_balance is None or _get_collaborator_display_name is None:
        flash('Funções de jornada não disponíveis. Sistema simplificado.', 'warning')
        return redirect(url_for('jornada.index'))
    
    try:
        # Buscar todos os registros (não arquivados)
        records = TimeOffRecord.query.order_by(TimeOffRecord.date.desc(), TimeOffRecord.id.desc()).limit(500).all()
        
        colaboradores = _get_all_collaborators()
        all_stats = []
        for colab in colaboradores:
            balance = _calculate_simple_balance(colab.id)
            all_stats.append({
                'collaborator': colab,
                'display_name': _get_collaborator_display_name(colab),
                'balance': balance
            })
        
        total_horas = sum(float(s['balance'].get('total_horas', 0.0)) for s in all_stats)
        total_horas_residuais = sum(float(s['balance'].get('horas_residuais', 0.0)) for s in all_stats)
        total_saldo_folgas = sum(int(s['balance'].get('saldo', 0)) for s in all_stats)
        total_folgas_usadas = sum(int(s['balance'].get('folgas_usadas', 0)) for s in all_stats)
        total_conversoes = sum(int(s['balance'].get('conversoes', 0)) for s in all_stats)
        
        html = render_template(
            'jornada/pdf/em_aberto.html',
            records=records,
            all_stats=all_stats,
            meses_abertos=[],
            total_horas=total_horas,
            total_horas_residuais=total_horas_residuais,
            total_saldo_folgas=total_saldo_folgas,
            total_folgas_usadas=total_folgas_usadas,
            total_conversoes=total_conversoes,
            generated_at=datetime.now(ZoneInfo('America/Sao_Paulo'))
        )
        
        pdf = HTML(string=html).write_pdf()
        
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=jornada_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        return response
    except Exception as e:
        flash(f'Erro ao gerar PDF: {str(e)}', 'danger')
        return redirect(url_for('jornada.index'))

@bp.route('/fechado-revisao', methods=['GET'], strict_slashes=False)
@login_required
def fechado_revisao():
    """Gera PDF da página principal de Jornada (compatibilidade)"""
    if not WEASYPRINT_AVAILABLE:
        flash('WeasyPrint não está disponível.', 'danger')
        return redirect(url_for('jornada.index'))
    
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('home.index'))
    
    # Redirecionar para a página principal simplificada
    return redirect(url_for('jornada.index'))

@bp.route('/arquivados', methods=['GET'], strict_slashes=False)
@login_required
def arquivados():
    """Gera PDF da página principal de Jornada (compatibilidade)"""
    if not WEASYPRINT_AVAILABLE:
        flash('WeasyPrint não está disponível.', 'danger')
        return redirect(url_for('jornada.index'))
    
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('home.index'))
    
    # Redirecionar para a página principal simplificada
    return redirect(url_for('jornada.index'))

@bp.route('/situacao-final', methods=['GET'], strict_slashes=False)
@login_required
def situacao_final():
    """Gera PDF da página principal de Jornada (compatibilidade)"""
    if not WEASYPRINT_AVAILABLE:
        flash('WeasyPrint não está disponível.', 'danger')
        return redirect(url_for('jornada.index'))
    
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('home.index'))
    
    # Redirecionar para a página principal simplificada
    return redirect(url_for('jornada.index'))
