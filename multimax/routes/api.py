from flask import Blueprint, jsonify, request, g
from flask_login import current_user
from functools import wraps
from datetime import date, datetime, timedelta
import hashlib
from .. import db
from ..models import Produto, Historico, Fornecedor, User, CleaningTask, NotificationRead, Collaborator, Recipe

bp = Blueprint('api', __name__, url_prefix='/api/v1')

cache = {}
CACHE_TTL = 30

def _cache_get(key: str):
    v = cache.get(key)
    if not v:
        return None
    data, exp = v
    if datetime.now() < exp:
        return data
    cache.pop(key, None)
    return None

def _cache_set(key: str, value, ttl: int = CACHE_TTL):
    cache[key] = (value, datetime.now() + timedelta(seconds=ttl))

def verify_api_key():
    api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
    if not api_key:
        return None
    
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    user = User.query.filter_by(api_key_hash=key_hash).first()
    return user

def api_auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = verify_api_key()
        if user:
            g.api_user = user
        elif current_user.is_authenticated:
            g.api_user = current_user
        else:
            return jsonify({'error': 'Autenticação necessária. Use X-API-Key header ou faça login.', 'code': 401}), 401
        
        if g.api_user.nivel not in ['operador', 'admin']:
            return jsonify({'error': 'Acesso negado', 'code': 403}), 403
        return f(*args, **kwargs)
    return decorated_function

def api_admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'api_user') or g.api_user.nivel != 'admin':
            return jsonify({'error': 'Apenas administradores podem realizar esta ação', 'code': 403}), 403
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/produtos', methods=['GET'])
@api_auth_required
def listar_produtos():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    busca = request.args.get('busca', '').strip()
    
    query = Produto.query
    if busca:
        query = query.filter(
            (Produto.nome.contains(busca)) | 
            (Produto.codigo.contains(busca))
        )
    
    produtos_pag = query.order_by(Produto.nome.asc()).paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'produtos': [{
            'id': p.id,
            'codigo': p.codigo,
            'nome': p.nome,
            'quantidade': p.quantidade,
            'estoque_minimo': p.estoque_minimo,
            'preco_custo': p.preco_custo,
            'preco_venda': p.preco_venda,
            'data_validade': p.data_validade.isoformat() if p.data_validade else None,
            'lote': p.lote,
            'fornecedor_id': p.fornecedor_id
        } for p in produtos_pag.items],
        'total': produtos_pag.total,
        'page': page,
        'per_page': per_page,
        'pages': produtos_pag.pages
    })

@bp.route('/produtos/<int:id>', methods=['GET'])
@api_auth_required
def obter_produto(id: int):
    produto = Produto.query.get_or_404(id)
    return jsonify({
        'id': produto.id,
        'codigo': produto.codigo,
        'nome': produto.nome,
        'quantidade': produto.quantidade,
        'estoque_minimo': produto.estoque_minimo,
        'preco_custo': produto.preco_custo,
        'preco_venda': produto.preco_venda,
        'data_validade': produto.data_validade.isoformat() if produto.data_validade else None,
        'lote': produto.lote,
        'fornecedor_id': produto.fornecedor_id
    })

@bp.route('/produtos', methods=['POST'])
@api_auth_required
def criar_produto():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Dados JSON não fornecidos'}), 400
    
    nome = data.get('nome', '').strip()
    if not nome:
        return jsonify({'error': 'Nome é obrigatório'}), 400
    
    codigo = data.get('codigo', '').strip()
    if not codigo:
        return jsonify({'error': 'Código é obrigatório'}), 400
    
    if Produto.query.filter_by(codigo=codigo).first():
        return jsonify({'error': 'Código já existe'}), 400
    
    produto = Produto()
    produto.codigo = codigo
    produto.nome = nome
    produto.quantidade = data.get('quantidade', 0)
    produto.estoque_minimo = data.get('estoque_minimo', 0)
    produto.preco_custo = data.get('preco_custo', 0.0)
    produto.preco_venda = data.get('preco_venda', 0.0)
    
    if data.get('data_validade'):
        try:
            produto.data_validade = datetime.strptime(data['data_validade'], '%Y-%m-%d').date()
        except:
            pass
    
    produto.lote = data.get('lote')
    produto.fornecedor_id = data.get('fornecedor_id')
    
    db.session.add(produto)
    db.session.commit()
    
    return jsonify({
        'message': 'Produto criado com sucesso',
        'id': produto.id
    }), 201

