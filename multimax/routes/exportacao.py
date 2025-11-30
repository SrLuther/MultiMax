from datetime import datetime
import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from flask import Blueprint, redirect, url_for, flash, send_file, request
from flask_login import login_required, current_user
from ..models import Produto, CleaningTask, CleaningHistory, Historico
from io import BytesIO
from reportlab.platypus import Image
from reportlab.pdfbase.pdfmetrics import stringWidth
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

bp = Blueprint('exportacao', __name__)

@bp.route('/exportar/cronograma/pdf')
@login_required
def exportar_cronograma_pdf():
    if current_user.nivel not in ['operador', 'admin']:
        flash('Você não tem permissão para exportar o cronograma.', 'danger')
        return redirect(url_for('cronograma.cronograma'))
    try:
        filename = 'cronograma_limpeza_multimax.pdf'
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        styles.add(ParagraphStyle(name='Footer', fontSize=8, alignment=2, textColor=colors.gray))
        story.append(Paragraph('<b>MultiMax - Cronograma de Limpeza</b>', styles['Title']))
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(f'Gerado por: {current_user.name} ({current_user.nivel.upper()})', styles['Normal']))
        story.append(Paragraph(f"Data de Geração: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['Normal']))
        story.append(Spacer(1, 0.5 * inch))
        story.append(Paragraph('<b>Tarefas de Limpeza Agendadas</b>', styles['h2']))
        story.append(Spacer(1, 0.2 * inch))
        tarefas = CleaningTask.query.order_by(CleaningTask.proxima_data.asc()).all()
        data = [["Área/Limpeza", "Frequência", "Última Data", "Próxima Prevista", "Designado(s)", "Observações"]]
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
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#007bff')),
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
        data_hist = [["Data Conclusão", "Limpeza", "Realizado Por", "Observações"]]
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
            footer_text = f"Página {canvas.getPageNumber()} | MultiMax Cronograma | {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
            canvas.drawString(inch, 0.5 * inch, footer_text)
            canvas.restoreState()
        doc.build(story, onFirstPage=footer_on_page, onLaterPages=footer_on_page)
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
        story = []
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
            footer_text = f"Página {canvas.getPageNumber()} | MultiMax Tarefa | {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
            canvas.drawString(inch, 0.5 * inch, footer_text)
            canvas.restoreState()
        doc.build(story, onFirstPage=footer_on_page, onLaterPages=footer_on_page)
        pdf_buffer.seek(0)
        return send_file(pdf_buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')
    except Exception as e:
        flash(f'Erro ao gerar PDF da Tarefa: {e}', 'danger')
        return redirect(url_for('cronograma.cronograma'))

@bp.route('/exportar/estoque/pdf')
@login_required
def exportar():
    try:
        filename = 'relatorio_estoque_multimax.pdf'
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        story.append(Paragraph('<b>MultiMax - Relatório de Estoque</b>', styles['Title']))
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(f'Gerado por: {current_user.name} ({current_user.nivel.upper()})', styles['Normal']))
        story.append(Paragraph(f"Data de Geração: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['Normal']))
        story.append(Spacer(1, 0.5 * inch))
        produtos = Produto.query.order_by(Produto.quantidade.asc()).all()
        data = [["Cód.", "Produto", "Estoque", "Mínimo", "Custo (R$)", "Venda (R$)", "Status"]]
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
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#007bff')),
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
            footer_text = f"Página {canvas.getPageNumber()} | MultiMax Estoque | {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
            canvas.drawString(inch, 0.5 * inch, footer_text)
            canvas.restoreState()
        doc.build(story, onFirstPage=footer_on_page, onLaterPages=footer_on_page)
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
        story = []
        story.append(Paragraph('<b>MultiMax - Gráficos de Movimentação</b>', styles['Title']))
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(f"Produto: <b>{produto.nome}</b> (Cód: {produto.codigo})", styles['Normal']))
        story.append(Paragraph(f"Gerado por: {current_user.name}", styles['Normal']))
        story.append(Paragraph(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['Normal']))
        story.append(Spacer(1, 0.3 * inch))

        def fetch_hist(start_date=None, end_date=None):
            q = Historico.query.filter(Historico.product_id == produto.id)
            if start_date:
                q = q.filter(Historico.data >= start_date)
            if end_date:
                q = q.filter(Historico.data <= end_date)
            return q.order_by(Historico.data.asc()).all()

        def build_fig(labels, entradas, saidas, title):
            fig, ax = plt.subplots(figsize=(8.5, 3.5))
            x = range(len(labels))
            ax.bar(x, entradas, label='Entradas', color='#16A34A')
            ax.bar(x, saidas, bottom=entradas, label='Saídas', color='#EAB308', alpha=0.85)
            ax.set_title(title)
            ax.set_xticks(x)
            ax.set_xticklabels(labels, rotation=45, ha='right')
            ax.legend(loc='upper right')
            ax.grid(axis='y', linestyle='--', alpha=0.3)
            buf = BytesIO()
            fig.tight_layout()
            fig.savefig(buf, format='png', dpi=160)
            plt.close(fig)
            buf.seek(0)
            return buf

        def agg_weekly():
            from datetime import date, timedelta
            end = date.today()
            start = end - timedelta(days=7*8)
            hist = fetch_hist(datetime.combine(start, datetime.min.time()))
            buckets = {}
            cursor = start - timedelta(days=start.weekday())
            while cursor <= end:
                key = cursor
                buckets[key] = {'entrada': 0, 'saida': 0, 'label': f"Sem {cursor.strftime('%d/%m')}"}
                cursor += timedelta(days=7)
            for h in hist:
                d = h.data.date()
                monday = d - timedelta(days=d.weekday())
                if monday in buckets:
                    buckets[monday][h.action] += (h.quantidade or 0)
            labels = [v['label'] for k, v in sorted(buckets.items())]
            entradas = [v['entrada'] for k, v in sorted(buckets.items())]
            saidas = [v['saida'] for k, v in sorted(buckets.items())]
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
            labels = [buckets[yy]['label'] for yy in sorted(buckets.keys())]
            entradas = [buckets[yy]['entrada'] for yy in sorted(buckets.keys())]
            saidas = [buckets[yy]['saida'] for yy in sorted(buckets.keys())]
            return labels, entradas, saidas

        labels, entradas, saidas = agg_weekly()
        buf = build_fig(labels, entradas, saidas, 'Semanal (Últimas 8 semanas)')
        story.append(Image(buf, width=6.5*inch, height=2.7*inch))
        story.append(Spacer(1, 0.2 * inch))

        labels, entradas, saidas = agg_monthly()
        buf = build_fig(labels, entradas, saidas, 'Mensal (Últimos 12 meses)')
        story.append(Image(buf, width=6.5*inch, height=2.7*inch))
        story.append(Spacer(1, 0.2 * inch))

        labels, entradas, saidas = agg_yearly()
        buf = build_fig(labels, entradas, saidas, 'Anual (Últimos 5 anos)')
        story.append(Image(buf, width=6.5*inch, height=2.7*inch))

        def parse_date_safe(s):
            from datetime import datetime as _dt
            try:
                return _dt.strptime(s, '%Y-%m-%d')
            except Exception:
                return None

        di_dt = parse_date_safe(data_inicio_str)
        df_dt = parse_date_safe(data_fim_str)
        if di_dt and df_dt:
            if di_dt > df_dt:
                di_dt, df_dt = df_dt, di_dt
            hist = fetch_hist(di_dt, df_dt)
            from datetime import timedelta as _td
            buckets = {}
            cursor = di_dt.date()
            while cursor <= df_dt.date():
                buckets[cursor] = {'entrada': 0, 'saida': 0, 'label': cursor.strftime('%d/%m')}
                cursor += _td(days=1)
            for h in hist:
                d = h.data.date()
                if d in buckets:
                    buckets[d][h.action] += (h.quantidade or 0)
            items = [buckets[k] for k in sorted(buckets.keys())]
            labels = [v['label'] for v in items]
            entradas = [v['entrada'] for v in items]
            saidas = [v['saida'] for v in items]
            buf = build_fig(labels, entradas, saidas, 'Período Personalizado')
            story.append(Spacer(1, 0.2 * inch))
            story.append(Image(buf, width=6.5*inch, height=2.7*inch))

        def footer_on_page(canvas, doc):
            canvas.saveState()
            canvas.setFont('Helvetica', 8)
            footer_text = f"Página {canvas.getPageNumber()} | MultiMax Gráficos | {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
            canvas.drawString(inch, 0.5 * inch, footer_text)
            canvas.restoreState()
        doc.build(story, onFirstPage=footer_on_page, onLaterPages=footer_on_page)
        pdf_buffer.seek(0)
        return send_file(pdf_buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')
    except Exception as e:
        flash(f'Erro ao gerar PDF de Gráficos: {e}', 'danger')
        return redirect(url_for('usuarios.graficos'))
