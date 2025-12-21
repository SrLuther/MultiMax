from flask import Blueprint, render_template, request, redirect, url_for, flash
from markupsafe import Markup
from flask_login import login_required, current_user
from .. import db
from ..models import HelpArticle, Suggestion, SuggestionVote, ArticleVote
from datetime import datetime
from zoneinfo import ZoneInfo
import re


def render_markdown(text):
    if not text:
        return ''
    html = text
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'^\- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'^(\d+)\. (.+)$', r'<li>\2</li>', html, flags=re.MULTILINE)
    html = re.sub(r'(<li>.*</li>\n?)+', lambda m: '<ul>' + m.group(0) + '</ul>', html)
    html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)
    paragraphs = []
    for block in html.split('\n\n'):
        block = block.strip()
        if block and not block.startswith('<'):
            block = f'<p>{block}</p>'
        paragraphs.append(block)
    html = '\n'.join(paragraphs)
    html = html.replace('\n', '<br>\n')
    html = html.replace('<br>\n</ul>', '</ul>')
    html = html.replace('<br>\n<li>', '<li>')
    html = html.replace('</li><br>', '</li>')
    return Markup(html)

bp = Blueprint('ajuda', __name__)


def init_default_articles():
    if HelpArticle.query.count() == 0:
        articles = [
            {"categoria": "Início", "titulo": "Bem-vindo ao MultiMax", "ordem": 1, "conteudo": """
# Bem-vindo ao MultiMax

O MultiMax é uma plataforma completa de gestão interna para supermercados, focada especialmente no setor de açougue e câmara fria.

## Principais Funcionalidades

- **Estoque**: Controle completo de produtos, entradas e saídas
- **Cronograma**: Gestão de limpezas e higienização
- **Colaboradores**: Gestão de equipe, escalas e banco de horas
- **Temperatura**: Monitoramento de câmaras frias
- **Receitas**: Cálculo de custos de produção
- **Relatórios**: Exportação e análise de dados

## Primeiros Passos

1. Acesse o sistema com seu usuário e senha
2. Na página inicial, você verá um resumo das principais informações
3. Use o menu lateral para navegar entre as funcionalidades
"""},
            {"categoria": "Estoque", "titulo": "Como adicionar entrada de produtos", "ordem": 2, "conteudo": """
# Como Registrar Entrada de Produtos

## Passo a Passo

1. Clique em **Estoque** no menu lateral
2. Selecione **Entrada de Produtos**
3. Escolha o produto na lista ou busque pelo nome/código
4. Informe a quantidade recebida
5. Preencha a data de validade (se aplicável)
6. Adicione o número do lote
7. Clique em **Confirmar Entrada**

## Dicas

- Sempre verifique a data de validade antes de registrar
- O sistema ordena automaticamente por FIFO (primeiro a entrar, primeiro a sair)
- Produtos próximos do vencimento aparecerão em destaque
"""},
            {"categoria": "Estoque", "titulo": "Como registrar saída de produtos", "ordem": 3, "conteudo": """
# Como Registrar Saída de Produtos

## Passo a Passo

1. Acesse **Estoque** no menu lateral
2. Clique em **Saída de Produtos**
3. Localize o produto desejado
4. Informe a quantidade de saída
5. Selecione o motivo (venda, perda, transferência, etc.)
6. Confirme a operação

## Observações

- O sistema alertará se a quantidade for maior que o estoque disponível
- Saídas por perda são registradas automaticamente no controle de perdas
"""},
            {"categoria": "Temperatura", "titulo": "Como registrar temperatura", "ordem": 4, "conteudo": """
# Registrando Temperatura das Câmaras

## Frequência Recomendada

- Manhã: 1 registro entre 6h e 8h
- Tarde: 1 registro entre 14h e 16h
- Noite: 1 registro entre 20h e 22h

## Passo a Passo

1. Acesse **Temperatura** no menu
2. Clique em **Novo Registro**
3. Selecione o local (Câmara 1, Câmara 2, etc.)
4. Informe a temperatura lida no termômetro
5. Tire uma foto do display (opcional)
6. Adicione observações se necessário
7. Confirme o registro

## Alertas

- O sistema alertará automaticamente se a temperatura estiver fora dos limites
- Limites padrão: -18°C a -12°C para congelados
"""},
            {"categoria": "Colaboradores", "titulo": "Como registrar banco de horas", "ordem": 5, "conteudo": """
# Gerenciando Banco de Horas

## Adicionar Horas Extras

1. Vá em **Gestão** no menu
2. Selecione a aba **Banco de Horas**
3. Clique em **Adicionar Lançamento**
4. Escolha o colaborador
5. Informe a data e quantidade de horas
6. Selecione o tipo (hora extra, compensação, etc.)
7. Confirme

## Regras do Sistema

- A cada 8 horas acumuladas, o sistema converte em 1 dia de folga
- O saldo residual aparece no resumo do colaborador
- Domingos e feriados contam horas em dobro (conforme configuração)
"""},
            {"categoria": "Colaboradores", "titulo": "Como gerenciar escalas", "ordem": 6, "conteudo": """
# Gerenciando Escalas de Trabalho

## Escala Automática

O sistema pode gerar escalas automaticamente baseado em:
- 2 equipes de 3 colaboradores cada
- Rotação semanal entre abertura e fechamento
- Escala especial para domingos

## Escala Manual/Personalizada

1. Acesse **Escala** no menu
2. Navegue até a semana desejada
3. Clique no dia do colaborador
4. Selecione o turno desejado
5. Para remanejamentos, use a opção **Escala Personalizada**

## Turnos Disponíveis

- **Abertura 5h**: 05:00 às 15:00
- **Abertura 6h**: 06:00 às 16:00
- **Fechamento**: 09:30 às 19:30
- **Domingo 5h**: 05:00 às 13:00
- **Domingo 6h**: 06:00 às 13:00
"""},
            {"categoria": "Cronograma", "titulo": "Como concluir tarefas de limpeza", "ordem": 7, "conteudo": """
# Concluindo Tarefas de Limpeza

## Passo a Passo

1. Acesse **Cronograma** no menu
2. Selecione o tipo de limpeza (Parcial, Geral, Expositores, etc.)
3. Localize a tarefa a ser concluída
4. Clique em **Concluir**
5. Preencha:
   - Data de conclusão
   - Observações
   - Responsáveis
   - Checklist de itens (se houver)
   - Fotos de comprovação (opcional)
6. Confirme

## Frequências

- **Semanal**: Caixa de gordura
- **15 dias**: Limpeza parcial da câmara
- **40 dias**: Limpeza geral da câmara
- **Mensal**: Expositores do açougue
"""},
            {"categoria": "Receitas", "titulo": "Como calcular custo de receitas", "ordem": 8, "conteudo": """
# Calculando Custo de Receitas

## Cadastrando uma Receita

1. Acesse **Receitas** no menu
2. Clique em **Nova Receita**
3. Informe o nome e categoria
4. Adicione os ingredientes:
   - Selecione o ingrediente do catálogo
   - Informe a quantidade em kg
   - O sistema busca o custo do estoque automaticamente
5. Informe o rendimento (quantas porções/kg produz)
6. Salve a receita

## Cálculo Automático

O sistema calcula:
- **Custo total** = soma de (quantidade × preço de custo) de cada ingrediente
- **Custo por porção** = custo total ÷ rendimento
"""},
            {"categoria": "Relatórios", "titulo": "Como exportar dados para Excel", "ordem": 9, "conteudo": """
# Exportando Dados para Excel

## Relatórios Disponíveis

- Estoque atual
- Histórico de movimentações
- Registros de temperatura
- Cronograma de limpezas
- Banco de horas

## Como Exportar

1. Acesse **Relatórios** no menu
2. Selecione o tipo de relatório
3. Defina o período (se aplicável)
4. Clique em **Exportar Excel**
5. O arquivo será baixado automaticamente

## Importação

Também é possível importar dados de planilhas Excel:
1. Acesse **Relatórios > Importar**
2. Selecione o arquivo Excel
3. Mapeie as colunas
4. Confirme a importação
"""},
            {"categoria": "Avançado", "titulo": "Gerenciando férias e atestados", "ordem": 10, "conteudo": """
# Férias e Atestados Médicos

## Registrar Férias

1. Acesse **Gestão**
2. Vá na aba **Férias**
3. Clique em **Adicionar Férias**
4. Selecione o colaborador
5. Informe data de início e fim
6. Confirme

## Registrar Atestado Médico

1. Em **Gestão**, vá na aba **Atestados**
2. Clique em **Novo Atestado**
3. Selecione o colaborador
4. Informe período de afastamento
5. Anexe foto do atestado (opcional)
6. Informe CID e médico (opcional)
7. Confirme

O colaborador ficará com status "Afastado" durante o período.
"""},
        ]
        
        for art in articles:
            article = HelpArticle()
            article.titulo = art['titulo']
            article.conteudo = art['conteudo']
            article.categoria = art['categoria']
            article.ordem = art['ordem']
            article.criado_por = 'Sistema'
            db.session.add(article)
        
        db.session.commit()