@bp.route('/produtos/<int:id>', methods=['PUT'])
@api_auth_required
def atualizar_produto(id: int):
    produto = Produto.query.get_or_404(id)
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Dados JSON não fornecidos'}), 400
    
    if 'nome' in data:
        produto.nome = data['nome']
    if 'quantidade' in data:
        produto.quantidade = data['quantidade']
    if 'estoque_minimo' in data:
        produto.estoque_minimo = data['estoque_minimo']
    if 'preco_custo' in data:
        produto.preco_custo = data['preco_custo']
    if 'preco_venda' in data:
        produto.preco_venda = data['preco_venda']
    if 'data_validade' in data:
        if data['data_validade']:
            try:
                produto.data_validade = datetime.strptime(data['data_validade'], '%Y-%m-%d').date()
            except:
                pass
        else:
            produto.data_validade = None
    if 'lote' in data:
        produto.lote = data['lote']
    if 'fornecedor_id' in data:
        produto.fornecedor_id = data['fornecedor_id']
    
    db.session.commit()
    
    return jsonify({'message': 'Produto atualizado com sucesso'})

@bp.route('/produtos/<int:id>', methods=['DELETE'])
@api_auth_required
def excluir_produto(id: int):
    if g.api_user.nivel != 'admin':
        return jsonify({'error': 'Apenas administradores podem excluir produtos'}), 403
    
    produto = Produto.query.get_or_404(id)
    Historico.query.filter_by(product_id=id).delete()
    db.session.delete(produto)
    db.session.commit()
    
    return jsonify({'message': 'Produto excluído com sucesso'})

@bp.route('/produtos/<int:id>/entrada', methods=['POST'])
@api_auth_required
def entrada_produto(id: int):
    produto = Produto.query.get_or_404(id)
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Dados JSON não fornecidos'}), 400
    
    quantidade = data.get('quantidade', 0)
    if quantidade <= 0:
        return jsonify({'error': 'Quantidade deve ser positiva'}), 400
    
    produto.quantidade += quantidade
    
    hist = Historico()
    hist.product_id = produto.id
    hist.product_name = produto.nome
    hist.action = 'entrada'
    hist.quantidade = quantidade
    hist.details = data.get('detalhes', 'Entrada via API')
    hist.usuario = g.api_user.username
    db.session.add(hist)
    db.session.commit()
    
    return jsonify({
        'message': 'Entrada registrada com sucesso',
        'novo_estoque': produto.quantidade
    })

@bp.route('/produtos/<int:id>/saida', methods=['POST'])
@api_auth_required
def saida_produto(id: int):
    produto = Produto.query.get_or_404(id)
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Dados JSON não fornecidos'}), 400
    
    quantidade = data.get('quantidade', 0)
    if quantidade <= 0:
        return jsonify({'error': 'Quantidade deve ser positiva'}), 400
    
    if quantidade > produto.quantidade:
        return jsonify({'error': 'Quantidade insuficiente em estoque'}), 400
    
    produto.quantidade -= quantidade
    
    hist = Historico()
    hist.product_id = produto.id
    hist.product_name = produto.nome
    hist.action = 'saida'
    hist.quantidade = quantidade
    hist.details = data.get('detalhes', 'Saída via API')
    hist.usuario = g.api_user.username
    db.session.add(hist)
    db.session.commit()
    
    return jsonify({
        'message': 'Saída registrada com sucesso',
        'novo_estoque': produto.quantidade
    })

@bp.route('/fornecedores', methods=['GET'])
@api_auth_required
def listar_fornecedores():
    fornecedores = Fornecedor.query.order_by(Fornecedor.nome.asc()).all()
    return jsonify({
        'fornecedores': [{
            'id': f.id,
            'nome': f.nome,
            'cnpj': f.cnpj,
            'telefone': f.telefone,
            'email': f.email,
            'endereco': f.endereco,
            'ativo': f.ativo
        } for f in fornecedores]
    })

