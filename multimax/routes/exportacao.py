from datetime import datetime
from zoneinfo import ZoneInfo
import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, Flowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from flask import Blueprint, redirect, url_for, flash, send_file, request
from flask_login import login_required, current_user
from ..models import Produto, CleaningTask as CleaningTaskModel, CleaningHistory as CleaningHistoryModel, Historico, MeatReception, MeatCarrier, MeatPart, User, Recipe, RecipeIngredient
from ..models import Collaborator, HourBankEntry, LeaveCredit, LeaveAssignment, LeaveConversion
from sqlalchemy import func
from flask import render_template
from io import BytesIO
from typing import Any
from reportlab.platypus import Image
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
 

bp = Blueprint('exportacao', __name__)

_UBUNTU_AVAILABLE = False
def _register_ubuntu_fonts():
    global _UBUNTU_AVAILABLE
    try:
        root = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), '..'))
        env_norm = (os.getenv('PDF_FONT_UBUNTU_TTF') or '').strip()
        env_bold = (os.getenv('PDF_FONT_UBUNTU_BOLD_TTF') or '').strip()
        candidates_norm = [
            env_norm,
            os.path.join(root, 'static', 'fonts', 'Ubuntu-Regular.ttf'),
            r'C:\Windows\Fonts\Ubuntu-R.ttf',
            r'/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf',
        ]
        candidates_bold = [
            env_bold,
            os.path.join(root, 'static', 'fonts', 'Ubuntu-Bold.ttf'),
            r'C:\Windows\Fonts\Ubuntu-B.ttf',
            r'/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf',
        ]
        norm = next((p for p in candidates_norm if p and os.path.exists(p)), None)
        bold = next((p for p in candidates_bold if p and os.path.exists(p)), None)
        if norm and bold:
            pdfmetrics.registerFont(TTFont('Ubuntu', norm))
            pdfmetrics.registerFont(TTFont('Ubuntu-Bold', bold))
            _UBUNTU_AVAILABLE = True
    except Exception:
        _UBUNTU_AVAILABLE = False
_register_ubuntu_fonts()
def _font_normal():
    return 'Ubuntu' if _UBUNTU_AVAILABLE else 'Helvetica'
def _font_bold():
    return 'Ubuntu-Bold' if _UBUNTU_AVAILABLE else 'Helvetica-Bold'

def _now_br() -> datetime:
    try:
        return datetime.now(ZoneInfo('America/Sao_Paulo'))
    except Exception:
        return datetime.now()

PDF_PRIMARY = '#00ff88'
PDF_PRIMARY_DARK = '#00cc6a'
PDF_SECONDARY = '#198754'
PDF_DARK_BG = '#0f172a'
PDF_DARK_SECONDARY = '#1e293b'
PDF_TEXT_MUTED = '#64748b'
PDF_BORDER = '#334155'
PDF_SUCCESS = '#22c55e'
PDF_WARNING = '#f59e0b'
PDF_DANGER = '#ef4444'

def _brand_header(canvas, doc, content_type=None):
    canvas.saveState()
    header_h = 1.0 * inch
    y = doc.pagesize[1] - header_h
    w = doc.pagesize[0]
    steps = 32
    color_start = (0x0f, 0x17, 0x2a)
    color_mid = (0x1e, 0x29, 0x3b)
    color_end = (0x0f, 0x17, 0x2a)
    for i in range(steps):
        t = i / max(steps - 1, 1)
        if t < 0.5:
            k = t / 0.5
            r = int(color_start[0] + (color_mid[0] - color_start[0]) * k)
            g = int(color_start[1] + (color_mid[1] - color_start[1]) * k)
            b = int(color_start[2] + (color_mid[2] - color_start[2]) * k)
        else:
            k = (t - 0.5) / 0.5
            r = int(color_mid[0] + (color_end[0] - color_mid[0]) * k)
            g = int(color_mid[1] + (color_end[1] - color_mid[1]) * k)
            b = int(color_mid[2] + (color_end[2] - color_mid[2]) * k)
        canvas.setFillColor(colors.HexColor(f'#{r:02x}{g:02x}{b:02x}'))
        band_y = y + (header_h * (i / steps))
        canvas.rect(0, band_y, w, header_h / steps + 1, fill=True, stroke=False)
    canvas.setStrokeColor(colors.HexColor(PDF_PRIMARY))
    canvas.setLineWidth(3)
    canvas.line(0, y, w, y)
    logo_h = 1.3 * cm
    logo_w = logo_h
    try:
        root = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), '..'))
        logo_path = os.path.join(root, 'static', 'icons', 'logo-user.png')
        if os.path.exists(logo_path):
            canvas.drawImage(ImageReader(logo_path), 0.7 * cm, y + (header_h - logo_h) / 2, width=logo_w, height=logo_h, preserveAspectRatio=True, mask='auto')
    except Exception:
        pass
    title_main = 'MultiMax'
    title_sub = 'Gestao Amora'
    canvas.setFillColor(colors.HexColor(PDF_PRIMARY))
    canvas.setFont(_font_bold(), 20)
    tw_main = stringWidth(title_main, _font_bold(), 20)
    canvas.setFont(_font_normal(), 11)
    tw_sub = stringWidth(title_sub, _font_normal(), 11)
    total_tw = tw_main + 8 + tw_sub
    cx = w / 2.0 - total_tw / 2.0
    ty = y + header_h / 2
    if content_type:
        ty += 6
    canvas.setFont(_font_bold(), 20)
    canvas.drawString(cx, ty, title_main)
    canvas.setFillColor(colors.HexColor('#cbd5e1'))
    canvas.setFont(_font_normal(), 11)
    canvas.drawString(cx + tw_main + 8, ty + 2, title_sub)
    if content_type:
        ct_font = _font_bold()
        ct_size = 12
        tw_ct = stringWidth(str(content_type), ct_font, ct_size)
        cx_ct = w / 2.0 - tw_ct / 2.0
        canvas.setFillColor(colors.white)
        canvas.setFont(ct_font, ct_size)
        canvas.drawString(cx_ct, ty - 18, str(content_type))
    canvas.restoreState()

