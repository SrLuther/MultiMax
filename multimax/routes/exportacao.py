from datetime import datetime
from zoneinfo import ZoneInfo
import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from flask import Blueprint, redirect, url_for, flash, send_file, request
from flask_login import login_required, current_user
from ..models import Produto, CleaningTask, CleaningHistory, Historico, MeatReception, MeatCarrier, MeatPart, User
from io import BytesIO
from typing import Any
from reportlab.platypus import Image
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

bp = Blueprint('exportacao', __name__)

def _now_br() -> datetime:
    try:
        return datetime.now(ZoneInfo('America/Sao_Paulo'))
    except Exception:
        return datetime.now()

def _brand_header(canvas, doc):
    canvas.saveState()
    logo_h = 1.0 * cm
    h = 1.5 * cm
    y = doc.pagesize[1] - h
    canvas.setFillColor(colors.HexColor('#0d6efd'))
    canvas.rect(0, y, doc.pagesize[0], h, fill=True, stroke=False)
    x = 0.2 * inch
    logo_w = logo_h
    try:
        root = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), '..'))
        logo_path = os.path.join(root, 'static', 'icons', 'logo-user.png')
        if os.path.exists(logo_path):
            canvas.drawImage(ImageReader(logo_path), x, y + (h - logo_h) / 2, width=logo_w, height=logo_h, preserveAspectRatio=True, mask='auto')
            x += logo_w + 0.2 * inch
    except Exception:
        pass
    canvas.setFillColor(colors.white)
    canvas.setFont('Helvetica-Bold', 14)
    base_text = 'MultiMax - '
    canvas.drawString(x, y + h / 2 - 6, base_text)
    next_x = x + stringWidth(base_text, 'Helvetica-Bold', 14)
    canvas.setFont('Helvetica-Oblique', 14)
    canvas.drawString(next_x, y + h / 2 - 6, 'Gestão Amora')
    canvas.restoreState()

