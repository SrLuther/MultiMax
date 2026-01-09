"""Rotas de PDF para o módulo Jornada usando WeasyPrint"""
from flask import Blueprint, render_template, make_response, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, date
from zoneinfo import ZoneInfo
from sqlalchemy import func
from .. import db
from ..models import MonthStatus, TimeOffRecord, JornadaArchive, Collaborator
from .jornada import (
    _get_all_collaborators, _calculate_collaborator_balance,
    _get_collaborator_display_name, _get_month_status
)

try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

bp = Blueprint('jornada_pdf', __name__, url_prefix='/jornada/pdf')

@bp.route('/em-aberto', methods=['GET'], strict_slashes=False)
@login_required
def em_aberto():
    """Gera PDF da página Em Aberto"""
    if not WEASYPRINT_AVAILABLE:
        flash('WeasyPrint não está disponível. Instale com: pip install weasyprint', 'danger')
        return redirect(url_for('jornada.em_aberto'))
    
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('home.index'))
    
    try:
        meses_abertos = MonthStatus.query.filter_by(status='aberto').order_by(
            MonthStatus.year.desc(), MonthStatus.month.desc()
        ).all()
        
        hoje = date.today()
        try:
            mes_atual = _get_month_status(hoje.year, hoje.month)
            if not meses_abertos or (mes_atual.status == 'aberto' and mes_atual not in meses_abertos):
                if mes_atual.status == 'aberto':
                    meses_abertos.append(mes_atual)
        except Exception:
            pass
        
        records = []
        if meses_abertos:
            from calendar import monthrange
            for mes_status in meses_abertos:
                first_day = date(mes_status.year, mes_status.month, 1)
                last_day = date(mes_status.year, mes_status.month, monthrange(mes_status.year, mes_status.month)[1])
                mes_records = TimeOffRecord.query.filter(
                    TimeOffRecord.date >= first_day,
                    TimeOffRecord.date <= last_day
                ).order_by(TimeOffRecord.date.desc()).all()
                records.extend(mes_records)
        
        colaboradores = _get_all_collaborators()
        all_stats = []
        for colab in colaboradores:
            balance = _calculate_collaborator_balance(colab.id)
            all_stats.append({
                'collaborator': colab,
                'display_name': _get_collaborator_display_name(colab),
                'balance': balance
            })
        
        total_horas = sum(float(s['balance'].get('total_bruto_hours', 0.0)) for s in all_stats)
        total_horas_residuais = sum(float(s['balance'].get('residual_hours', 0.0)) for s in all_stats)
        total_saldo_folgas = sum(int(s['balance'].get('saldo_days', 0)) for s in all_stats)
        total_folgas_usadas = sum(int(s['balance'].get('assigned_sum', 0)) for s in all_stats)
        total_conversoes = sum(int(s['balance'].get('converted_sum', 0)) for s in all_stats)
        
        html = render_template(
            'jornada/pdf/em_aberto.html',
            records=records,
            all_stats=all_stats,
            meses_abertos=meses_abertos,
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
        response.headers['Content-Disposition'] = f'inline; filename=jornada_em_aberto_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        return response
    except Exception as e:
        flash(f'Erro ao gerar PDF: {str(e)}', 'danger')
        return redirect(url_for('jornada.em_aberto'))

@bp.route('/fechado-revisao', methods=['GET'], strict_slashes=False)
@login_required
def fechado_revisao():
    """Gera PDF da página Fechado para Revisão"""
    if not WEASYPRINT_AVAILABLE:
        flash('WeasyPrint não está disponível.', 'danger')
        return redirect(url_for('jornada.fechado_revisao'))
    
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('home.index'))
    
    try:
        meses_fechados = MonthStatus.query.filter_by(status='fechado').order_by(
            MonthStatus.year.desc(), MonthStatus.month.desc()
        ).all()
        
        records = []
        for mes_status in meses_fechados:
            from calendar import monthrange
            first_day = date(mes_status.year, mes_status.month, 1)
            last_day = date(mes_status.year, mes_status.month, monthrange(mes_status.year, mes_status.month)[1])
            mes_records = TimeOffRecord.query.filter(
                TimeOffRecord.date >= first_day,
                TimeOffRecord.date <= last_day
            ).order_by(TimeOffRecord.date.desc()).all()
            records.extend(mes_records)
        
        records_2025 = TimeOffRecord.query.filter(
            func.extract('year', TimeOffRecord.date) == 2025
        ).order_by(TimeOffRecord.date.desc()).all()
        
        existing_ids = {r.id for r in records}
        for r in records_2025:
            if r.id not in existing_ids:
                records.append(r)
        
        colaboradores = _get_all_collaborators()
        all_stats = []
        for colab in colaboradores:
            colab_records = [r for r in records if r.collaborator_id == colab.id]
            if colab_records:
                balance = _calculate_collaborator_balance(colab.id)
                all_stats.append({
                    'collaborator': colab,
                    'display_name': _get_collaborator_display_name(colab),
                    'balance': balance
                })
        
        total_horas = sum(float(s['balance'].get('total_bruto_hours', 0.0)) for s in all_stats)
        total_horas_residuais = sum(float(s['balance'].get('residual_hours', 0.0)) for s in all_stats)
        total_saldo_folgas = sum(int(s['balance'].get('saldo_days', 0)) for s in all_stats)
        total_folgas_usadas = sum(int(s['balance'].get('assigned_sum', 0)) for s in all_stats)
        total_conversoes = sum(int(s['balance'].get('converted_sum', 0)) for s in all_stats)
        
        html = render_template(
            'jornada/pdf/fechado_revisao.html',
            records=records,
            all_stats=all_stats,
            meses_fechados=meses_fechados,
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
        response.headers['Content-Disposition'] = f'inline; filename=jornada_fechado_revisao_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        return response
    except Exception as e:
        flash(f'Erro ao gerar PDF: {str(e)}', 'danger')
        return redirect(url_for('jornada.fechado_revisao'))

@bp.route('/arquivados', methods=['GET'], strict_slashes=False)
@login_required
def arquivados():
    """Gera PDF da página Arquivados"""
    if not WEASYPRINT_AVAILABLE:
        flash('WeasyPrint não está disponível.', 'danger')
        return redirect(url_for('jornada.arquivados'))
    
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('home.index'))
    
    try:
        meses_arquivados = MonthStatus.query.filter_by(status='arquivado').order_by(
            MonthStatus.year.desc(), MonthStatus.month.desc()
        ).all()
        
        archived_records = JornadaArchive.query.order_by(
            JornadaArchive.archived_at.desc(),
            JornadaArchive.date.desc()
        ).all()
        
        total_hours = sum(float(r.hours or 0.0) for r in archived_records if r.record_type == 'horas' and (r.hours or 0.0) > 0)
        total_folgas_creditos = sum(int(r.days or 0) for r in archived_records if r.record_type == 'folga_adicional' and (not r.origin or r.origin != 'horas'))
        total_folgas_usadas = sum(int(r.days or 0) for r in archived_records if r.record_type == 'folga_usada')
        total_conversoes = sum(int(r.days or 0) for r in archived_records if r.record_type == 'conversao')
        total_valor_pago = sum(float(r.amount_paid or 0.0) for r in archived_records if r.amount_paid)
        
        html = render_template(
            'jornada/pdf/arquivados.html',
            records=archived_records,
            meses_arquivados=meses_arquivados,
            total_hours=total_hours,
            total_folgas_creditos=total_folgas_creditos,
            total_folgas_usadas=total_folgas_usadas,
            total_conversoes=total_conversoes,
            total_valor_pago=total_valor_pago,
            generated_at=datetime.now(ZoneInfo('America/Sao_Paulo'))
        )
        
        pdf = HTML(string=html).write_pdf()
        
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=jornada_arquivados_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        return response
    except Exception as e:
        flash(f'Erro ao gerar PDF: {str(e)}', 'danger')
        return redirect(url_for('jornada.arquivados'))

