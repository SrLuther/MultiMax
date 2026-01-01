from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from .. import db
from ..models import LossRecord, Produto

bp = Blueprint('perdas', __name__, url_prefix='/perdas')

# ============================================================================
# Constantes
# ============================================================================

MOTIVOS_PERDA = [
    ('vencimento', 'Vencimento'),
    ('avaria', 'Avaria/Dano'),
    ('furto', 'Furto/Perda'),
    ('quebra', 'Quebra'),
    ('contaminacao', 'Contaminação'),
    ('erro_producao', 'Erro de Produção'),
    ('retorno', 'Retorno/Devolução'),
    ('outro', 'Outro')
]

# ============================================================================
# Funções auxiliares
# ============================================================================

def _now():
    """Retorna datetime atual com timezone"""
    return datetime.now(ZoneInfo('America/Sao_Paulo'))


def _parse_date_safe(date_str: str) -> datetime | None:
    """Parse seguro de data"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return None


def _get_registros_filtrados(page: int = 1, motivo_filter: str = '', 
                              data_inicio: str = '', data_fim: str = '', per_page: int = 10):
    """Busca registros de perdas com filtros e paginação"""
    query = LossRecord.query
    
    if motivo_filter:
        query = query.filter(LossRecord.motivo == motivo_filter)
    
    dt_ini = _parse_date_safe(data_inicio)
    if dt_ini:
        query = query.filter(LossRecord.data_registro >= dt_ini)
    
    if data_fim:
        dt_fim = _parse_date_safe(data_fim)
        if dt_fim:
            query = query.filter(LossRecord.data_registro < dt_fim + timedelta(days=1))
    
    query = query.order_by(LossRecord.data_registro.desc())
    return query.paginate(page=page, per_page=per_page, error_out=False)


def _get_kpis_perdas():
    """Calcula KPIs de perdas"""
    hoje = date.today()
    inicio_mes = date(hoje.year, hoje.month, 1)
    
    return {
        'total_registros': LossRecord.query.count(),
        'custo_total': db.session.query(db.func.sum(LossRecord.custo_estimado)).scalar() or 0,
        'custo_mes': db.session.query(db.func.sum(LossRecord.custo_estimado)).filter(
            LossRecord.data_registro >= inicio_mes
        ).scalar() or 0,
        'registros_mes': LossRecord.query.filter(LossRecord.data_registro >= inicio_mes).count(),
    }


# ============================================================================
# Rotas
# ============================================================================

@bp.route('/', methods=['GET'], strict_slashes=False)
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    motivo_filter = request.args.get('motivo', '').strip()
    data_inicio = request.args.get('data_inicio', '').strip()
    data_fim = request.args.get('data_fim', '').strip()
    
    registros_pag = _get_registros_filtrados(page, motivo_filter, data_inicio, data_fim)
    kpis = _get_kpis_perdas()
    produtos = Produto.query.order_by(Produto.nome).all()
    
    return render_template(
        'perdas.html',
        active_page='perdas',
        registros=registros_pag.items,
        registros_pag=registros_pag,
        motivo_filter=motivo_filter,
        data_inicio=data_inicio,
        data_fim=data_fim,
        motivos=MOTIVOS_PERDA,
        produtos=produtos,
        **kpis
    )

@bp.route('/registrar', methods=['POST'], strict_slashes=False)
@login_required
def registrar():
    if current_user.nivel == 'visualizador':
        flash('Visualizadores não têm permissão para fazer alterações no sistema.', 'danger')
        return redirect(url_for('perdas.index'))
    if current_user.nivel not in ('operador', 'admin', 'DEV'):
        flash('Sem permissão para registrar perdas.', 'warning')
        return redirect(url_for('perdas.index'))
    
    produto_id = request.form.get('produto_id', type=int)
    produto_nome = (request.form.get('produto_nome') or '').strip()
    quantidade_str = (request.form.get('quantidade') or '').strip()
    unidade = (request.form.get('unidade') or 'un').strip()
    motivo = (request.form.get('motivo') or '').strip()
    custo_str = (request.form.get('custo') or '0').strip()
    observacao = (request.form.get('observacao') or '').strip()
    
    if not motivo or not quantidade_str:
        flash('Informe a quantidade e o motivo da perda.', 'warning')
        return redirect(url_for('perdas.index'))
    
    try:
        quantidade = float(quantidade_str.replace(',', '.'))
        custo = float(custo_str.replace(',', '.'))
    except ValueError:
        flash('Valores inválidos.', 'warning')
        return redirect(url_for('perdas.index'))
    
    produto = None
    if produto_id:
        produto = Produto.query.get(produto_id)
        if produto:
            produto_nome = produto.nome
            if custo == 0 and produto.preco_custo:
                custo = quantidade * produto.preco_custo
    
    if not produto_nome:
        flash('Informe o produto.', 'warning')
        return redirect(url_for('perdas.index'))
    
    # Validação adicional
    if quantidade <= 0:
        flash('A quantidade deve ser maior que zero.', 'warning')
        return redirect(url_for('perdas.index'))
    
    if len(motivo) > 255:
        motivo = motivo[:255]
    if len(observacao) > 500:
        observacao = observacao[:500]
    
    reg = LossRecord()
    reg.produto_id = produto_id
    reg.produto_nome = produto_nome[:100] if produto_nome else ''
    reg.quantidade = quantidade
    reg.unidade = unidade[:10] if unidade else 'un'
    reg.motivo = motivo
    reg.custo_estimado = max(0, custo)  # Garantir não negativo
    reg.observacao = observacao
    reg.usuario = current_user.username[:100] if current_user.username else ''
    reg.data_registro = _now()
    
    try:
        db.session.add(reg)
        
        if produto and produto.quantidade > 0:
            produto.quantidade = max(0, produto.quantidade - int(quantidade))
        
        db.session.commit()
        flash('Perda registrada com sucesso.', 'success')
    except Exception as e:
        db.session.rollback()
        import logging
        logging.getLogger(__name__).error(f"Erro ao registrar perda: {e}", exc_info=True)
        flash('Erro ao registrar perda. Tente novamente.', 'danger')
    return redirect(url_for('perdas.index'))

@bp.route('/<int:id>/excluir', methods=['POST'], strict_slashes=False)
@login_required
def excluir(id: int):
    if current_user.nivel == 'visualizador':
        flash('Visualizadores não têm permissão para fazer alterações no sistema.', 'danger')
        return redirect(url_for('perdas.index'))
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Apenas administradores podem excluir registros.', 'warning')
        return redirect(url_for('perdas.index'))
    
    reg = LossRecord.query.get_or_404(id)
    try:
        db.session.delete(reg)
        db.session.commit()
        flash('Registro excluído.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir: {e}', 'danger')
    
    return redirect(url_for('perdas.index'))

@bp.route('/relatorio', methods=['GET'], strict_slashes=False)
@login_required
def relatorio():
    hoje = date.today()
    inicio_mes = date(hoje.year, hoje.month, 1)
    
    por_motivo = db.session.query(
        LossRecord.motivo,
        db.func.count(LossRecord.id).label('total'),
        db.func.sum(LossRecord.custo_estimado).label('custo')
    ).group_by(LossRecord.motivo).all()
    
    por_produto = db.session.query(
        LossRecord.produto_nome,
        db.func.count(LossRecord.id).label('total'),
        db.func.sum(LossRecord.custo_estimado).label('custo')
    ).group_by(LossRecord.produto_nome).order_by(db.desc('custo')).limit(10).all()
    
    ultimos_30_dias = []
    for i in range(30):
        dia = hoje - timedelta(days=i)
        custo = db.session.query(db.func.sum(LossRecord.custo_estimado)).filter(
            db.func.date(LossRecord.data_registro) == dia
        ).scalar() or 0
        ultimos_30_dias.append({'data': dia, 'custo': custo})
    
    ultimos_30_dias.reverse()
    
    motivos_dict = dict(MOTIVOS_PERDA)
    
    return render_template(
        'perdas_relatorio.html',
        active_page='perdas',
        por_motivo=por_motivo,
        por_produto=por_produto,
        ultimos_30_dias=ultimos_30_dias,
        motivos_dict=motivos_dict
    )
