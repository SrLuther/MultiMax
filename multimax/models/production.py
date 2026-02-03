"""
Modelos para Gestão de Produção, Receitas e Ingredientes
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from . import db


class Produto(db.Model):
    """Modelo para armazenar produtos"""

    __tablename__ = "produto"
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False, index=True)
    nome = db.Column(db.String(100), nullable=False, index=True)
    quantidade = db.Column(db.Integer, default=0, index=True)
    estoque_minimo = db.Column(db.Integer, default=0, index=True)
    preco_custo = db.Column(db.Float, default=0.00)
    preco_venda = db.Column(db.Float, default=0.00)
    data_validade = db.Column(db.Date, nullable=True, index=True)
    lote = db.Column(db.String(50), nullable=True)
    categoria = db.Column(db.String(50), nullable=True, index=True)
    unidade = db.Column(db.String(10), default="un")
    localizacao = db.Column(db.String(50), nullable=True)
    ativo = db.Column(db.Boolean, default=True, index=True)

    historicos = db.relationship("Historico", backref="produto", lazy=True)

    def __repr__(self):
        return f"<Produto {self.nome} - {self.quantidade}>"


class Recipe(db.Model):
    """Modelo para armazenar receitas"""

    __tablename__ = "recipe"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    preparo = db.Column(db.Text)
    embalagem = db.Column(db.String(10))
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    rendimento = db.Column(db.String(50), nullable=True)
    tempo_preparo = db.Column(db.Integer, nullable=True)

    ingredients = db.relationship(
        "RecipeIngredient",
        backref="recipe",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Recipe {self.nome}>"


class RecipeIngredient(db.Model):
    """Modelo para armazenar ingredientes de receitas"""

    __tablename__ = "recipe_ingredient"
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey("recipe.id"))
    produto_id = db.Column(db.Integer, db.ForeignKey("produto.id"), nullable=True)
    nome = db.Column(db.String(100), nullable=False)
    quantidade = db.Column(db.String(50), nullable=True)
    quantidade_kg = db.Column(db.Float, nullable=True)
    custo_unitario = db.Column(db.Float, nullable=True)

    def __repr__(self):
        return f"<RecipeIngredient {self.nome} - {self.quantidade}>"


class IngredientCatalog(db.Model):
    """Modelo para catálogo de ingredientes"""

    __tablename__ = "ingredient_catalog"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)
    categoria = db.Column(db.String(50))
    unidade_padrao = db.Column(db.String(20), default="kg")
    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )

    def __repr__(self):
        return f"<IngredientCatalog {self.nome}>"