@bp.route('/ajuda', strict_slashes=False)
@login_required
def ajuda():
    init_default_articles()
    
    categoria = request.args.get('categoria', '')
    busca = request.args.get('busca', '')
    ordenar = request.args.get('ordenar', 'ordem')
    
    query = HelpArticle.query.filter_by(ativo=True)
    
    if categoria:
        query = query.filter_by(categoria=categoria)
    
    if busca:
        query = query.filter(
            db.or_(
                HelpArticle.titulo.ilike(f'%{busca}%'),
                HelpArticle.conteudo.ilike(f'%{busca}%')
            )
        )
    
    if ordenar == 'mais_uteis':
        query = query.order_by(HelpArticle.votos_util.desc().nullslast(), HelpArticle.titulo)
    elif ordenar == 'recentes':
        query = query.order_by(HelpArticle.criado_em.desc().nullslast(), HelpArticle.titulo)
    else:
        query = query.order_by(HelpArticle.ordem, HelpArticle.titulo)
    
    articles = query.all()
    
    categorias = db.session.query(HelpArticle.categoria).filter_by(ativo=True).distinct().all()
    categorias = [c[0] for c in categorias]
    
    sugestoes = Suggestion.query.order_by(Suggestion.votos.desc(), Suggestion.criado_em.desc()).limit(10).all()
    
    user_votes = []
    if current_user.is_authenticated:
        votes = SuggestionVote.query.filter_by(user_id=current_user.id).all()
        user_votes = [v.suggestion_id for v in votes]
    
    return render_template('ajuda.html',
        articles=articles,
        categorias=categorias,
        categoria_atual=categoria,
        busca=busca,
        ordenar=ordenar,
        sugestoes=sugestoes,
        user_votes=user_votes
    )


