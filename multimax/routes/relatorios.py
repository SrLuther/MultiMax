from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from .. import db
from ..models import Produto, Historico, Fornecedor
from datetime import datetime
import io
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

bp = Blueprint('relatorios', __name__, url_prefix='/relatorios')

@bp.route('/')
@login_required
def index():
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('home.index'))
    return render_template('relatorios.html', active_page='relatorios')

@bp.route('/exportar/produtos')
@login_required
def exportar_produtos():
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Você não tem permissão para exportar dados.', 'danger')
        return redirect(url_for('relatorios.index'))
    
    produtos = Produto.query.order_by(Produto.nome.asc()).all()
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Produtos"
    
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    headers = ['Código', 'Nome', 'Quantidade', 'Estoque Mínimo', 'Preço Custo', 'Preço Venda', 'Data Validade', 'Lote', 'Fornecedor']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border
    
    for row, produto in enumerate(produtos, 2):
        fornecedor_nome = ""
        if produto.fornecedor_id:
            fornecedor = Fornecedor.query.get(produto.fornecedor_id)
            if fornecedor:
                fornecedor_nome = fornecedor.nome
        
        data = [
            produto.codigo,
            produto.nome,
            produto.quantidade,
            produto.estoque_minimo,
            produto.preco_custo or 0,
            produto.preco_venda or 0,
            produto.data_validade.strftime('%d/%m/%Y') if produto.data_validade else '',
            produto.lote or '',
            fornecedor_nome
        ]
        for col, value in enumerate(data, 1):
            cell = ws.cell(row=row, column=col, value=value)
            cell.border = thin_border
    
    for col in range(1, len(headers) + 1):
        ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = 15
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    filename = f"produtos_multimax_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     download_name=filename, as_attachment=True)

@bp.route('/exportar/historico')
@login_required
def exportar_historico():
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Você não tem permissão para exportar dados.', 'danger')
        return redirect(url_for('relatorios.index'))
    
    historico = Historico.query.order_by(Historico.data.desc()).all()
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Histórico"
    
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="70AD47", end_color="70AD47", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    headers = ['Data/Hora', 'Produto', 'Ação', 'Quantidade', 'Detalhes', 'Usuário']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border
    
    for row, h in enumerate(historico, 2):
        data = [
            h.data.strftime('%d/%m/%Y %H:%M:%S') if h.data else '',
            h.product_name or '',
            'Entrada' if h.action == 'entrada' else 'Saída',
            h.quantidade or 0,
            h.details or '',
            h.usuario or ''
        ]
        for col, value in enumerate(data, 1):
            cell = ws.cell(row=row, column=col, value=value)
            cell.border = thin_border
    
    for col in range(1, len(headers) + 1):
        ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = 18
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    filename = f"historico_multimax_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     download_name=filename, as_attachment=True)

@bp.route('/exportar/fornecedores')
@login_required
def exportar_fornecedores():
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Você não tem permissão para exportar dados.', 'danger')
        return redirect(url_for('relatorios.index'))
    
    fornecedores = Fornecedor.query.order_by(Fornecedor.nome.asc()).all()
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Fornecedores"
    
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="ED7D31", end_color="ED7D31", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    headers = ['Nome', 'CNPJ', 'Telefone', 'Email', 'Endereço', 'Observação', 'Ativo']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border
    
    for row, f in enumerate(fornecedores, 2):
        data = [
            f.nome or '',
            f.cnpj or '',
            f.telefone or '',
            f.email or '',
            f.endereco or '',
            f.observacao or '',
            'Sim' if f.ativo else 'Não'
        ]
        for col, value in enumerate(data, 1):
            cell = ws.cell(row=row, column=col, value=value)
            cell.border = thin_border
    
    for col in range(1, len(headers) + 1):
        ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = 18
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    filename = f"fornecedores_multimax_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     download_name=filename, as_attachment=True)

@bp.route('/importar/produtos', methods=['GET', 'POST'])
@login_required
def importar_produtos():
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Apenas administradores podem importar produtos.', 'danger')
        return redirect(url_for('relatorios.index'))
    
    if request.method == 'POST':
        if 'arquivo' not in request.files:
            flash('Nenhum arquivo selecionado.', 'warning')
            return redirect(url_for('relatorios.importar_produtos'))
        
        arquivo = request.files['arquivo']
        if arquivo.filename == '':
            flash('Nenhum arquivo selecionado.', 'warning')
            return redirect(url_for('relatorios.importar_produtos'))
        
        if not arquivo.filename.endswith('.xlsx'):
            flash('Formato inválido. Use arquivos .xlsx', 'danger')
            return redirect(url_for('relatorios.importar_produtos'))
        
        try:
            wb = load_workbook(arquivo)
            ws = wb.active
            
            importados = 0
            atualizados = 0
            erros = 0
            
            for row in ws.iter_rows(min_row=2, values_only=True):
                if not row or not row[0]:
                    continue
                
                codigo = str(row[0]).strip()
                nome = str(row[1]).strip() if row[1] else ''
                
                if not nome:
                    erros += 1
                    continue
                
                try:
                    quantidade = int(row[2]) if row[2] else 0
                except Exception:
                    quantidade = 0
                
                try:
                    estoque_minimo = int(row[3]) if row[3] else 0
                except Exception:
                    estoque_minimo = 0
                
                try:
                    preco_custo = float(row[4]) if row[4] else 0.0
                except Exception:
                    preco_custo = 0.0
                
                try:
                    preco_venda = float(row[5]) if row[5] else 0.0
                except Exception:
                    preco_venda = 0.0
                
                produto = Produto.query.filter_by(codigo=codigo).first()
                
                if produto:
                    produto.nome = nome
                    produto.quantidade = quantidade
                    produto.estoque_minimo = estoque_minimo
                    produto.preco_custo = preco_custo
                    produto.preco_venda = preco_venda
                    atualizados += 1
                else:
                    novo_produto = Produto()
                    novo_produto.codigo = codigo
                    novo_produto.nome = nome
                    novo_produto.quantidade = quantidade
                    novo_produto.estoque_minimo = estoque_minimo
                    novo_produto.preco_custo = preco_custo
                    novo_produto.preco_venda = preco_venda
                    db.session.add(novo_produto)
                    importados += 1
            
            db.session.commit()
            flash(f'Importação concluída! {importados} novos produtos, {atualizados} atualizados, {erros} erros.', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao importar: {e}', 'danger')
        
        return redirect(url_for('relatorios.index'))
    
    return render_template('importar_produtos.html', active_page='relatorios')

@bp.route('/modelo/produtos')
@login_required
def modelo_produtos():
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Você não tem permissão para baixar modelos.', 'danger')
        return redirect(url_for('relatorios.index'))
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Modelo Produtos"
    
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    headers = ['Código', 'Nome', 'Quantidade', 'Estoque Mínimo', 'Preço Custo', 'Preço Venda']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
    
    exemplo = ['CX-0001', 'Produto Exemplo', 100, 10, 15.50, 25.00]
    for col, value in enumerate(exemplo, 1):
        cell = ws.cell(row=2, column=col, value=value)
        cell.border = thin_border
    
    for col in range(1, len(headers) + 1):
        ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = 15
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     download_name='modelo_produtos.xlsx', as_attachment=True)