def _premium_footer(canvas, doc, section_name='Documento'):
    canvas.saveState()
    footer_h = 0.5 * inch
    w = doc.pagesize[0]
    for i in range(16):
        t = i / 15.0
        alpha = int(0x0f + (0x1e - 0x0f) * t)
        canvas.setFillColor(colors.HexColor(f'#{alpha:02x}{0x17 + int((0x29 - 0x17) * t):02x}{0x2a + int((0x3b - 0x2a) * t):02x}'))
        band_h = footer_h / 16
        canvas.rect(0, footer_h - (i + 1) * band_h, w, band_h + 0.5, fill=True, stroke=False)
    canvas.setStrokeColor(colors.HexColor(PDF_PRIMARY))
    canvas.setLineWidth(2)
    canvas.line(0, footer_h, w, footer_h)
    canvas.setFillColor(colors.HexColor('#94a3b8'))
    canvas.setFont(_font_normal(), 8)
    page_text = f"Pagina {canvas.getPageNumber()}"
    canvas.drawString(0.6 * inch, 0.2 * inch, page_text)
    date_text = _now_br().strftime('%d/%m/%Y %H:%M')
    tw_date = stringWidth(date_text, _font_normal(), 8)
    canvas.drawString(w - 0.6 * inch - tw_date, 0.2 * inch, date_text)
    canvas.setFillColor(colors.HexColor('#0f172a'))
    site_text = "www.multimax.tec.br"
    canvas.setFont(_font_normal(), 10)
    tw_site = stringWidth(site_text, _font_normal(), 10)
    canvas.drawString(w / 2.0 - tw_site / 2.0, 1.0 * cm, site_text)
    canvas.restoreState()

def _draw_cards_bg(canvas, doc, first_page: bool):
    canvas.saveState()
    x = doc.leftMargin - 4
    top = doc.pagesize[1] - doc.topMargin + 8
    bottom = doc.bottomMargin - 4
    w = doc.width + 8
    canvas.setFillColor(colors.HexColor('#f8fafc'))
    canvas.setStrokeColor(colors.HexColor('#e2e8f0'))
    canvas.setLineWidth(1)
    canvas.roundRect(x, bottom, w, top - bottom, 12, stroke=True, fill=True)
    canvas.setStrokeColor(colors.HexColor(PDF_PRIMARY))
    canvas.setLineWidth(0.5)
    canvas.line(x + 12, top - 1, x + w - 12, top - 1)
    canvas.restoreState()

def _get_pdf_template_path() -> str:
    try:
        root = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), '..'))
        default_path = os.path.join(root, 'templates', 'ModeloBasePDF.pdf')
        p = os.getenv('PDF_TEMPLATE_PATH', default_path)
        return p
    except Exception:
        try:
            root = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), '..'))
            return os.path.join(root, 'templates', 'ModeloBasePDF.pdf')
        except Exception:
            return r'C:\Users\Ciano\Desktop\MultiMax\templates\ModeloBasePDF.pdf'

def _has_pdf_template() -> bool:
    return False

def _finalize_pdf(pdf_buffer: BytesIO) -> BytesIO:
    pdf_buffer.seek(0)
    return BytesIO(pdf_buffer.read())

def _send_pdf(pdf_io: BytesIO, filename: str):
    mode = (request.args.get('mode') or '').strip().lower()
    if mode in ('view', 'print'):
        as_attach = False
    else:
        v = (request.args.get('download') or '1').strip().lower()
        as_attach = v not in ('0', 'false', 'no')
    return send_file(pdf_io, as_attachment=as_attach, download_name=filename, mimetype='application/pdf')

def _template_has_footer() -> bool:
    try:
        v = os.getenv('PDF_TEMPLATE_HAS_FOOTER', '0').strip().lower()
        return v in ('1', 'true', 'yes', 'y')
    except Exception:
        return False

class InfoCard(Flowable):
    def __init__(self, inner: Any, padding: float = 12, radius: float = 12, stroke_color: str = '#e2e8f0', accent_color: str | None = None):
        super().__init__()
        self.inner = inner
        self.padding = padding
        self.radius = radius
        self.stroke_color = stroke_color
        self.accent_color = accent_color or PDF_PRIMARY
        self._iw = 0
        self._ih = 0
    def wrap(self, availWidth, availHeight):
        iw, ih = 0, 0
        try:
            iw, ih = self.inner.wrap(availWidth - 2*self.padding, 1e9)
        except Exception:
            iw, ih = availWidth - 2*self.padding, 0.5 * inch
        self._iw, self._ih = iw, ih
        return (min(availWidth, iw + 2*self.padding), ih + 2*self.padding)
    def draw(self):
        from reportlab.lib.colors import HexColor
        c = self.canv
        c.saveState()
        total_w = self._iw + 2*self.padding
        total_h = self._ih + 2*self.padding
        c.setFillColor(colors.white)
        c.setStrokeColor(HexColor(self.stroke_color))
        c.setLineWidth(1)
        c.roundRect(0, 0, total_w, total_h, self.radius, stroke=True, fill=True)
        c.setFillColor(HexColor(self.accent_color))
        c.rect(0, total_h - 4, total_w, 4, fill=True, stroke=False)
        try:
            self.inner.drawOn(c, self.padding, self.padding)
        except Exception:
            pass
        c.restoreState()

