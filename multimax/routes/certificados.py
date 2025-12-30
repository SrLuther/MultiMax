from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from ..models import SanitaryCertificate, TemperatureCertificate, MeatReception, Fornecedor, TemperatureLog, TemperatureLocation, db
from sqlalchemy import func, desc

bp = Blueprint('certificados', __name__, url_prefix='/certificados')

@bp.route('/sanitarios', methods=['GET'])
@login_required
def sanitarios():
    busca = request.args.get('busca', '').strip()
    status = request.args.get('status', '').strip()
    
    query = SanitaryCertificate.query
    if busca:
        query = query.filter(
            (SanitaryCertificate.numero_certificado.ilike(f'%{busca}%')) |
            (SanitaryCertificate.tipo.ilike(f'%{busca}%'))
        )
    if status == 'vencido':
        query = query.filter(SanitaryCertificate.data_validade < date.today())
    elif status == 'vencendo':
        vencendo = date.today() + timedelta(days=30)
        query = query.filter(
            SanitaryCertificate.data_validade >= date.today(),
            SanitaryCertificate.data_validade <= vencendo
        )
    elif status == 'ativo':
        query = query.filter(
            SanitaryCertificate.data_validade >= date.today(),
            SanitaryCertificate.ativo == True
        )
    
    certificados = query.order_by(desc(SanitaryCertificate.data_validade)).all()
    
    return render_template('certificados/sanitarios.html',
                         certificados=certificados,
                         busca=busca,
                         status=status,
                         active_page='certificados')

@bp.route('/sanitarios/novo', methods=['GET', 'POST'])
@login_required
def sanitario_novo():
    if current_user.nivel == 'visualizador':
        flash('Visualizadores não têm permissão para fazer alterações.', 'danger')
        return redirect(url_for('certificados.sanitarios'))
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Você não tem permissão para criar certificados.', 'danger')
        return redirect(url_for('certificados.sanitarios'))
    
    if request.method == 'POST':
        reception_id = int(request.form.get('reception_id', '0') or '0') if request.form.get('reception_id') else None
        fornecedor_id = int(request.form.get('fornecedor_id', '0') or '0') if request.form.get('fornecedor_id') else None
        numero = request.form.get('numero_certificado', '').strip()
        tipo = request.form.get('tipo', '').strip()
        data_emissao_str = request.form.get('data_emissao', '').strip()
        data_validade_str = request.form.get('data_validade', '').strip()
        observacao = request.form.get('observacao', '').strip()
        
        if not numero or not data_validade_str:
            flash('Número e data de validade são obrigatórios.', 'warning')
            return redirect(url_for('certificados.sanitario_novo'))
        
        cert = SanitaryCertificate()
        cert.reception_id = reception_id
        cert.fornecedor_id = fornecedor_id
        cert.numero_certificado = numero
        cert.tipo = tipo
        
        if data_emissao_str:
            try:
                cert.data_emissao = datetime.strptime(data_emissao_str, '%Y-%m-%d').date()
            except Exception:
                pass
        try:
            cert.data_validade = datetime.strptime(data_validade_str, '%Y-%m-%d').date()
        except Exception:
            flash('Data de validade inválida.', 'warning')
            return redirect(url_for('certificados.sanitario_novo'))
        
        cert.observacao = observacao
        
        try:
            db.session.add(cert)
            db.session.commit()
            flash('Certificado sanitário cadastrado!', 'success')
            return redirect(url_for('certificados.sanitarios'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar certificado: {e}', 'danger')
    
    recepcoes = MeatReception.query.order_by(desc(MeatReception.data)).limit(50).all()
    fornecedores = Fornecedor.query.filter_by(ativo=True).order_by(Fornecedor.nome).all()
    
    return render_template('certificados/sanitario_novo.html',
                         recepcoes=recepcoes,
                         fornecedores=fornecedores,
                         active_page='certificados')

@bp.route('/temperatura/gerar', methods=['POST'])
@login_required
def temperatura_gerar():
    if current_user.nivel == 'visualizador':
        flash('Visualizadores não têm permissão para fazer alterações.', 'danger')
        return redirect(url_for('certificados.temperatura'))
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Você não tem permissão para gerar certificados.', 'danger')
        return redirect(url_for('certificados.temperatura'))
    
    periodo_inicio_str = request.form.get('periodo_inicio', '').strip()
    periodo_fim_str = request.form.get('periodo_fim', '').strip()
    localizacao = request.form.get('localizacao', '').strip()
    
    if not periodo_inicio_str or not periodo_fim_str or not localizacao:
        flash('Todos os campos são obrigatórios.', 'warning')
        return redirect(url_for('certificados.temperatura'))
    
    try:
        periodo_inicio = datetime.strptime(periodo_inicio_str, '%Y-%m-%d')
        periodo_fim = datetime.strptime(periodo_fim_str, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
    except Exception:
        flash('Datas inválidas.', 'warning')
        return redirect(url_for('certificados.temperatura'))
    
    # Buscar registros de temperatura no período
    logs = TemperatureLog.query.filter(
        TemperatureLog.local == localizacao,
        TemperatureLog.data_registro >= periodo_inicio,
        TemperatureLog.data_registro <= periodo_fim
    ).all()
    
    if not logs:
        flash('Nenhum registro de temperatura encontrado no período.', 'warning')
        return redirect(url_for('certificados.temperatura'))
    
    temperaturas = [float(log.temperatura) for log in logs if log.temperatura]
    temp_media = sum(temperaturas) / len(temperaturas) if temperaturas else 0
    temp_min = min(temperaturas) if temperaturas else 0
    temp_max = max(temperaturas) if temperaturas else 0
    
    cert = TemperatureCertificate()
    cert.periodo_inicio = periodo_inicio
    cert.periodo_fim = periodo_fim
    cert.localizacao = localizacao
    cert.temperatura_media = temp_media
    cert.temperatura_min = temp_min
    cert.temperatura_max = temp_max
    cert.registros_count = len(logs)
    cert.gerado_por = current_user.name
    
    try:
        db.session.add(cert)
        db.session.commit()
        flash('Certificado de temperatura gerado!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao gerar certificado: {e}', 'danger')
    
    return redirect(url_for('certificados.temperatura'))

@bp.route('/temperatura', methods=['GET'])
@login_required
def temperatura():
    certificados = TemperatureCertificate.query.order_by(desc(TemperatureCertificate.gerado_em)).limit(50).all()
    locais = TemperatureLocation.query.filter_by(ativo=True).all()
    
    return render_template('certificados/temperatura.html',
                         certificados=certificados,
                         locais=locais,
                         active_page='certificados')

