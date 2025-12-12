import os
from datetime import date, datetime
from zoneinfo import ZoneInfo
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import json
from .. import db
from ..models import EventoDoDia, NotificacaoPersonalizada, NotificacaoDiaria

def _enabled() -> bool:
    return (os.getenv('NOTIFICACOES_ENABLED', 'false') or 'false').lower() == 'true'

def registrar_evento(tipo: str, produto: str | None = None, quantidade: int | None = None, limite: int | None = None, descricao: str | None = None):
    if not _enabled():
        return
    e = EventoDoDia()
    e.tipo = tipo
    e.produto = produto
    e.quantidade = quantidade
    e.limite = limite
    e.descricao = descricao
    e.data = date.today()
    db.session.add(e)
    db.session.commit()

def _coletar_eventos(d: date):
    if not _enabled():
        return []
    return EventoDoDia.query.filter_by(data=d).order_by(EventoDoDia.id.asc()).all()

def _coletar_personalizadas_pendentes():
    if not _enabled():
        return []
    return NotificacaoPersonalizada.query.filter_by(enviada=False).order_by(NotificacaoPersonalizada.data_criacao.asc()).all()

def gerar_relatorio(d: date | None = None):
    if not _enabled():
        return ''
    if not d:
        d = date.today()
    eventos = _coletar_eventos(d)
    msgs = _coletar_personalizadas_pendentes()
    partes = []
    if eventos:
        linhas = []
        for e in eventos:
            base = e.tipo
            dets = []
            if e.produto:
                dets.append(e.produto)
            if e.quantidade is not None:
                dets.append(str(e.quantidade))
            if e.limite is not None:
                dets.append(f"limite {e.limite}")
            if e.descricao:
                dets.append(e.descricao)
            if dets:
                base = base + ": " + ", ".join(dets)
            linhas.append("• " + base)
        partes.append("Eventos do dia:\n" + "\n".join(linhas))
    if msgs:
        linhas_m = ["• " + (m.mensagem or '').strip() for m in msgs if (m.mensagem or '').strip()]
        if linhas_m:
            partes.append("Avisos:\n" + "\n".join(linhas_m))
    if not partes:
        return ''
    cab = f"Relatório diário {d.strftime('%d/%m/%Y')}"
    return cab + "\n\n" + "\n\n".join(partes)

def _post_whatsapp(message: str) -> bool:
    if not _enabled():
        return False
    gid = os.getenv('WPP_GROUP_ID', '')
    if not gid:
        return False
    api_url = (os.getenv('WHATSAPP_API_URL') or '').strip()
    if not api_url:
        base = os.getenv('WPP_BASE_URL', 'http://localhost:3005').rstrip('/')
        api_url = base + '/send'
    payload = {'groupId': gid, 'message': message}
    try:
        try:
            import requests  # type: ignore
            r = requests.post(api_url, json=payload, timeout=8)
            return 200 <= (getattr(r, 'status_code', 500) or 500) < 300
        except Exception:
            data = json.dumps(payload).encode('utf-8')
            req = Request(api_url, data=data, headers={'Content-Type':'application/json'})
            with urlopen(req, timeout=8) as resp:
                return 200 <= (resp.getcode() or 500) < 300
    except Exception:
        return False

def enviar_relatorio_diario(tipo: str = 'automatico', limpar_personalizadas: bool = False) -> tuple[bool, str]:
    if not _enabled():
        return False, ''
    hoje = date.today()
    texto = gerar_relatorio(hoje)
    if not texto:
        return False, ''
    ok = _post_whatsapp(texto)
    n = NotificacaoDiaria()
    n.data = hoje
    n.hora = datetime.now(ZoneInfo('America/Sao_Paulo')).strftime('%H:%M')
    n.tipo = tipo
    n.conteudo = texto
    n.enviado = bool(ok)
    db.session.add(n)
    if limpar_personalizadas:
        pend = _coletar_personalizadas_pendentes()
        for m in pend:
            m.enviada = True
    db.session.commit()
    return ok, texto

def criar_mensagem_personalizada(mensagem: str, reenviar_20h: bool = True):
    if not _enabled():
        return None
    msg = NotificacaoPersonalizada()
    msg.mensagem = mensagem
    msg.enviar_novamente = bool(reenviar_20h)
    msg.enviada = False
    db.session.add(msg)
    db.session.commit()
    registrar_evento('aviso', descricao=mensagem)
    return msg