def _make_info_block(tipo: str, pairs: list[tuple[str, str]], registrado_por=None):
    styles = getSampleStyleSheet()
    key_style = ParagraphStyle(name='InfoKey', parent=styles['Normal'], fontName=_font_bold(), fontSize=9, leading=12, alignment=0, wordWrap='LTR', textColor=colors.HexColor('#475569'))
    val_style = ParagraphStyle(name='InfoVal', parent=styles['Normal'], fontName=_font_normal(), fontSize=9, leading=12, alignment=0, wordWrap='LTR', textColor=colors.HexColor('#0f172a'))
    rows: list[list[Any]] = [
        [Paragraph('Gerado por', key_style), Paragraph(f"{current_user.name} ({current_user.nivel.upper()})", val_style)],
        [Paragraph('Data e Hora', key_style), Paragraph(_now_br().strftime('%d/%m/%Y %H:%M:%S'), val_style)],
    ]
    if registrado_por:
        rows.insert(1, [Paragraph('Registrado por', key_style), Paragraph(str(registrado_por), val_style)])
    for k, v in pairs:
        rows.append([Paragraph(str(k), key_style), Paragraph(str(v), val_style)])
    tbl = Table(rows, colWidths=[2.0*inch, None], hAlign='LEFT')
    tbl.setStyle(TableStyle([
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#0f172a')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (0, -1), _font_bold()),
        ('FONTNAME', (1, 0), (1, -1), _font_normal()),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    return InfoCard(tbl, padding=14, radius=12)

def _premium_table_style(header_color=None):
    if header_color is None:
        header_color = PDF_SECONDARY
    return TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(header_color)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), _font_bold()),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
    ])

@bp.route('/exportar/receita/<int:id>.pdf')
@login_required
def exportar_receita_pdf(id: int):
    try:
        r = Recipe.query.get_or_404(id)
        ings = RecipeIngredient.query.filter_by(recipe_id=r.id).order_by(RecipeIngredient.id.asc()).all()
        filename = f"receita_{r.id}.pdf"
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, leftMargin=0.6*inch, rightMargin=0.6*inch, topMargin=1.15*inch, bottomMargin=0.7*inch)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Cell', parent=styles['Normal'], fontSize=10, leading=14, wordWrap='LTR', textColor=colors.HexColor('#0f172a')))
        styles.add(ParagraphStyle(name='SectionTitle', parent=styles['Heading2'], fontSize=14, leading=18, textColor=colors.HexColor(PDF_SECONDARY), fontName=_font_bold(), spaceBefore=12, spaceAfter=8))
        story: list[Any] = []
        story.append(_make_info_block('Receita', [('Nome', r.nome), ('Embalagem', ('Embalado a vacuo' if (r.embalagem or '') == 'vacuo' else 'Caixa'))], registrado_por=None))
        story.append(Spacer(1, 0.3 * inch))
        story.append(Paragraph('Modo de Preparo', styles['SectionTitle']))
        story.append(Paragraph(r.preparo or '-', styles['Cell']))
        story.append(Spacer(1, 0.35 * inch))
        story.append(Paragraph('Ingredientes', styles['SectionTitle']))
        data: list[list[Any]] = [["Ingrediente", "Quantidade"]]
        if ings:
            for it in ings:
                data.append([it.nome, it.quantidade or '-'])
        else:
            data.append(["-", "-"])
        table = Table(data, colWidths=[4.0*inch, 2.5*inch])
        table.setStyle(_premium_table_style())
        story.append(table)
        def on_page(canvas, doc):
            _brand_header(canvas, doc, 'Receita')
            _draw_cards_bg(canvas, doc, canvas.getPageNumber() == 1)
            _premium_footer(canvas, doc, 'Receita')
        doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
        final_io = _finalize_pdf(pdf_buffer)
        return _send_pdf(final_io, filename)
    except Exception as e:
        flash(f'Erro ao gerar PDF da Receita: {e}', 'danger')
        return redirect(url_for('receitas.index', id=id))

@bp.route('/exportar/cronograma/pdf')
@login_required
def exportar_cronograma_pdf():
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Você não tem permissão para exportar o cronograma.', 'danger')
        return redirect(url_for('cronograma.cronograma'))
    try:
        filename = 'cronograma_limpeza_multimax.pdf'
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, leftMargin=0.4*inch, rightMargin=0.4*inch, topMargin=1.15*inch, bottomMargin=0.7*inch)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Cell', parent=styles['Normal'], fontSize=9, leading=11, wordWrap='LTR'))
        styles.add(ParagraphStyle(name='SectionTitle', parent=styles['Heading2'], fontSize=14, leading=18, textColor=colors.HexColor(PDF_SECONDARY), fontName=_font_bold(), spaceBefore=12, spaceAfter=8))
        story: list[Any] = []
        story.append(_make_info_block('Cronograma de Limpeza', [], registrado_por=None))
        story.append(Spacer(1, 0.4 * inch))
        story.append(Paragraph('Tarefas de Limpeza Agendadas', styles['SectionTitle']))
        story.append(Spacer(1, 0.2 * inch))
        tarefas = CleaningTaskModel.query.order_by(CleaningTaskModel.proxima_data.asc()).all()
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
        table.setStyle(_premium_table_style())
        story.append(table)
        story.append(PageBreak())
        story.append(Paragraph('Histórico de Conclusões (Recentes)', styles['SectionTitle']))
        story.append(Spacer(1, 0.15 * inch))
        historico = CleaningHistoryModel.query.order_by(CleaningHistoryModel.data_conclusao.desc()).limit(20).all()
        data_hist: list[list[Any]] = [["Data Conclusão", "Limpeza", "Realizado Por", "Observações"]]
        for h in historico:
            data_hist.append([h.data_conclusao.strftime('%d/%m/%Y %H:%M'), Paragraph(h.nome_limpeza, styles['Normal']), h.designados, Paragraph(h.observacao or '-', styles['Normal'])])
        table_hist = Table(data_hist, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 2*inch])
        table_hist.setStyle(_premium_table_style('#6c757d'))
        story.append(table_hist)
        def on_page(canvas, doc):
            _brand_header(canvas, doc, 'Cronograma de Limpeza')
            _draw_cards_bg(canvas, doc, canvas.getPageNumber() == 1)
            _premium_footer(canvas, doc, 'Cronograma de Limpeza')
        doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
        final_io = _finalize_pdf(pdf_buffer)
        return _send_pdf(final_io, filename)
    except Exception as e:
        flash(f'Erro ao gerar PDF do Cronograma: {e}', 'danger')
        return redirect(url_for('cronograma.cronograma'))