@bp.route('/ajuda/artigo/<int:id>')
@login_required
def artigo(id):
    article = HelpArticle.query.get_or_404(id)
    conteudo_html = render_markdown(article.conteudo)
    
    user_vote = None
    if current_user.is_authenticated:
        vote = ArticleVote.query.filter_by(article_id=id, user_id=current_user.id).first()
        if vote:
            user_vote = 'util' if vote.util else 'nao_util'
    
    return render_template('ajuda_artigo.html', 
        article=article, 
        conteudo_html=conteudo_html,
        user_vote=user_vote)


@bp.route('/ajuda/artigo/<int:id>/votar', methods=['POST'])
@login_required
def votar_artigo(id):
    article = HelpArticle.query.get_or_404(id)
    util = request.form.get('util') == '1'
    
    existing = ArticleVote.query.filter_by(article_id=id, user_id=current_user.id).first()
    
    if existing:
        if existing.util != util:
            if existing.util:
                article.votos_util = max(0, (article.votos_util or 0) - 1)
                article.votos_nao_util = (article.votos_nao_util or 0) + 1
            else:
                article.votos_nao_util = max(0, (article.votos_nao_util or 0) - 1)
                article.votos_util = (article.votos_util or 0) + 1
            existing.util = util
            existing.voted_at = datetime.now(ZoneInfo('America/Sao_Paulo'))
    else:
        vote = ArticleVote()
        vote.article_id = id
        vote.user_id = current_user.id
        vote.util = util
        db.session.add(vote)
        
        if util:
            article.votos_util = (article.votos_util or 0) + 1
        else:
            article.votos_nao_util = (article.votos_nao_util or 0) + 1
    
    db.session.commit()
    flash('Obrigado pelo seu feedback!', 'success')
    return redirect(url_for('ajuda.artigo', id=id))


