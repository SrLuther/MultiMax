from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from .. import db
from ..models import LossRecord, Produto

bp = Blueprint('perdas', __name__, url_prefix='/perdas')

def _now():
    return datetime.now(ZoneInfo('America/Sao_Paulo'))

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

@bp.route('/', methods=['GET'], strict_slashes=False)
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    motivo_filter = request.args.get('motivo', '').strip()
    data_inicio = request.args.get('data_inicio', '').strip()
    data_fim = request.args.get('data_fim', '').strip()
    
    query = LossRecord.query
    if motivo_filter:
        query = query.filter(LossRecord.motivo == motivo_filter)
    if data_inicio:
        try:
            dt_ini = datetime.strptime(data_inicio, '%Y-%m-%d')
            query = query.filter(LossRecord.data_registro >= dt_ini)
        except ValueError:
            pass
    if data_fim:
        try:
            dt_fim = datetime.strptime(data_fim, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(LossRecord.data_registro < dt_fim)
        except ValueError:
            pass
    
    query = query.order_by(LossRecord.data_registro.desc())
    per_page = int(current_app.config.get('PER_PAGE', 10))
    registros_pag = query.paginate(page=page, per_page=per_page, error_out=False)
    
    total_registros = LossRecord.query.count()
    custo_total = db.session.query(db.func.sum(LossRecord.custo_estimado)).scalar() or 0
    
    hoje = date.today()
    inicio_mes = date(hoje.year, hoje.month, 1)
    custo_mes = db.session.query(db.func.sum(LossRecord.custo_estimado)).filter(
        LossRecord.data_registro >= inicio_mes
    ).scalar() or 0
    
    registros_mes = LossRecord.query.filter(LossRecord.data_registro >= inicio_mes).count()
    
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
        total_registros=total_registros,
        custo_total=custo_total,
        custo_mes=custo_mes,
        registros_mes=registros_mes
    )

@bp.route('/registrar', methods=['POST'], strict_slashes=False)
@login_required
def registrar():
    if current_user.nivel not in ('operador', 'admin'):
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
    
    reg = LossRecord()
    reg.produto_id = produto_id
    reg.produto_nome = produto_nome
    reg.quantidade = quantidade
    reg.unidade = unidade
    reg.motivo = motivo
    reg.custo_estimado = custo
    reg.observacao = observacao
    reg.usuario = current_user.username
    reg.data_registro = _now()
    
    db.session.add(reg)
    
    if produto and produto.quantidade > 0:
        produto.quantidade = max(0, produto.quantidade - int(quantidade))
    
    db.session.commit()
    
    flash('Perda registrada com sucesso.', 'success')
    return redirect(url_for('perdas.index'))

@bp.route('/<int:id>/excluir', methods=['POST'], strict_slashes=False)
@login_required
def excluir(id: int):
    if current_user.nivel != 'admin':
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