@bp.route('/exportar/cronograma/tarefa/<int:id>.pdf')
@login_required
def exportar_tarefa_pdf(id):
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Você não tem permissão para exportar tarefas.', 'danger')
        return redirect(url_for('cronograma.cronograma'))
    try:
        tarefa = CleaningTaskModel.query.get_or_404(id)
        filename = f"tarefa_{tarefa.id}_cronograma.pdf"
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, leftMargin=0.6*inch, rightMargin=0.6*inch, topMargin=1.15*inch, bottomMargin=0.7*inch)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Cell', parent=styles['Normal'], fontSize=9, leading=11, wordWrap='LTR'))
        styles.add(ParagraphStyle(name='SectionTitle', parent=styles['Heading2'], fontSize=14, leading=18, textColor=colors.HexColor(PDF_SECONDARY), fontName=_font_bold(), spaceBefore=12, spaceAfter=8))
        story: list[Any] = []
        story.append(_make_info_block('Detalhes da Tarefa de Limpeza', [
            ('Tarefa', tarefa.nome_limpeza),
            ('Frequência/Regra', tarefa.frequencia),
            ('Última Realização', tarefa.ultima_data.strftime('%d/%m/%Y')),
            ('Próxima Prevista', tarefa.proxima_data.strftime('%d/%m/%Y')),
        ], registrado_por=None))
        story.append(Spacer(1, 0.3 * inch))
        hist = CleaningHistoryModel.query.filter_by(nome_limpeza=tarefa.nome_limpeza).order_by(CleaningHistoryModel.data_conclusao.desc()).limit(5).all()
        obs = tarefa.observacao or ('Sem observações.' if not hist else hist[0].observacao or 'Sem observações.')
        desig = tarefa.designados or ('Não especificado' if not hist else hist[0].designados or 'Não especificado')
        story.append(Paragraph(f"Observações: {obs}", styles['Cell']))
        story.append(Paragraph(f"Designado(s): {desig}", styles['Cell']))
        story.append(Spacer(1, 0.3 * inch))
        if hist:
            story.append(Paragraph('Últimas Conclusões', styles['SectionTitle']))
            data_hist = [["Data", "Realizado Por", "Observações"]]
            for h in hist:
                data_hist.append([h.data_conclusao.strftime('%d/%m/%Y %H:%M'), h.designados, h.observacao or '-'])
            table_hist = Table(data_hist, colWidths=[1.5*inch, 2*inch, 3*inch])
            table_hist.setStyle(_premium_table_style('#6c757d'))
            story.append(table_hist)
        def on_page(canvas, doc):
            _brand_header(canvas, doc, 'Detalhes da Tarefa de Limpeza')
            _draw_cards_bg(canvas, doc, canvas.getPageNumber() == 1)
            _premium_footer(canvas, doc, 'Tarefa de Limpeza')
        doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
        final_io = _finalize_pdf(pdf_buffer)
        return _send_pdf(final_io, filename)
    except Exception as e:
        flash(f'Erro ao gerar PDF da Tarefa: {e}', 'danger')
        return redirect(url_for('cronograma.cronograma'))

@bp.route('/exportar/limpeza/historico/<int:id>.pdf')
@login_required
def exportar_historico_limpeza_pdf(id):
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Você não tem permissão para exportar histórico de limpezas.', 'danger')
        return redirect(url_for('cronograma.cronograma'))
    try:
        h = CleaningHistoryModel.query.get_or_404(id)
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, leftMargin=0.6*inch, rightMargin=0.6*inch, topMargin=1.15*inch, bottomMargin=0.7*inch)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Cell', parent=styles['Normal'], fontSize=10, leading=14, wordWrap='LTR', textColor=colors.HexColor('#0f172a')))
        story: list[Any] = []
        story.append(_make_info_block('Histórico de Limpeza', [
            ('Data', h.data_conclusao.strftime('%d/%m/%Y %H:%M')),
            ('Tipo', h.nome_limpeza),
            ('Realizado por', h.designados or h.usuario_conclusao or '-'),
            ('Observação', h.observacao or '-'),
        ], registrado_por=None))
        def on_page(canvas, doc):
            _brand_header(canvas, doc, 'Histórico de Limpeza')
            _draw_cards_bg(canvas, doc, canvas.getPageNumber() == 1)
            _premium_footer(canvas, doc, 'Histórico de Limpeza')
        doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
        final_io = _finalize_pdf(pdf_buffer)
        filename = f"historico_{id}.pdf"
        return _send_pdf(final_io, filename)
    except Exception as e:
        flash(f'Erro ao gerar PDF do histórico: {e}', 'danger')
        return redirect(url_for('cronograma.cronograma'))