@bp.route('/ajuda/novo', methods=['GET', 'POST'])
@login_required
def novo_artigo():
    if current_user.nivel != 'admin':
        flash('Apenas administradores podem criar tutoriais.', 'danger')
        return redirect(url_for('ajuda.ajuda'))
    
    if request.method == 'POST':
        titulo = request.form.get('titulo', '').strip()
        conteudo = request.form.get('conteudo', '').strip()
        categoria = request.form.get('categoria', 'Geral').strip()
        
        if not titulo or not conteudo:
            flash('Título e conteúdo são obrigatórios.', 'danger')
            return redirect(url_for('ajuda.novo_artigo'))
        
        article = HelpArticle()
        article.titulo = titulo
        article.conteudo = conteudo
        article.categoria = categoria
        article.criado_por = current_user.name
        
        db.session.add(article)
        db.session.commit()
        
        flash('Tutorial criado com sucesso!', 'success')
        return redirect(url_for('ajuda.ajuda'))
    
    return render_template('ajuda_form.html', article=None)


@bp.route('/ajuda/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_artigo(id):
    if current_user.nivel != 'admin':
        flash('Apenas administradores podem editar tutoriais.', 'danger')
        return redirect(url_for('ajuda.ajuda'))
    
    article = HelpArticle.query.get_or_404(id)
    
    if request.method == 'POST':
        article.titulo = request.form.get('titulo', '').strip()
        article.conteudo = request.form.get('conteudo', '').strip()
        article.categoria = request.form.get('categoria', 'Geral').strip()
        
        db.session.commit()
        flash('Tutorial atualizado!', 'success')
        return redirect(url_for('ajuda.ajuda'))
    
    return render_template('ajuda_form.html', article=article)


@bp.route('/ajuda/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_artigo(id):
    if current_user.nivel != 'admin':
        flash('Apenas administradores podem excluir tutoriais.', 'danger')
        return redirect(url_for('ajuda.ajuda'))
    
    article = HelpArticle.query.get_or_404(id)
    db.session.delete(article)
    db.session.commit()
    
    flash('Tutorial excluído.', 'success')
    return redirect(url_for('ajuda.ajuda'))


@bp.route('/ajuda/sugestao', methods=['POST'])
@login_required
def nova_sugestao():
    titulo = request.form.get('titulo', '').strip()
    descricao = request.form.get('descricao', '').strip()
    categoria = request.form.get('categoria', 'Melhoria').strip()
    
    if not titulo or not descricao:
        flash('Título e descrição são obrigatórios.', 'danger')
        return redirect(url_for('ajuda.ajuda'))
    
    sugestao = Suggestion()
    sugestao.titulo = titulo
    sugestao.descricao = descricao
    sugestao.categoria = categoria
    sugestao.criado_por = current_user.name
    
    db.session.add(sugestao)
    db.session.commit()
    
    flash('Sugestão enviada com sucesso!', 'success')
    return redirect(url_for('ajuda.ajuda'))


@bp.route('/ajuda/votar/<int:id>', methods=['POST'])
@login_required
def votar_sugestao(id):
    sugestao = Suggestion.query.get_or_404(id)
    
    existing_vote = SuggestionVote.query.filter_by(
        suggestion_id=id,
        user_id=current_user.id
    ).first()
    
    if existing_vote:
        db.session.delete(existing_vote)
        sugestao.votos = max(0, sugestao.votos - 1)
        flash('Voto removido.', 'info')
    else:
        vote = SuggestionVote()
        vote.suggestion_id = id
        vote.user_id = current_user.id
        db.session.add(vote)
        sugestao.votos += 1
        flash('Voto registrado!', 'success')
    
    db.session.commit()
    return redirect(url_for('ajuda.ajuda'))


@bp.route('/ajuda/sugestao/<int:id>/status', methods=['POST'])
@login_required
def atualizar_status_sugestao(id):
    if current_user.nivel != 'admin':
        flash('Apenas administradores podem alterar status.', 'danger')
        return redirect(url_for('ajuda.ajuda'))
    
    sugestao = Suggestion.query.get_or_404(id)
    novo_status = request.form.get('status', 'pendente')
    
    if novo_status in ['pendente', 'em_analise', 'aprovada', 'implementada', 'rejeitada']:
        sugestao.status = novo_status
        db.session.commit()
        flash('Status atualizado!', 'success')
    
    return redirect(url_for('ajuda.ajuda'))