@bp.route('/historico', methods=['GET'])
@api_auth_required
def listar_historico():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    produto_id = request.args.get('produto_id', type=int)
    
    query = Historico.query
    if produto_id:
        query = query.filter_by(product_id=produto_id)
    
    historico_pag = query.order_by(Historico.data.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'historico': [{
            'id': h.id,
            'data': h.data.isoformat() if h.data else None,
            'product_id': h.product_id,
            'product_name': h.product_name,
            'action': h.action,
            'quantidade': h.quantidade,
            'details': h.details,
            'usuario': h.usuario
        } for h in historico_pag.items],
        'total': historico_pag.total,
        'page': page,
        'per_page': per_page,
        'pages': historico_pag.pages
    })

@bp.route('/estoque/baixo', methods=['GET'])
@api_auth_required
def produtos_estoque_baixo():
    key = 'produtos_estoque_baixo'
    cached = _cache_get(key)
    if cached is not None:
        return jsonify(cached)
    produtos = Produto.query.filter(
        Produto.quantidade <= Produto.estoque_minimo,
        Produto.estoque_minimo > 0
    ).order_by(Produto.nome.asc()).all()
    data = {
        'produtos': [{
            'id': p.id,
            'codigo': p.codigo,
            'nome': p.nome,
            'quantidade': p.quantidade,
            'estoque_minimo': p.estoque_minimo
        } for p in produtos],
        'total': len(produtos)
    }
    _cache_set(key, data)
    return jsonify(data)

@bp.route('/notifications', methods=['GET'])
def get_notifications():
    if not current_user.is_authenticated:
        return jsonify({'notifications': [], 'count': 0})
    
    notifications = []
    today = date.today()
    
    try:
        crit = Produto.query.filter(
            Produto.estoque_minimo.isnot(None),
            Produto.estoque_minimo > 0,
            Produto.quantidade <= Produto.estoque_minimo
        ).order_by(Produto.quantidade.asc()).limit(10).all()
        
        for p in crit:
            is_read = NotificationRead.query.filter_by(
                user_id=current_user.id, tipo='estoque', ref_id=p.id
            ).first() is not None
            if not is_read:
                notifications.append({
                    'id': p.id,
                    'type': 'estoque',
                    'icon': 'exclamation-triangle-fill',
                    'color': 'danger',
                    'title': f'Estoque crítico: {p.nome[:25]}',
                    'subtitle': f'{p.quantidade}/{p.estoque_minimo} unidades',
                    'url': '/estoque',
                    'time': 'Agora'
                })
    except Exception:
        pass
    
    try:
        horizon = today + timedelta(days=3)
        tasks = CleaningTask.query.filter(
            CleaningTask.proxima_data.isnot(None),
            CleaningTask.proxima_data <= horizon
        ).order_by(CleaningTask.proxima_data.asc()).limit(10).all()
        
        for t in tasks:
            is_read = NotificationRead.query.filter_by(
                user_id=current_user.id, tipo='limpeza', ref_id=t.id
            ).first() is not None
            if not is_read:
                if t.proxima_data < today:
                    status = 'Atrasada'
                    color = 'danger'
                elif t.proxima_data == today:
                    status = 'Hoje'
                    color = 'warning'
                else:
                    status = t.proxima_data.strftime('%d/%m')
                    color = 'info'
                notifications.append({
                    'id': t.id,
                    'type': 'limpeza',
                    'icon': 'calendar-check',
                    'color': color,
                    'title': f'Tarefa: {t.nome_limpeza[:25]}',
                    'subtitle': status,
                    'url': '/cronograma/',
                    'time': status
                })
    except Exception:
        pass
    
    try:
        prox_validade = Produto.query.filter(
            Produto.data_validade.isnot(None),
            Produto.data_validade <= today + timedelta(days=7),
            Produto.quantidade > 0
        ).order_by(Produto.data_validade.asc()).limit(5).all()
        
        for p in prox_validade:
            if p.data_validade < today:
                status = 'Vencido'
                color = 'danger'
            elif p.data_validade == today:
                status = 'Vence hoje'
                color = 'danger'
            else:
                dias = (p.data_validade - today).days
                status = f'Vence em {dias}d'
                color = 'warning'
            notifications.append({
                'id': p.id,
                'type': 'validade',
                'icon': 'clock-history',
                'color': color,
                'title': f'Validade: {p.nome[:25]}',
                'subtitle': status,
                'url': '/estoque',
                'time': status
            })
    except Exception:
        pass
    
    return jsonify({
        'notifications': notifications[:15],
        'count': len(notifications)
    })

