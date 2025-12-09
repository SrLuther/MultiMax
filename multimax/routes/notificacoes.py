from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from .. import db
from ..models import EventoDoDia, NotificacaoDiaria, NotificacaoPersonalizada
from ..services.notificacao_service import enviar_relatorio_diario, criar_mensagem_personalizada, registrar_evento, gerar_relatorio
from datetime import date
import os
from urllib.request import Request, urlopen

bp = Blueprint('notificacoes', __name__, url_prefix='/notificacoes')

@bp.route('/', methods=['GET'], strict_slashes=False)
@login_required
def index():
    hoje = date.today()
    eventos = EventoDoDia.query.filter_by(data=hoje).order_by(EventoDoDia.id.asc()).all()
    msgs = NotificacaoPersonalizada.query.filter_by(enviada=False).order_by(NotificacaoPersonalizada.data_criacao.asc()).all()
    historico = NotificacaoDiaria.query.order_by(NotificacaoDiaria.id.desc()).limit(20).all()
    prev = gerar_relatorio(hoje)
    base = (os.getenv('WHATSAPP_API_URL') or '').strip()
    if not base:
        base = os.getenv('WPP_BASE_URL', 'http://localhost:3005').rstrip('/') + '/send'
    status_ok = False
    try:
        try:
            import requests  # type: ignore
            r = requests.get(base, timeout=3)
            status_ok = True if r is not None else False
        except Exception:
            req = Request(base)
            with urlopen(req, timeout=3) as resp:
                status_ok = True if resp is not None else False
    except Exception:
        status_ok = False
    return render_template('notificacoes.html', active_page='notificacoes', eventos=eventos, msgs=msgs, historico=historico, previa=prev, status_ok=status_ok)

@bp.route('/mensagem', methods=['POST'], strict_slashes=False)
@login_required
def mensagem():
    texto = (request.form.get('mensagem') or '').strip()
    reenviar = bool(request.form.get('reenviar_20h'))
    if not texto:
        flash('Informe a mensagem.', 'warning')
        return redirect(url_for('notificacoes.index'))
    criar_mensagem_personalizada(texto, reenviar)
    flash('Mensagem adicionada.', 'success')
    return redirect(url_for('notificacoes.index'))

@bp.route('/enviar-agora', methods=['POST'], strict_slashes=False)
@login_required
def enviar_agora():
    limpar = bool(request.form.get('limpar_apos_envio'))
    ok, texto = enviar_relatorio_diario('manual', limpar)
    if not texto:
        flash('Sem conteúdo relevante para enviar.', 'info')
        return redirect(url_for('notificacoes.index'))
    if ok:
        flash('Enviado com sucesso ao WhatsApp.', 'success')
    else:
        flash('Falha ao enviar ao WhatsApp.', 'danger')
    return redirect(url_for('notificacoes.index'))