@bp.route('/situacao-final', methods=['GET'], strict_slashes=False)
@login_required
def situacao_final():
    """Gera PDF da página Situação Final"""
    if not WEASYPRINT_AVAILABLE:
        flash('WeasyPrint não está disponível.', 'danger')
        return redirect(url_for('jornada.situacao_final'))
    
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('home.index'))
    
    try:
        colaboradores = _get_all_collaborators()
        situacoes = []
        
        for colab in colaboradores:
            balance = _calculate_collaborator_balance(colab.id)
            active_records = TimeOffRecord.query.filter_by(collaborator_id=colab.id).all()
            
            total_horas = sum(float(r.hours or 0.0) for r in active_records if r.record_type == 'horas' and (r.hours or 0.0) > 0)
            total_folgas_adicionadas = sum(int(r.days or 0) for r in active_records if r.record_type == 'folga_adicional' and (not r.origin or r.origin != 'horas'))
            total_folgas_usadas = sum(int(r.days or 0) for r in active_records if r.record_type == 'folga_usada')
            total_conversoes = sum(int(r.days or 0) for r in active_records if r.record_type == 'conversao')
            
            situacoes.append({
                'display_name': _get_collaborator_display_name(colab),
                'total_horas': total_horas,
                'horas_residuais': balance.get('residual_hours', 0.0),
                'dias_das_horas': balance.get('days_from_hours', 0),
                'folgas_adicionadas': total_folgas_adicionadas,
                'folgas_usadas': total_folgas_usadas,
                'conversoes': total_conversoes,
                'saldo_folgas': balance.get('saldo_days', 0)
            })
        
        situacoes.sort(key=lambda x: x['display_name'])
        
        total_geral_horas = sum(s['total_horas'] for s in situacoes)
        total_geral_folgas_adicionadas = sum(s['folgas_adicionadas'] for s in situacoes)
        total_geral_folgas_usadas = sum(s['folgas_usadas'] for s in situacoes)
        total_geral_conversoes = sum(s['conversoes'] for s in situacoes)
        total_geral_saldo = sum(s['saldo_folgas'] for s in situacoes)
        
        html = render_template(
            'jornada/pdf/situacao_final.html',
            situacoes=situacoes,
            total_geral_horas=total_geral_horas,
            total_geral_folgas_adicionadas=total_geral_folgas_adicionadas,
            total_geral_folgas_usadas=total_geral_folgas_usadas,
            total_geral_conversoes=total_geral_conversoes,
            total_geral_saldo=total_geral_saldo,
            generated_at=datetime.now(ZoneInfo('America/Sao_Paulo'))
        )
        
        pdf = HTML(string=html).write_pdf()
        
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=jornada_situacao_final_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        return response
    except Exception as e:
        flash(f'Erro ao gerar PDF: {str(e)}', 'danger')
        return redirect(url_for('jornada.situacao_final'))
