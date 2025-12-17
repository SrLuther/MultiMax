from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from .. import db
from ..models import EventoDoDia, NotificacaoDiaria, NotificacaoPersonalizada
from ..services.notificacao_service import enviar_relatorio_diario, criar_mensagem_personalizada, registrar_evento, gerar_relatorio
from datetime import date

bp = Blueprint('notificacoes', __name__, url_prefix='/notificacoes')

@bp.route('/', methods=['GET'], strict_slashes=False)
@login_required
def index():
    hoje = date.today()
    eventos = EventoDoDia.query.filter_by(data=hoje).order_by(EventoDoDia.id.asc()).all()
    msgs = NotificacaoPersonalizada.query.filter_by(enviada=False).order_by(NotificacaoPersonalizada.data_criacao.asc()).all()
    historico = NotificacaoDiaria.query.order_by(NotificacaoDiaria.id.desc()).limit(20).all()
    prev = gerar_relatorio(hoje)
    return render_template('notificacoes.html', active_page='notificacoes', eventos=eventos, msgs=msgs, historico=historico, previa=prev)

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
        flash('Relatório registrado com sucesso.', 'success')
    else:
        flash('Falha ao registrar relatório.', 'danger')
    return redirect(url_for('notificacoes.index'))