@bp.route('/notifications/read', methods=['POST'])
def mark_notification_read():
    if not current_user.is_authenticated:
        return jsonify({'error': 'Não autenticado'}), 401
    
    data = request.get_json() or {}
    tipo = data.get('type')
    ref_id = data.get('id')
    
    if not tipo or not ref_id:
        return jsonify({'error': 'Dados inválidos'}), 400
    
    try:
        existing = NotificationRead.query.filter_by(
            user_id=current_user.id, tipo=tipo, ref_id=ref_id
        ).first()
        if not existing:
            nr = NotificationRead()
            nr.user_id = current_user.id
            nr.tipo = tipo
            nr.ref_id = ref_id
            db.session.add(nr)
            db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/search', methods=['GET'])
def global_search():
    if not current_user.is_authenticated:
        return jsonify({'results': []})
    
    q = request.args.get('q', '').strip().lower()
    if len(q) < 2:
        return jsonify({'results': []})
    
    results = []
    
    try:
        produtos = Produto.query.filter(
            (Produto.nome.ilike(f'%{q}%')) | (Produto.codigo.ilike(f'%{q}%'))
        ).limit(5).all()
        for p in produtos:
            results.append({
                'type': 'produto',
                'icon': 'box-seam',
                'title': p.nome,
                'subtitle': f'Código: {p.codigo} | Estoque: {p.quantidade}',
                'url': f'/estoque/editar/{p.id}'
            })
    except Exception:
        pass
    
    try:
        fornecedores = Fornecedor.query.filter(
            Fornecedor.nome.ilike(f'%{q}%')
        ).limit(3).all()
        for f in fornecedores:
            results.append({
                'type': 'fornecedor',
                'icon': 'truck',
                'title': f.nome,
                'subtitle': f.telefone or f.email or '',
                'url': f'/fornecedores/editar/{f.id}'
            })
    except Exception:
        pass
    
    try:
        colaboradores = Collaborator.query.filter(
            Collaborator.name.ilike(f'%{q}%')
        ).limit(3).all()
        for c in colaboradores:
            results.append({
                'type': 'colaborador',
                'icon': 'person',
                'title': c.name,
                'subtitle': c.role or 'Colaborador',
                'url': '/colaboradores/escala'
            })
    except Exception:
        pass
    
    try:
        receitas = Recipe.query.filter(
            Recipe.nome.ilike(f'%{q}%')
        ).limit(3).all()
        for r in receitas:
            results.append({
                'type': 'receita',
                'icon': 'journal-text',
                'title': r.nome,
                'subtitle': 'Receita',
                'url': f'/receitas/{r.id}'
            })
    except Exception:
        pass
    
    pages = [
        {'name': 'Dashboard', 'url': '/home/', 'icon': 'house-door'},
        {'name': 'Estoque', 'url': '/estoque', 'icon': 'box-seam'},
        {'name': 'Cronograma', 'url': '/cronograma/', 'icon': 'calendar-check'},
        {'name': 'Fornecedores', 'url': '/fornecedores/', 'icon': 'truck'},
        {'name': 'Relatórios', 'url': '/relatorios/', 'icon': 'file-earmark-bar-graph'},
        {'name': 'Previsão', 'url': '/previsao/', 'icon': 'graph-up-arrow'},
        {'name': 'Carnes', 'url': '/carnes/', 'icon': 'basket'},
        {'name': 'Receitas', 'url': '/receitas/', 'icon': 'journal-text'},
        {'name': 'Escalas', 'url': '/colaboradores/escala', 'icon': 'people'},
        {'name': 'Gestão', 'url': '/gestao', 'icon': 'gear'},
    ]
    
    for page in pages:
        if q in page['name'].lower():
            results.append({
                'type': 'pagina',
                'icon': page['icon'],
                'title': page['name'],
                'subtitle': 'Ir para página',
                'url': page['url']
            })
    
    return jsonify({'results': results[:12]})