@bp.route('/exportar/cronograma/pdf')
@login_required
def exportar_cronograma_pdf():
    if current_user.nivel not in ['operador', 'admin']:
        flash('Você não tem permissão para exportar o cronograma.', 'danger')
        return redirect(url_for('cronograma.cronograma'))
    try:
        filename = 'cronograma_limpeza_multimax.pdf'
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, leftMargin=0.4*inch, rightMargin=0.4*inch, topMargin=0.5*inch, bottomMargin=0.5*inch)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Cell', parent=styles['Normal'], fontSize=9, leading=11))
        styles.add(ParagraphStyle(name='Cell', parent=styles['Normal'], fontSize=9, leading=11, wordWrap='LTR'))
        story: list[Any] = []
        styles.add(ParagraphStyle(name='Footer', fontSize=8, alignment=2, textColor=colors.gray))
        story.append(Paragraph('<b>MultiMax - Cronograma de Limpeza</b>', styles['Title']))
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(f'Gerado por: {current_user.name} ({current_user.nivel.upper()})', styles['Normal']))
        story.append(Paragraph(f"Data de Geração: {_now_br().strftime('%d/%m/%Y %H:%M:%S')}", styles['Normal']))
        story.append(Spacer(1, 0.5 * inch))
        story.append(Paragraph('<b>Tarefas de Limpeza Agendadas</b>', styles['h2']))
        story.append(Spacer(1, 0.2 * inch))
        tarefas = CleaningTask.query.order_by(CleaningTask.proxima_data.asc()).all()
        data: list[list[Any]] = [["Área/Limpeza", "Frequência", "Última Data", "Próxima Prevista", "Designado(s)", "Observações"]]
        for t in tarefas:
            data.append([
                Paragraph(t.nome_limpeza, styles['Normal']),
                t.frequencia,
                t.ultima_data.strftime('%d/%m/%Y'),
                t.proxima_data.strftime('%d/%m/%Y'),
                Paragraph(t.designados or 'Não especificado', styles['Normal']),
                Paragraph(t.observacao or '-', styles['Normal'])
            ])
        table = Table(data, colWidths=[2*inch, 0.8*inch, 1*inch, 1*inch, 1.5*inch, 2.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#198754')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ]))
        story.append(table)
        story.append(PageBreak())
        story.append(Paragraph('<b>Histórico de Conclusões (Recentes)</b>', styles['h2']))
        story.append(Spacer(1, 0.2 * inch))
        historico = CleaningHistory.query.order_by(CleaningHistory.data_conclusao.desc()).limit(20).all()
        data_hist: list[list[Any]] = [["Data Conclusão", "Limpeza", "Realizado Por", "Observações"]]
        for h in historico:
            data_hist.append([h.data_conclusao.strftime('%d/%m/%Y %H:%M'), Paragraph(h.nome_limpeza, styles['Normal']), h.designados, Paragraph(h.observacao or '-', styles['Normal'])])
        table_hist = Table(data_hist, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 2*inch])
        table_hist.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6c757d')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ]))
        story.append(table_hist)
        def footer_on_page(canvas, doc):
            canvas.saveState()
            canvas.setFont('Helvetica', 8)
            footer_text = f"Página {canvas.getPageNumber()} | MultiMax Cronograma | {_now_br().strftime('%d/%m/%Y %H:%M:%S')}"
            canvas.drawString(inch, 0.5 * inch, footer_text)
            canvas.restoreState()
        def on_page(canvas, doc):
            _brand_header(canvas, doc)
            footer_on_page(canvas, doc)
        doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
        pdf_buffer.seek(0)
        return send_file(pdf_buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')
    except Exception as e:
        flash(f'Erro ao gerar PDF do Cronograma: {e}', 'danger')
        return redirect(url_for('cronograma.cronograma'))

@bp.route('/exportar/cronograma/tarefa/<int:id>.pdf')
@login_required
def exportar_tarefa_pdf(id):
    if current_user.nivel not in ['operador', 'admin']:
        flash('Você não tem permissão para exportar tarefas.', 'danger')
        return redirect(url_for('cronograma.cronograma'))
    try:
        tarefa = CleaningTask.query.get_or_404(id)
        filename = f"tarefa_{tarefa.id}_cronograma.pdf"
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Cell', parent=styles['Normal'], fontSize=9, leading=11, wordWrap='LTR'))
        story: list[Any] = []
        story.append(Paragraph('<b>MultiMax - Detalhes da Tarefa de Limpeza</b>', styles['Title']))
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(f"Tarefa: <b>{tarefa.nome_limpeza}</b>", styles['Normal']))
        story.append(Paragraph(f"Frequência/Regra: {tarefa.frequencia}", styles['Normal']))
        story.append(Paragraph(f"Última Realização: {tarefa.ultima_data.strftime('%d/%m/%Y')}", styles['Normal']))
        story.append(Paragraph(f"Próxima Prevista: {tarefa.proxima_data.strftime('%d/%m/%Y')}", styles['Normal']))
        story.append(Spacer(1, 0.2 * inch))
        hist = CleaningHistory.query.filter_by(nome_limpeza=tarefa.nome_limpeza).order_by(CleaningHistory.data_conclusao.desc()).limit(5).all()
        obs = tarefa.observacao or ('Sem observações.' if not hist else hist[0].observacao or 'Sem observações.')
        desig = tarefa.designados or ('Não especificado' if not hist else hist[0].designados or 'Não especificado')
        story.append(Paragraph(f"Observações: {obs}", styles['Normal']))
        story.append(Paragraph(f"Designado(s): {desig}", styles['Normal']))
        story.append(Spacer(1, 0.3 * inch))
        if hist:
            story.append(Paragraph('<b>Últimas Conclusões</b>', styles['h2']))
            data_hist = [["Data", "Realizado Por", "Observações"]]
            for h in hist:
                data_hist.append([h.data_conclusao.strftime('%d/%m/%Y %H:%M'), h.designados, h.observacao or '-'])
            table_hist = Table(data_hist, colWidths=[1.5*inch, 2*inch, 3*inch])
            table_hist.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6c757d')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ]))
            story.append(table_hist)
        def footer_on_page(canvas, doc):
            canvas.saveState()
            canvas.setFont('Helvetica', 8)
            footer_text = f"Página {canvas.getPageNumber()} | MultiMax Tarefa | {_now_br().strftime('%d/%m/%Y %H:%M:%S')}"
            canvas.drawString(inch, 0.5 * inch, footer_text)
            canvas.restoreState()
        def on_page(canvas, doc):
            _brand_header(canvas, doc)
            footer_on_page(canvas, doc)
        doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
        pdf_buffer.seek(0)
        return send_file(pdf_buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')
    except Exception as e:
        flash(f'Erro ao gerar PDF da Tarefa: {e}', 'danger')
        return redirect(url_for('cronograma.cronograma'))

@bp.route('/exportar/limpeza/historico/<int:id>.pdf')
@login_required
def exportar_historico_limpeza_pdf(id):
    if current_user.nivel not in ['operador', 'admin']:
        flash('Você não tem permissão para exportar histórico de limpezas.', 'danger')
        return redirect(url_for('cronograma.cronograma'))
    try:
        h = CleaningHistory.query.get_or_404(id)
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story: list[Any] = []
        story.append(Paragraph('<b>MultiMax - Histórico de Limpeza</b>', styles['Title']))
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(f"Data: {h.data_conclusao.strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
        story.append(Paragraph(f"Tipo: {h.nome_limpeza}", styles['Normal']))
        story.append(Paragraph(f"Realizado por: {h.designados or h.usuario_conclusao or '-'}", styles['Normal']))
        if h.observacao:
            story.append(Paragraph(f"Observação: {h.observacao}", styles['Normal']))
        def footer_on_page(canvas, doc):
            canvas.saveState()
            canvas.setFont('Helvetica', 8)
            footer_text = f"Página {canvas.getPageNumber()} | MultiMax Histórico | {_now_br().strftime('%d/%m/%Y %H:%M:%S')}"
            canvas.drawString(inch, 0.5 * inch, footer_text)
            canvas.restoreState()
        def on_page(canvas, doc):
            _brand_header(canvas, doc)
            footer_on_page(canvas, doc)
        doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
        pdf_buffer.seek(0)
        filename = f"historico_{id}.pdf"
        return send_file(pdf_buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')
    except Exception as e:
        flash(f'Erro ao gerar PDF do histórico: {e}', 'danger')
        return redirect(url_for('cronograma.cronograma'))

@bp.route('/exportar/estoque/pdf')
@login_required
def exportar():
    try:
        filename = 'relatorio_estoque_multimax.pdf'
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Cell', parent=styles['Normal'], fontSize=9, leading=11, wordWrap='LTR'))
        story: list[Any] = []
        story.append(Paragraph('<b>MultiMax - Relatório de Estoque</b>', styles['Title']))
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(f'Gerado por: {current_user.name} ({current_user.nivel.upper()})', styles['Normal']))
        story.append(Paragraph(f"Data de Geração: {_now_br().strftime('%d/%m/%Y %H:%M:%S')}", styles['Normal']))
        story.append(Spacer(1, 0.5 * inch))
        produtos = Produto.query.order_by(Produto.quantidade.asc()).all()
        data: list[list[Any]] = [["Cód.", "Produto", "Estoque", "Mínimo", "Custo (R$)", "Venda (R$)", "Status"]]
        # Larguras dinâmicas baseadas na largura disponível da página
        avail_in = (doc.width) / inch
        code_env_in = float(os.getenv('PDF_CODE_COL_IN', '0.5'))
        # Medir código com hífen não separável para manter em uma única linha
        def code_display(c):
            return (c or '').replace('-', '\u2011')
        try:
            max_code_pts = max(stringWidth(code_display(p.codigo), 'Helvetica', 8) for p in produtos) if produtos else 0
        except Exception:
            max_code_pts = 0
        code_req_in = (max_code_pts / inch) + 0.08  # padding
        code_col_width_in = min(max(code_env_in, code_req_in), 1.2)  # limitar para não consumir demais
        # Larguras fixas para colunas numéricas/status
        estoque_in = 0.8
        minimo_in = 0.8
        custo_in = 1.0
        venda_in = 1.0
        status_in = 1.0
        numeric_sum_in = estoque_in + minimo_in + custo_in + venda_in + status_in
        # Produto ocupa o restante e quebra linha
        product_col_width_in = max(1.2, avail_in - code_col_width_in - numeric_sum_in)
        code_col_width = code_col_width_in * inch
        product_col_width = product_col_width_in * inch
        code_style = ParagraphStyle(name='CodeCell', fontName='Helvetica', fontSize=8, leading=9)
        product_style = ParagraphStyle(name='ProductCell', fontName='Helvetica', fontSize=9, leading=10, wordWrap='LTR')
        def fit_text_to_width(text, width_pts, font='Helvetica', font_size=8, padding=4):
            if text is None:
                return ''
            t = str(text)
            max_width = max(0, width_pts - padding)
            if stringWidth(t, font, font_size) <= max_width:
                return t
            # truncate with ellipsis
            ell = '…'
            # conservative start
            low, high = 0, len(t)
            best = ''
            while low <= high:
                mid = (low + high) // 2
                cand = t[:mid] + ell
                w = stringWidth(cand, font, font_size)
                if w <= max_width:
                    best = cand
                    low = mid + 1
                else:
                    high = mid - 1
            return best or ell
        for p in produtos:
            status = 'OK'
            if p.quantidade < p.estoque_minimo:
                status = 'CRÍTICO'
            elif p.quantidade == p.estoque_minimo:
                status = 'ATENÇÃO'
            codigo_nb = code_display(p.codigo)
            data.append([
                Paragraph(codigo_nb, code_style),
                Paragraph(p.nome or '-', product_style),
                str(p.quantidade),
                str(p.estoque_minimo),
                f"{p.preco_custo:.2f}",
                f"{p.preco_venda:.2f}",
                status
            ])
        table = Table(
            data,
            colWidths=[code_col_width, product_col_width, estoque_in*inch, minimo_in*inch, custo_in*inch, venda_in*inch, status_in*inch]
        )
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#198754')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ]))
        for i, p in enumerate(produtos):
            row_index = i + 1
            if p.quantidade < p.estoque_minimo:
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, row_index), (-1, row_index), colors.red),
                    ('TEXTCOLOR', (0, row_index), (-1, row_index), colors.white),
                ]))
            elif p.quantidade == p.estoque_minimo:
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, row_index), (-1, row_index), colors.yellow),
                    ('TEXTCOLOR', (0, row_index), (-1, row_index), colors.black),
                ]))
        story.append(table)
        def footer_on_page(canvas, doc):
            canvas.saveState()
            canvas.setFont('Helvetica', 8)
            footer_text = f"Página {canvas.getPageNumber()} | MultiMax Estoque | {_now_br().strftime('%d/%m/%Y %H:%M:%S')}"
            canvas.drawString(inch, 0.5 * inch, footer_text)
            canvas.restoreState()
        def on_page(canvas, doc):
            _brand_header(canvas, doc)
            footer_on_page(canvas, doc)
        doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
        pdf_buffer.seek(0)
        return send_file(pdf_buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')
    except Exception as e:
        flash(f'Erro ao gerar PDF do Estoque: {e}', 'danger')
        return redirect(url_for('estoque.index'))

@bp.route('/exportar/graficos/produto/<int:id>.pdf')
@login_required
def exportar_graficos_produto(id):
    try:
        produto = Produto.query.get_or_404(id)
        data_inicio_str = request.args.get('data_inicio', '').strip()
        data_fim_str = request.args.get('data_fim', '').strip()
        filename = f"graficos_{produto.codigo}.pdf"
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story: list[Any] = []
        story.append(Paragraph('<b>MultiMax - Movimentação por Período</b>', styles['Title']))
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(f"Produto: <b>{produto.nome}</b> (Cód: {produto.codigo})", styles['Normal']))
        story.append(Paragraph(f"Gerado por: {current_user.name}", styles['Normal']))
        story.append(Paragraph(f"Data: {_now_br().strftime('%d/%m/%Y %H:%M:%S')}", styles['Normal']))
        story.append(Spacer(1, 0.3 * inch))

        def fetch_hist(start_date=None, end_date=None):
            q = Historico.query.filter(Historico.product_id == produto.id)
            if start_date:
                q = q.filter(Historico.data >= start_date)
            if end_date:
                q = q.filter(Historico.data <= end_date)
            return q.order_by(Historico.data.asc()).all()

        def add_table(title, labels, entradas, saidas):
            data = [["Período", "Entradas", "Saídas"]]
            for i in range(max(len(labels), len(entradas), len(saidas))):
                label = labels[i] if i < len(labels) else "-"
                e = entradas[i] if i < len(entradas) else 0
                s = saidas[i] if i < len(saidas) else 0
                data.append([label, str(e), str(s)])
            table = Table(data, colWidths=[3.5*inch, 1.5*inch, 1.5*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#007bff')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ]))
            story.append(table)
            story.append(Spacer(1, 0.2 * inch))

        def add_bar_chart(title, labels, entradas, saidas):
            try:
                story.append(Paragraph(f"<b>{title}</b>", styles['h2']))
                # configurar tamanho conforme quantidade de labels
                count = max(len(labels or []), 1)
                width_in = max(6.0, min(10.0, 0.45 * count))
                fig, ax = plt.subplots(figsize=(width_in, 3.2))
                x = list(range(len(labels or [])))
                e_vals = [int(v or 0) for v in (entradas or [])]
                s_vals = [int(v or 0) for v in (saidas or [])]
                w = 0.4
                ax.bar([i - w/2 for i in x], e_vals, width=w, label='Entradas', color='#198754')
                ax.bar([i + w/2 for i in x], s_vals, width=w, label='Saídas', color='#dc3545')
                ax.set_xticks(x)
                ax.set_xticklabels(labels or [], rotation=45, ha='right')
                ax.legend()
                ax.grid(axis='y', alpha=0.3)
                buf = BytesIO()
                fig.tight_layout()
                fig.savefig(buf, format='PNG', dpi=160)
                plt.close(fig)
                buf.seek(0)
                img = Image(buf)
                max_w = doc.width
                max_h = 3.5 * inch
                iw = getattr(img, 'imageWidth', None)
                ih = getattr(img, 'imageHeight', None)
                if iw and ih and iw > 0 and ih > 0:
                    scale = min(max_w / iw, max_h / ih)
                    img.drawWidth = iw * scale
                    img.drawHeight = ih * scale
                else:
                    img.drawWidth = max_w
                    img.drawHeight = max_h
                story.append(img)
                story.append(Spacer(1, 0.15 * inch))
            except Exception:
                pass

        def agg_weekly():
            from datetime import date, timedelta
            end = date.today()
            start = end - timedelta(days=7*8)
            hist = fetch_hist(datetime.combine(start, datetime.min.time()))
            buckets = {}
            cursor = start - timedelta(days=start.weekday())
            while cursor <= end:
                key = cursor
                buckets[key] = {'entrada': 0, 'saida': 0, 'label': f"Semana {cursor.strftime('%d/%m')}"}
                cursor += timedelta(days=7)
            for h in hist:
                d = h.data.date()
                monday = d - timedelta(days=d.weekday())
                if monday in buckets:
                    buckets[monday][h.action] += (h.quantidade or 0)
            items = [buckets[k] for k in sorted(buckets.keys())]
            labels = [v['label'] for v in items]
            entradas = [v['entrada'] for v in items]
            saidas = [v['saida'] for v in items]
            return labels, entradas, saidas

        def agg_monthly():
            from datetime import date
            today = date.today()
            buckets = {}
            y, m = today.year, today.month
            for i in range(11, -1, -1):
                yy = y
                mm = m - i
                while mm <= 0:
                    yy -= 1
                    mm += 12
                buckets[(yy, mm)] = {'entrada': 0, 'saida': 0, 'label': f"{mm:02d}/{yy}"}
            hist = fetch_hist()
            for h in hist:
                k = (h.data.year, h.data.month)
                if k in buckets:
                    buckets[k][h.action] += (h.quantidade or 0)
            items = [buckets[k] for k in sorted(buckets.keys())]
            labels = [v['label'] for v in items]
            entradas = [v['entrada'] for v in items]
            saidas = [v['saida'] for v in items]
            return labels, entradas, saidas

        def agg_yearly():
            from datetime import date
            this = date.today().year
            buckets = {yy: {'entrada': 0, 'saida': 0, 'label': str(yy)} for yy in range(this-4, this+1)}
            hist = fetch_hist()
            for h in hist:
                yy = h.data.year
                if yy in buckets:
                    buckets[yy][h.action] += (h.quantidade or 0)
            items = [buckets[yy] for yy in sorted(buckets.keys())]
            labels = [v['label'] for v in items]
            entradas = [v['entrada'] for v in items]
            saidas = [v['saida'] for v in items]
            return labels, entradas, saidas

        labels, entradas, saidas = agg_weekly()
        add_bar_chart('Semanal (Últimas 8 semanas)', labels, entradas, saidas)
        add_table('Semanal (Últimas 8 semanas)', labels, entradas, saidas)
        story.append(PageBreak())

        labels, entradas, saidas = agg_monthly()
        add_bar_chart('Mensal (Últimos 12 meses)', labels, entradas, saidas)
        add_table('Mensal (Últimos 12 meses)', labels, entradas, saidas)
        story.append(PageBreak())

        labels, entradas, saidas = agg_yearly()
        add_bar_chart('Anual (Últimos 5 anos)', labels, entradas, saidas)
        add_table('Anual (Últimos 5 anos)', labels, entradas, saidas)

        def parse_date_safe(s):
            from datetime import datetime as _dt
            try:
                return _dt.strptime(s, '%Y-%m-%d')
            except Exception:
                return None

        di_dt = parse_date_safe(data_inicio_str)
        df_dt = parse_date_safe(data_fim_str)
        if di_dt and df_dt:
            story.append(PageBreak())
            if di_dt > df_dt:
                di_dt, df_dt = df_dt, di_dt
            hist = fetch_hist(di_dt, df_dt)
            from datetime import timedelta as _td
            buckets = {}
            cursor = di_dt.date()
            while cursor <= df_dt.date():
                buckets[cursor] = {'entrada': 0, 'saida': 0, 'label': cursor.strftime('%d/%m')}
                cursor += _td(days=1)
            items = [buckets[k] for k in sorted(buckets.keys())]
            for h in hist:
                d = h.data.date()
                if d in buckets:
                    buckets[d][h.action] += (h.quantidade or 0)
            items = [buckets[k] for k in sorted(buckets.keys())]
            labels = [v['label'] for v in items]
            entradas = [v['entrada'] for v in items]
            saidas = [v['saida'] for v in items]
            add_bar_chart('Período Personalizado', labels, entradas, saidas)
            add_table('Período Personalizado', labels, entradas, saidas)

        def footer_on_page(canvas, doc):
            canvas.saveState()
            canvas.setFont('Helvetica', 8)
            footer_text = f"Página {canvas.getPageNumber()} | MultiMax Gráficos | {_now_br().strftime('%d/%m/%Y %H:%M:%S')}"
            canvas.drawString(inch, 0.5 * inch, footer_text)
            canvas.restoreState()
        def on_page(canvas, doc):
            _brand_header(canvas, doc)
            footer_on_page(canvas, doc)
        doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
        pdf_buffer.seek(0)
        return send_file(pdf_buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')
    except Exception as e:
        flash(f'Erro ao gerar PDF de Gráficos: {e}', 'danger')
        return redirect(url_for('usuarios.graficos'))

@bp.route('/exportar/carnes/relatorio/<int:id>.pdf')
@login_required
def exportar_relatorio_carnes_pdf(id):
    if current_user.nivel not in ['operador', 'admin']:
        flash('Você não tem permissão para exportar relatório de carnes.', 'danger')
        return redirect(url_for('carnes.index'))
    try:
        r = MeatReception.query.get_or_404(id)
        carriers = MeatCarrier.query.filter_by(reception_id=r.id).all()
        carriers_map = {c.id: c for c in carriers}
        parts = MeatPart.query.filter_by(reception_id=r.id).order_by(MeatPart.id.asc()).all()
        group_size = 4 if (r.tipo or 'bovina') == 'bovina' else 2
        animais = {}
        total_bruto = 0.0
        total_liquido = 0.0
        for idx, p in enumerate(parts):
            c = carriers_map.get(p.carrier_id)
            cw = c.peso if c else 0.0
            bruto = float(p.peso_bruto or 0.0)
            sub = cw if cw > 0 else float(p.tara or 0.0)
            liquido = max(0.0, bruto - sub)
            total_bruto += bruto
            total_liquido += liquido
            fallback_num = (idx // group_size) + 1
            an = p.animal_numero if p.animal_numero is not None else fallback_num
            if an not in animais:
                animais[an] = []
            animais[an].append({
                'categoria': p.categoria,
                'lado': p.lado,
                'peso_bruto': bruto,
                'carrier_nome': (c.nome if c else None),
                'carrier_peso': cw if cw > 0 else None,
                'tara': (p.tara or None),
                'peso_liquido': liquido,
            })
        funcionarios_aplicado_total = sum((pp.get('carrier_peso') or 0.0) for plist in animais.values() for pp in plist)
        taras_total = sum((pp.get('tara') or 0.0) for plist in animais.values() for pp in plist)

        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Cell', parent=styles['Normal'], fontSize=9, leading=11, wordWrap='LTR'))
        story: list[Any] = []
        story.append(Paragraph('<b>MultiMax - Relatório de Recepção de Carnes</b>', styles['Title']))
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(f"Gerado por: {current_user.name} ({current_user.nivel.upper()})", styles['Normal']))
        story.append(Paragraph(f"Data de Geração: {_now_br().strftime('%d/%m/%Y %H:%M:%S')}", styles['Normal']))
        story.append(Spacer(1, 0.4 * inch))
        story.append(Paragraph('<b>Recepção</b>', styles['h2']))
        story.append(Paragraph(f"Data: {r.data.strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
        story.append(Paragraph(f"Número de referência: {r.reference_code or '-'}", styles['Normal']))
        story.append(Paragraph(f"Fornecedor: {r.fornecedor}", styles['Cell']))
        story.append(Paragraph(f"Tipo: {(r.tipo or '').capitalize()}", styles['Normal']))
        story.append(Paragraph(f"Observação: {r.observacao or '-'}", styles['Cell']))
        try:
            recebedor = User.query.get(getattr(r, 'recebedor_id', None))
        except Exception:
            recebedor = None
        story.append(Paragraph(f"Recebido por: {recebedor.name} ({recebedor.username})" if recebedor else "Recebido por: -", styles['Normal']))

        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph('<b>Entregadores</b>', styles['h2']))
        carriers_data: list[list[Any]] = [['Nome', 'Peso (kg)']]
        for c in carriers:
            carriers_data.append([Paragraph(c.nome, styles['Cell']), f"{(c.peso or 0.0):.2f}"])
        if len(carriers) == 0:
            carriers_data.append(['Nenhum registrado', '-'])
        carriers_table = Table(carriers_data, colWidths=[doc.width * 0.7, doc.width * 0.3])
        carriers_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8f9fa')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(carriers_table)
        story.append(Spacer(1, 0.3 * inch))
        peso_nota = float(r.peso_nota or 0.0)
        # removido cálculo não utilizado (perda_transporte)
        totals_data: list[list[Any]] = [['Item', 'Valor']]
        if (r.tipo or 'bovina').lower() == 'bovina':
            totals_data.extend([
                ['Partes', str(sum(len(ps) for ps in animais.values()))],
                ['Romaneios', str(len(animais))],
                ['Peso na Nota (kg)', f"{peso_nota:.2f}"],
                ['Bruto Total (kg)', f"{total_bruto:.2f}"],
                ['Tara/Entregadores (kg)', f"{(funcionarios_aplicado_total + taras_total):.2f}"],
                ['Percas (kg)', f"{(peso_nota - float(total_liquido or 0.0)):.2f}"],
                ['Líquido (kg)', f"{total_liquido:.2f}"],
            ])
        else:
            totals_data.extend([
                ['Partes', str(sum(len(ps) for ps in animais.values()))],
                ['Romaneios', str(len(animais))],
                ['Bruto Total (kg)', f"{total_bruto:.2f}"],
                ['Tara/Entregadores (kg)', f"{(funcionarios_aplicado_total + taras_total):.2f}"],
                ['Líquido (kg)', f"{total_liquido:.2f}"],
            ])
        cols_t = len(totals_data[0])
        max_w_t = [0.0] * cols_t
        for row in totals_data:
            for j in range(cols_t):
                t = str(row[j])
                w = float(stringWidth(t, 'Helvetica', 9))
                if w > max_w_t[j]:
                    max_w_t[j] = w
        widths_t = [m + 12 for m in max_w_t]
        total_t = sum(widths_t)
        scale_t = doc.width / (total_t if total_t > 0 else 1)
        widths_t = [w * scale_t for w in widths_t]
        totals_table = Table(totals_data, colWidths=widths_t)
        totals_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8f9fa')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(KeepTogether([Paragraph('<b>Resumo</b>', styles['h2']), totals_table]))

        for num in sorted(animais.keys()):
            header = Paragraph(f"<b>Romaneio #{num}</b>", styles['h2'])
            data_rows_strings: list[list[str]] = [[
                'Parte', 'Peso bruto (kg)', 'Entregador', 'Tara caixa (kg)', 'Peso líquido (kg)'
            ]]
            subtotal_bruto = 0.0
            subtotal_liquido = 0.0
            subtotal_func = 0.0
            subtotal_tara = 0.0
            for p in animais[num]:
                subtotal_bruto += float(p.get('peso_bruto') or 0.0)
                subtotal_liquido += float(p.get('peso_liquido') or 0.0)
                subtotal_func += float(p.get('carrier_peso') or 0.0)
                subtotal_tara += float(p.get('tara') or 0.0)
                parte_label = f"{(p.get('categoria') or '').capitalize()} — {p.get('lado') or ''}"
                data_rows_strings.append([
                    parte_label,
                    f"{float(p.get('peso_bruto') or 0.0):.2f}",
                    p.get('carrier_nome') or '-',
                    (p.get('tara') is not None) and f"{float(p.get('tara') or 0.0):.2f}" or '-',
                    f"{float(p.get('peso_liquido') or 0.0):.2f}",
                ])
            data_rows_strings.append([
                'Subtotal', f"{subtotal_bruto:.2f}", f"{subtotal_func:.2f}", f"{subtotal_tara:.2f}", f"{subtotal_liquido:.2f}"
            ])
            # calcular larguras por conteúdo
            cols = len(data_rows_strings[0])
            max_w = [0.0] * cols
            for row in data_rows_strings:
                for j in range(cols):
                    t = str(row[j])
                    w = float(stringWidth(t, 'Helvetica', 9))
                    if w > max_w[j]:
                        max_w[j] = w
            widths_pts = [m + 12 for m in max_w]
            total_pts = sum(widths_pts)
            scale = doc.width / (total_pts if total_pts > 0 else 1)
            widths_pts = [w * scale for w in widths_pts]
            # construir dados com Paragraphs para evitar overflow
            table_data: list[list[Any]] = []
            for i, row in enumerate(data_rows_strings):
                table_row: list[Any] = []
                for j, cell in enumerate(row):
                    if j in (0, 2) and i != 0:  # Parte e Entregador
                        table_row.append(Paragraph(str(cell), styles['Cell']))
                    else:
                        table_row.append(str(cell))
                table_data.append(table_row)
            table = Table(table_data, colWidths=widths_pts, repeatRows=1)
            table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8f9fa')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f8f9fa')),
                ('ALIGN', (1, 1), (-1, -2), 'RIGHT'),
                ('ALIGN', (1, -1), (-1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('FONTNAME', (4, 1), (4, -1), 'Helvetica-Bold'),
                ('TEXTCOLOR', (4, 1), (4, -1), colors.HexColor('#198754')),
            ]))
            story.append(KeepTogether([header, table, Spacer(1, 0.2 * inch)]))

        styles.add(ParagraphStyle(name='Explain10', parent=styles['Normal'], fontSize=10, leading=12))
        calc_title = f"<b>COMO OS CÁLCULOS SÃO FEITOS ({(r.tipo or '').capitalize()}):</b><br/>"
        explain_html = (
            calc_title +
            '• Peso líquido por parte = Peso bruto − desconto aplicado.<br/>'
            '• Desconto aplicado:<br/>'
            '  - bovina usa o peso do entregador selecionado;<br/>'
            '  - suína usa a tara informada;<br/>'
            '  - frango não possui desconto por parte.<br/>'
            '• Subtotais por romaneio somam pesos bruto, líquido e descontos.<br/>'
            '• Totais gerais são a soma dos subtotais.<br/>'
            '• Bovina: Percas = Peso na Nota − Líquido.<br/>'
            '• Frango: o peso informado é considerado diretamente como líquido total.'
        )
        story.append(Spacer(1, 0.25 * inch))
        story.append(KeepTogether([Paragraph(explain_html, styles['Explain10'])]))

        
        
        def footer_on_page(canvas, doc):
            canvas.saveState()
            canvas.setFillColor(colors.black)
            canvas.setFont('Helvetica', 8)
            footer_text = f"Página {canvas.getPageNumber()} | MultiMax Carnes | {_now_br().strftime('%d/%m/%Y %H:%M:%S')}"
            canvas.drawString(inch, 0.5 * inch, footer_text)
            canvas.restoreState()
        def on_page(canvas, doc):
            _brand_header(canvas, doc)
            footer_on_page(canvas, doc)
        doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
        pdf_buffer.seek(0)
        ref = r.reference_code or f"R{r.id:04d}"
        filename = f"{ref}_CARNE.pdf"
        return send_file(pdf_buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')
    except Exception as e:
        flash(f'Erro ao gerar PDF de Carnes: {e}', 'danger')
        return redirect(url_for('carnes.relatorio', id=id))
