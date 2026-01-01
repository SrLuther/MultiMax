from flask import Blueprint, render_template, request, current_app
from flask_login import login_required
from datetime import date, timedelta
from ..models import Produto

bp = Blueprint('validade', __name__, url_prefix='/validade')

# ============================================================================
# Funções auxiliares
# ============================================================================

def _today():
    """Retorna data de hoje"""
    return date.today()


def _calcular_status_validade(produto: Produto, today: date) -> tuple[str, int]:
    """Calcula status e dias restantes de validade"""
    if not produto.data_validade:
        return 'sem_validade', 0
    
    delta = (produto.data_validade - today).days
    if delta < 0:
        return 'vencido', abs(delta)
    elif delta <= 3:
        return 'critico', delta
    elif delta <= 7:
        return 'alerta', delta
    else:
        return 'ok', delta


def _get_produtos_validade_filtrados(page: int = 1, dias_alerta: int = 7, 
                                      apenas_vencidos: bool = False, per_page: int = 10):
    """Busca produtos com filtros de validade"""
    today = _today()
    limite = today + timedelta(days=dias_alerta)
    
    query = Produto.query.filter(Produto.data_validade.isnot(None))
    
    if apenas_vencidos:
        query = query.filter(Produto.data_validade < today)
    else:
        query = query.filter(Produto.data_validade <= limite)
    
    query = query.order_by(Produto.data_validade.asc())
    return query.paginate(page=page, per_page=per_page, error_out=False)


def _enrich_produtos_validade(produtos: list, today: date):
    """Adiciona status e dias restantes aos produtos"""
    for p in produtos:
        p.status_validade, p.dias_restantes = _calcular_status_validade(p, today)


def _get_kpis_validade():
    """Calcula KPIs de validade"""
    today = _today()
    return {
        'total_com_validade': Produto.query.filter(Produto.data_validade.isnot(None)).count(),
        'vencidos': Produto.query.filter(Produto.data_validade < today).count(),
        'proximos_7dias': Produto.query.filter(
            Produto.data_validade >= today,
            Produto.data_validade <= today + timedelta(days=7)
        ).count(),
        'proximos_30dias': Produto.query.filter(
            Produto.data_validade >= today,
            Produto.data_validade <= today + timedelta(days=30)
        ).count(),
    }


# ============================================================================
# Rotas
# ============================================================================

@bp.route('/', methods=['GET'], strict_slashes=False)
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    dias_alerta = request.args.get('dias', 7, type=int)
    apenas_vencidos = request.args.get('vencidos', '') == '1'
    
    today = _today()
    produtos_pag = _get_produtos_validade_filtrados(page, dias_alerta, apenas_vencidos)
    _enrich_produtos_validade(produtos_pag.items, today)
    kpis = _get_kpis_validade()
    
    return render_template(
        'validade.html',
        active_page='validade',
        produtos=produtos_pag.items,
        produtos_pag=produtos_pag,
        dias_alerta=dias_alerta,
        apenas_vencidos=apenas_vencidos,
        today=today,
        **kpis
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