@bp.route('/exportar/estoque/pdf')
@login_required
def exportar():
    try:
        filename = 'relatorio_estoque_multimax.pdf'
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, leftMargin=0.6*inch, rightMargin=0.6*inch, topMargin=1.15*inch, bottomMargin=0.7*inch)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Cell', parent=styles['Normal'], fontSize=9, leading=11, wordWrap='LTR'))
        story: list[Any] = []
        story.append(_make_info_block('Relatório de Estoque', [], registrado_por=None))
        story.append(Spacer(1, 0.4 * inch))
        produtos = Produto.query.order_by(Produto.quantidade.asc()).all()
        data: list[list[Any]] = [["Cód.", "Produto", "Estoque", "Mínimo", "Status"]]
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
        status_in = 1.0
        numeric_sum_in = estoque_in + minimo_in + status_in
        # Produto ocupa o restante e quebra linha
        product_col_width_in = max(1.2, avail_in - code_col_width_in - numeric_sum_in)
        code_col_width = code_col_width_in * inch
        product_col_width = product_col_width_in * inch
        code_style = ParagraphStyle(name='CodeCell', fontName=_font_normal(), fontSize=8, leading=9)
        product_style = ParagraphStyle(name='ProductCell', fontName=_font_normal(), fontSize=9, leading=10, wordWrap='LTR')
        def fit_text_to_width(text, width_pts, font=None, font_size=8, padding=4):
            if font is None:
                font = _font_normal()
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
                status
            ])
        table = Table(
            data,
            colWidths=[code_col_width, product_col_width, estoque_in*inch, minimo_in*inch, status_in*inch]
        )
        table.setStyle(_premium_table_style())
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ]))
        for i, p in enumerate(produtos):
            row_index = i + 1
            if p.quantidade < p.estoque_minimo:
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, row_index), (-1, row_index), colors.HexColor(PDF_DANGER)),
                    ('TEXTCOLOR', (0, row_index), (-1, row_index), colors.white),
                ]))
            elif p.quantidade == p.estoque_minimo:
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, row_index), (-1, row_index), colors.HexColor(PDF_WARNING)),
                    ('TEXTCOLOR', (0, row_index), (-1, row_index), colors.black),
                ]))
        story.append(table)
        def on_page(canvas, doc):
            _brand_header(canvas, doc, 'Relatório de Estoque')
            _draw_cards_bg(canvas, doc, canvas.getPageNumber() == 1)
            _premium_footer(canvas, doc, 'Relatório de Estoque')
        doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
        final_io = _finalize_pdf(pdf_buffer)
        return _send_pdf(final_io, filename)
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
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, leftMargin=0.6*inch, rightMargin=0.6*inch, topMargin=1.15*inch, bottomMargin=0.7*inch)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='SectionTitle', parent=styles['Heading2'], fontSize=14, leading=18, textColor=colors.HexColor(PDF_SECONDARY), fontName=_font_bold(), spaceBefore=12, spaceAfter=8))
        story: list[Any] = []
        story.append(_make_info_block('Relatório de Movimentação', [('Produto', f"{produto.nome}"), ('Código', f"{produto.codigo}")], registrado_por=None))
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
            table.setStyle(_premium_table_style('#007bff'))
            story.append(table)
            story.append(Spacer(1, 0.2 * inch))

        def add_bar_chart(title, labels, entradas, saidas):
            try:
                story.append(Paragraph(title, styles['SectionTitle']))
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

        def on_page(canvas, doc):
            _brand_header(canvas, doc, 'Relatório de Movimentação')
            _draw_cards_bg(canvas, doc, canvas.getPageNumber() == 1)
            _premium_footer(canvas, doc, 'Relatório de Movimentação')
        doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
        final_io = _finalize_pdf(pdf_buffer)
        return _send_pdf(final_io, filename)
    except Exception as e:
        flash(f'Erro ao gerar PDF de Gráficos: {e}', 'danger')
        return redirect(url_for('usuarios.graficos'))

