from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from .. import db
from ..models import Produto

bp = Blueprint('validade', __name__, url_prefix='/validade')

def _today():
    return date.today()

@bp.route('/', methods=['GET'], strict_slashes=False)
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    dias_alerta = request.args.get('dias', 7, type=int)
    apenas_vencidos = request.args.get('vencidos', '') == '1'
    
    today = _today()
    limite = today + timedelta(days=dias_alerta)
    
    query = Produto.query.filter(Produto.data_validade.isnot(None))
    
    if apenas_vencidos:
        query = query.filter(Produto.data_validade < today)
    else:
        query = query.filter(Produto.data_validade <= limite)
    
    query = query.order_by(Produto.data_validade.asc())
    per_page = int(current_app.config.get('PER_PAGE', 10))
    produtos_pag = query.paginate(page=page, per_page=per_page, error_out=False)
    
    total_com_validade = Produto.query.filter(Produto.data_validade.isnot(None)).count()
    vencidos = Produto.query.filter(Produto.data_validade < today).count()
    proximos_7dias = Produto.query.filter(
        Produto.data_validade >= today,
        Produto.data_validade <= today + timedelta(days=7)
    ).count()
    proximos_30dias = Produto.query.filter(
        Produto.data_validade >= today,
        Produto.data_validade <= today + timedelta(days=30)
    ).count()
    
    for p in produtos_pag.items:
        if p.data_validade:
            delta = (p.data_validade - today).days
            if delta < 0:
                p.status_validade = 'vencido'
                p.dias_restantes = abs(delta)
            elif delta <= 3:
                p.status_validade = 'critico'
                p.dias_restantes = delta
            elif delta <= 7:
                p.status_validade = 'alerta'
                p.dias_restantes = delta
            else:
                p.status_validade = 'ok'
                p.dias_restantes = delta
    
    return render_template(
        'validade.html',
        active_page='validade',
        produtos=produtos_pag.items,
        produtos_pag=produtos_pag,
        dias_alerta=dias_alerta,
        apenas_vencidos=apenas_vencidos,
        total_com_validade=total_com_validade,
        vencidos=vencidos,
        proximos_7dias=proximos_7dias,
        proximos_30dias=proximos_30dias,
        today=today
    )

@bp.route('/fifo', methods=['GET'], strict_slashes=False)
@login_required
def fifo():
    page = request.args.get('page', 1, type=int)
    
    query = Produto.query.filter(
        Produto.data_validade.isnot(None),
        Produto.quantidade > 0
    ).order_by(Produto.data_validade.asc())
    
    per_page = int(current_app.config.get('PER_PAGE', 20))
    produtos_pag = query.paginate(page=page, per_page=per_page, error_out=False)
    
    today = _today()
    for p in produtos_pag.items:
        if p.data_validade:
            delta = (p.data_validade - today).days
            if delta < 0:
                p.prioridade = 'urgente'
            elif delta <= 3:
                p.prioridade = 'alta'
            elif delta <= 7:
                p.prioridade = 'media'
            else:
                p.prioridade = 'normal'
    
    return render_template(
        'validade_fifo.html',
        active_page='validade',
        produtos=produtos_pag.items,
        produtos_pag=produtos_pag,
        today=today
    )

@bp.route('/sugerir-promocao', methods=['GET'], strict_slashes=False)
@login_required
def sugerir_promocao():
    today = _today()
    limite = today + timedelta(days=10)
    
    produtos = Produto.query.filter(
        Produto.data_validade.isnot(None),
        Produto.data_validade >= today,
        Produto.data_validade <= limite,
        Produto.quantidade > 0
    ).order_by(Produto.data_validade.asc()).limit(20).all()
    
    sugestoes = []
    for p in produtos:
        delta = (p.data_validade - today).days
        if delta <= 3:
            desconto = 50
        elif delta <= 5:
            desconto = 30
        elif delta <= 7:
            desconto = 20
        else:
            desconto = 10
        
        preco_promocional = p.preco_venda * (1 - desconto / 100) if p.preco_venda else 0
        
        sugestoes.append({
            'produto': p,
            'dias_restantes': delta,
            'desconto_sugerido': desconto,
            'preco_original': p.preco_venda or 0,
            'preco_promocional': preco_promocional
        })
    
    return render_template(
        'validade_promocao.html',
        active_page='validade',
        sugestoes=sugestoes,
        today=today
    )
