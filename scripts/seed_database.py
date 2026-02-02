"""
Seed data - Inicializar banco com dados padrão
"""

import os

from flask import Flask
from werkzeug.security import generate_password_hash

from multimax.models import User, WhatsappConfig, db


def seed_database(app: Flask) -> None:
    """
    Inicializa banco com dados padrão
    Executar após alembic upgrade
    """
    with app.app_context():
        print("🌱 Iniciando seed do banco de dados...")

        try:
            # Verificar se já existem dados
            if User.query.first() is not None:
                print("✅ Banco já contém dados, skipping seed.")
                return

            # 1. Criar usuário admin
            print("📝 Criando usuário admin...")
            admin_user = User(
                username="admin",
                email="admin@multimax.local",
                password_hash=generate_password_hash("admin123"),
                role="admin",
                ativo=True,
            )
            db.session.add(admin_user)

            # 2. Criar configuração de telefone de alerta
            print("📞 Criando configuração de telefone de alerta...")
            alert_phone_config = WhatsappConfig(
                chave="alert_phone",
                valor="+55 11 98765-4321",  # Padrão - deve ser alterado
                descricao="Telefone padrão para alertas do sistema",
                ativo=True,
            )
            db.session.add(alert_phone_config)

            # 3. Criar configuração de webhook token
            print("🔐 Criando token webhook...")
            webhook_token_config = WhatsappConfig(
                chave="webhook_token",
                valor="seu_token_webhook_aqui",
                descricao="Token para validar webhooks recebidos",
                ativo=True,
            )
            db.session.add(webhook_token_config)

            # Commit
            db.session.commit()
            print("✅ Seed concluído com sucesso!")
            print("\n📌 IMPORTANTE:")
            print("1. Altere o usuário admin: PUT /api/users/admin com nova senha")
            print("2. Configure o telefone de alerta: PUT /api/settings/alert-phone")
            print("3. Configure o webhook token: PUT /api/settings/webhook-token")

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao fazer seed: {e}")
            raise


if __name__ == "__main__":
    from multimax import create_app

    app = create_app()
    seed_database(app)