@bp.route('/exportar/carnes/relatorio/<int:id>.pdf')
@login_required
def exportar_relatorio_carnes_pdf(id):
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
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
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, leftMargin=0.6*inch, rightMargin=0.6*inch, topMargin=1.15*inch, bottomMargin=0.7*inch)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Cell', parent=styles['Normal'], fontSize=9, leading=11, wordWrap='LTR'))
        styles.add(ParagraphStyle(name='SectionTitle', parent=styles['Heading2'], fontSize=14, leading=18, textColor=colors.HexColor(PDF_SECONDARY), fontName=_font_bold(), spaceBefore=12, spaceAfter=8))
        story: list[Any] = []
        try:
            recebedor = User.query.get(getattr(r, 'recebedor_id', None))
        except Exception:
            recebedor = None
        story.append(Paragraph('Dados da Recepção', styles['SectionTitle']))
        story.append(Paragraph(f"Data: {r.data.strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
        story.append(Paragraph(f"Número de referência: {r.reference_code or '-'}", styles['Normal']))
        story.append(Paragraph(f"Fornecedor: {r.fornecedor}", styles['Cell']))
        story.append(Paragraph(f"Tipo: {(r.tipo or '').capitalize()}", styles['Normal']))
        story.append(Paragraph(f"Observação: {r.observacao or '-'}", styles['Cell']))
        if recebedor:
            story.append(Paragraph(f"Registrado por: {recebedor.name} ({recebedor.username})", styles['Normal']))

        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph('Entregadores', styles['SectionTitle']))
        carriers_data: list[list[Any]] = [['Nome', 'Peso (kg)']]
        for c in carriers:
            carriers_data.append([Paragraph(c.nome, styles['Cell']), f"{(c.peso or 0.0):.2f}"])
        if len(carriers) == 0:
            carriers_data.append(['Nenhum registrado', '-'])
        carriers_table = Table(carriers_data, colWidths=[doc.width * 0.7, doc.width * 0.3])
        carriers_table.setStyle(_premium_table_style())
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
                w = float(stringWidth(t, _font_normal(), 9))
                if w > max_w_t[j]:
                    max_w_t[j] = w
        widths_t = [m + 12 for m in max_w_t]
        total_t = sum(widths_t)
        scale_t = doc.width / (total_t if total_t > 0 else 1)
        widths_t = [w * scale_t for w in widths_t]
        totals_table = Table(totals_data, colWidths=widths_t)
        totals_table.setStyle(_premium_table_style('#6c757d'))
        story.append(KeepTogether([Paragraph('Resumo', styles['SectionTitle']), totals_table]))

        for num in sorted(animais.keys()):
            header = Paragraph(f"Romaneio #{num}", styles['SectionTitle'])
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
                    w = float(stringWidth(t, _font_normal(), 9))
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
            table.setStyle(_premium_table_style('#6c757d'))
            table.setStyle(TableStyle([
                ('FONTNAME', (0, -1), (-1, -1), _font_bold()),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f1f5f9')),
                ('ALIGN', (1, 1), (-1, -2), 'RIGHT'),
                ('ALIGN', (1, -1), (-1, -1), 'RIGHT'),
                ('FONTNAME', (4, 1), (4, -1), _font_bold()),
                ('TEXTCOLOR', (4, 1), (4, -1), colors.HexColor(PDF_SUCCESS)),
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

        
        
        def on_page(canvas, doc):
            _brand_header(canvas, doc, 'Relatório de Recepção de Carnes')
            _draw_cards_bg(canvas, doc, canvas.getPageNumber() == 1)
            _premium_footer(canvas, doc, 'Relatório de Carnes')
        doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
        final_io = _finalize_pdf(pdf_buffer)
        ref = r.reference_code or f"R{r.id:04d}"
        filename = f"{ref}_CARNE.pdf"
        return _send_pdf(final_io, filename)
    except Exception as e:
        flash(f'Erro ao gerar PDF de Carnes: {e}', 'danger')
        return redirect(url_for('carnes.relatorio', id=id))

@bp.route('/exportar/carnes/relatorio/periodo.pdf')
@login_required
def exportar_relatorio_carnes_periodo():
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Você não tem permissão para exportar relatório de carnes.', 'danger')
        return redirect(url_for('carnes.index'))
    try:
        tipo = (request.args.get('tipo') or '').strip().lower()
        escopo = (request.args.get('escopo') or 'dia').strip().lower()
        data_str = (request.args.get('data') or '').strip()
        if tipo not in ('bovina','suina','frango'):
            tipo = 'frango'
        from datetime import datetime, timedelta, date as _date
        tz = ZoneInfo('America/Sao_Paulo')
        base_date = None
        if data_str:
            try:
                base_date = datetime.strptime(data_str, '%Y-%m-%d').date()
            except Exception:
                base_date = None
        if not base_date:
            base_date = _date.today()
        if escopo == 'semana':
            monday = base_date - timedelta(days=base_date.weekday())
            sunday = monday + timedelta(days=6)
            start_dt = datetime.combine(monday, datetime.min.time()).replace(tzinfo=tz)
            end_dt = datetime.combine(sunday, datetime.max.time()).replace(tzinfo=tz)
            escopo_label = f"Semana {monday.strftime('%d/%m/%Y')} — {sunday.strftime('%d/%m/%Y')}"
        else:
            start_dt = datetime.combine(base_date, datetime.min.time()).replace(tzinfo=tz)
            end_dt = datetime.combine(base_date, datetime.max.time()).replace(tzinfo=tz)
            escopo_label = f"Dia {base_date.strftime('%d/%m/%Y')}"

        recs = (
            MeatReception.query
            .filter(MeatReception.tipo == tipo)
            .filter(MeatReception.data >= start_dt)
            .filter(MeatReception.data <= end_dt)
            .order_by(MeatReception.data.asc())
            .all()
        )
        # Otimização: usar lista de IDs diretamente ao invés de list comprehension desnecessária
        reception_ids = [r.id for r in recs] if recs else []
        carriers_all = MeatCarrier.query.filter(MeatCarrier.reception_id.in_(reception_ids)).all() if reception_ids else []
        carriers_by_rec = {}
        for c in carriers_all:
            carriers_by_rec.setdefault(c.reception_id, []).append(c)
        parts_all = MeatPart.query.filter(MeatPart.reception_id.in_(reception_ids)).order_by(MeatPart.id.asc()).all() if reception_ids else []
        parts_by_rec = {}
        for p in parts_all:
            parts_by_rec.setdefault(p.reception_id, []).append(p)

        def _total_liquido(r: MeatReception) -> float:
            if tipo == 'frango':
                return float(r.peso_frango or 0.0)
            total = 0.0
            plist = parts_by_rec.get(r.id, [])
            if tipo == 'bovina':
                cmap = {c.id: c for c in carriers_by_rec.get(r.id, [])}
                for part in plist:
                    c = cmap.get(part.carrier_id)
                    cw = (c.peso if c else 0.0)
                    bruto = float(part.peso_bruto or 0.0)
                    sub = cw if cw > 0 else float(part.tara or 0.0)
                    total += max(0.0, bruto - sub)
            else:  # suina
                for part in plist:
                    bruto = float(part.peso_bruto or 0.0)
                    tara = float(part.tara or 0.0)
                    total += max(0.0, bruto - tara)
            return float(total)

        filename = f"relatorio_carnes_{tipo}_{escopo}_{base_date.strftime('%Y%m%d')}.pdf"
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, leftMargin=0.6*inch, rightMargin=0.6*inch, topMargin=1.15*inch, bottomMargin=0.7*inch)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Cell', parent=styles['Normal'], fontSize=9, leading=11, wordWrap='LTR'))
        story: list[Any] = []
        story.append(_make_info_block('Relatório de Recepção de Carnes', [
            ('Escopo', escopo_label),
            ('Tipo', (tipo or '').capitalize()),
        ], registrado_por=None))
        story.append(Spacer(1, 0.35 * inch))

        data_rows: list[list[Any]] = [['Data/Hora', 'Fornecedor', 'Ref.', 'Recebedor', 'Total (kg)']]
        total_geral = 0.0
        for r in recs:
            try:
                recebedor = User.query.get(getattr(r, 'recebedor_id', None))
            except Exception:
                recebedor = None
            tot = _total_liquido(r)
            total_geral += tot
            data_rows.append([
                r.data.strftime('%d/%m/%Y %H:%M'),
                Paragraph(r.fornecedor, styles['Cell']),
                r.reference_code or '-',
                (recebedor and f"{recebedor.name} ({recebedor.username})" or '-'),
                f"{tot:.2f}",
            ])

        avail_in = (doc.width) / inch
        date_in = 1.2
        ref_in = 0.9
        total_in = 1.2
        recebedor_in = 1.5
        fixed_sum = date_in + ref_in + total_in + recebedor_in
        fornecedor_in = max(1.2, avail_in - fixed_sum)
        if fornecedor_in + fixed_sum > avail_in:
            excess = (fornecedor_in + fixed_sum) - avail_in
            recebedor_in = max(1.2, recebedor_in - excess)
        table = Table(data_rows, colWidths=[date_in*inch, fornecedor_in*inch, ref_in*inch, recebedor_in*inch, total_in*inch])
        table.setStyle(_premium_table_style())
        story.append(table)
        story.append(Spacer(1, 0.3 * inch))
        styles.add(ParagraphStyle(name='SectionTitle', parent=styles['Heading2'], fontSize=14, leading=18, textColor=colors.HexColor(PDF_SECONDARY), fontName=_font_bold(), spaceBefore=12, spaceAfter=8))
        story.append(Paragraph(f"Total geral: {total_geral:.2f} kg", styles['SectionTitle']))

        def on_page(canvas, doc):
            _brand_header(canvas, doc, 'Relatório de Recepção de Carnes — Período')
            _draw_cards_bg(canvas, doc, canvas.getPageNumber() == 1)
            _premium_footer(canvas, doc, 'Relatório de Carnes — Período')
        doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
        final_io = _finalize_pdf(pdf_buffer)
        return _send_pdf(final_io, filename)
    except Exception as e:
        flash(f'Erro ao gerar PDF de Carnes (período): {e}', 'danger')
        return redirect(url_for('carnes.index'))

@bp.route('/exportar/exemplo/pdf')
@login_required
def exportar_exemplo_pdf():
    try:
        filename = 'exemplo_layout_multimax.pdf'
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, leftMargin=0.6*inch, rightMargin=0.6*inch, topMargin=1.15*inch, bottomMargin=0.7*inch)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Cell', parent=styles['Normal'], fontSize=10, leading=13, wordWrap='LTR'))
        styles.add(ParagraphStyle(name='SectionTitle', parent=styles['Heading2'], fontSize=14, leading=18, textColor=colors.HexColor(PDF_SECONDARY), fontName=_font_bold(), spaceBefore=12, spaceAfter=8))
        story: list[Any] = []
        story.append(_make_info_block('Exemplo de Layout Padrão', [('Seção', 'Demonstração'), ('Ambiente', 'Local')], registrado_por=None))
        story.append(Spacer(1, 0.35 * inch))
        story.append(Paragraph('Conteúdo Principal', styles['SectionTitle']))
        lorem = ('Este é um exemplo de PDF com cabeçalho padronizado, cards com cantos arredondados e conteúdo consistente. '
                 'A primeira página possui um card menor com metadados da requisição (usuário, data/hora e tipo), seguido por um card ocupando o restante da página com o conteúdo principal. '
                 'As páginas seguintes usam um card único ocupando toda a página para o conteúdo.')
        for _ in range(3):
            story.append(Paragraph(lorem, styles['Cell']))
            story.append(Spacer(1, 0.2 * inch))
        for i in range(1, 25):
            story.append(Paragraph(f"Linha de exemplo #{i:02d} — conteúdo demonstrativo.", styles['Cell']))
        def on_page(canvas, doc):
            _brand_header(canvas, doc, 'Exemplo de Layout Padrão')
            _draw_cards_bg(canvas, doc, canvas.getPageNumber() == 1)
            _premium_footer(canvas, doc, 'Exemplo')
        doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
        final_io = _finalize_pdf(pdf_buffer)
        return _send_pdf(final_io, filename)
    except Exception as e:
        flash(f'Erro ao gerar PDF de Exemplo: {e}', 'danger')
        return redirect(url_for('home.index'))


@bp.route('/exportar/jornada/pdf')
@login_required
def exportar_jornada_pdf():
    if current_user.nivel not in ['operador', 'admin', 'DEV']:
        flash('Você não tem permissão para exportar relatório de jornada.', 'danger')
        return redirect(url_for('jornada.index'))
    try:
        collab_id = request.args.get('collaborator_id', type=int)
        inicio = (request.args.get('inicio') or '').strip()
        fim = (request.args.get('fim') or '').strip()
        di = None
        df = None
        try:
            if inicio:
                di = datetime.strptime(inicio, '%Y-%m-%d').date()
        except Exception:
            di = None
        try:
            if fim:
                df = datetime.strptime(fim, '%Y-%m-%d').date()
        except Exception:
            df = None
        colaboradores = Collaborator.query.filter_by(active=True).order_by(Collaborator.name.asc()).all()
        def _range_filter(q, col):
            if di and df:
                return q.filter(col.between(di, df))
            if di:
                return q.filter(col >= di)
            if df:
                return q.filter(col <= df)
            return q
        resumo = []
        eventos = []
        targets = colaboradores if not collab_id else [c for c in colaboradores if c.id == collab_id]
        for c in targets:
            try:
                hq = _range_filter(HourBankEntry.query.filter(HourBankEntry.collaborator_id == c.id), HourBankEntry.date)
                cq = _range_filter(LeaveCredit.query.filter(LeaveCredit.collaborator_id == c.id), LeaveCredit.date)
                aq = _range_filter(LeaveAssignment.query.filter(LeaveAssignment.collaborator_id == c.id), LeaveAssignment.date)
                vq = _range_filter(LeaveConversion.query.filter(LeaveConversion.collaborator_id == c.id), LeaveConversion.date)
                hsum = float(hq.with_entities(func.coalesce(func.sum(HourBankEntry.hours), 0.0)).scalar() or 0.0)
                residual_hours = (hsum % 8.0) if hsum >= 0.0 else - ((-hsum) % 8.0)
                credits_sum = int(cq.with_entities(func.coalesce(func.sum(LeaveCredit.amount_days), 0)).scalar() or 0)
                assigned_sum = int(aq.with_entities(func.coalesce(func.sum(LeaveAssignment.days_used), 0)).scalar() or 0)
                converted_sum = int(vq.with_entities(func.coalesce(func.sum(LeaveConversion.amount_days), 0)).scalar() or 0)
                saldo_days = credits_sum - assigned_sum - converted_sum
                resumo.append({'id': c.id, 'name': c.name, 'residual_hours': residual_hours, 'saldo_days': saldo_days})
                for e in hq.order_by(HourBankEntry.date.desc()).all():
                    eventos.append(['horas', e.date.strftime('%d/%m/%Y'), c.name, f"{float(e.hours or 0.0):.2f} h", e.reason or ''])
                for cr in cq.order_by(LeaveCredit.date.desc()).all():
                    eventos.append(['dias_add', cr.date.strftime('%d/%m/%Y'), c.name, f"+{int(cr.amount_days or 0)} dia(s)", cr.notes or ''])
                for a in aq.order_by(LeaveAssignment.date.desc()).all():
                    eventos.append(['dias_uso', a.date.strftime('%d/%m/%Y'), c.name, f"-{int(a.days_used or 0)} dia(s)", a.notes or ''])
                for v in vq.order_by(LeaveConversion.date.desc()).all():
                    eventos.append(['dias_pago', v.date.strftime('%d/%m/%Y'), c.name, f"{int(v.amount_days or 0)} dia(s) — R$ {float(v.amount_paid or 0):.2f}", v.notes or ''])
            except Exception:
                pass
        eventos.sort(key=lambda it: (it[2], it[1]), reverse=True)
        filename = 'relatorio_jornada_multimax.pdf'
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, leftMargin=0.6*inch, rightMargin=0.6*inch, topMargin=1.15*inch, bottomMargin=0.7*inch)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Cell', parent=styles['Normal'], fontSize=9, leading=12, wordWrap='LTR'))
        styles.add(ParagraphStyle(name='SectionTitle', parent=styles['Heading2'], fontSize=14, leading=18, textColor=colors.HexColor(PDF_SECONDARY), fontName=_font_bold(), spaceBefore=12, spaceAfter=8))
        story: list[Any] = []
        story.append(_make_info_block('Relatório de Jornada', [
            ('Colaborador', (next((c.name for c in colaboradores if c.id == collab_id), 'Todos') if collab_id else 'Todos')),
            ('Período', (f"{inicio or '-'} até {fim or '-'}"))
        ], registrado_por=None))
        story.append(Spacer(1, 0.35 * inch))
        story.append(Paragraph('Resumo de Saldos', styles['SectionTitle']))
        story.append(Spacer(1, 0.15 * inch))
        data_resumo: list[list[Any]] = [['Colaborador', 'Horas restantes', 'Dias restantes']]
        for r in resumo:
            data_resumo.append([Paragraph(r['name'], styles['Cell']), f"{float(r['residual_hours']):.2f} h", f"{int(r['saldo_days'])} dia(s)"])
        table_resumo = Table(data_resumo, hAlign='LEFT')
        table_resumo.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
            ('FONTNAME', (0,0), (-1,0), _font_bold()),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(table_resumo)
        story.append(Spacer(1, 0.3 * inch))
        story.append(Paragraph('Eventos do Período', styles['SectionTitle']))
        story.append(Spacer(1, 0.15 * inch))
        data_eventos: list[list[Any]] = [['Data', 'Colaborador', 'Tipo', 'Valor', 'Observações']]
        for e in eventos:
            tipo_label = {'horas':'Horas registradas','dias_add':'Dias acrescentados','dias_uso':'Dias usados','dias_pago':'Dias convertidos em R$'}.get(e[0], e[0])
            data_eventos.append([e[1], Paragraph(e[2], styles['Cell']), tipo_label, e[3], Paragraph(e[4], styles['Cell'])])
        table_events = Table(data_eventos, hAlign='LEFT', colWidths=[1.0*inch, 2.0*inch, 1.8*inch, 1.2*inch, None])
        table_events.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
            ('FONTNAME', (0,0), (-1,0), _font_bold()),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(table_events)
        def on_page(canvas, doc):
            _brand_header(canvas, doc, 'Relatório de Jornada')
            _draw_cards_bg(canvas, doc, canvas.getPageNumber() == 1)
            _premium_footer(canvas, doc, 'Jornada')
        doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
        final_io = _finalize_pdf(pdf_buffer)
        return _send_pdf(final_io, filename)
    except Exception as e:
        flash(f'Erro ao gerar PDF de Jornada: {e}', 'danger')
        return redirect(url_for('jornada.index'))
